# CLAUDE.md — myfriend_adani

Instructions for Claude (Claude Code, the `@claude` GitHub Action, or a Claude project session) when working in this repository. Read this before changing any file.

## What this repo is
Content pipeline for the Instagram page **@myfriend_adani**, run by RebootIndia (rebootindia.com). The page documents the Adani Group's growth, its intersections with government decisions, and every major case or controversy — using only public records valid on the day of posting. GitHub Actions drafts, fact-checks, renders and publishes carousel posts; the owner approves each post by merging its pull request.

Editorial policy lives in `prompts/editorial_charter.md`. It is binding for every change you make.

## Repository map
| Path | Purpose |
|---|---|
| `data/claims.xlsx` | **Source of truth.** Sheets: Claims, Inbox, PostLog, Guide |
| `data/*.csv` | Auto-generated mirrors of the sheets. Never edit by hand |
| `config/settings.yml` | LLM provider, schedules knobs, feeds, brand colours, image host |
| `prompts/drafter.md` / `checker.md` | System prompts for drafting and the independent fact-check |
| `scripts/common.py` | Excel read/write helpers (`read_sheet`, `write_sheet`, `export_csv`) |
| `scripts/draft.py` → `render.py` | Draft + render posts into `posts/<post_id>/` |
| `scripts/validate.py` | CI safety gate (runs on every PR) |
| `scripts/publish.py` | Instagram Graph API carousel publishing |
| `scripts/monitor.py` / `reverify.py` | News intake; weekly link + status re-check |
| `.github/workflows/` | monitor, draft, validate, publish, reverify, claude |
| `assets/fonts/` | Poppins (OFL). Slides must use these fonts only |

## Commands
```bash
pip install -r requirements.txt
cd scripts
LLM_PROVIDER=mock python draft.py     # offline draft + render
python validate.py                     # must exit 0 before any PR is ready
DRY_RUN=1 python publish.py            # never run without DRY_RUN locally
python render.py ../posts/<post_id>    # re-render after editing post.json
```

## How to make changes
1. **Always work on a branch and open a pull request.** Never push to `main` directly. Branch names: `draft/<post_id>` for posts, `register/<short-desc>` for data, `fix/<short-desc>` for code.
2. **Editing the register:** change `data/claims.xlsx` only through `scripts/common.py` (`read_sheet` / `write_sheet`), which preserves dropdowns and regenerates the CSVs. Keep register edits in their own PR, separate from post drafts — the Excel file is binary and cannot be merged.
3. **Editing a post:** edit `posts/<post_id>/post.json`, regenerate `caption.txt` if the caption changed, re-run `render.py`, then `validate.py`. Never hand-edit PNGs.
4. **Code changes:** keep `validate.py` at least as strict as it is now. Run the mock draft + validate + dry-run publish before opening the PR.
5. Commit messages: imperative, one line summary, e.g. `Add sources to C003`, `Shorten slide 3 of C001-P1`.

## Non-negotiable content rules
- **Only facts present in the claim's sources.** Never add figures, dates, names or quotes from memory. If you research a claim, every new fact needs a URL added to `source_urls`.
- **Status labels:** PROVEN (court/regulator finding) · ALLEGED (reported / under investigation) · DISPUTED (denied by the group) · CLEARED (dismissed by an authority). Wording must match the label; never state guilt unless PROVEN.
- **Clearances:** set the label to CLEARED, add the clearance order URL, and let the UPDATE post state the allegation, the parties, and the clearance with links.
- **Every post includes** the Adani Group's (and where relevant the government's) response, or "not found in public record as of <date>".
- **Timing patterns are facts plus a question**, never presented as proof of a quid pro quo.
- **No AI-generated realistic images of real people, no fabricated documents or quotes.** Visuals are typographic slides, charts, maps and timelines.
- **Only a human sets `verified = Yes`.** You may fill every other field and propose `post_status = Ready`, but leave `verified` as `No` and say in the PR that it needs the owner's check.
- Preferred sources: court orders, SEBI, CAG, parliamentary records, US DOJ/SEC filings, stock-exchange disclosures, Reuters, FT, The Hindu, Indian Express, Scroll, The Wire, Newslaundry, OCCRP.

## Never
- Commit secrets or tokens (`IG_ACCESS_TOKEN`, `ANTHROPIC_API_KEY`, Cloudinary keys). They live in GitHub Actions secrets only.
- Run `publish.py` without `DRY_RUN=1`, or trigger the publish workflow with dry run off.
- Weaken or bypass `validate.py`, or set `check.override` on a blocked post without the owner asking.
- Delete PostLog rows or published post folders; corrections are new UPDATE posts.

## PR description template
- What changed and why
- Claims touched (IDs) and their labels
- Sources added (URLs)
- Output of `python validate.py`
- Anything the owner must verify by hand
