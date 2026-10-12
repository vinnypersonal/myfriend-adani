# myfriend_adani: content pipeline

Automated research → draft → fact-check → approve → publish pipeline for the Instagram page **@myfriend_adani**, run entirely on GitHub Actions. The Excel file in `data/` is the single source of truth; nothing is posted that isn't in it, verified, and sourced.

## How it works

| When (IST) | Workflow | What it does |
|---|---|---|
| Daily 06:45 | `monitor.yml` | Pulls Google News feeds (EN + HI) into the **Inbox** sheet for you to triage |
| Mon & Thu 07:45 | `draft.yml` | Takes the next **Ready** claim → fetches its sources → Claude (or GitHub Models) drafts → a second model call fact-checks → renders carousel PNGs → opens a **pull request** |
| Every PR | `validate.yml` | Blocks merge if: claim not verified, sources not in register, crime words on unproven claims, no hedging on ALLEGED posts, no response slide, draft older than 7 days, caption over 2,200 chars |
| You | — | Review the PR (slides render in "Files changed"). **Merge = approve.** Comment `@claude …` to request edits |
| Daily 18:50 | `publish.yml` | Re-validates, then publishes merged posts as Instagram carousels and records them in **PostLog** |
| Sun 08:40 | `reverify.yml` | Link-checks every source, flags stale claims, and when you change a published claim's label (e.g. ALLEGED → CLEARED) queues an **UPDATE** post. Opens an issue with the report |

## The claims register (`data/claims.xlsx`)

Sheets: **Claims**, **Inbox**, **PostLog**, **Guide**. CSV mirrors are written alongside so diffs are readable in PRs.

To queue a post, fill a Claims row: `summary`, `parties`, `status_label` (PROVEN / ALLEGED / DISPUTED / CLEARED), `govt_link`, `adani_response`, `source_urls` (one per line), `last_verified`, then set `verified = Yes` and `post_status = Ready`. Commit the file (GitHub web "Upload files" works).

**Clearances:** change the claim's `status_label` to CLEARED, add the clearance order to `source_urls`, update `last_verified`. The weekly run turns it into an UPDATE post covering the allegation, parties, and the clearance with links.

The 8 starter rows are research topics with no sources; the pipeline ignores them until you complete them.

## Setup (≈20 minutes)

1. Create a GitHub repo and push this folder.
2. **Settings → Secrets and variables → Actions**, add:
   - `ANTHROPIC_API_KEY` for Claude drafting and `@claude` comments (skip if using only GitHub Models)
   - `IG_USER_ID`, `IG_ACCESS_TOKEN`: Instagram Professional account linked to a Facebook Page; Meta app with `instagram_content_publish`; long-lived token (refresh every 60 days)
3. **Settings → Environments → New `instagram`**: optionally add yourself as required reviewer for a second sign-off before each publish.
4. **Issues → Labels**: create `post-draft` and `reverify`.
5. **Settings → Actions → General**: allow GitHub Actions to create pull requests.
6. Images: Instagram fetches images by public URL.
   - Public repo: keep `image_host: github_raw`.
   - Private repo: set `image_host: cloudinary` in `config/settings.yml` and add `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`.
7. Test: **Actions → Draft posts → Run workflow → provider `mock`**, then **Publish → Run workflow** with dry run on.

## Claude or Copilot

`config/settings.yml → llm.provider`:
- `claude`: Anthropic API (`claude-sonnet-5-5` by default)
- `github`: GitHub Models, the API behind Copilot's model access, billed to your GitHub account and authenticated by the workflow's own token (no extra secret)
- `mock`: offline test

You can also pick the provider per run from the "Run workflow" button.

## Run locally

```bash
pip install -r requirements.txt
cd scripts
LLM_PROVIDER=mock python draft.py      # draft + render
python validate.py                      # safety gate
DRY_RUN=1 python publish.py             # no posting
```

## Files

```
config/settings.yml        provider, schedule knobs, brand colours, feeds
data/claims.xlsx           the register (+ CSV mirrors)
prompts/editorial_charter.md  page policy & research scope
prompts/drafter.md         drafting rules (labels, hedging, response slide)
prompts/checker.md         independent fact-check rules
scripts/                   monitor, draft, render, validate, publish, reverify
assets/fonts/              Poppins (OFL)
posts/<post_id>/           post.json, caption.txt, slide PNGs
```
