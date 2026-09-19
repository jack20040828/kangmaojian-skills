"""Bind page QA to the current v1.3 manifest, DOCX, PDF and complete page set."""
import hashlib
import json
from pathlib import Path

EXTRA_CHECKS = ['image_correspondence_check', 'reference_number_check', 'text_flow_check', 'image_crop_check']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def enabled(qa_path):
    manifest = qa_path.parent/'delivery_manifest.json'
    return manifest.is_file() and json.loads(manifest.read_text(encoding='utf-8')).get('schema_version') == '1.3'


def snapshot(qa_path, docx, pdf, renders):
    if not docx or not docx.is_file():
        raise ValueError('v1.3 page rendering needs --docx')
    paths = [qa_path.parent/'delivery_manifest.json', docx, pdf, *renders]
    record = {'page_count': len(renders), 'files': {str(p.resolve()): digest(p) for p in paths},
              'render_paths': [str(p.resolve()) for p in renders]}
    qa_path.with_suffix('.snapshot.json').write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')


def errors(qa_path, rows):
    from pypdf import PdfReader
    issues = []
    snapshot_path = qa_path.with_suffix('.snapshot.json')
    if not snapshot_path.is_file():
        return ['Missing page QA integrity snapshot; re-render']
    saved = json.loads(snapshot_path.read_text(encoding='utf-8'))
    for path, old in saved['files'].items():
        if not Path(path).is_file() or digest(path) != old:
            issues.append('QA snapshot stale: '+path)
    if not rows:
        return issues+['No pages checked']
    pdf = Path(rows[0]['report_pdf'])
    if not pdf.is_file() or len(PdfReader(pdf).pages) != len(rows) or saved['page_count'] != len(rows):
        issues.append('QA rows do not cover the complete exported PDF')
    renders = [str(Path(r['render_path']).resolve()) for r in rows]
    if renders != saved['render_paths']:
        issues.append('QA page renders differ from snapshot')
    for row in rows:
        for field in ['report_docx', 'report_pdf']:
            if str(Path(row[field]).resolve()) not in saved['files']:
                issues.append('QA substituted an unverified document')
        for field in EXTRA_CHECKS:
            if row.get(field) != '通过':
                issues.append(f"Page {row.get('page_no')}: {field} is not 通过")
    return issues
