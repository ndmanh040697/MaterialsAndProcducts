
from materials_app import create_app, db
from materials_app.models import Material, Product, BOMItem, Inventory

app = create_app()
with app.app_context():
    db.create_all()
    # Sample data
    pA = Product(name="San pham A", uom="cay")
    pB = Product(name="San pham B", uom="cay")
    db.session.add_all([pA, pB])
    db.session.flush()

    m1 = Material(name="Giay Tissue", uom="kg")
    m2 = Material(name="Keo dán", uom="kg")
    m3 = Material(name="Loi A", uom="cai")
    m4 = Material(name="Loi B", uom="cai")
    db.session.add_all([m1, m2, m3, m4])
    db.session.flush()

    db.session.add_all([
        BOMItem(product_id=pA.id, material_id=m1.id, qty_per_unit=1.0),
        BOMItem(product_id=pA.id, material_id=m2.id, qty_per_unit=0.1),
        BOMItem(product_id=pA.id, material_id=m3.id, qty_per_unit=1.0, choice_group="CORE"),
        BOMItem(product_id=pA.id, material_id=m4.id, qty_per_unit=1.0, choice_group="CORE"),
        BOMItem(product_id=pB.id, material_id=m1.id, qty_per_unit=0.5),
    ])

    db.session.add_all([
        Inventory(material_id=m1.id, qty_on_hand=10),
        Inventory(material_id=m2.id, qty_on_hand=2),
        Inventory(material_id=m3.id, qty_on_hand=100),
        Inventory(material_id=m4.id, qty_on_hand=50),
    ])
    db.session.commit()
    print("Seeded!")
