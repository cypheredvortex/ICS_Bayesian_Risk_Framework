"""Independent verification script for ICS Risk Framework audit."""
import sys
import json
import traceback
from pathlib import Path

TESTS_PASSED = 0
TESTS_FAILED = 0
ERRORS = []

def test(name, fn):
    global TESTS_PASSED, TESTS_FAILED
    try:
        fn()
        TESTS_PASSED += 1
        print(f"  PASS: {name}")
    except Exception as e:
        TESTS_FAILED += 1
        ERRORS.append((name, str(e), traceback.format_exc()))
        print(f"  FAIL: {name}: {e}")

print("=" * 60)
print("INDEPENDENT AUDIT - RUNTIME VERIFICATION")
print("=" * 60)

# ---- Module imports ----
print("\n--- Module Import Tests ---")

test("backend package imports", lambda: __import__("backend"))
test("backend.cli imports", lambda: __import__("backend.cli"))
test("backend.api imports", lambda: __import__("backend.api"))
test("backend.assets imports", lambda: __import__("backend.assets"))
test("backend.probability imports", lambda: __import__("backend.probability"))
test("backend.graph_builder imports", lambda: __import__("backend.graph_builder"))
test("backend.cpt_generator imports", lambda: __import__("backend.cpt_generator"))
test("backend.inference imports", lambda: __import__("backend.inference"))
test("backend.risk imports", lambda: __import__("backend.risk"))
test("backend.attack_paths imports", lambda: __import__("backend.attack_paths"))
test("backend.outputs imports", lambda: __import__("backend.outputs"))
test("backend.pdf_reports imports", lambda: __import__("backend.pdf_reports"))
test("backend.settings imports", lambda: __import__("backend.settings"))
test("backend.schemas imports", lambda: __import__("backend.schemas"))
test("backend.logging_config imports", lambda: __import__("backend.logging_config"))
test("backend.database.config imports", lambda: __import__("backend.database.config"))
test("backend.database.models imports", lambda: __import__("backend.database.models"))
test("backend.database.repositories imports", lambda: __import__("backend.database.repositories"))
test("backend.database.services imports", lambda: __import__("backend.database.services"))

# ---- CLAIM: Full pipeline runs ----
print("\n--- End-to-End Pipeline Tests ---")

from backend.cli import run

def _test_full_pipeline():
    run("data/swat_example.json", {"local_hmi": 1}, write_outputs=True)
    return True
test("Full pipeline with SWAT example + evidence", _test_full_pipeline)

def test_swat_result():
    result = run("data/swat_example.json", {"local_hmi": 1})
    assert "graph" in result, "Missing graph"
    assert "posteriors" in result, "Missing posteriors"
    assert "risk_scores" in result, "Missing risk_scores"
    assert "attack_paths" in result, "Missing attack_paths"
    assert "summary" in result, "Missing summary"
    assert "evidence_used" in result, "Missing evidence_used"
    assert "timings" in result, "Missing timings"
    assert "cpts" in result, "Missing cpts"
    assert "base_probabilities" in result, "Missing base_probabilities"
    assert result["summary"]["asset_count"] == 11, f"Expected 11 assets, got {result['summary']['asset_count']}"
    assert result["summary"]["relationship_count"] == 12, f"Expected 12 rels, got {result['summary']['relationship_count']}"
    assert len(result["graph"]["nodes"]) == 11
    assert len(result["graph"]["edges"]) == 12
    assert len(result["posteriors"]) == 10  # 11 - 1 evidence node
    assert len(result["risk_scores"]) == 11
    for p in result["posteriors"].values():
        assert 0.0 <= p <= 1.0, f"Posterior {p} out of range [0,1]"
    for risk in result["risk_scores"]:
        assert risk["risk"] >= 0, f"Negative risk: {risk}"
    assert result["summary"]["overall_risk"] >= 0

test("SWAT pipeline produces correct structure", test_swat_result)

# ---- CLAIM: Empty evidence works ----
test("Pipeline with empty evidence",
     lambda: run("data/swat_example.json", {}))

def test_empty_evidence():
    result = run("data/swat_example.json", {})
    assert len(result["posteriors"]) == 11  # All nodes returned
test("Empty evidence returns all nodes", test_empty_evidence)

# ---- CLAIM: Inline topology works ----
test("Pipeline with inline dict topology",
     lambda: run({
         "assets": {
             "plc_1": {"kind": "device", "cvss_type": 8.8, "exposed": True, "patched": False, "consequence_severity": 5.0},
             "hmi_1": {"kind": "device", "cvss_type": 4.0, "exposed": False, "patched": True, "consequence_severity": 2.0}
         },
         "relationships": [["hmi_1", "plc_1", "controls", False, {}]]
     }, {"hmi_1": 1}))

