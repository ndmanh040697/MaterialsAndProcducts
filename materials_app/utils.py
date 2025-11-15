from datetime import datetime, date

def parse_any_date(s: str):
    """Trả về date() nếu parse được; chấp nhận dd/mm/yyyy, dd/mm/yy, yyyy-mm-dd."""
    if not s:
        return None
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None
