from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from .. import db
from ..models import Product, FGInventory, FGTxn, FGTxnAudit
from ..services import upsert_fg_inventory, get_or_create_fg_inventory
from ..utils import parse_any_date
import pandas as pd
from datetime import datetime, date, timedelta
from io import BytesIO
import json

bp = Blueprint("fg", __name__, template_folder="../templates")

@bp.route("/")
def fg_page():
    inv_rows = db.session.query(FGInventory).join(Product).order_by(Product.name).all()
    products = Product.query.order_by(Product.name).all()

    # filters
    product_id = request.args.get("f_product_id", type=int)
    date_from = request.args.get("f_date_from", default="")
    date_to   = request.args.get("f_date_to", default="")
    ref_type  = request.args.get("f_ref_type", default="")

    q = db.session.query(FGTxn).join(Product).order_by(FGTxn.ts.desc())
    

    def parse_d(s):
        try: return datetime.strptime(s, "%d/%m/%y")
        except: return None

    dt_from = parse_d(date_from)
    dt_to_raw = parse_d(date_to)
    if dt_from:   q = q.filter(FGTxn.ts >= dt_from)
    if dt_to_raw: q = q.filter(FGTxn.ts < (dt_to_raw + timedelta(days=1)))
    if product_id: q = q.filter(FGTxn.product_id == product_id)
    if ref_type:   q = q.filter(FGTxn.ref_type == ref_type)

    txns = q.limit(500).all()
    print(">>> Rendering fg_inventory.html")
    return render_template(
        "fg_inventory.html",
        inventory=inv_rows,
        products=products,
        txns=txns,
        f_product_id=product_id or 0,
        f_date_from=date_from,
        f_date_to=date_to,
        f_ref_type=ref_type
    )

@bp.route("/import", methods=["POST"])
def import_fg_inventory():
    file = request.files.get("file")
    if not file:
        flash("Chưa chọn file.", "warning")
        return redirect(url_for("fg.fg_page"))
    try:
        df = pd.read_excel(file)
        # columns: product_name, uom, qty_on_hand
        for _, r in df.iterrows():
            name = str(r["product_name"]).strip()
            uom  = str(r["uom"]).strip()
            qty  = float(r["qty_on_hand"])
            p = Product.query.filter_by(name=name).first()
            if not p:
                p = Product(name=name, uom=uom)
                db.session.add(p); db.session.flush()
            else:
                # cập nhật uom nếu file có (tránh ghi None)
                if uom: p.uom = uom
            inv = get_or_create_fg_inventory(p.id)
            inv.qty_on_hand = qty
        db.session.commit()
        flash("Import tồn kho thành phẩm thành công!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Lỗi import: {e}", "danger")
    return redirect(url_for("fg.fg_page"))

@bp.route("/adjust", methods=["POST"])
def fg_adjust():
    dates = request.form.getlist("date[]")
    product_ids = request.form.getlist("product_id[]")
    qty_ins = request.form.getlist("qty_in[]")
    qty_outs = request.form.getlist("qty_out[]")
    notes = request.form.getlist("note[]")

    count = 0
    for date_str, pid, qin, qout, note in zip(dates, product_ids, qty_ins, qty_outs, notes):
        if not pid:
            continue
        p = Product.query.get(int(pid))
        if not p:
            continue
        try:
            d = parse_any_date(date_str)
            ts_override = datetime.combine(d, datetime.now().time()) if d else datetime.now()
        except:
            ts_override = datetime.now()

        delta = float(qin or 0) - float(qout or 0)
        upsert_fg_inventory(int(pid), delta, p.uom, note=note, ref_type="Manual", ts=ts_override)
        count += 1

    if count:
        db.session.commit()
        flash(f"Đã ghi nhận {count} dòng xuất/nhập thành phẩm.", "success")
    else:
        flash("Không có dòng hợp lệ để ghi nhận.", "warning")
    return redirect(url_for("fg.fg_page"))


