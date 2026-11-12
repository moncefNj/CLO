#!/usr/bin/env python3
"""
clo_inputs.py -- plain inputs for CLO, no RDF needed.

CLO's knowledge base is an OWL A-Box, but a governance team does not have to write Turtle. This
tool turns two plain files into that A-Box:

  organisation.yaml   who needs which key and why: roles and the keys they need, policies and the
                      roles they serve, where each policy is attached (organisation, OU, account,
                      team or category), teams and the roles they play, how a missing value may be
                      filled in (value sources), and which spellings mean the same key (synonyms).
                      Optional: `what_if` scenarios for CLO Studio and a guided `tour`.
  inventory.csv       one row per resource, as an inventory export gives it:
                      id, type, account, owner, complete, tags[, part_of]
                        type      catalogue type name, e.g. aws_ec2_instance, gcp_bucket
                                  (ontology/clo_types*.ttl; `--list-types` prints them)
                        owner     owning team; several teams separated by "+"; empty if none
                        complete  true if the provider response shows the whole tag set,
                                  false if the listing may have omitted tags (no verdict)
                        tags      key=value pairs separated by ";"
                        part_of   id of the parent resource (composition), optional

  python3 tools/clo_inputs.py --org examples/studio/organisation.yaml \
      --inventory examples/studio/inventory.csv --out /tmp/abox.ttl
  python3 tools/clo_inputs.py --list-types | grep -i bucket

The same files drive CLO Studio (tools/clo_demo.py --org ... --inventory ...).
tests/test_inputs.py checks that examples/studio/ yields exactly the findings of
examples/company_example.ttl.
"""
import argparse
import csv
import os
import re
import sys

import rdflib
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ONTO = os.path.join(ROOT, "ontology")
CLO = "http://example.org/clo/ontology/clo#"
C = rdflib.Namespace(CLO)
PREFIX = (f"@prefix clo: <{CLO}> .\n@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
          "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
          "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n")
COLUMNS = ["id", "type", "account", "owner", "complete", "tags"]
VALUE_SOURCES = {"inherit", "account-default", "team-default"}


class InputError(ValueError):
    pass


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", str(s)).strip("_").lower() or "x"


