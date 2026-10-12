"""Daily: pull news/regulator feeds into the Inbox sheet for human triage."""
import datetime as dt
import time

import feedparser

from common import now, read_sheet, settings, write_sheet


def main() -> None:
    cfg = settings()["monitor"]
    inbox = read_sheet("Inbox")
    seen = {r["url"] for r in inbox}
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=cfg["keep_days"])
    added = 0
    for feed_url in cfg["feeds"]:
        feed = feedparser.parse(feed_url)
        for e in feed.entries:
            link = e.get("link", "")
            if not link or link in seen:
                continue
            ts = e.get("published_parsed") or e.get("updated_parsed")
            if ts and dt.datetime.fromtimestamp(time.mktime(ts), dt.timezone.utc) < cutoff:
                continue
            inbox.append({
                "found_at": now(), "feed": feed.feed.get("title", feed_url)[:80],
                "title": e.get("title", "")[:300], "url": link,
                "published": e.get("published", ""), "triage": "New", "claim_id": "",
            })
            seen.add(link)
            added += 1
    write_sheet("Inbox", inbox)
    print(f"Inbox: {added} new items")


if __name__ == "__main__":
    main()
