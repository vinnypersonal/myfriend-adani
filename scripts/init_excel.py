"""Create data/claims.xlsx with the register layout and starter backlog rows.

The starter rows are research TOPICS, not verified facts: verified=No and no sources,
so the pipeline will refuse to draft them until a human fills them in.
"""
from common import XLSX, create_workbook, export_csv, write_sheet

TOPICS = [
    ("C001", "Hindenburg Research report on Adani Group and SEBI proceedings", "Markets / regulator"),
    ("C002", "SEBI orders on Hindenburg-related allegations (check for clearances)", "Markets / regulator"),
    ("C003", "US DOJ / SEC case on solar power contracts: current status", "International case"),
    ("C004", "Mumbai and other airports: 2019 bidding rules and outcomes", "Govt decision"),
    ("C005", "Mundra port & SEZ land allotment: rates, CAG / court observations", "Land"),
    ("C006", "DRI coal import valuation case: current status", "Customs / regulator"),
    ("C007", "Bangladesh power purchase agreement: terms and review", "International deal"),
    ("C008", "Dharavi redevelopment award", "Govt decision"),
]

if __name__ == "__main__":
    if XLSX.exists():
        raise SystemExit(f"{XLSX} already exists; refusing to overwrite.")
    create_workbook()
    write_sheet("Claims", [{
        "claim_id": cid, "title": title, "category": cat,
        "verified": "No", "post_status": "Backlog",
        "notes": "Research topic. Add sources, summary, label, response; then verified=Yes, post_status=Ready.",
    } for cid, title, cat in TOPICS])
    export_csv()
    print(f"Created {XLSX}")
