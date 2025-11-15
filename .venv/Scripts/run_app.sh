#!/usr/bin/env bash
set -euo pipefail

# === Config mặc định (có thể override qua tham số) ===
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-5000}"
MODE="prod"          # prod/dev
SEED=0               # 1 để seed

# === Đọc tham số CLI ===
for arg in "$@"; do
  case "$arg" in
    dev) MODE="dev" ;;
    prod) MODE="prod" ;;
    --seed) SEED=1 ;;
    --host=*) HOST="${arg#*=}" ;;
    --port=*) PORT="${arg#*=}" ;;
    *) echo "Unknown arg: $arg" ;;
  esac
done

# === Đổi về thư mục gốc dự án (chứa requirements.txt) ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$APP_DIR"

# === Chọn Python phù hợp ===
PY="python3"
command -v python3 >/dev/null 2>&1 || PY="python"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "❌ Không tìm thấy Python. Hãy cài Python trước."
  exit 1
fi

# === Tạo venv nếu thiếu & kích hoạt ===
if [ ! -d ".venv" ]; then
  echo "👉 Tạo virtualenv .venv"
  "$PY" -m venv .venv
fi
# activate (Linux/macOS/Git Bash)
# shellcheck disable=SC1091
source .venv/bin/activate

# === Cài dependencies ===
python -m pip install --upgrade pip
pip install -r requirements.txt

# === Khai báo app factory cho Flask CLI ===
export FLASK_APP="materials_app:create_app"

# === Migrate/upgrade DB (tự init nếu thiếu) ===
if ! flask db upgrade; then
  echo "⚙️  Khởi tạo migrations..."
  flask db init
  flask db migrate -m "init"
  flask db upgrade
fi

# === Seed dữ liệu mẫu (nếu yêu cầu) ===
if [ "$SEED" -eq 1 ]; then
  echo "🌱 Seed dữ liệu mẫu..."
  python seed.py
fi

# === Chạy server ===
if [ "$MODE" = "dev" ]; then
  echo "🚀 Dev server: http://$HOST:$PORT  (auto-reload)"
  exec flask run --host="$HOST" --port="$PORT"
else
  echo "🚀 Prod server (waitress): http://$HOST:$PORT"
  pip install waitress >/dev/null
  exec waitress-serve --listen="$HOST:$PORT" run:app
fi