@bp.route("/sample-template")
def fg_sample_template():
    sample = pd.DataFrame([
        {"product_name":"TP A", "uom":"cây", "qty_on_hand":100},
        {"product_name":"TP B", "uom":"thùng","qty_on_hand":20},
    ])
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as w:
        sample.to_excel(w, index=False, sheet_name="FG")
    bio.seek(0)
    return send_file(bio, as_attachment=True,
        download_name="fg_inventory_import_template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@bp.route("/logs/export")
def fg_export_logs():
    product_id = request.args.get("f_product_id", type=int)
    date_from  = request.args.get("f_date_from", default="")
    date_to    = request.args.get("f_date_to", default="")
    ref_type   = request.args.get("f_ref_type", default="")
    q = db.session.query(FGTxn).join(Product).order_by(FGTxn.ts.desc())

    def parse_d(s):
        try: return datetime.strptime(s, "%d/%m/%y")
        except: return None
    dt_from = parse_d(date_from)
    dt_to_raw = parse_d(date_to)
    if dt_from:   q = q.filter(FGTxn.ts >= dt_from)
    if dt_to_raw: q = q.filter(FGTxn.ts < (dt_to_raw + timedelta(days=1)))
    if product_id: q = q.filter(FGTxn.product_id == product_id)
    if ref_type:   q = q.filter(FGTxn.ref_type == ref_type)

    rows = q.all()
    data = [{
        "time_utc": t.ts.strftime("%Y-%m-%d %H:%M:%S"),
        "product": t.product.name,
        "uom": t.uom,
        "qty_in": t.qty_in,
        "qty_out": t.qty_out,
        "note": t.note or "",
        "ref_type": t.ref_type or "",
        "ref_id": t.ref_id or "",
        "entry_ts": t.entry_ts.strftime("%Y-%m-%d %H:%M")
    } for t in rows]
    df = pd.DataFrame(data)
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Logs")
    bio.seek(0)
    return send_file(bio, as_attachment=True,
        download_name="fg_txn_logs.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def _serialize_txn(txn):
    return {
        "id": txn.id,
        "ts": txn.ts.strftime("%Y-%m-%d") if txn.ts else None,
        "product_id": txn.product_id,
        "qty_in": float(txn.qty_in or 0),
        "qty_out": float(txn.qty_out or 0),
        "uom": txn.uom,
        "note": txn.note or "",
        "ref_type": txn.ref_type or "",
        "ref_id": txn.ref_id or "",
    }

@bp.route("/logs/apply", methods=["POST"])
def fg_apply_log_changes():
    data = request.get_json(force=True) or {}
    edits = data.get("edits") or []
    deletes = data.get("deletes") or []
    now = datetime.utcnow()
    try:
        with db.session.begin():
            # delete
            for tid in deletes:
                txn = FGTxn.query.get(int(tid))
                if not txn: 
                    continue
                old = _serialize_txn(txn)
                delta = (txn.qty_in or 0) - (txn.qty_out or 0)
                inv = get_or_create_fg_inventory(txn.product_id)
                inv.qty_on_hand = (inv.qty_on_hand or 0) - delta
                db.session.add(FGTxnAudit(
                    txn_id=txn.id, product_id=txn.product_id, action="delete",
                    changed_fields="*", old_json=json.dumps(old, ensure_ascii=False),
                    new_json=json.dumps({}, ensure_ascii=False), editor_ts=now
                ))
                db.session.delete(txn)

            # edit
            for e in edits:
                txn = FGTxn.query.get(int(e["id"]))
                if not txn: 
                    continue
                old = _serialize_txn(txn)

                new_ts = parse_any_date(e.get("ts")) or txn.ts.date() if txn.ts else date.today()
                new_qty_in  = float(e.get("qty_in")  or 0)
                new_qty_out = float(e.get("qty_out") or 0)
                new_uom  = e.get("uom") or txn.uom
                new_note = e.get("note") or txn.note

                old_delta = (txn.qty_in or 0) - (txn.qty_out or 0)
                new_delta = new_qty_in - new_qty_out
                diff = new_delta - old_delta

                inv = get_or_create_fg_inventory(txn.product_id)
                inv.qty_on_hand = (inv.qty_on_hand or 0) + diff

                txn.ts = datetime.combine(new_ts, datetime.min.time())
                txn.qty_in = new_qty_in
                txn.qty_out = new_qty_out
                txn.uom = new_uom
                txn.note = new_note

                changed = []
                if old["ts"] != e.get("ts"):              changed.append("ts")
                if float(old["qty_in"]) != new_qty_in:    changed.append("qty_in")
                if float(old["qty_out"]) != new_qty_out:  changed.append("qty_out")
                if (old["uom"] or "") != (new_uom or ""): changed.append("uom")
                if (old["note"] or "") != (new_note or ""): changed.append("note")

                db.session.add(FGTxnAudit(
                    txn_id=txn.id, product_id=txn.product_id, action="edit",
                    changed_fields=", ".join(changed) or "(none)",
                    old_json=json.dumps(old, ensure_ascii=False),
                    new_json=json.dumps(_serialize_txn(txn), ensure_ascii=False),
                    editor_ts=now
                ))
        return jsonify({"ok": True})
    except Exception as ex:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(ex)}), 400
