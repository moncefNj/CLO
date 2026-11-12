#!/usr/bin/env python3
"""
test_inputs.py -- plain inputs (organisation.yaml + inventory.csv) are equivalent to the Turtle A-Box.

examples/studio/ restates examples/company_example.ttl without RDF. Checks: same findings, root causes
and role coverage (resource IRIs aside); the what-if fragments parse; malformed inputs are rejected
with a message that names the line and the problem.

  python3 tests/test_inputs.py            # from the repository root
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import rdflib  # noqa: E402
from tools import clo_audit, clo_inputs  # noqa: E402

ORG = os.path.join(ROOT, "examples", "studio", "organisation.yaml")
INV = os.path.join(ROOT, "examples", "studio", "inventory.csv")
fails = 0


def check(name, ok):
    global fails
    print(("PASS " if ok else "FAIL ") + name)
    fails += not ok


tmp = tempfile.mkdtemp()
ab = os.path.join(tmp, "abox.ttl")
open(ab, "w").write(clo_inputs.abox(ORG, INV))
a, _ = clo_audit.run([os.path.join(ROOT, "examples", "company_example.ttl")], os.path.join(tmp, "a"))
b, _ = clo_audit.run([ab], os.path.join(tmp, "b"))
norm = lambda r: sorted(json.dumps({k: v for k, v in f.items() if k != "iri"}, sort_keys=True, default=str)
                        for f in r["findings"])
check("same findings as company_example.ttl", norm(a) == norm(b))
check("same root-cause counts", a["root_cause_counts"] == b["root_cause_counts"])
check("same role coverage", a["role_coverage"] == b["role_coverage"])
org = clo_inputs.load_org(ORG)
ok = True
for wi in org.get("what_if", []):
    try:
        rdflib.Graph().parse(data=clo_inputs.whatif_turtle(org, wi, "wi-" + wi["id"]), format="turtle")
    except Exception:
        ok = False
check("what-if fragments are valid Turtle", ok)


def rejects(csv_text, needle):
    p = os.path.join(tmp, "bad.csv")
    open(p, "w").write("id,type,account,owner,complete,tags\n" + csv_text + "\n")
    try:
        clo_inputs.abox(ORG, p)
    except clo_inputs.InputError as e:
        return needle in str(e) and "line 2" in str(e)
    return False


check("unknown type rejected, with suggestions", rejects("x,aws_ec2_instanse,aws-prod,Data,true,", "unknown type"))
check("undeclared account rejected", rejects("x,aws_ec2_instance,aws-dev,Data,true,", "account 'aws-dev'"))
check("undeclared team rejected", rejects("x,aws_ec2_instance,aws-prod,Sales,true,", "owner 'Sales'"))
check("malformed tag rejected", rejects("x,aws_ec2_instance,aws-prod,Data,true,env", "not key=value"))
print(f"\n{fails} failure(s)")
sys.exit(1 if fails else 0)
