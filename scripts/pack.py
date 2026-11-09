#!/usr/bin/env python3
"""app-research pack helper: init, log sources and evidence, mask images, coverage, validate.

Python 3.9+, stdlib only (Pillow optional for `mask`). Run from the project root.
The active pack root is remembered in ./.app-research (one line: the root path);
every command also accepts --root to override it.
"""
import argparse
import json
import os
import re
import shutil
import sys
from collections import defaultdict
from datetime import date

POINTER = ".app-research"
KINDS = ["screen", "nav", "field", "control", "table", "workflow", "rule", "state",
         "role", "message", "api", "report", "look"]
TYPES = ["help", "guide", "pdf", "video", "api", "forum", "customer", "course",
         "release-notes", "other"]
PII_PATTERNS = [
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("phone", re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)")),
    ("ssn", re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")),
]
# Vendor/support addresses are not personal data; allow them in source URLs only.


def die(msg):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(1)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def resolve_root(args):
    if getattr(args, "root", None):
        return args.root
    if os.path.exists(POINTER):
        with open(POINTER) as f:
            return f.read().strip()
    die("no pack yet: run `pack.py init --app ... --edition ...` first")


def load_pack(root):
    p = os.path.join(root, "pack.json")
    if not os.path.exists(p):
        die("no pack.json in " + root)
    with open(p) as f:
        return json.load(f)


def save_pack(root, pack):
    with open(os.path.join(root, "pack.json"), "w") as f:
        json.dump(pack, f, indent=2)
        f.write("\n")


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def append_jsonl(path, row):
    with open(path, "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_component(spec):
    if ":" in spec:
        cid, name = spec.split(":", 1)
    else:
        cid, name = spec, spec
    return {"id": cid.strip(), "name": name.strip(), "checklist": []}


# ---------------------------------------------------------------- commands

def cmd_init(args):
    root = args.root or os.path.join("research", slug(args.app))
    pj = os.path.join(root, "pack.json")
    if os.path.exists(pj):
        print("pack exists at %s: resuming" % root)
        with open(POINTER, "w") as f:
            f.write(root + "\n")
        return cmd_status(argparse.Namespace(root=root))
    for d in ["components", "media/raw", "media/masked"]:
        os.makedirs(os.path.join(root, d), exist_ok=True)
    pack = {"app": args.app, "edition": args.edition, "created": str(date.today()),
            "phase": "intake", "components": [parse_component(c) for c in (args.components or [])]}
    save_pack(root, pack)
    for name in ["sources.jsonl", "evidence.jsonl"]:
        open(os.path.join(root, name), "a").close()
    # keep raw media local
    gi = os.path.join(root, ".gitignore")
    with open(gi, "w") as f:
        f.write("media/raw/\n")
    with open(POINTER, "w") as f:
        f.write(root + "\n")
    for c in pack["components"]:
        os.makedirs(os.path.join(root, "components", c["id"]), exist_ok=True)
    print("init OK: %s (%s, %s), %d components" % (root, args.app, args.edition, len(pack["components"])))


def cmd_add_component(args):
    root = resolve_root(args)
    pack = load_pack(root)
    existing = {c["id"]: c for c in pack["components"]}
    c = existing.get(args.id) or {"id": args.id, "name": args.name, "checklist": []}
    c["name"] = args.name
    for row in args.checklist or []:
        if row not in c["checklist"]:
            c["checklist"].append(row)
    if args.id not in existing:
        pack["components"].append(c)
    save_pack(root, pack)
    os.makedirs(os.path.join(root, "components", args.id), exist_ok=True)
    print("component %s: %s (%d checklist rows)" % (c["id"], c["name"], len(c["checklist"])))


def cmd_phase(args):
    root = resolve_root(args)
    pack = load_pack(root)
    pack["phase"] = args.phase
    save_pack(root, pack)
    print("phase:", args.phase)


def cmd_source(args):
    root = resolve_root(args)
    path = os.path.join(root, "sources.jsonl")
    rows = read_jsonl(path)
    norm = args.url.rstrip("/")
    for r in rows:
        if r["url"].rstrip("/") == norm:
            print("already logged as %s (%s): %s" % (r["id"], r["status"], r.get("reason", "")))
            return
    if args.status == "used" and args.edition == "mismatch":
        die("a wrong-edition source cannot be 'used'; log it as rejected")
    row = {"id": "src-%03d" % (len(rows) + 1), "url": args.url, "title": args.title,
           "tier": args.tier, "type": args.type, "edition": args.edition,
           "status": args.status, "reason": args.reason or "",
           "components": [c for c in (args.components or "").split(",") if c],
           "published": args.published or "", "logged": str(date.today())}
    append_jsonl(path, row)
    print(row["id"])


def cmd_evidence(args):
    root = resolve_root(args)
    pack = load_pack(root)
    ids = {c["id"] for c in pack["components"]}
    if args.component not in ids:
        die("unknown component %s (add it with add-component)" % args.component)
    srcs = {r["id"]: r for r in read_jsonl(os.path.join(root, "sources.jsonl"))}
    for s in args.src:
        if s not in srcs:
            die("unknown source " + s)
        if srcs[s]["status"] != "used":
            die("%s is %s; only 'used' sources can back evidence" % (s, srcs[s]["status"]))
    if all(srcs[s]["edition"] == "unverified" for s in args.src) and not args.unverified_ok:
        print("WARN: backed only by unverified-edition sources; it will count as a gap "
              "until a matching source confirms it", file=sys.stderr)
    if args.media and not args.media.startswith("media/masked/"):
        die("--media must point into media/masked/ (run `mask` first)")
    path = os.path.join(root, "evidence.jsonl")
    rows = read_jsonl(path)
    row = {"id": "ev-%04d" % (len(rows) + 1), "component": args.component, "kind": args.kind,
           "fact": args.fact, "src": args.src, "loc": args.loc or "", "media": args.media or "",
           "conflicts": args.conflicts or [], "checklist": args.checklist or []}
    append_jsonl(path, row)
    print(row["id"])


def cmd_gap(args):
    root = resolve_root(args)
    pack = load_pack(root)
    if args.component not in {c["id"] for c in pack["components"]}:
        die("unknown component %s" % args.component)
    path = os.path.join(root, "gaps.jsonl")
    rows = read_jsonl(path)
    for r in rows:
        if r["component"] == args.component and r["gap"] == args.gap:
            die("gap already logged as %s" % r["id"])
    row = {"id": "gap-%03d" % (len(rows) + 1), "component": args.component, "gap": args.gap,
           "why": args.why, "next": args.next}
    append_jsonl(path, row)
    print(row["id"])


def cmd_mask(args):
    root = resolve_root(args)
    src = args.image
    if not os.path.exists(src):
        die("no such file " + src)
    out_dir = os.path.join(root, "media", "masked")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, os.path.basename(src))
    try:
        from PIL import Image, ImageDraw  # type: ignore
    except ImportError:
        if args.box:
            die("Pillow is needed to draw mask boxes: pip3 install --user pillow")
        shutil.copyfile(src, out)
        print("copied (no boxes): " + os.path.relpath(out, root))
        return
    im = Image.open(src).convert("RGB")
    d = ImageDraw.Draw(im)
    for b in args.box or []:
        try:
            x, y, w, h = [int(v) for v in b.split(",")]
        except ValueError:
            die("bad --box %r, want x,y,w,h" % b)
        d.rectangle([x, y, x + w, y + h], fill=(0, 0, 0))
    im.save(out)
    print("masked %d box(es): %s" % (len(args.box or []), os.path.relpath(out, root)))


def _gather(root):
    pack = load_pack(root)
    srcs = read_jsonl(os.path.join(root, "sources.jsonl"))
    evs = read_jsonl(os.path.join(root, "evidence.jsonl"))
    return pack, {s["id"]: s for s in srcs}, srcs, evs


def _confirmed(ev, srcmap):
    return any(srcmap.get(s, {}).get("edition") == "match" for s in ev["src"])


def cmd_status(args):
    root = resolve_root(args)
    pack, srcmap, srcs, evs = _gather(root)
    print("%s (%s) at %s, phase: %s" % (pack["app"], pack["edition"], root, pack["phase"]))
    st = defaultdict(int)
    for s in srcs:
        st[s["status"]] += 1
    print("sources: %d (%s)" % (len(srcs), ", ".join("%s %d" % kv for kv in sorted(st.items())) or "none"))
    per = defaultdict(list)
    for e in evs:
        per[e["component"]].append(e)
    for c in pack["components"]:
        rows = per[c["id"]]
        conf = sum(1 for e in rows if _confirmed(e, srcmap))
        print("  %-10s %-30s evidence %3d (edition-confirmed %d), checklist %d"
              % (c["id"], c["name"][:30], len(rows), conf, len(c["checklist"])))
    for s in srcs[-5:]:
        print("  last: %s %-11s %s" % (s["id"], s["status"], s["title"][:70]))


def cmd_coverage(args):
    root = resolve_root(args)
    pack, srcmap, srcs, evs = _gather(root)
    per = defaultdict(list)
    for e in evs:
        per[e["component"]].append(e)
    lines = ["# Coverage: %s (%s)" % (pack["app"], pack["edition"]), "",
             "Generated by pack.py coverage. Counts only evidence backed by an edition-matched source.", "",
             "| Component | Evidence | " + " | ".join(KINDS) + " | Checklist covered |",
             "|---|---|" + "---|" * len(KINDS) + "---|"]
    gaps = []
    total_rows = total_cov = 0
    for c in pack["components"]:
        conf = [e for e in per[c["id"]] if _confirmed(e, srcmap)]
        k = defaultdict(int)
        for e in conf:
            k[e["kind"]] += 1
        covered = {r for e in conf for r in e.get("checklist", [])}
        cl = c["checklist"]
        n_cov = sum(1 for r in cl if r in covered)
        total_rows += len(cl)
        total_cov += n_cov
        cl_txt = "%d/%d" % (n_cov, len(cl)) if cl else "no checklist"
        lines.append("| %s %s | %d | %s | %s |" % (c["id"], c["name"], len(conf),
                     " | ".join(str(k[x]) if k[x] else "·" for x in KINDS), cl_txt))
        for r in cl:
            if r not in covered:
                weak = [e for e in per[c["id"]] if r in e.get("checklist", []) and not _confirmed(e, srcmap)]
                why = "only unverified-edition sources" if weak else "no source shows it"
                gaps.append((c["id"], r, why))
        if not conf:
            gaps.append((c["id"], "(whole component)", "no edition-matched evidence yet"))
    if total_rows:
        lines += ["", "Checklist coverage: %d of %d rows (%.0f%%)." % (total_cov, total_rows, 100.0 * total_cov / total_rows)]
    unreach = [s for s in srcs if s["status"] == "unreachable"]
    if unreach:
        lines += ["", "## Unreachable sources", ""]
        lines += ["- %s %s: %s (%s)" % (s["id"], s["title"], s["reason"], s["url"]) for s in unreach]
    with open(os.path.join(root, "coverage.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    gp = os.path.join(root, "gaps.md")
    existing = {}
    if os.path.exists(gp):  # keep the human/agent-written "next action" column
        for line in open(gp):
            parts = [p.strip() for p in line.strip().strip("|").split("|")]
            if len(parts) == 4 and parts[0] not in ("Component", "---"):
                existing[(parts[0], parts[1])] = parts[3]
    logged = read_jsonl(os.path.join(root, "gaps.jsonl"))
    keys = {(r["component"], r["gap"]) for r in logged}
    gaps = [g for g in gaps if (g[0], g[1]) not in keys]  # a logged gap overrides the generated row
    for r in logged:
        gaps.append((r["component"], r["gap"], r["why"]))
        existing[(r["component"], r["gap"])] = r["next"]
    g = ["# Gaps: %s (%s)" % (pack["app"], pack["edition"]), "",
         "Generated by pack.py coverage from the checklist and gaps.jsonl. Edit gaps with `pack.py gap`, not here.", "",
         "| Component | Gap | Why | Next action |", "|---|---|---|---|"]
    for cid, r, why in gaps:
        g.append("| %s | %s | %s | %s |" % (cid, r, why, existing.get((cid, r), "TODO")))
    with open(gp, "w") as f:
        f.write("\n".join(g) + "\n")
    print("coverage.md and gaps.md written: %d gap(s)%s" % (
        len(gaps), ", checklist %d/%d" % (total_cov, total_rows) if total_rows else ""))


def cmd_validate(args):
    root = resolve_root(args)
    cmd_coverage(args)  # reports are always regenerated from the logs, never stale
    pack, srcmap, srcs, evs = _gather(root)
    errs = []
    todo = [l for l in open(os.path.join(root, "gaps.md")) if l.rstrip().endswith("| TODO |")]
    if todo:
        errs.append("gaps.md has %d gap(s) with no next action (log them with `pack.py gap`)" % len(todo))
    for e in evs:
        for s in e["src"]:
            if srcmap.get(s, {}).get("status") != "used":
                errs.append("%s cites %s which is not a used source" % (e["id"], s))
        if e.get("media"):
            if not os.path.exists(os.path.join(root, e["media"])):
                errs.append("%s media missing: %s" % (e["id"], e["media"]))
    for s in srcs:
        if s["status"] in ("rejected", "unreachable") and not s.get("reason"):
            errs.append("%s is %s with no reason" % (s["id"], s["status"]))
    cited = re.compile(r"\[src:(src-\d+)")
    for dirpath, dirnames, files in os.walk(root):
        if os.path.join("media", "raw") in dirpath or "/media" in dirpath.replace(root, ""):
            continue
        for fn in files:
            if not fn.endswith((".md", ".jsonl", ".json")):
                continue
            p = os.path.join(dirpath, fn)
            text = open(p, encoding="utf-8", errors="replace").read()
            if "media/raw/" in text and fn.endswith(".md"):
                errs.append("%s references media/raw/ (use media/masked/)" % os.path.relpath(p, root))
            scan = text
            if fn == "sources.jsonl":  # URLs may contain vendor addresses; scan titles/reasons only
                scan = "\n".join("%s %s" % (r.get("title", ""), r.get("reason", "")) for r in read_jsonl(p))
            for name, pat in PII_PATTERNS:
                for m in pat.finditer(scan):
                    errs.append("%s: possible %s %r" % (os.path.relpath(p, root), name, m.group(0)))
            if fn.endswith(".md"):
                for sid in cited.findall(text):
                    if sid not in srcmap:
                        errs.append("%s cites unknown %s" % (os.path.relpath(p, root), sid))
                    elif srcmap[sid]["status"] != "used":
                        errs.append("%s cites %s (%s)" % (os.path.relpath(p, root), sid, srcmap[sid]["status"]))
    gi = os.path.join(root, ".gitignore")
    if not os.path.exists(gi) or "media/raw/" not in open(gi).read():
        errs.append(".gitignore no longer ignores media/raw/")
    for c in pack["components"]:
        if not os.path.exists(os.path.join(root, "components", c["id"], "explored.md")):
            errs.append("components/%s/explored.md missing" % c["id"])
    if errs:
        for e in errs:
            print("FAIL " + e)
        print("validate FAILED: %d problem(s)" % len(errs))
        sys.exit(1)
    print("validate OK: %d sources, %d evidence rows, %d components" % (len(srcs), len(evs), len(pack["components"])))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.add_argument("--app", required=True)
    p.add_argument("--edition", required=True)
    p.add_argument("--root")
    p.add_argument("--components", nargs="*")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("add-component")
    p.add_argument("id")
    p.add_argument("name")
    p.add_argument("--checklist", nargs="*")
    p.add_argument("--root")
    p.set_defaults(fn=cmd_add_component)

    p = sub.add_parser("phase")
    p.add_argument("phase", choices=["intake", "map", "hunt", "extract", "write", "done"])
    p.add_argument("--root")
    p.set_defaults(fn=cmd_phase)

    p = sub.add_parser("source")
    p.add_argument("--url", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--tier", type=int, choices=[1, 2, 3, 4], required=True)
    p.add_argument("--type", choices=TYPES, required=True)
    p.add_argument("--edition", choices=["match", "mismatch", "unverified"], required=True)
    p.add_argument("--status", choices=["used", "rejected", "unreachable"], required=True)
    p.add_argument("--reason")
    p.add_argument("--components")
    p.add_argument("--published")
    p.add_argument("--root")
    p.set_defaults(fn=cmd_source)

    p = sub.add_parser("evidence")
    p.add_argument("--component", required=True)
    p.add_argument("--kind", choices=KINDS, required=True)
    p.add_argument("--fact", required=True)
    p.add_argument("--src", nargs="+", required=True)
    p.add_argument("--loc")
    p.add_argument("--media")
    p.add_argument("--conflicts", nargs="*")
    p.add_argument("--checklist", nargs="*")
    p.add_argument("--unverified-ok", action="store_true")
    p.add_argument("--root")
    p.set_defaults(fn=cmd_evidence)

    p = sub.add_parser("gap")
    p.add_argument("--component", required=True)
    p.add_argument("--gap", required=True)
    p.add_argument("--why", required=True)
    p.add_argument("--next", required=True)
    p.add_argument("--root")
    p.set_defaults(fn=cmd_gap)

    p = sub.add_parser("mask")
    p.add_argument("image")
    p.add_argument("--box", nargs="*")
    p.add_argument("--root")
    p.set_defaults(fn=cmd_mask)

    for name, fn in [("status", cmd_status), ("coverage", cmd_coverage), ("validate", cmd_validate)]:
        p = sub.add_parser(name)
        p.add_argument("--root")
        p.set_defaults(fn=fn)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
