# My Friend Adani

Public-record content pipeline for Instagram **@myfriend_adani**, run by
[RebootIndia](https://rebootindia.com). Covers the Adani Group's growth,
intersections with government decisions, and major cases and controversies.

## Setup

Use a **public repository**: Instagram downloads the approved JPEGs from immutable
GitHub raw URLs. Enable Actions and “Allow GitHub Actions to create and approve pull
requests” in repository Actions settings (the workflow creates PRs, not approvals).
Protect the default branch: require owner review, disallow direct pushes, and
restrict merging to the page owner. Never auto-merge content.

Set Actions secrets:

| Secret | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Drafting and independent evidence audit |
| `INSTAGRAM_ACCESS_TOKEN` | Meta token for the page's Instagram professional account |

Set Actions variables:

| Variable | Purpose |
| --- | --- |
| `POST_APPROVER` | Exact GitHub login of the owner authorized to merge for publication |
| `INSTAGRAM_USER_ID` | Instagram professional account ID, not Facebook Page ID |
| `INSTAGRAM_GRAPH_VERSION` | Supported Meta Graph API version, e.g. `v25.0`; confirm in your Meta app |
| `OPENAI_MODEL` | Optional JSON-capable model; default `gpt-4.1` |

Use Meta's Instagram API **with Facebook Login**: link the professional account
to a Facebook Page, grant the app the required Page access and
`instagram_basic` / `instagram_content_publish` permissions, and complete any
required app review. Refresh the access token before expiry. Verify account
permissions and raw image accessibility before your first real publication.
The pipeline confirms the account username is `myfriend_adani`.

## Editorial workflow

1. Maintain a GitHub issue backlog covering **growth**, **government decisions**,
   and **cases/controversies**. The editor is responsible for tracking every major
   case and updating its status; this pipeline does not discover news or guarantee
   exhaustive coverage. Record pending appeals, denials, later orders and resolutions.
2. On the default branch, run **Draft Instagram carousel** with a topic and a JSON
   array of 1–8 public-record URLs, for example
   `["https://www.sebi.gov.in/<actual-record-path>"]`. Supply actual records, not
   homepages, search results or example URLs. Include the latest status documents.
3. Actions fetches official HTML/text/PDF records, drafts 2–10 slides, checks exact
   evidence quotations, performs a separate model audit, renders 1080×1350 JPEGs,
   and opens a PR containing only `content/<post-id>/post.json` and images.
4. The owner reviews **every image, caption, quotation and source**, independently
   checks current status and omissions, and merges to approve publication.
   Allegations must be attributed and distinguished from findings; company claims
   must be identified as company statements. No speculation or implied guilt.
5. The merge workflow accepts only one newly added carousel approved by
   `POST_APPROVER`. It runs trusted default-branch code, re-fetches records and
   repeats the audit before creating and publishing an Instagram carousel.

**Draft, approve and publish on the same calendar day in Asia/Kolkata.** The
approved slides display that date. If approval is delayed, evidence changes, a
source is unavailable, an audit fails, or the rendered images differ, publication
stops. Generate a new PR; never silently rewrite approved content. To correct
text or images, redraft rather than editing the generated files.

Sources are restricted to the official-domain allowlist in `pipeline.py`;
redirects cannot leave that allowlist. Records and retrieval hashes are archived
in the PR, with exact quotations per slide and source links in the Instagram
caption. Scanned PDFs, unsupported formats and oversized records fail closed.
Extend the allowlist through a separately reviewed code PR when another official
record publisher is needed. Records are sent to the configured OpenAI model;
provide public information only.

Publication saves the carousel container ID as a bot comment **before** the
publish call. Rerunning a failed publish job reuses that container and checks
whether it is already published to avoid duplicates. Do not delete receipt
comments. For expired containers or ambiguous API outcomes, reconcile in Meta
before taking manual action; do not blindly create another post.

Model checks are aids, **not guarantees of factual accuracy or completeness**.
The owner remains accountable for editorial review, freshness and coverage.
No credentials are committed and no content is published merely by drafting.

## Local validation

Python 3.12 and DejaVu Sans (installed on the Ubuntu Actions runner) are required.
Set `CAROUSEL_FONT` to an equivalent font path for local rendering.

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python pipeline.py --help
```

Tests use mocked external services and synthetic records; they never publish.
Live drafting requires an OpenAI key. Live publication also requires the configured
Meta account and a GitHub bot token with PR-comment permissions.
