import os
import shutil
import pathlib
import datetime

# 🟢 CẤU HÌNH CƠ BẢN
DB_FILE = r"F:\Production\app\myproject\instance\materials.db"   # 👉 Đường dẫn tới file SQLite thật
BACKUP_DIR = r"F:\Production\app\myproject\db_backups" # 👉 Thư mục lưu backup
KEEP_DAYS = 10  # 👉 Giữ 10 bản mới nhất

# 🟢 TẠO THƯ MỤC BACKUP NẾU CHƯA CÓ
pathlib.Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)

# 🟢 TẠO TÊN FILE BACKUP THEO NGÀY
today = datetime.datetime.now().strftime("%Y-%m-%d")
backup_name = f"{today}_app.db"     
backup_path = os.path.join(BACKUP_DIR, backup_name)

# 🟢 SAO CHÉP FILE DB
if os.path.exists(DB_FILE):
    shutil.copy2(DB_FILE, backup_path)
    print(f"✅ Backup created: {backup_path}")
else:
    print(f"❌ Database not found: {DB_FILE}")
    exit(1)

# 🟢 XOÁ FILE CŨ (chỉ giữ 10 file mới nhất)
files = sorted(
    pathlib.Path(BACKUP_DIR).glob("*.db"),
    key=lambda f: f.stat().st_mtime,
    reverse=True
)
for f in files[KEEP_DAYS:]:
    try:
        f.unlink()
        print(f"🗑️  Deleted old backup: {f.name}")
    except Exception as e:
        print(f"⚠️  Could not delete {f.name}: {e}")

print("✅ Done — kept", KEEP_DAYS, "most recent backups.")
