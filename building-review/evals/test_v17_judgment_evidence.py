"""Anonymous paired regression cases for v1.7 judgment gates and report integration."""
from pathlib import Path
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from judgment_evidence import validate_data, numeric_result, placeholders


def fixture():
    rule = {"rule_id": "TEST", "required_facts": ["Observed dimension"], "judgment_requirements": {
        "obligations": [{"id": "height", "kind": "numeric", "operator": ">=", "threshold": "2000", "unit": "mm"}]}}
    check = {"check_id": "C1", "rule_id": "TEST", "decision_state": "resolved", "applicability": "适用", "conclusion": "符合", "fact_ids": "F1"}
    facts = {"F1": {"value": "2.0", "unit": "m", "needs_verification": "no"}}
    data = {"schema_version": "1.0", "checks": [{"check_id": "C1", "object_id": "shower-A", "obligations": [
        {"id": "height", "fact_ids": ["F1"], "observation": "Height dimension 2.0 m at shower wall", "reason": "2.0 m equals 2000 mm", "result": "pass"}
    ], "counterevidence": {"fact_ids": ["F1"], "finding": "consistent", "reason": "Compared note and local dimension"}}], "issue_screening": []}
    return data, [check], {"TEST": rule}, facts, [], {}


class JudgmentTests(unittest.TestCase):
    def test_valid_numeric_and_units(self):
        self.assertEqual(validate_data(*fixture()), [])

    def test_1800_cannot_pass_2000(self):
        args=fixture();args[3]["F1"]["value"]="1.8"
        self.assertTrue(any("numeric comparison" in e for e in validate_data(*args)))

    def test_noncompliant_numeric_can_close(self):
        args=fixture();args[3]["F1"]["value"]="1.8";args[1][0]["conclusion"]="不符合"
        args[0]["checks"][0]["obligations"][0]["result"]="fail"
        self.assertEqual(validate_data(*args), [])

    def test_slope_wrong_and_correct(self):
        rule={"operator": ">=", "threshold": "5", "unit": "%"}
        self.assertEqual(numeric_result({"value":"1","unit":"%"},rule),"fail")
        self.assertEqual(numeric_result({"value":"0.05","unit":"ratio"},rule),"pass")

    def test_width_not_height(self):
        args=fixture();args[0]["checks"][0]["obligations"][0]["id"]="width"
        self.assertTrue(any("incomplete" in e for e in validate_data(*args)))

    def test_multiple_obligations(self):
        args=fixture();args[2]["TEST"]["judgment_requirements"]["obligations"].append({"id":"sign","kind":"judgment"})
        self.assertTrue(validate_data(*args))
        args[0]["checks"][0]["obligations"].append({"id":"sign","fact_ids":["F1"],"observation":"Sign is located above exit","reason":"Compared sign location","result":"pass"})
        self.assertEqual(validate_data(*args),[])

    def test_no_issue_does_not_prove_compliant(self):
        args=fixture();args[0]["checks"][0]["obligations"][0]["fact_ids"]=[]
        self.assertTrue(any("missing check-specific" in e for e in validate_data(*args)))

    def test_missing_observation(self):
        args=fixture();args[0]["checks"][0]["obligations"][0]["observation"]=""
        self.assertTrue(validate_data(*args))

    def test_unresolved_fact(self):
        args=fixture();args[3]["F1"]["needs_verification"]="yes"
        self.assertTrue(validate_data(*args))

    def test_conclusion_cannot_override_result(self):
        args=fixture();args[1][0]["conclusion"]="不符合"
        self.assertTrue(any("conclusion conflicts" in e for e in validate_data(*args)))

    def test_counterevidence(self):
        args=fixture();args[0]["checks"][0]["counterevidence"]["finding"]="conflict"
        self.assertTrue(validate_data(*args))
        args[0]["checks"][0]["counterevidence"]["finding"]="none_found"
        self.assertEqual(validate_data(*args),[])

    def test_already_present(self):
        args=fixture();args[0]["checks"][0]["assertion"]="absent"
        args[0]["checks"][0]["counterevidence"]["observed"]="present"
        self.assertTrue(any("already present" in e for e in validate_data(*args)))

    def test_invalid_units(self):
        args=fixture();args[3]["F1"]["unit"]="dB"
        self.assertTrue(any("incompatible units" in e for e in validate_data(*args)))

    def test_cannot_waive_applicable_requirement(self):
        args=fixture();args[0]["checks"][0]["obligations"][0]["result"]="not_applicable"
        self.assertTrue(any("cannot be waived" in e for e in validate_data(*args)))

    def test_unknown_stays_open(self):
        args=fixture();args[0]["checks"][0]["obligations"][0]["result"]="unknown"
        self.assertTrue(validate_data(*args))

    def test_room_window_association(self):
        args=fixture();rule=args[2]["TEST"];rule["judgment_requirements"]["object_linkage"]="room_window"
        record=args[0]["checks"][0];record["object_id"]="bedroom-A";record["association_observation"]="Opening W-A is in wall A bounding bedroom A"
        record["object_links"]=[]
        for role, obj, parent in [("room","bedroom-A",""),("exterior_wall","wall-A","bedroom-A"),("window_position","window-A","wall-A"),("window_mark","window-A",""),("schedule","window-A","")]:
            fid="F-"+role;gid="G-"+role;args[3][fid]={"needs_verification":"no"}
            args[5][gid]={"check_id":"C1","fact_ids":fid}
            record["object_links"].append({"role":role,"object_id":obj,"related_object_id":parent,"fact_id":fid,"chain_id":gid,"mark":"W-A"})
        self.assertEqual(validate_data(*args),[])
        record["object_links"][2]["related_object_id"]="bathroom-wall"
        self.assertTrue(any("another wall or room" in e for e in validate_data(*args)))

    def test_client_data_vs_design(self):
        args=fixture();args[4].append({"issue_id":"I1","status":"ai_ready"})
        row={"issue_id":"I1","responsibility":"client_data","reason":"Owner investigation needed","delivery_decision":"include","design_action":"Obtain data"}
        args[0]["issue_screening"].append(row)
        self.assertTrue(validate_data(*args))
        args[4][0]["status"]="rejected";row["delivery_decision"]="exclude"
        self.assertEqual(validate_data(*args),[])
        args[4][0]["status"]="ai_ready";row.update(responsibility="design",delivery_decision="include",design_action="Resolve architectural detail using supplied data")
        self.assertEqual(validate_data(*args),[])
        row["value_basis"]="index_difficulty_only"
        self.assertTrue(validate_data(*args))

    def test_placeholders_never_close_checks(self):
        args=fixture();data=placeholders(args[1],args[2])
        self.assertEqual(data["checks"][0]["obligations"][0]["result"],"unknown")
        self.assertTrue(validate_data(data,*args[1:]))

    def test_no_duplicate_or_dangling(self):
        args=fixture();args[0]["checks"].append(copy.deepcopy(args[0]["checks"][0]))
        self.assertTrue(validate_data(*args))

    def test_manual_gap_routes(self):
        from review_rules import applicable_rules
        from test_v16_ai_initial_review import complete_profile
        with tempfile.TemporaryDirectory() as value:
            profile_path=Path(value)/'profile.json'
            from create_review_workspace import initial_profile
            profile_path.write_text(json.dumps(initial_profile('single','1.7')),encoding='utf-8')
            complete_profile(profile_path)
            profile=json.loads(profile_path.read_text(encoding='utf-8'))
            profile['facts']['building_use'].update(status='known',value='住宅')
            profile['facts']['location_province'].update(status='known',value='湖南')
            profile['facts']['wet_rooms'].update(status='known',value=True)
            catalog=json.loads((ROOT/'generated/review-rules.json').read_text(encoding='utf-8'))
            routed={r['rule_id'] for family in ['设计说明','目录索引','平面图','墙身大样','其他大样','材料做法表','门窗表','楼梯大样'] for r,state in applicable_rules(catalog,profile,family,'single')}
            expected={'DEPTH-SPECIALTY-NOTES-COORDINATION','GREEN-HUNAN-ARTICLE12-DESIGN-NOTES','WATER-4.1.1-SPECIAL-DESIGN','WATER-4.6.4-WALL-UPTURN-HEIGHT','RES-4.2.2-STAIR-HORIZONTAL-HANDRAIL','ENV-2.1.3-EXTERNAL-NOISE','RES-6.1.2-PARTITION-ACOUSTICS','RES-6.1.3-FACADE-ACOUSTICS','ENERGY-1.0.2-CURRENT-BASIS','FIRE-7.1.5-EGRESS-CLEARANCE','RES-4.1.14-NEW-DWELLING-DOOR','WATER-4.5.3-WINDOW-SILL-SLOPE','WATER-4.5.3-WINDOW-HEAD-DRIP'}
            self.assertFalse(expected-routed,expected-routed)


