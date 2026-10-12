"""Scheduled: draft carousel posts for Ready claims (and Update posts for changed labels).

Flow per claim: fetch source text -> drafter LLM -> checker LLM -> render slides ->
write posts/<post_id>/. The workflow then opens a pull request,
which is the human approval step.
"""
from __future__ import annotations

import html
import json
import os
import re

import requests

from common import (POSTS, PROMPTS, LABELS, now, read_sheet, settings,
                    source_list, today)
from llm import complete_json
from render import render_post

UA = {"User-Agent": "Mozilla/5.0 (myfriend_adani research bot)"}


def fetch_text(url: str, limit: int) -> str:
    try:
        r = requests.get(url, headers=UA, timeout=30)
        r.raise_for_status()
        if "pdf" in r.headers.get("content-type", ""):
            return f"[PDF at {url}: read manually; text not extracted]"
        t = re.sub(r"(?is)<(script|style|nav|footer|header).*?</\1>", " ", r.text)
        t = html.unescape(re.sub(r"<[^>]+>", " ", t))
        return re.sub(r"\s+", " ", t)[:limit]
    except Exception as e:  # noqa: BLE001
        return f"[could not fetch {url}: {e}]"


def eligible(claims: list[dict]) -> list[tuple[dict, str]]:
    # Claims already sitting in an open draft PR are skipped (set by the workflow).
    skip = {x.strip() for x in os.environ.get("SKIP_CLAIMS", "").split(",") if x.strip()}
    out = []
    for c in claims:
        if c["claim_id"] in skip:
            continue
        if str(c.get("verified")).lower() != "yes" or not source_list(c):
            continue
        if c.get("status_label") not in LABELS:
            continue
        if c.get("post_status") == "Ready":
            out.append((c, "new"))
        elif c.get("post_status") == "Update-needed":
            out.append((c, "update"))
    return out


def mock_draft(c: dict, kind: str) -> dict:
    srcs = source_list(c)
    return {
        "headline": ("UPDATE: " if kind == "update" else "") + str(c["title"])[:60],
        "slides": [
            {"title": "What happened", "body": str(c.get("summary", ""))[:220]},
            {"title": "Who is involved", "body": str(c.get("parties", ""))},
            {"title": "The government link", "body": str(c.get("govt_link", "") or "None documented in the sources.")},
            {"title": "Adani Group's response", "body": str(c.get("adani_response", "") or f"Not found in public record as of {today()}.")},
            {"title": "Sources", "body": "\n".join(f"{i+1}. {u.split('/')[2]}" for i, u in enumerate(srcs))},
        ],
        "caption_en": f"{c['title']}. Status: {c['status_label']} as of {today()}. What do you think?",
        "caption_hi": f"{c['title']} — स्थिति: {c['status_label']} ({today()})",
        "hashtags": ["#Adani", "#Accountability", "#India"],
        "sources": [{"name": u.split("/")[2], "url": u} for u in srcs],
        "risk_notes": ["MOCK OUTPUT — offline test, not model-written."],
    }


def build_caption(d: dict, claim: dict, as_of: str) -> str:
    src = "\n".join(f"• {s['name']}: {s['url']}" for s in d["sources"])
    return (f"{d['caption_en']}\n\n{d['caption_hi']}\n\n"
            f"Status: {claim['status_label']} as of {as_of}.\nSources:\n{src}\n\n"
            + " ".join(d["hashtags"][:12]))


def main() -> None:
    cfg = settings()
    claims = read_sheet("Claims")
    queue = eligible(claims)[: cfg["drafting"]["posts_per_run"]]
    if not queue:
        print("Nothing Ready to draft.")
        return
    drafter_sys = (PROMPTS / "drafter.md").read_text(encoding="utf-8") \
        .replace("{slides_min}", str(cfg["drafting"]["slides_min"])) \
        .replace("{slides_max}", str(cfg["drafting"]["slides_max"]))
    checker_sys = (PROMPTS / "checker.md").read_text(encoding="utf-8")
    summary_lines = []

    for claim, kind in queue:
        as_of = today()
        n = len(list(POSTS.glob(f"{claim['claim_id']}-*"))) + 1
        post_id = f"{claim['claim_id']}-{'U' if kind == 'update' else 'P'}{n}"
        sources_text = "\n\n".join(
            f"### SOURCE {u}\n{fetch_text(u, cfg['drafting']['max_source_chars'])}"
            for u in source_list(claim))
        claim_view = {k: str(v) for k, v in claim.items()}
        user = (f"KIND: {kind}\nDATE: {as_of}\n"
                + (f"PREVIOUS POST: {claim.get('post_id')} (label then: {claim.get('published_label')})\n" if kind == "update" else "")
                + f"CLAIM:\n{json.dumps(claim_view, ensure_ascii=False, indent=2)}\n\nSOURCE TEXT:\n{sources_text}")

        draft = complete_json(drafter_sys, user, mock=mock_draft(claim, kind))
        check = complete_json(
            checker_sys,
            f"CLAIM:\n{json.dumps(claim_view, ensure_ascii=False)}\n\nSOURCE TEXT:\n{sources_text}\n\nDRAFT:\n{json.dumps(draft, ensure_ascii=False)}",
            mock={"verdict": "pass", "issues": []})

        post = {
            "post_id": post_id, "claim_id": claim["claim_id"], "kind": kind,
            "status_label": claim["status_label"], "category": claim.get("category", ""),
            "as_of": as_of, "created_at": now(), "state": "queued",
            "provider": os.environ.get("LLM_PROVIDER", cfg["llm"]["provider"]),
            **draft, "check": check,
        }
        post["caption"] = build_caption(draft, claim, as_of)
        out = POSTS / post_id
        out.mkdir(parents=True, exist_ok=True)
        post["images"] = [p.name for p in render_post(post, out)]
        (out / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "caption.txt").write_text(post["caption"], encoding="utf-8")

        issues = "\n".join(f"  - {i.get('where')}: {i.get('problem')}" for i in check.get("issues", []))
        summary_lines.append(f"### {post_id} — {claim['title']}\n- Kind: {kind}\n- Label: {claim['status_label']} (as of {as_of})\n"
                             f"- Checker verdict: **{check.get('verdict', '?')}**\n{issues}\n"
                             f"- Risk notes: {'; '.join(draft.get('risk_notes', [])) or 'none'}\n")

    # The register is NOT edited here (binary Excel merges badly); publish.py updates it on main.
    (POSTS / "_last_run.md").write_text("\n".join(summary_lines), encoding="utf-8")
    print("\n".join(summary_lines))


if __name__ == "__main__":
    main()
