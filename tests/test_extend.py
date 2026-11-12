#!/usr/bin/env python3
"""
test_extend.py -- extending CLO is data, not rules (paper, Listing 1).

examples/extend/private_cloud.ttl adds a provider with its constraints, a resource type mapped to an
existing base kind, a new base kind in an existing category, and an internal key with the role that
needs it, its value source and a spelling variant. No rule is edited. Checks: CLO-R derives provider,
category, base kind, scope and the new requirement; the audit reports the new key and its variant;
HermiT (if Java is available) derives the same operative entailments.

  python3 tests/test_extend.py            # from the repository root
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clo import audit, kb  # noqa: E402

C = "http://example.org/clo/ontology/clo#"
T = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
EX = [os.path.join(kb.ROOT, "examples", "company_example.ttl"),
      os.path.join(kb.ROOT, "examples", "extend", "private_cloud.ttl")]
fails = 0


def check(name, ok):
    global fails
    print(("PASS " if ok else "FAIL ") + name)
    fails += not ok


st, _ = kb.run_clo_r(EX)
E = kb.entailments_store(st)


def has(s, p, o):
    return (C + s, p if p.startswith("http") else C + p, C + o) in E


check("new type: provider, base kind and category derived (C-1, C-6, C-2)",
      has("os_vm", "hostedBy", "PrivateCloud") and has("os_vm", "hasBaseKind", "InstanceKind")
      and has("os_vm", "belongsToCategory", "Compute"))
check("new base kind: category derived, resource in audit scope",
      has("lic_db", "belongsToCategory", "Governance") and has("lic_db", T, "AuditableResource"))
check("new role: shared standard now requires retention (C-9)", has("pol_shared", "requiresLabel", "k_retention"))
check("new account: shared policy reaches it through the organisation (C-4)", has("lic_db", "governedBy", "pol_shared"))
F = audit.Audit(st).run()
check("audit: keep-until reported as a variant of retention for Compliance",
      any(f["rule"] == "I-22" and f["r"] == C + "os_vm" and f.get("used") == "keep-until"
          and f.get("roles") == ["Compliance"] for f in F))
check("audit: retention missing on the licence, value asked from the owner",
      any(f["rule"] == "I-07" and f["r"] == C + "lic_db" and f.get("k") == C + "k_retention"
          and f["repair"][0] == "ask-owner" for f in F))
if shutil.which("java"):
    g, info = kb.materialise("hermit", EX, timeout=900)
    check("HermiT: consistent, same operative entailments as CLO-R", g is not None and kb.entailments(g) == E)
else:
    print("SKIP HermiT (no Java)")
print(f"\n{fails} failure(s)")
sys.exit(1 if fails else 0)