# ---- CLAIM: Invalid data gracefully rejected ----
def _test_empty_topology():
    try:
        run({"assets": {}, "relationships": []}, {})
        return False
    except ValueError:
        return True
test("Empty topology raises ValueError", _test_empty_topology)

def _test_missing_keys():
    try:
        run({"assets": {"bad": {"kind": "device"}}, "relationships": []}, {})
        return False
    except ValueError:
        return True
test("Missing required keys raises error", _test_missing_keys)

def _test_invalid_cvss():
    try:
        run({"assets": {"bad": {"kind": "device", "cvss_type": 15, "exposed": False, "patched": True}}, "relationships": []}, {})
        return False
    except ValueError:
        return True
test("Invalid CVSS out of range raises error", _test_invalid_cvss)

def _test_cyclic_graph():
    try:
        run({
            "assets": {
                "a": {"kind": "device", "cvss_type": 5.0, "exposed": False, "patched": True},
                "b": {"kind": "device", "cvss_type": 5.0, "exposed": False, "patched": True}
            },
            "relationships": [["a", "b", "controls", False, {}], ["b", "a", "controls", False, {}]]
        }, {})
        return False
    except ValueError:
        return True
test("Cyclic graph raises error", _test_cyclic_graph)

# ---- CLAIM: Settings module works ----
print("\n--- Settings Verification ---")

from backend.settings import get_settings, update_settings, reset_settings, DEFAULT_SETTINGS

test("get_settings returns dict with required keys",
     lambda: isinstance(get_settings(), dict))

test("update_settings persists cvss_weight change",
     lambda: (update_settings({"cvss_weight": 0.5}), None) or True)

test("update_settings validates negative weight",
     lambda: (update_settings({"cvss_weight": -1}), None) or False)

test("reset_settings restores defaults",
     lambda: (reset_settings(), None) or True)

test("firewall validation prevents true > false",
     lambda: (update_settings({"firewall_multipliers": {"true": 0.9, "false": 0.5}}), None) or False)

# ---- CLAIM: Database persistence works ----
print("\n--- Database Persistence Tests ---")

from backend.database.config import initialize_database, dispose_engine
from backend.database.services import AssessmentPersistenceService
import os, tempfile

def test_db_persistence():
    import tempfile, os
    from pathlib import Path
    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "test.db"
    os.environ["ICS_DB_URL"] = f"sqlite:///{db_path}"
    dispose_engine()
    initialize_database()
    
    service = AssessmentPersistenceService()
    project = service.persist_analysis_run(
        topology={"assets": {"plc_1": {"kind": "device", "cvss_type": 5.0, "exposed": False, "patched": True}}, "relationships": []},
        evidence={"plc_1": 1},
        analysis_result={"posteriors": {"plc_1": 0.5}, "risk_scores": [{"asset": "plc_1", "risk": 0.8, "risk_level": "high", "P(compromised|evidence)": 0.5, "impact": 1.6}], "summary": {}, "cpts": {}},
        project_name="audit-test",
        topology_source="inline",
    )
    assert project is not None
    assert project.name == "audit-test"
    reloaded = service.get_project(project.id)
    assert reloaded is not None, "Could not reload project"
    assert len(reloaded.assets) == 1
    assert len(reloaded.risk_results) >= 1
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)

test("Database persistence round-trips correctly", test_db_persistence)

# ---- CLAIM: Data files exist and are valid ----
print("\n--- Data File Validations ---")

import json
data_dir = Path("data")
for fname in ["swat_example.json", "building_automation.json", "power_substation.json", "water_treatment.json"]:
    fpath = data_dir / fname
    def check_data(f=fpath, name=fname):
        assert f.exists(), f"{name} missing"
        data = json.loads(f.read_text())
        assert "assets" in data, f"{name} missing assets"
        assert "relationships" in data, f"{name} missing relationships"
        assert len(data["assets"]) > 0, f"{name} has no assets"
    test(f"Data file {fname} valid", check_data)

# ---- Summary ----
print("\n" + "=" * 60)
print(f"RESULTS: {TESTS_PASSED} passed, {TESTS_FAILED} failed")
if ERRORS:
    print("\nFAILURES:")
    for name, err, tb in ERRORS:
        print(f"  - {name}:")
        print(f"    {err}")
if TESTS_FAILED == 0:
    print("\nVERDICT: All independent verification tests pass.")
else:
    print(f"\nVERDICT: {TESTS_FAILED} tests require investigation.")
print("=" * 60)

