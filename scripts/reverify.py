"""Weekly: keep published claims 'valid on the day'.

- Checks every source URL still resolves.
- Flags claims whose last_verified is older than the threshold.
- If a published claim's status_label was changed in the register (e.g. ALLEGED -> CLEARED),
  marks it Update-needed so the next draft run produces an UPDATE post.
Writes reverify_report.md; the workflow opens an issue from it.
"""
import datetime as dt

import requests

from common import ROOT, read_sheet, settings, source_list, today, write_sheet

UA = {"User-Agent": "Mozilla/5.0 (myfriend_adani link check)"}


def alive(url: str) -> bool:
    try:
        r = requests.head(url, headers=UA, timeout=20, allow_redirects=True)
        if r.status_code in (403, 405):
            r = requests.get(url, headers=UA, timeout=30, stream=True)
        return r.status_code < 400
    except Exception:  # noqa: BLE001
        return False


def main() -> None:
    stale_days = settings()["reverify"]["stale_after_days"]
    claims = read_sheet("Claims")
    dead, stale, updates = [], [], []
    for c in claims:
        if str(c.get("verified")).lower() != "yes":
            continue
        for u in source_list(c):
            if not alive(u):
                dead.append(f"{c['claim_id']}: {u}")
        lv = str(c.get("last_verified", ""))[:10]
        try:
            age = (dt.date.today() - dt.date.fromisoformat(lv)).days
        except ValueError:
            age = 9999
        if c.get("post_status") == "Published" and age > stale_days:
            stale.append(f"{c['claim_id']} ({c['title']}): last verified {lv or 'never'}")
        if (c.get("post_status") == "Published" and c.get("published_label")
                and c.get("status_label") != c.get("published_label")):
            c["post_status"] = "Update-needed"
            updates.append(f"{c['claim_id']}: {c['published_label']} -> {c['status_label']}")
    write_sheet("Claims", claims)
    report = [f"# Re-verification report, {today()}", ""]
    report += ["## Status changed: UPDATE post queued"] + [f"- {x}" for x in updates or ["none"]] + [""]
    report += ["## Dead or blocked source links"] + [f"- {x}" for x in dead or ["none"]] + [""]
    report += [f"## Published claims not re-verified in {stale_days}+ days"] + [f"- {x}" for x in stale or ["none"]]
    (ROOT / "reverify_report.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
