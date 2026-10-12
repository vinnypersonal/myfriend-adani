"""Scheduled: publish approved (merged) posts to Instagram as carousels.

A post reaches main only by a merged pull request, so anything on main with
state=queued has been approved by a human.

Secrets: IG_USER_ID, IG_ACCESS_TOKEN (long-lived, instagram_content_publish).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import requests

from common import POSTS, now, read_sheet, settings, write_sheet
from validate import check_post

GRAPH = "https://graph.facebook.com"


def image_urls(post: dict, cfg: dict) -> list[str]:
    host = cfg["publishing"]["image_host"]
    pid = post["post_id"]
    if host == "github_raw":
        repo = os.environ["GITHUB_REPOSITORY"]
        ref = os.environ.get("GITHUB_SHA", "main")
        return [f"https://raw.githubusercontent.com/{repo}/{ref}/posts/{pid}/{n}" for n in post["images"]]
    if host == "cloudinary":
        cloud, key, secret = (os.environ[k] for k in (
            "CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"))
        urls = []
        for n in post["images"]:
            ts = str(int(time.time()))
            public_id = f"myfriend_adani/{pid}/{n.rsplit('.', 1)[0]}"
            sig = hashlib.sha1(f"public_id={public_id}&timestamp={ts}{secret}".encode()).hexdigest()
            with open(POSTS / pid / n, "rb") as fh:
                r = requests.post(f"https://api.cloudinary.com/v1_1/{cloud}/image/upload",
                                  data={"api_key": key, "timestamp": ts, "public_id": public_id, "signature": sig},
                                  files={"file": fh}, timeout=120)
            r.raise_for_status()
            urls.append(r.json()["secure_url"])
        return urls
    raise ValueError(f"unknown image_host {host}")


def gpost(path: str, **params) -> dict:
    v = settings()["publishing"]["graph_version"]
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.post(f"{GRAPH}/{v}/{path}", data=params, timeout=120)
    if not r.ok:
        raise RuntimeError(f"Graph API {path}: {r.status_code} {r.text}")
    return r.json()


def gget(path: str, **params) -> dict:
    v = settings()["publishing"]["graph_version"]
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.get(f"{GRAPH}/{v}/{path}", params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def wait_ready(container_id: str) -> None:
    for _ in range(30):
        if gget(container_id, fields="status_code").get("status_code") == "FINISHED":
            return
        time.sleep(5)
    raise RuntimeError(f"container {container_id} not ready")


def publish(post: dict, cfg: dict) -> tuple[str, str]:
    ig = os.environ["IG_USER_ID"]
    children = []
    for url in image_urls(post, cfg):
        c = gpost(f"{ig}/media", image_url=url, is_carousel_item="true")["id"]
        wait_ready(c)
        children.append(c)
    carousel = gpost(f"{ig}/media", media_type="CAROUSEL",
                     children=",".join(children), caption=post["caption"])["id"]
    wait_ready(carousel)
    media_id = gpost(f"{ig}/media_publish", creation_id=carousel)["id"]
    permalink = gget(media_id, fields="permalink").get("permalink", "")
    return media_id, permalink


def main() -> int:
    cfg = settings()
    dry = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
    claims = read_sheet("Claims")
    by_id = {c["claim_id"]: c for c in claims}
    log = read_sheet("PostLog")
    queued = []
    for pj in sorted(POSTS.glob("*/post.json")):
        p = json.loads(pj.read_text(encoding="utf-8"))
        if p.get("state") == "queued":
            queued.append((pj, p))
    if not queued:
        print("No approved posts waiting.")
        return 0
    for pj, post in queued[: cfg["publishing"]["max_per_run"]]:
        errs = check_post(post, by_id)  # re-validate on the day of publishing
        if errs:
            print("\n".join(f"::error::{e}" for e in errs))
            return 1
        if dry:
            print(f"[dry run] would publish {post['post_id']} with {len(post['images'])} images")
            continue
        media_id, link = publish(post, cfg)
        post.update(state="published", published_at=now(), ig_media_id=media_id, permalink=link)
        pj.write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
        c = by_id[post["claim_id"]]
        c.update(post_status="Published", published_label=post["status_label"], post_id=post["post_id"])
        log.append({"post_id": post["post_id"], "claim_id": post["claim_id"], "kind": post["kind"],
                    "created_at": post["created_at"], "status_label": post["status_label"],
                    "published_at": post["published_at"], "ig_media_id": media_id, "permalink": link})
        print(f"Published {post['post_id']}: {link}")
    write_sheet("Claims", claims)
    write_sheet("PostLog", log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
