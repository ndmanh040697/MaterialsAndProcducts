
from datetime import datetime
from typing import List, Dict
from flask import current_app
from .models import db, Material, Product, BOMItem, Inventory, MaterialTxn, IssueHeader, IssueLine, get_or_create_inventory
import math
from . import db
from .models import FGInventory, FGTxn

from datetime import datetime
# ...
def upsert_inventory(material_id: int, delta_qty: float, uom: str,
                     note: str = "", ref_type: str = "Manual", ref_id: int = None,
                     ts: datetime | None = None):   # <— thêm ts
    inv = get_or_create_inventory(material_id)
    inv.qty_on_hand = inv.qty_on_hand + delta_qty
    txn = MaterialTxn(
        ts = ts or datetime.utcnow(),   # <— dùng ts nếu có, mặc định UTC hiện tại
        material_id = material_id,
        qty_in = max(delta_qty, 0),
        qty_out = abs(min(delta_qty, 0)),
        uom = uom,
        note = note,
        ref_type = ref_type,
        ref_id = ref_id
    )
    db.session.add(txn)
    db.session.commit()
    return inv.qty_on_hand


def calc_materials_for_product(product_id: int, product_qty: float, selected_material_ids: List[int] = None) -> List[Dict]:
    """
    Compute required materials for a given product and quantity, respecting choice_group selections.
    If selected_material_ids is provided, only include BOM items that are either:
      - no choice_group (required), or
      - in choice_group and material_id is selected in that group
    """
    q = BOMItem.query.filter_by(product_id=product_id, is_active=True).all()
    results = []
    # Determine chosen items for groups
    groups = {}
    for item in q:
        if item.choice_group:
            groups.setdefault(item.choice_group, []).append(item)
    selected = set(selected_material_ids or [])

    for item in q:
        # Required items (no group) are always included
        if not item.choice_group:
            results.append({
                "product_id": product_id,
                "material_id": item.material_id,
                "material_name": item.material.name,
                "uom": item.material.uom,
                "qty": item.qty_per_unit * product_qty
            })
        else:
            # only include if this material was chosen in its group
            if item.material_id in selected:
                results.append({
                    "product_id": product_id,
                    "material_id": item.material_id,
                    "material_name": item.material.name,
                    "uom": item.material.uom,
                    "qty": item.qty_per_unit * product_qty
                })
    return results

def create_issue(plan_date, created_by, lines_payload: List[Dict]):
    """
    lines_payload: list of dicts with keys: product_id, material_id, product_qty, qty, uom
    Creates IssueHeader + IssueLines and posts out transactions to inventory.
    """
    header = IssueHeader(plan_date=plan_date, created_by=created_by)
    db.session.add(header)
    db.session.flush()  # get header.id

    for ln in lines_payload:
        line = IssueLine(
            header_id=header.id,
            product_id=ln["product_id"],
            material_id=ln["material_id"],
            product_qty=ln["product_qty"],
            qty=ln["qty"],
            uom=ln["uom"]
        )
        db.session.add(line)

    db.session.commit()

    # Post inventory movements
    for ln in header.lines:
        upsert_inventory(
            material_id=ln.material_id,
            delta_qty=-ln.qty,
            uom=ln.uom,
            note=f"Issue #{header.id} for product {ln.product.name}",
            ref_type="Issue",
            ref_id=header.id
        )
    return header.id

def units_producible_from_inventory(material_id: int, qty_per_unit: float) -> int:
    inv = Inventory.query.get(material_id)
    if not inv or qty_per_unit <= 0:
        return 0
    return math.floor(inv.qty_on_hand / qty_per_unit)

def get_or_create_fg_inventory(product_id: int) -> FGInventory:
    inv = FGInventory.query.filter_by(product_id=product_id).first()
    if not inv:
        inv = FGInventory(product_id=product_id, qty_on_hand=0.0)
        db.session.add(inv)
        db.session.flush()
    return inv

def upsert_fg_inventory(product_id: int, delta: float, uom: str, *, note="", ref_type="Manual", ref_id=None, ts=None):
    """
    delta > 0: nhập; delta < 0: xuất
    """
    now = datetime.utcnow()
    inv = get_or_create_fg_inventory(product_id)
    inv.qty_on_hand = (inv.qty_on_hand or 0.0) + (delta or 0.0)

    qty_in  = delta if (delta or 0) > 0 else 0.0
    qty_out = -delta if (delta or 0) < 0 else 0.0

    txn = FGTxn(
        ts = ts or now,
        entry_ts = now,
        product_id = product_id,
        qty_in = qty_in, qty_out = qty_out,
        uom = uom, note = note,
        ref_type = ref_type, ref_id = ref_id
    )
    db.session.add(txn)
    db.session.commit()
    return txn