def lit(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _catalogue():
    g = rdflib.Graph()
    for f in ("clo_types.ttl", "clo_types_ext.ttl", "clo_org.ttl", "clo_ontology_v8.ttl"):
        p = os.path.join(ONTO, f)
        if os.path.exists(p):
            g.parse(p)
    types = {str(n): t for t, n in g.subject_objects(C.resourceTypeName)}
    roles = {str(l).lower(): r for r in g.subjects(rdflib.RDF.type, C.GovernanceRole) for l in g.objects(r, rdflib.RDFS.label)}
    cats = {str(c).split("#")[-1].lower(): c for c in g.subjects(rdflib.RDF.type, C.FunctionalCategory)}
    return types, roles, cats


_CAT = None


def catalogue():
    global _CAT
    if _CAT is None:
        _CAT = _catalogue()
    return _CAT


class Names:
    """Stable IRIs from names; the built-in roles of clo_org.ttl are reused by label."""

    def __init__(self):
        self.types, self.builtin_roles, self.cats = catalogue()

    def role(self, name):
        r = self.builtin_roles.get(str(name).lower())
        return f"<{r}>" if r is not None else f"clo:role_{slug(name)}"

    key = staticmethod(lambda n: f"clo:k_{slug(n)}")
    value = staticmethod(lambda n: f"clo:v_{slug(n)}")
    policy = staticmethod(lambda n: f"clo:pol_{slug(n)}")
    team = staticmethod(lambda n: f"clo:team_{slug(n)}")
    unit = staticmethod(lambda n: f"clo:org_{slug(n)}")
    res = staticmethod(lambda n: f"clo:res_{slug(n)}")


def load_org(path):
    org = yaml.safe_load(open(path)) or {}
    if not isinstance(org, dict) or "organisation" not in org:
        raise InputError(f"{path}: expected a mapping with at least `organisation: <name>`")
    return org


def read_inventory(path):
    rows = list(csv.DictReader(open(newline="", file=path)))
    if rows:
        missing = [c for c in COLUMNS if c not in rows[0]]
        if missing:
            raise InputError(f"{path}: missing column(s) {', '.join(missing)}; expected {', '.join(COLUMNS)}[, part_of]")
    return rows


def parse_tags(s, where):
    out = []
    for part in [p.strip() for p in (s or "").split(";") if p.strip()]:
        if "=" not in part:
            raise InputError(f"{where}: tag '{part}' is not key=value")
        k, v = part.split("=", 1)
        out.append((k.strip(), v.strip()))
    return out


def _org_entities(org, N):
    """name -> IRI for every place a policy can be attached."""
    root = org["organisation"]
    places = {root: N.unit(root)}
    for u in (org.get("units") or {}):
        places[u] = N.unit(u)
    for a in (org.get("accounts") or {}):
        places[a] = f"clo:acct_{slug(a)}"
    for t in (org.get("teams") or {}):
        places[t] = N.team(t)
    return places


def org_turtle(org, N=None, fragment=False):
    """The organisational A-Box. With fragment=True (what-if scenarios) only what is given is emitted."""
    N = N or Names()
    L = []
    root = org.get("organisation")
    keys = set()
    for ks in (org.get("roles") or {}).values():
        keys |= set(ks or [])
    keys |= set((org.get("keys") or {}).keys())
    for canon, members in (org.get("synonyms") or {}).items():
        keys |= {canon, *(members or [])}
    for k in sorted(keys):
        L.append(f"{N.key(k)} a clo:LabelKey , owl:NamedIndividual ; clo:keyName {lit(k)} .")
    for k, srcs in sorted((org.get("keys") or {}).items()):
        srcs = srcs or []
        bad = set(srcs) - VALUE_SOURCES
        if bad:
            raise InputError(f"key {k}: unknown value source(s) {sorted(bad)}; use {sorted(VALUE_SOURCES)}")
        if srcs:
            L.append(f"{N.key(k)} clo:valueSource " + " , ".join(lit(s) for s in srcs) + " .")
    for r, ks in (org.get("roles") or {}).items():
        iri = N.role(r)
        if iri.startswith("clo:"):
            L.append(f"{iri} a clo:GovernanceRole , owl:NamedIndividual ; rdfs:label {lit(r)} .")
        if ks:
            L.append(f"{iri} clo:needsLabel " + " , ".join(N.key(k) for k in ks) + " .")
    for canon, members in (org.get("synonyms") or {}).items():
        L.append(f"clo:sg_{slug(canon)} a clo:SynonymGroup , owl:NamedIndividual ; clo:canonicalKey {lit(canon)} ; "
                 f"clo:hasMember " + " , ".join(N.key(k) for k in [canon, *(members or [])]) + " .")
    if not fragment:
        L.append(f"{N.unit(root)} a clo:OrganizationalRoot , owl:NamedIndividual ; rdfs:label {lit(root)} .")
        for u, parent in (org.get("units") or {}).items():
            L.append(f"{N.unit(u)} a clo:OrganizationalUnit , owl:NamedIndividual ; rdfs:label {lit(u)} ; "
                     f"clo:orgPartOf {N.unit(parent or root)} .")
        for a, parent in (org.get("accounts") or {}).items():
            L.append(f"clo:acct_{slug(a)} a clo:Account , owl:NamedIndividual ; rdfs:label {lit(a)} ; "
                     f"clo:orgPartOf {N.unit(parent or root)} .")
        for t, spec in (org.get("teams") or {}).items():
            plays = (spec or {}).get("plays") or []
            L.append(f"{N.team(t)} a clo:Team , owl:NamedIndividual ; rdfs:label {lit(t)}"
                     + (" ; clo:playsRole " + " , ".join(N.role(r) for r in plays) if plays else "") + " .")
        if org.get("ownership_from_key"):
            L.append(f"{N.unit(root)} clo:ownershipFromKey {N.key(org['ownership_from_key'])} .")
    places = _org_entities(org, N) if not fragment else None
    for p, spec in (org.get("policies") or {}).items():
        spec = spec or {}
        serves = spec.get("serves") or []
        if fragment and not serves:
            continue
        head = f"{N.policy(p)}" if fragment else f"{N.policy(p)} a clo:LabelingPolicy , owl:NamedIndividual ; rdfs:label {lit(p)}"
        L.append(head + (" ; " if not fragment and serves else " " if serves else "")
                 + ("clo:servesRole " + " , ".join(N.role(r) for r in serves) if serves else "") + " .")
        for where in spec.get("attached_to") or []:
            if str(where).lower().startswith("category:"):
                c = N.cats.get(str(where).split(":", 1)[1].strip().lower())
                if c is None:
                    raise InputError(f"policy {p}: unknown category in '{where}'; known: {', '.join(sorted(N.cats))}")
                L.append(f"{N.policy(p)} clo:appliesToCategory <{c}> .")
            else:
                if places is None or where not in places:
                    raise InputError(f"policy {p}: attached to '{where}', which is not the organisation, a unit, an account or a team")
                L.append(f"{places[where]} clo:governedBy {N.policy(p)} .")
    return "\n".join(L) + "\n"


def inventory_turtle(rows, org, N=None, where="inventory"):
    N = N or Names()
    accounts = set((org.get("accounts") or {}).keys())
    teams = set((org.get("teams") or {}).keys())
    ids = {r["id"].strip() for r in rows}
    L, values = [], set()
    for i, r in enumerate(rows, start=2):
        loc = f"{where}, line {i}"
        rid, t = r["id"].strip(), r["type"].strip()
        if not rid:
            raise InputError(f"{loc}: empty id")
        if t not in N.types:
            near = [n for n in N.types if t.split("_")[-1] in n][:5]
            raise InputError(f"{loc}: unknown type '{t}'" + (f"; did you mean {', '.join(near)}?" if near else
                                                            "; see tools/clo_inputs.py --list-types"))
        acct = r["account"].strip()
        if acct not in accounts:
            raise InputError(f"{loc}: account '{acct}' is not declared under `accounts` in the organisation file")
        owners = [o.strip() for o in (r.get("owner") or "").split("+") if o.strip()]
        for o in owners:
            if o not in teams:
                raise InputError(f"{loc}: owner '{o}' is not declared under `teams`")
        comp = (r.get("complete") or "").strip().lower()
        if comp not in ("true", "false"):
            raise InputError(f"{loc}: complete must be true or false")
        tags = parse_tags(r.get("tags"), loc)
        parts = [f"{N.res(rid)} a clo:CloudResource , owl:NamedIndividual", f"clo:resourceId {lit(rid)}",
                 f"clo:hasResourceType <{N.types[t]}>", f"clo:belongsToAccount clo:acct_{slug(acct)}"]
        parts += [f"clo:ownedBy {N.team(o)}" for o in owners]
        parts.append(f"clo:recordComplete {comp}")
        par = (r.get("part_of") or "").strip()
        if par:
            if par not in ids:
                raise InputError(f"{loc}: part_of '{par}' is not a resource id of the inventory")
            parts.append(f"clo:partOf {N.res(par)}")
        labs = [f"clo:l_{slug(rid)}_{j}" for j in range(1, len(tags) + 1)]
        if labs:
            parts.append("clo:hasLabel " + " , ".join(labs))
        L.append(" ;\n    ".join(parts) + " .")
        for lab, (k, v) in zip(labs, tags):
            L.append(f"{lab} a clo:Label , owl:NamedIndividual ; clo:hasLabelKey {N.key(k)} ; clo:hasLabelValue {N.value(v)} .")
            L.append(f"{N.key(k)} a clo:LabelKey , owl:NamedIndividual ; clo:keyName {lit(k)} .")
            values.add(v)
    for v in sorted(values):
        L.append(f"{N.value(v)} a clo:LabelValue , owl:NamedIndividual ; clo:valueName {lit(v)} .")
    return "\n".join(L) + "\n"


def abox(org_path, inv_path, name="clo-input"):
    org, rows = load_org(org_path), read_inventory(inv_path)
    N = Names()
    return (PREFIX + f"<{CLO}{slug(name)}> a owl:Ontology .\n\n# organisation: {os.path.basename(org_path)}\n"
            + org_turtle(org, N) + f"\n# inventory: {os.path.basename(inv_path)}\n"
            + inventory_turtle(rows, org, N, where=os.path.basename(inv_path)))


def whatif_turtle(org, wi, name):
    frag = {"roles": wi.get("roles"), "keys": wi.get("keys"), "synonyms": wi.get("synonyms"),
            "policies": {p: {"serves": (s or {}).get("serves")} for p, s in (wi.get("policies") or {}).items()}}
    return PREFIX + f"<{CLO}{slug(name)}> a owl:Ontology .\n" + org_turtle(frag, Names(), fragment=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--org")
    ap.add_argument("--inventory")
    ap.add_argument("--out", default="-")
    ap.add_argument("--list-types", action="store_true", help="print the catalogue type names and exit")
    a = ap.parse_args()
    if a.list_types:
        print("\n".join(sorted(catalogue()[0])))
        return
    if not (a.org and a.inventory):
        ap.error("--org and --inventory are required")
    try:
        ttl = abox(a.org, a.inventory)
    except InputError as e:
        sys.exit(f"error: {e}")
    if a.out == "-":
        sys.stdout.write(ttl)
    else:
        open(a.out, "w").write(ttl)
        print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
