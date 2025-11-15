# scripts/stamp_head.py
import os, sys, glob, re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from materials_app import create_app, db

def log(*a): print("[stamp]", *a)

def find_head():
    versions_glob = os.path.join(os.path.dirname(__file__), "..", "migrations", "versions", "*.py")
    files = sorted(glob.glob(versions_glob), key=os.path.getmtime, reverse=True)
    log("versions dir:", os.path.abspath(os.path.dirname(versions_glob)))
    log("found files:", [os.path.basename(f) for f in files])
    if not files:
        raise SystemExit("❌ Không thấy file revision. Hãy tạo baseline: "
                         "flask --app materials_app:create_app db init && "
                         "flask --app materials_app:create_app db revision -m \"baseline\"")
    with open(files[0], "r", encoding="utf-8") as f:
        m = re.search(r'revision\s*=\s*[\'"]([0-9a-f]+)[\'"]', f.read())
        if not m:
            raise SystemExit("❌ Không parse được revision.")
        return m.group(1)

def main():
    app = create_app()
    with app.app_context():
        log("DB url:", str(db.engine.url))
        head = find_head()
        log("HEAD =", head)

        # tạo bảng alembic_version nếu chưa có
        db.session.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
        before = db.session.execute(text("SELECT * FROM alembic_version")).fetchall()
        log("alembic_version BEFORE:", before)

        # UPDATE -> nếu không đổi dòng nào thì INSERT
        db.session.execute(text("UPDATE alembic_version SET version_num=:v"), {"v": head})
        changed_row = db.session.execute(text("SELECT changes()")).first()
        changed = changed_row[0] if changed_row else 0
        if changed == 0:
            db.session.execute(text("INSERT INTO alembic_version(version_num) VALUES (:v)"), {"v": head})
        db.session.commit()

        after = db.session.execute(text("SELECT * FROM alembic_version")).fetchall()
        log("alembic_version AFTER :", after)
        log("✅ Stamped successfully.")

if __name__ == "__main__":
    main()
