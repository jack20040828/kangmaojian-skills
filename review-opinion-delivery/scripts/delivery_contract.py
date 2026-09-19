"""v1.3 editorial authority and evidence checks; no technical-review decisions."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

APPROVED_FIELDS = ("opinion_text", "regulation_text", "opinion_type", "drawing_refs")
PDF_REF = re.compile(r"PDF第[1-9]\d*页《[^《》\r\n]+》")
CONTINUATION = re.compile(r"第\s*(\d+)\s*条\s*续")


def normalized(text):
    return re.sub(r"\s+", "", str(text or "")).replace(":", "：").replace(",", "，")


def locator_errors(manifest):
    policy = manifest.get("location_policy", {})
    mode = policy.get("mode", "drawing_number_title")
    errors = []
    if mode not in {"drawing_number_title", "pdf_page_title"}:
        return ["unknown location_policy mode"]
    if mode == "pdf_page_title" and not policy.get("authorization_ref"):
        errors.append("PDF page locator requires explicit user authorization")
    for item in manifest.get("items", []):
        text = item.get("drawing_refs", "")
        if mode == "pdf_page_title":
            residue = PDF_REF.sub("", text)
            if item.get("drawing_no") or not PDF_REF.search(text) or residue.strip(" ；;、，,。\n"):
                errors.append(f"{item.get('item_id')}: locator must be PDF第N页《图名》 with empty drawing_no")
        elif "PDF" in text.upper():
            errors.append(f"{item.get('item_id')}: unapproved PDF locator")
    return errors


def validate_contract(root: Path, manifest: dict) -> list[str]:
    errors = locator_errors(manifest)
    items = manifest.get("items", [])
    by_item = {i.get("item_id"): i for i in items}
    source_rows = manifest.get("source_items", [])
    sources = {s.get("source_id"): s for s in source_rows if isinstance(s, dict)}
    if len(sources) != len(source_rows) or not sources or None in sources:
        errors.append("source_items require unique nonempty source_id records")
    for sid, source in sources.items():
        disposition = source.get("disposition")
        targets = source.get("item_ids", [])
        if not source.get("source_ref") or not source.get("reason") or disposition not in {"included", "merged", "withdrawn", "excluded"}:
            errors.append(f"{sid}: unresolved source disposition")
        if disposition in {"withdrawn", "excluded"}:
            if targets or not source.get("confirmation_ref"):
                errors.append(f"{sid}: withdrawn/excluded source requires confirmation and no deliverable mapping")
        elif not targets or not set(targets).issubset(by_item):
            errors.append(f"{sid}: source has missing or dangling item mapping")
        elif any(sid not in by_item[i].get("source_ids", []) for i in targets):
            errors.append(f"{sid}: source-to-item mapping is not reciprocal")
    for conflict in manifest.get("source_conflicts", []):
        if conflict.get("status") != "resolved" or not conflict.get("resolution_ref"):
            errors.append("unresolved material source conflict")
    evidence_ids = set()
    for item in items:
        iid = item.get("item_id")
        sids = item.get("source_ids", [])
        if not sids or not set(sids).issubset(sources):
            errors.append(f"{iid}: missing source correspondence")
        for sid in sids:
            source = sources.get(sid, {})
            if source.get("disposition") in {"withdrawn", "excluded"} or iid not in source.get("item_ids", []):
                errors.append(f"{iid}: withdrawn or unmapped source returned")
        approved = item.get("approved_content", {})
        if not item.get("approval_ref"):
            errors.append(f"{iid}: approved content source is missing")
        for field in APPROVED_FIELDS:
            if not approved.get(field) or normalized(approved[field]) != normalized(item.get(field)):
                errors.append(f"{iid}: unapproved change to {field}")
        numeric_tokens = re.findall(r"\d+(?:\.\d+)?\s*(?:mm|m²|m|%|dB|毫米|米|厘米|%)", item.get("opinion_text", ""))
        traced_values = {normalized(v.get("value")) for v in item.get("value_origins", [])}
        if any(normalized(token) not in traced_values for token in numeric_tokens):
            errors.append(f"{iid}: numeric opinion values need explicit origins")
        for value in item.get("value_origins", []):
            token = normalized(value.get("value"))
            if not token or not value.get("source_ref") or value.get("origin") not in {"reviewer_remedy", "code_requirement", "drawing_fact"}:
                errors.append(f"{iid}: unresolved numeric wording origin")
            elif value.get("origin") == "reviewer_remedy" and token in normalized(item.get("regulation_text")):
                errors.append(f"{iid}: reviewer remedy cannot be presented as a code minimum")
        for change in item.get("scope_changes", []):
            if change.get("included") is True and (change.get("status") != "approved" or not change.get("approval_ref")):
                errors.append(f"{iid}: unapproved cross-drawing scope expansion")
        claims = item.get("claims", [])
        by_claim = {c.get("claim_id"): c for c in claims}
        if len(by_claim) != len(claims) or not claims or None in by_claim:
            errors.append(f"{iid}: unique claim-to-evidence records required")
        for cid, claim in by_claim.items():
            if not claim.get("text_quote") or normalized(claim['text_quote']) not in normalized(item.get('opinion_text')) or not claim.get('object_label'):
                errors.append(f"{iid}/{cid}: claim does not match approved wording/object")
            if claim.get("requires_image") is not True and not claim.get("no_image_reason"):
                errors.append(f"{iid}/{cid}: image exemption needs a reason")
        visible = set()
        for evidence in item.get("evidence_images", []):
            eid = evidence.get("evidence_id")
            if not eid or eid in evidence_ids:
                errors.append(f"{iid}: duplicate or missing evidence_id")
            evidence_ids.add(eid)
            digest = evidence.get("image_sha256", "")
            if not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
                errors.append(f"{eid}: evidence image hash required")
            path = evidence.get("image_path")
            if path and (root/path).is_file() and hashlib.sha256((root/path).read_bytes()).hexdigest() != digest.lower():
                errors.append(f"{eid}: evidence image changed")
            for observed in evidence.get("observed_evidence", []):
                cid = observed.get("claim_id")
                if cid not in by_claim or observed.get("object_label") != by_claim.get(cid, {}).get("object_label"):
                    errors.append(f"{eid}: image object differs from opinion object")
                elif observed.get("visible") is True and observed.get("observation"):
                    visible.add(cid)
                else:
                    errors.append(f"{eid}: decisive evidence is not visibly verified")
            if not evidence.get("observed_evidence"):
                errors.append(f"{eid}: approved images are not exempt from correspondence checks")
            crop = evidence.get("word_crop", [0, 0, 0, 0])
            if not isinstance(crop,list) or len(crop)!=4 or any(not isinstance(x,(int,float)) or x<0 or x>=1 for x in crop) or crop[0]+crop[2]>=1 or crop[1]+crop[3]>=1:
                errors.append(f"{eid}: invalid Word crop fractions")
            if not isinstance(evidence.get("display_width_inches"),(int,float)) or evidence['display_width_inches']<=0:
                errors.append(f"{eid}: actual Word display width required")
            if evidence.get("strategy", "pdf_provenance") == "pdf_provenance":
                from evidence_geometry import geometry_errors
                errors.extend(f"{eid}: {message}" for message in geometry_errors(evidence))
        for cid, claim in by_claim.items():
            if claim.get("requires_image") is True and cid not in visible:
                errors.append(f"{iid}/{cid}: no image proves the required claim")
    history = manifest.get("evidence_history", [])
    history_ids = [row.get('evidence_id') for row in history]
    if len(history_ids)!=len(set(history_ids)):
        errors.append('duplicate evidence history IDs')
    for old in history:
        action = old.get("disposition")
        if action not in {"retained", "removed", "replaced"} or not old.get("reason") or not old.get("source_ref"):
            errors.append("unresolved previous image disposition")
        if action == "removed" and old.get("evidence_id") in evidence_ids:
            errors.append("removed image returned to deliverable")
        if action == "retained" and old.get("evidence_id") not in evidence_ids:
            errors.append("retained image is missing")
        if action == "replaced" and (not old.get("replacement_ids") or not set(old['replacement_ids']).issubset(evidence_ids)):
            errors.append("replacement image has no traceable destination")
    return errors


def docx_evidence_errors(doc, paragraphs, item):
    """Hash/order, Word crop, display size, and stale continuation checks."""
    errors=[];actual=[]
    for paragraph in paragraphs:
        for match in CONTINUATION.finditer(paragraph.text):
            if int(match.group(1)) != item['item_no']:
                errors.append(f"{item['item_id']}: stale continuation number {match.group(1)}")
        for drawing in paragraph._p.xpath('.//w:drawing'):
            blips=drawing.xpath('.//a:blip')
            if not blips:continue
            from docx.oxml.ns import qn
            part=doc.part.related_parts[blips[0].get(qn('r:embed'))]
            rects=drawing.xpath('.//a:srcRect')
            crop=[int(rects[0].get(k,'0'))/100000 for k in ['l','t','r','b']] if rects else [0,0,0,0]
            ext=drawing.xpath('.//wp:extent')
            width=int(ext[0].get('cx'))/914400 if ext else 0
            actual.append((hashlib.sha256(part.blob).hexdigest(),crop,width))
            if drawing.xpath('.//wp:anchor') and paragraph.text.strip():
                errors.append(f"{item['item_id']}: floating image anchored in text requires layout repair")
    expected=item.get('evidence_images',[])
    if len(actual)!=len(expected):return errors+['evidence count mismatch']
    for got,want in zip(actual,expected):
        if got[0]!=want.get('image_sha256','').lower():errors.append(f"{item['item_id']}: image hash/order mismatch")
        if got[1]!=want.get('word_crop',[0,0,0,0]):errors.append(f"{item['item_id']}: Word crop differs from approved evidence")
        if abs(got[2]-want.get('display_width_inches',0))>0.02:errors.append(f"{item['item_id']}: Word image display size changed")
    return errors
