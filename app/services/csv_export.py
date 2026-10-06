import csv
import io

HEADERS = [
    "id", "submitted_by", "category", "amount", "status",
    "submitted_at", "reviewer_comment", "description",
]
# A cell starting with one of these is run as a formula by Excel/Sheets
# ("CSV injection"), so text fields are prefixed with an apostrophe.
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def _safe(value) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(_FORMULA_START) else text


def expenses_to_csv(expenses) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(HEADERS)
    for e in expenses:
        writer.writerow([
            e.id,
            _safe(e.owner_name),
            _safe(e.category),
            f"{e.amount:.2f}",
            e.status.value,
            e.created_at.isoformat(timespec="seconds") if e.created_at else "",
            _safe(e.reviewer_comment),
            _safe(e.description),
        ])
    return out.getvalue()
