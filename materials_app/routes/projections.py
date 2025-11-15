from flask import Blueprint, render_template
from sqlalchemy import func
from ..models import db, Material, Inventory

bp = Blueprint("projections", __name__, template_folder="../templates")

@bp.route("/")
def projection_page():
    THRESHOLD = 5000  # Cảnh báo nếu tồn < 1000 (đơn vị NVL)

    # LEFT JOIN materials -> inventory, dùng COALESCE để hết None
    rows_db = (
        db.session.query(
            Material.id,
            Material.name,
            Material.uom,
            func.coalesce(Inventory.qty_on_hand, 0.0).label("qty_on_hand"),
        )
        .outerjoin(Inventory, Inventory.material_id == Material.id)
        .order_by(Material.name)
        .all()
    )

    rows = []
    for mid, name, uom, qty in rows_db:
        inv_qty = float(qty or 0.0)
        rows.append({
            "material": name,
            "uom": uom or "",             # dùng key 'uom'
            "material_uom": uom or "",    # thêm key 'material_uom' cho template cũ
            "inventory": inv_qty,
            "alert": inv_qty < THRESHOLD,
        })

    return render_template("projections.html", rows=rows, threshold=THRESHOLD)