def integration():
    from test_v16_ai_initial_review import make_rule_assets, build_workspace, run, read_rows
    from validate_review_package import workspace_input_hashes
    with tempfile.TemporaryDirectory(prefix="review-v17-") as temp:
        root=Path(temp);_,catalog,index=make_rule_assets(root)
        workspace,_=build_workspace(root/'single',"single",catalog,index)
        manifest_path=workspace/'review_manifest.json'
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest['schema_version']='1.7'
        manifest_path.write_text(json.dumps(manifest,ensure_ascii=False),encoding='utf-8')
        checks=read_rows(workspace/'check_matrix.csv');rules={r['rule_id']:r for r in json.loads(catalog.read_text(encoding='utf-8'))['rules']}
        data=placeholders(checks,rules);r=data['checks'][0];r['object_id']='anonymous-object'
        for o in r['obligations']:o.update(fact_ids=['F001'],observation='Anonymous source explicitly conflicts with example requirement',reason='Compared source text with example requirement',result='fail')
        r['counterevidence']={'fact_ids':['F001'],'finding':'consistent','reason':'Checked the full anonymous source text'}
        data['issue_screening']=[{'issue_id':'AI-001','responsibility':'design','delivery_decision':'include','design_action':'Correct the anonymous architectural detail','reason':'Specific demonstrated contradiction'}]
        path=workspace/'judgment_evidence.json';path.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        run([sys.executable,str(ROOT/'scripts/audit_review_completeness.py'),str(workspace)])
        self_hash=workspace_input_hashes(workspace);assert 'judgment_evidence.json' in self_hash
        report=run([sys.executable,str(ROOT/'scripts/generate_review_report.py'),str(workspace)])
        docx=Path(report.stdout.strip().splitlines()[-1]);run([sys.executable,str(ROOT/'scripts/validate_docx_content.py'),str(workspace),str(docx)])
        output=os.environ.get('BUILDING_REVIEW_V17_ARTIFACT_DIR')
        if output:
            target=Path(output);target.mkdir(parents=True,exist_ok=True);shutil.copy2(docx,target/'building-review-v17.docx')
        data['checks'][0]['counterevidence']['finding']='conflict';path.write_text(json.dumps(data),encoding='utf-8')
        run([sys.executable,str(ROOT/'scripts/validate_review_package.py'),str(workspace)],1,'counterevidence conflict')
        run([sys.executable,str(ROOT/'scripts/generate_review_report.py'),str(workspace)],1)
    print('PASS: v1.7 complete package, report generation, stale audit and counterevidence blocking')


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(JudgmentTests)
    if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():raise SystemExit(1)
    integration()
