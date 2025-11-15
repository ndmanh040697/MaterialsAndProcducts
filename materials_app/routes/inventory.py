
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from .. import db
from ..models import Material, Inventory, MaterialTxn, get_or_create_inventory
from ..services import upsert_inventory
import pandas as pd
from datetime import datetime, date
from ..utils import parse_any_date
from ..models import db, Material, Inventory, MaterialTxn, MaterialTxnAudit
from datetime import datetime, timedelta
import json
from sqlalchemy import func

bp = Blueprint("inventory", __name__, template_folder="../templates")

@bp.route("/")
def inv_page():



    # tồn kho + danh sách NVL
    inv_rows = db.session.query(Inventory).join(Material).order_by(Material.name).all()
    materials = Material.query.order_by(Material.name).all()

    # ---- filters (querystring) ----
    material_id = request.args.get("f_material_id", type=int)  # id NVL
    date_from = request.args.get("f_date_from", default="")    # dd/mm/yy
    date_to   = request.args.get("f_date_to", default="")      # dd/mm/yy
    ref_type  = request.args.get("f_ref_type", default="")     # Manual/Issue/...

    q = db.session.query(MaterialTxn).join(Material).order_by(MaterialTxn.ts.desc())

    # parse ngày dd/mm/yy
    def parse_d(s):
        try:
            return datetime.strptime(s, "%d/%m/%y")
        except Exception:
            return None

    dt_from = parse_d(date_from)
    dt_to_raw = parse_d(date_to)

    if dt_from:
        q = q.filter(MaterialTxn.ts >= dt_from)
    if dt_to_raw:
        q = q.filter(MaterialTxn.ts < (dt_to_raw + timedelta(days=1)))  # inclusive
    if material_id:
        q = q.filter(MaterialTxn.material_id == material_id)
    if ref_type:
        q = q.filter(MaterialTxn.ref_type == ref_type)

    txns = q.limit(500).all()  # lấy 500 dòng gần nhất

    return render_template(
        "inventory.html",
        inventory=inv_rows,
        materials=materials,
        txns=txns,
        f_material_id=material_id or 0,
        f_date_from=date_from,
        f_date_to=date_to,
        f_ref_type=ref_type
    )


@bp.route("/import", methods=["POST"])
def import_inventory():
    file = request.files.get("file")
    if not file:
        flash("Chưa chọn file.", "warning")
        return redirect(url_for("inventory.inv_page"))
    try:
        df = pd.read_excel(file)
        # Expected columns: material_name, uom, qty_on_hand
        for _, r in df.iterrows():
            name = str(r["material_name"]).strip()
            uom = str(r["uom"]).strip()
            qty = float(r["qty_on_hand"])
            m = Material.query.filter_by(name=name).first()
            if not m:
                m = Material(name=name, uom=uom)
                db.session.add(m)
                db.session.flush()
            inv = get_or_create_inventory(m.id)
            inv.qty_on_hand = qty
        db.session.commit()
        flash("Import tồn kho thành công!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Lỗi import: {e}", "danger")
    return redirect(url_for("inventory.inv_page"))


@bp.route("/adjust", methods=["POST"])
def adjust():
    dates = request.form.getlist("date[]")
    material_ids = request.form.getlist("material_id[]")
    qty_ins = request.form.getlist("qty_in[]")
    qty_outs = request.form.getlist("qty_out[]")
    notes = request.form.getlist("note[]")

    count = 0
    for date_str, mid, qin, qout, note in zip(dates, material_ids, qty_ins, qty_outs, notes):
        if not mid:
            continue
        m = Material.query.get(int(mid))
        if not m:
            continue

        try:
            d = parse_any_date(date_str)
            ts_override = datetime.combine(d, datetime.now().time()) if d else datetime.now()
        except:
            ts_override = datetime.now()

        delta = float(qin or 0) - float(qout or 0)
        upsert_inventory(int(mid), delta, m.uom, note=note, ref_type="Manual", ts=ts_override)
        count += 1

    if count:
        db.session.commit()
        flash(f"Đã ghi nhận {count} dòng xuất/nhập NVL.", "success")
    else:
        flash("Không có dòng hợp lệ để ghi nhận.", "warning")
    return redirect(url_for("inventory.inv_page"))

