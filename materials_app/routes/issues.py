
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from datetime import datetime
from .. import db
from ..models import Product, Material, BOMItem, Inventory
from ..services import calc_materials_for_product, create_issue
import pandas as pd

bp = Blueprint("issues", __name__, template_folder="../templates")

@bp.route("/")
def issues_page():
    products = Product.query.order_by(Product.name).all()
    products_payload = [{"id": p.id, "name": p.name, "uom": p.uom} for p in products]
    return render_template("issues.html", products=products_payload)

@bp.route("/calc", methods=["POST"])
def calc_issue():
    data = request.get_json()
    plan_date = datetime.strptime(data.get("plan_date"), "%d/%m/%y").date()
    items = data.get("items", [])  # list of {product_id, product_qty, selected_material_ids: []}
    results = []
    for it in items:
        res = calc_materials_for_product(
            product_id=int(it["product_id"]),
            product_qty=float(it["product_qty"]),
            selected_material_ids=[int(x) for x in it.get("selected_material_ids", [])]
        )
        # attach product info
        for r in res:
            r["product_name"] = next(p.name for p in Product.query.filter_by(id=r["product_id"]))
            results.append(r)
    return jsonify({"lines": results})

@bp.route("/commit", methods=["POST"])
def commit_issue():
    data = request.get_json()
    plan_date = datetime.strptime(data.get("plan_date"), "%d/%m/%y").date()
    created_by = data.get("created_by", "user")
    lines = data.get("lines", [])  # list of dicts: product_id, material_id, product_qty, qty, uom
    issue_id = create_issue(plan_date, created_by, lines)
    return jsonify({"issue_id": issue_id})

@bp.route("/import-products", methods=["POST"])
def import_products_list():
    # Excel import for type-2 flow: columns: product_name, qty, selected_material_names (optional, comma separated)
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file"}), 400
    df = pd.read_excel(file)
    items = []
    for _, r in df.iterrows():
        p = Product.query.filter_by(name=str(r["product_name"]).strip()).first()
        if not p:
            return jsonify({"error": f"Product not found: {r['product_name']}"}), 400
        sel_names = str(r.get("selected_material_names") or "").strip()
        selected_ids = []
        if sel_names:
            for nm in sel_names.split(","):
                nm = nm.strip()
                m = Material.query.filter_by(name=nm).first()
                if m:
                    selected_ids.append(m.id)
        items.append({"product_id": p.id, "product_qty": float(r["qty"]), "selected_material_ids": selected_ids})
    return jsonify({"items": items})

@bp.route("/sample-template", methods=["GET"])
def sample_template():
    import pandas as pd
    from io import BytesIO

    sample = pd.DataFrame([
        {"product_name": "San pham A", "qty": 100, "selected_material_names": "Loi A"},
        {"product_name": "San pham B", "qty": 50, "selected_material_names": ""},
    ])
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        sample.to_excel(writer, index=False, sheet_name="Issues")
    bio.seek(0)
    return send_file(
        bio,
        as_attachment=True,
        download_name="issues_import_template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
