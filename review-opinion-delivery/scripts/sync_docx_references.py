"""Update explicit stable-ID reference mappings on an output DOCX copy only."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from docx import Document
from compare_reviewer_docx import body_paragraphs

REFERENCE = re.compile(r"(?:第(?=\s*\d+\s*条\s*(?:续|意见))|(?:本报告|本意见|详见|见)\s*第)\s*(\d+)\s*条")
MAIN = re.compile(r"^\s*(\d+)\s*[、.]?\s*涉及图纸")


def number_map(manifest):
    return {i['item_id']: int(i['item_no']) for i in manifest['items']}


def replace_span(paragraph, start, end, value):
    offset = 0
    for run in paragraph.runs:
        text = run.text
        lo, hi = max(start-offset, 0), min(end-offset, len(text))
        if lo < hi:
            run.text = text[:lo] + (value if offset <= start < offset+len(text) else '') + text[hi:]
        offset += len(text)


def reference_errors(doc, manifest):
    numbers = number_map(manifest)
    rows = manifest.get('docx_references', [])
    mappings = {(r['paragraph_index'], r.get('occurrence', 0)): r for r in rows}
    errors = []
    if len(rows) != len(mappings):
        errors.append('duplicate stable reference mapping')
    found = set()
    for index, paragraph in enumerate(body_paragraphs(doc)):
        for occurrence, match in enumerate(REFERENCE.finditer(paragraph.text)):
            key = (index, occurrence)
            found.add(key)
            row = mappings.get(key)
            if not row or row.get('item_id') not in numbers or int(match.group(1)) != numbers[row['item_id']]:
                errors.append(f'paragraph {index}: stale or unmapped stable-ID reference')
    if set(mappings)-found:
        errors.append('stable reference points to a missing occurrence')
    return errors


def synchronize(doc, manifest, mappings):
    paragraphs = body_paragraphs(doc)
    numbers = number_map(manifest)
    edits = []
    changes = {}
    for row in mappings:
        index = row['paragraph_index']
        paragraph = paragraphs[index]
        if paragraph.text != row['before_text']:
            raise ValueError('Reference anchor changed; remap by stable ID before editing')
        if row['item_id'] not in numbers:
            raise ValueError('Reference targets a removed or unknown opinion')
        pattern = MAIN if row['kind'] == 'main' else REFERENCE
        match = list(pattern.finditer(paragraph.text))[row.get('occurrence', 0)]
        key = (index, match.start(1))
        if key in changes:
            raise ValueError('Duplicate reference update')
        changes[key] = (match.start(1), match.end(1), str(numbers[row['item_id']]))
        edits.append({**row, 'new_number': numbers[row['item_id']]})
    for (index, _), (start, end, value) in sorted(changes.items(), reverse=True):
        replace_span(paragraphs[index], start, end, value)
    return edits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('docx', type=Path)
    parser.add_argument('mapping', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    output = args.output.resolve()
    if not output.is_relative_to(root/'output') or output == args.docx.resolve():
        raise ValueError('Write a new output/ copy; never overwrite the source DOCX')
    manifest = json.loads((root/'delivery_manifest.json').read_text(encoding='utf-8'))
    doc = Document(args.docx)
    edits = synchronize(doc, manifest, json.loads(args.mapping.read_text(encoding='utf-8')))
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)
    output.with_suffix('.references.json').write_text(json.dumps(edits, ensure_ascii=False, indent=2), encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()
