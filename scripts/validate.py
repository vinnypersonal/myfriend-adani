"""CI gate on every pull request: a post cannot merge unless it passes these checks."""
from __future__ import annotations

import datetime as dt
import json
import re
import sys

from common import LABELS, POSTS, read_sheet, source_list

CRIME_WORDS = r"\b(thief|thieves|fraudster|scamster|crook|criminal|looter|chor)\b"
HEDGES = r"\b(alleg\w*|according to|claim\w*|report\w*|accus\w*|denied|denies)\b"
MAX_AGE_DAYS = 7


def check_post(post: dict, claims: dict) -> list[str]:
    errs: list[str] = []
    pid = post.get("post_id", "?")
    claim = claims.get(post.get("claim_id"))
    if not claim:
        return [f"{pid}: claim {post.get('claim_id')} not in register"]
    if str(claim.get("verified")).lower() != "yes":
        errs.append(f"{pid}: claim is not verified=Yes in the register")
    if post.get("status_label") not in LABELS:
        errs.append(f"{pid}: invalid status label")
    if post.get("status_label") != claim.get("status_label"):
        errs.append(f"{pid}: label {post.get('status_label')} differs from register "
                    f"({claim.get('status_label')}); redraft")
    allowed = set(source_list(claim))
    used = {s.get("url") for s in post.get("sources", [])}
    if not used:
        errs.append(f"{pid}: no sources")
    if used - allowed:
        errs.append(f"{pid}: sources not in register: {sorted(used - allowed)}")
    age = (dt.date.today() - dt.date.fromisoformat(post["as_of"])).days
    if age > MAX_AGE_DAYS:
        errs.append(f"{pid}: drafted {age} days ago; re-verify and redraft (policy: valid on the day)")
    verdict = post.get("check", {}).get("verdict")
    if verdict == "block" and not post.get("check", {}).get("override"):
        errs.append(f"{pid}: fact-checker verdict is BLOCK (fix it, or add check.override with a reason)")
    cap = post.get("caption", "")
    if len(cap) > 2200:
        errs.append(f"{pid}: caption {len(cap)} chars > 2200 Instagram limit")
    if len(re.findall(r"#\w+", cap)) > 30:
        errs.append(f"{pid}: more than 30 hashtags")
    imgs = post.get("images", [])
    if not 2 <= len(imgs) <= 10:
        errs.append(f"{pid}: carousel needs 2-10 images, has {len(imgs)}")
    for name in imgs:
        if not (POSTS / pid / name).exists():
            errs.append(f"{pid}: missing image {name}")
    text = " ".join([post.get("headline", ""), cap] +
                    [s.get("title", "") + " " + s.get("body", "") for s in post.get("slides", [])])
    if post.get("status_label") != "PROVEN" and re.search(CRIME_WORDS, text, re.I):
        errs.append(f"{pid}: crime words used on a non-PROVEN claim")
    if post.get("status_label") in ("ALLEGED", "DISPUTED") and not re.search(HEDGES, text, re.I):
        errs.append(f"{pid}: ALLEGED/DISPUTED post has no hedging language")
    if not any("response" in s.get("title", "").lower() for s in post.get("slides", [])):
        errs.append(f"{pid}: no response slide")
    return errs


def main() -> int:
    claims = {c["claim_id"]: c for c in read_sheet("Claims")}
    errors: list[str] = []
    n = 0
    for pj in sorted(POSTS.glob("*/post.json")):
        post = json.loads(pj.read_text(encoding="utf-8"))
        if post.get("state") != "queued":
            continue
        n += 1
        errors += check_post(post, claims)
    print(f"Checked {n} queued post(s).")
    for e in errors:
        print(f"::error::{e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
