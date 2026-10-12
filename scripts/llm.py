"""One interface over Claude (Anthropic API), GitHub Models (Copilot-side) and an offline mock."""
from __future__ import annotations

import json
import os
import re

import requests

from common import settings


def _extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"No JSON object in model output:\n{text[:500]}")
    return json.loads(m.group(0))


def complete_json(system: str, user: str, mock: dict | None = None) -> dict:
    cfg = settings()["llm"]
    provider = os.environ.get("LLM_PROVIDER", cfg["provider"]).lower()

    if provider == "mock":
        return mock or {}

    if provider == "claude":
        import anthropic
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        msg = client.messages.create(
            model=os.environ.get("CLAUDE_MODEL", cfg["claude_model"]),
            max_tokens=cfg["max_tokens"],
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return _extract_json("".join(b.text for b in msg.content if b.type == "text"))

    if provider == "github":
        # GitHub Models: needs `permissions: models: read` in the workflow.
        token = os.environ["GITHUB_TOKEN"]
        r = requests.post(
            "https://models.github.ai/inference/chat/completions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "model": os.environ.get("GITHUB_MODEL", cfg["github_model"]),
                "max_tokens": cfg["max_tokens"],
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
            },
            timeout=180,
        )
        r.raise_for_status()
        return _extract_json(r.json()["choices"][0]["message"]["content"])

    raise ValueError(f"Unknown LLM provider: {provider}")
