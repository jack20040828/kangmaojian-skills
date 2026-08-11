# Runtime Requirements

## Required

- Python 3.11 or later.
- `python-docx` for Word generation, comparison, and content validation.
- `Pillow` for evidence-image composition and anonymous regression fixtures.
- `pypdfium2` for rendering marked PDF pages.
- Microsoft Word, LibreOffice, or another reliable DOCX-to-PDF renderer for page-by-page visual QA.

## Configuration

- `REVIEW_OPINION_PROJECT_ROOT`: default workspace parent. Default: `./review-opinion-projects`.
- Use `--root <path>` to select a specific project workspace.
- Use `--font` and `--bold-font` with `compose_evidence_cards.py` when Microsoft YaHei is unavailable at the Windows default font paths.

Word COM export is Windows-specific. Other environments may use LibreOffice or another renderer, but every final page still requires visual inspection.
