# Runtime Requirements

## Required

- Python 3.11 or later.
- `python-docx` for Word generation and content checks.
- `pypdf` for PDF text extraction when the lawful local source has a text layer.
- Microsoft Word, LibreOffice, or another reliable DOCX-to-PDF renderer for page-by-page visual QA.
- A lawfully obtained, current local knowledge base supplied by the user. No standards, policies, cases, or project files are bundled.

## Configuration

- `BUILDING_REVIEW_KNOWLEDGE_BASE`: private local source directory used by `build_knowledge_index.py`.
- `BUILDING_REVIEW_INDEX_DIR`: directory where the generated index is written. Default: `./building-review-index`.
- `BUILDING_REVIEW_INDEX`: full path to `knowledge-index.json` for search and integrity snapshots. Default: `./building-review-index/knowledge-index.json`.
- `BUILDING_REVIEW_PROJECT_ROOT`: default workspace parent. Default: `./building-review-projects`.

Explicit CLI arguments take precedence where the script provides them.

## Optional CAD Automation

CAD automation is Windows-specific and requires an installed AutoCAD/Core Console environment. Run every generated CAD command through `scripts/run_cad_script_safely.py`. The core architectural review workflow does not require CAD automation when readable PDF or image evidence is available.
