
# NVL Manager (Flask)

App Flask quản lý Nguyên Vật Liệu, hướng đến tích hợp với MES sau này.

## Tính năng theo Page
1. **Định mức NVL (BOM)**: CRUD + import Excel. Hỗ trợ nhóm lựa chọn (choice_group) cho NVL thay thế (chọn 1 trong nhiều).
2. **Tồn kho & Xuất/Nhập**: Bảng tồn kho (Inventory) + form ghi xuất/nhập, tự log vào `material_txns`. Import tồn kho.
3. **Xuất NVL theo Lệnh SX**: Tính NVL theo định mức, cho phép chỉnh sửa trước khi xuất. Lưu phiếu xuất (IssueHeader, IssueLine) và trừ tồn.
4. **Dự tính NVL**: Tính độc lập số SP có thể SX theo từng cặp NVL–SP; cảnh báo khi dưới ngưỡng.

## Cài đặt nhanh
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask db init
flask db migrate -m "init"
flask db upgrade
python seed.py  # dữ liệu mẫu (tùy chọn)
python run.py
```
Mặc định DB SQLite `materials.db`.

## Import Excel
- BOM columns: `product_name, product_uom, material_name, material_uom, qty_per_unit, choice_group(optional)`
- Inventory columns: `material_name, uom, qty_on_hand`
- Issues Type-2 import: `product_name, qty, selected_material_names(optional: 'Tên 1, Tên 2')`

## Gợi ý tích hợp với MES
- Tạo API `/issues/commit` nhận `work_order_id` từ MES để liên kết.
- Đồng bộ master data (Products, Materials) từ MES bằng cron/API.
- Ghi `ref_type="WO"` và `ref_id=<WO id>` trong `MaterialTxn`.

## Ghi chú
- Page 3 demo đáp ứng luồng chuẩn; có thể mở rộng chỉnh tick NVL theo group chi tiết hơn.
- Alert threshold chỉnh qua env `MIN_UNITS_ALERT`, mặc định 10.
```env
MIN_UNITS_ALERT=15
```
