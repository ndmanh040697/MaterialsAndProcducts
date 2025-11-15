# --- start_app.ps1 ---
# Tự động chuyển sang ổ và thư mục dự án, kích hoạt venv, rồi chạy app Python

Set-Location F:\Production\app\myproject
& "F:\Production\app\myproject\.venv\Scripts\Activate.ps1"
python run.py

# Giữ cửa sổ PowerShell mở sau khi chạy xong (để xem log nếu có lỗi)
Pause