#xuất file mẫu
@bp.route("/sample-template", methods=["GET"], endpoint="sample_template")
def export_inventory_template():
    import pandas as pd
    from io import BytesIO

    sample = pd.DataFrame([
        {"material_name": "Giay Tissue", "uom": "kg", "qty_on_hand": 10},
        {"material_name": "Keo dán",    "uom": "kg", "qty_on_hand": 2},
        {"material_name": "Loi A",      "uom": "cai","qty_on_hand": 100},
    ])
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        sample.to_excel(writer, index=False, sheet_name="Inventory")
    bio.seek(0)
    return send_file(
        bio,
        as_attachment=True,
        download_name="inventory_import_template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

@bp.route("/logs/export")
def export_logs():
    from ..models import MaterialTxn
    from datetime import datetime, timedelta
    import pandas as pd
    from io import BytesIO

    material_id = request.args.get("f_material_id", type=int)
    date_from = request.args.get("f_date_from", default="")
    date_to   = request.args.get("f_date_to", default="")
    ref_type  = request.args.get("f_ref_type", default="")

    q = db.session.query(MaterialTxn).join(Material).order_by(MaterialTxn.ts.desc())

    def parse_d(s):
        try:
            return datetime.strptime(s, "%d/%m/%y")
        except Exception:
            return None

    dt_from = parse_d(date_from)
    dt_to_raw = parse_d(date_to)
    if dt_from:
        q = q.filter(MaterialTxn.ts >= dt_from)
    if dt_to_raw:
        q = q.filter(MaterialTxn.ts < (dt_to_raw + timedelta(days=1)))
    if material_id:
        q = q.filter(MaterialTxn.material_id == material_id)
    if ref_type:
        q = q.filter(MaterialTxn.ref_type == ref_type)

    rows = q.all()
    data = [{
        "time_utc": t.ts.strftime("%Y-%m-%d %H:%M:%S"),
        "material": t.material.name,
        "uom": t.uom,
        "qty_in": t.qty_in,
        "qty_out": t.qty_out,
        "note": t.note or "",
        "ref_type": t.ref_type or "",
        "ref_id": t.ref_id or "",
    } for t in rows]

    bio = BytesIO()
    df = pd.DataFrame(data)
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Logs")
    bio.seek(0)
    return send_file(
        bio, as_attachment=True,
        download_name="material_txn_logs.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
def _serialize_txn(txn):
    return {
        "id": txn.id,
        "ts": txn.ts.strftime("%Y-%m-%d") if txn.ts else None,
        "material_id": txn.material_id,
        "qty_in": float(txn.qty_in or 0),
        "qty_out": float(txn.qty_out or 0),
        "uom": txn.uom,
        "note": txn.note or "",
        "ref_type": txn.ref_type or "",
        "ref_id": txn.ref_id or "",
    }

def _get_or_create_inventory(mid: int):
    inv = Inventory.query.filter_by(material_id=mid).first()
    if not inv:
        inv = Inventory(material_id=mid, qty_on_hand=0.0)
        db.session.add(inv); db.session.flush()
    return inv

@bp.route("/logs/apply", methods=["POST"])
def apply_log_changes():
    """
    Payload JSON:
    {
      "edits":[{"id":..,"ts":"YYYY-MM-DD","qty_in":..,"qty_out":..,"uom":"..","note":".."}],
      "deletes":[txn_id1, txn_id2, ...]
    }
    """
    data = request.get_json(force=True) or {}
    edits = data.get("edits") or []
    deletes = data.get("deletes") or []

    now = datetime.utcnow()
    try:
        with db.session.begin():
            # 1) Xử lý xoá (điều chỉnh tồn theo -delta)
            for tid in deletes:
                txn = MaterialTxn.query.get(int(tid))
                if not txn: 
                    continue
                old = _serialize_txn(txn)
                delta = (txn.qty_in or 0) - (txn.qty_out or 0)
                inv = _get_or_create_inventory(txn.material_id)
                inv.qty_on_hand = (inv.qty_on_hand or 0) - delta

                db.session.add(MaterialTxnAudit(
                    txn_id=txn.id, material_id=txn.material_id, action="delete",
                    changed_fields="*", old_json=json.dumps(old, ensure_ascii=False),
                    new_json=json.dumps({}, ensure_ascii=False), editor_ts=now
                ))
                db.session.delete(txn)

            # 2) Xử lý sửa (điều chỉnh tồn theo (new_delta - old_delta))
            for e in edits:
                txn = MaterialTxn.query.get(int(e["id"]))
                if not txn: 
                    continue
                old = _serialize_txn(txn)

                # giá trị mới
                new_ts = parse_any_date(e.get("ts")) or txn.ts.date() if txn.ts else date.today()
                new_qty_in  = float(e.get("qty_in")  or 0)
                new_qty_out = float(e.get("qty_out") or 0)
                new_uom  = e.get("uom") or txn.uom
                new_note = e.get("note") or txn.note

                old_delta = (txn.qty_in or 0) - (txn.qty_out or 0)
                new_delta = new_qty_in - new_qty_out
                diff = new_delta - old_delta

                inv = _get_or_create_inventory(txn.material_id)
                inv.qty_on_hand = (inv.qty_on_hand or 0) + diff

                # áp giá trị mới vào txn (giữ entry_ts cũ)
                txn.ts = datetime.combine(new_ts, datetime.min.time())
                txn.qty_in = new_qty_in
                txn.qty_out = new_qty_out
                txn.uom = new_uom
                txn.note = new_note

                # ghi audit: những trường đã đổi
                changed = []
                if old["ts"] != e.get("ts"):       changed.append("ts")
                if float(old["qty_in"]) != new_qty_in:    changed.append("qty_in")
                if float(old["qty_out"]) != new_qty_out:  changed.append("qty_out")
                if (old["uom"] or "") != (new_uom or ""): changed.append("uom")
                if (old["note"] or "") != (new_note or ""): changed.append("note")

                db.session.add(MaterialTxnAudit(
                    txn_id=txn.id, material_id=txn.material_id, action="edit",
                    changed_fields=", ".join(changed) or "(none)",
                    old_json=json.dumps(old, ensure_ascii=False),
                    new_json=json.dumps(_serialize_txn(txn), ensure_ascii=False),
                    editor_ts=now
                ))
        return jsonify({"ok": True})
    except Exception as ex:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(ex)}), 400

