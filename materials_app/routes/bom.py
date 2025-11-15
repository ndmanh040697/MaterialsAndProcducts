
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from .. import db
from ..models import Material, Product, BOMItem
import pandas as pd
import io

bp = Blueprint("bom", __name__, template_folder="../templates")

@bp.route("/")
def bom_list():
    materials = Material.query.order_by(Material.name).all()
    products = Product.query.order_by(Product.name).all()
    bom = BOMItem.query.all()
    # Build a friendly view list
    rows = []
    for bi in bom:
        rows.append({
            "id": bi.id,
            "product": bi.product.name,
            "product_uom": bi.product.uom,
            "material": bi.material.name,
            "material_uom": bi.material.uom,
            "qty_per_unit": bi.qty_per_unit,
            "choice_group": bi.choice_group or ""
        })
    return render_template("bom.html", materials=materials, products=products, rows=rows)

@bp.route("/add", methods=["POST"])
def bom_add():
    product_id = int(request.form["product_id"])
    material_id = int(request.form["material_id"])
    qty_per_unit = float(request.form["qty_per_unit"])
    choice_group = request.form.get("choice_group") or None

    bi = BOMItem(product_id=product_id, material_id=material_id, qty_per_unit=qty_per_unit, choice_group=choice_group)
    db.session.add(bi)
    db.session.commit()
    flash("Đã thêm định mức.", "success")
    return redirect(url_for("bom.bom_list"))

@bp.route("/delete/<int:id>", methods=["POST"])
def bom_delete(id):
    bi = BOMItem.query.get_or_404(id)
    db.session.delete(bi)
    db.session.commit()
    flash("Đã xóa định mức.", "info")
    return redirect(url_for("bom.bom_list"))

@bp.route("/import", methods=["POST"])
def import_bom():
    file = request.files.get("file")
    if not file:
        flash("Chưa chọn file.", "warning")
        return redirect(url_for("bom.bom_list"))
    try:
        df = pd.read_excel(file)
        # Expected columns: product_name, product_uom, material_name, material_uom, qty_per_unit, choice_group
        for _, r in df.iterrows():
            p = Product.query.filter_by(name=str(r["product_name"]).strip()).first()
            if not p:
                p = Product(name=str(r["product_name"]).strip(), uom=str(r["product_uom"]).strip())
                db.session.add(p)
                db.session.flush()
            m = Material.query.filter_by(name=str(r["material_name"]).strip()).first()
            if not m:
                m = Material(name=str(r["material_name"]).strip(), uom=str(r["material_uom"]).strip())
                db.session.add(m)
                db.session.flush()
            qty = float(r["qty_per_unit"])
            cg = str(r["choice_group"]).strip() if not pd.isna(r.get("choice_group")) else None
            db.session.add(BOMItem(product_id=p.id, material_id=m.id, qty_per_unit=qty, choice_group=cg))
        db.session.commit()
        flash("Import BOM thành công!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Lỗi import: {e}", "danger")
    return redirect(url_for("bom.bom_list"))

@bp.route("/sample-template", methods=["GET"])
def sample_template():
    import pandas as pd
    from io import BytesIO

    sample = pd.DataFrame([
        {
            "product_name": "San pham A",
            "product_uom": "cay",
            "material_name": "Giay Tissue",
            "material_uom": "kg",
            "qty_per_unit": 1.0,
            "choice_group": ""
        },
        {
            "product_name": "San pham A",
            "product_uom": "cay",
            "material_name": "Keo dán",
            "material_uom": "kg",
            "qty_per_unit": 0.1,
            "choice_group": ""
        },
        {
            "product_name": "San pham A",
            "product_uom": "cay",
            "material_name": "Loi A",
            "material_uom": "cai",
            "qty_per_unit": 1.0,
            "choice_group": "CORE"
        },
    ])
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        sample.to_excel(writer, index=False, sheet_name="BOM")
    bio.seek(0)
    return send_file(
        bio,
        as_attachment=True,
        download_name="bom_import_template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
