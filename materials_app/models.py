
from datetime import datetime
from . import db


# --- Core master data ---
class Material(db.Model):
    __tablename__ = "materials"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    uom = db.Column(db.String(32), nullable=False)
    reorder_point = db.Column(db.Float, default=0.0)  # optional alert point

    def __repr__(self):
        return f"<Material {self.name}>"

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    uom = db.Column(db.String(32), nullable=False)

    def __repr__(self):
        return f"<Product {self.name}>"

# --- BOM: Bill of Materials / Định mức ---
class BOMItem(db.Model):
    __tablename__ = "bom_items"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    qty_per_unit = db.Column(db.Float, nullable=False)  # định mức NVL cho 1 đơn vị SP
    # choice_group: các NVL thuộc cùng group là lựa chọn thay thế (chọn 1 trong nhiều)
    choice_group = db.Column(db.String(64), nullable=True)  # ví dụ: "CORE" => lõi A hoặc lõi B
    is_active = db.Column(db.Boolean, default=True)

    product = db.relationship("Product", backref=db.backref("bom_items", lazy="dynamic"))
    material = db.relationship("Material")

    def __repr__(self):
        return f"<BOMItem P{self.product_id} M{self.material_id} qty {self.qty_per_unit} group {self.choice_group}>"

# --- Inventory (current qty) ---
class Inventory(db.Model):
    __tablename__ = "inventory"
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), primary_key=True)
    qty_on_hand = db.Column(db.Float, default=0.0, nullable=False)

    material = db.relationship("Material")

# --- Transaction log for stock movements ---

class MaterialTxn(db.Model):
    __tablename__ = "material_txns"
    id = db.Column(db.Integer, primary_key=True)
    ts = db.Column(db.DateTime, nullable=False, index=True)     # ngày thực tế (dùng để lọc, hiển thị)
    entry_ts = db.Column(db.DateTime, nullable=False,           # thời điểm nhập liệu
                         default=datetime.utcnow, index=True)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    qty_in = db.Column(db.Float, default=0)
    qty_out = db.Column(db.Float, default=0)
    uom = db.Column(db.String(32))
    note = db.Column(db.String(255))
    ref_type = db.Column(db.String(32))
    ref_id = db.Column(db.String(64))

    material = db.relationship("Material", backref="txns")


# --- Issue materials for work orders (page 3) ---
class IssueHeader(db.Model):
    __tablename__ = "issue_headers"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    plan_date = db.Column(db.Date)  # ngày nhập của user
    created_by = db.Column(db.String(80))

class IssueLine(db.Model):
    __tablename__ = "issue_lines"
    id = db.Column(db.Integer, primary_key=True)
    header_id = db.Column(db.Integer, db.ForeignKey("issue_headers.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    product_qty = db.Column(db.Float, nullable=False)   # số lượng SP cần SX cho dòng này
    qty = db.Column(db.Float, nullable=False)           # số lượng NVL xuất (đã tính từ BOM * product_qty, user có thể sửa)
    uom = db.Column(db.String(32), nullable=False)

    header = db.relationship("IssueHeader", backref=db.backref("lines", lazy="dynamic"))
    product = db.relationship("Product")
    material = db.relationship("Material")

# Convenience helpers
def get_or_create_inventory(material_id: int):
    inv = Inventory.query.get(material_id)
    if not inv:
        inv = Inventory(material_id=material_id, qty_on_hand=0.0)
        db.session.add(inv)
    return inv

class MaterialTxnAudit(db.Model):
    __tablename__ = "material_txn_audits"

    id = db.Column(db.Integer, primary_key=True)
    txn_id = db.Column(db.Integer, nullable=True)            # id của dòng nhật ký cũ (có thể None nếu đã xóa)
    material_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(10), nullable=False)        # 'edit' hoặc 'delete'
    changed_fields = db.Column(db.String(255), nullable=True)
    old_json = db.Column(db.Text, nullable=True)
    new_json = db.Column(db.Text, nullable=True)
    editor_ts = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<MaterialTxnAudit id={self.id} action={self.action} material_id={self.material_id}>"
    
class FGInventory(db.Model):
    __tablename__ = "fg_inventories"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), unique=True, nullable=False, index=True)
    qty_on_hand = db.Column(db.Float, default=0.0, nullable=False)

    product = db.relationship("Product")

class FGTxn(db.Model):
    __tablename__ = "fg_txns"
    id = db.Column(db.Integer, primary_key=True)
    ts = db.Column(db.DateTime, nullable=False, index=True)         # ngày thực tế
    entry_ts = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)  # nhập liệu lúc
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    qty_in  = db.Column(db.Float, default=0.0)
    qty_out = db.Column(db.Float, default=0.0)
    uom  = db.Column(db.String(32))
    note = db.Column(db.String(255))
    ref_type = db.Column(db.String(32))
    ref_id   = db.Column(db.String(64))

    product = db.relationship("Product")

class FGTxnAudit(db.Model):
    __tablename__ = "fg_txn_audits"
    id = db.Column(db.Integer, primary_key=True)
    txn_id = db.Column(db.Integer)                                   # id dòng cũ (sau khi xóa có thể None)
    product_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(10), nullable=False)                # 'edit' | 'delete'
    changed_fields = db.Column(db.String(255))
    old_json = db.Column(db.Text)
    new_json = db.Column(db.Text)
    editor_ts = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)    