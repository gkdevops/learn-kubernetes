#!/usr/bin/env python3
"""Render a markdown security report from trivy.json and kubescape.json.

Used by .github/workflows/security-scan.yml (into the run summary) and by
scripts/scan.sh locally, so both print exactly the same tables.

    python3 scripts/report.py --trivy trivy.json --kubescape kubescape.json
    python3 scripts/report.py --trivy trivy.json -o security-report.md
"""
import argparse
import collections
import json
import re
import sys

SEV_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]

# kubescape sometimes records absolute paths (e.g. D:/.../learn-kubernetes/...) and
# a "0" line number. Reduce every path to repo-relative "<file>[:<line>]".
REPO_MARKER = re.compile(r"(?:^|/)(?:\d\d-[^/]+|docs|scripts|\.github)(?:/|$)")


def rel_path(raw):
    """Normalise a kubescape sourcePath to a repo-relative file[:line]."""
    path = str(raw).replace("\\", "/")
    line = ""
    if ":" in path:
        head, _, tail = path.rpartition(":")
        if tail.isdigit():
            path, line = head, ("" if tail == "0" else f":{tail}")
    match = REPO_MARKER.search(path)
    if match:
        # keep the first character of the matched segment ("05-storage", not "5-storage")
        cut = match.start() + (1 if path[match.start()] == "/" else 0)
        path = path[cut:]
    return path + line


def load(path):
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"warning: could not read {path}: {exc}", file=sys.stderr)
        return None


def esc(text):
    """Make a value safe inside a markdown table cell."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def table(headers, rows, aligns=None):
    if not rows:
        return "_none_\n"
    aligns = aligns or ["---"] * len(headers)
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join(aligns) + " |"]
    for row in rows:
        out.append("| " + " | ".join(esc(c) for c in row) + " |")
    return "\n".join(out) + "\n"


# ----------------------------------------------------------------- trivy
def trivy_findings(data):
    findings = []
    for result in data.get("Results") or []:
        target = result.get("Target") or "?"
        for m in result.get("Misconfigurations") or []:
            cause = m.get("CauseMetadata") or {}
            line = cause.get("StartLine")
            findings.append({
                "severity": (m.get("Severity") or "UNKNOWN").upper(),
                "rule": m.get("ID") or "?",
                "title": m.get("Title") or m.get("Message") or "",
                "file": target,
                "line": line,
                "resource": cause.get("Resource") or "",
            })
    return findings


def trivy_section(data):
    findings = trivy_findings(data)
    if not findings:
        return "## Trivy\n\n_no findings_\n"

    counts = collections.Counter(f["severity"] for f in findings)
    total = len(findings)

    out = ["## Trivy - IaC misconfiguration (kube-linter `KSV-*` and friends)\n"]
    out.append(table(
        ["Severity", "Findings"],
        [["**total**", f"**{total}**"]] +
        [[s.lower(), counts.get(s, 0)] for s in SEV_ORDER],
        ["---", "---:"]))

    # which files are involved, worst first
    per_file = collections.defaultdict(collections.Counter)
    for f in findings:
        per_file[f["file"]][f["severity"]] += 1
    rows = []
    for path, c in sorted(per_file.items(), key=lambda kv: -sum(kv[1].values()))[:15]:
        rows.append([f"`{path}`", c.get("HIGH", 0), c.get("MEDIUM", 0),
                     c.get("LOW", 0), sum(c.values())])
    out.append("### Files with the most findings\n")
    out.append(table(["File", "high", "medium", "low", "total"], rows,
                     ["---", "---:", "---:", "---:", "---:"]))

    headers = ["Rule", "Finding", "Location", "Resource"]
    aligns = ["---", "---", "---", "---"]

    def rows_for(severity):
        rows = []
        for f in sorted((x for x in findings if x["severity"] == severity),
                        key=lambda x: (x["file"], x["rule"])):
            location = f"`{f['file']}:{f['line']}`" if f["line"] else f"`{f['file']}`"
            rows.append([f["rule"], f["title"], location, f["resource"] or "-"])
        return rows

    high = rows_for("HIGH")
    if high:
        out.append(f"### High severity findings ({len(high)})\n")
        out.append(table(headers, high, aligns))

    medium = rows_for("MEDIUM")
    if medium:
        shown = medium[:60]
        out.append(f"### Medium severity findings ({len(medium)})\n")
        out.append(table(headers, shown, aligns))
        if len(medium) > len(shown):
            out.append(f"_{len(medium) - len(shown)} more - see trivy.json_\n")

    low = rows_for("LOW")
    if low:
        out.append(f"### Low severity findings ({len(low)}, first 20)\n")
        out.append(table(headers, low[:20], aligns))
        if len(low) > 20:
            out.append(f"_{len(low) - 20} more - see trivy.json_\n")

    rule_rows = []
    grouped = collections.defaultdict(list)
    for f in findings:
        grouped[(f["rule"], f["title"])].append(f)
    for (rule, title), fs in sorted(grouped.items(), key=lambda kv: -len(kv[1]))[:15]:
        files = sorted({f["file"] for f in fs})
        rule_rows.append([rule, title, len(fs),
                          ", ".join(f"`{p}`" for p in files[:3]) +
                          (f" (+{len(files) - 3} more)" if len(files) > 3 else "")])
    out.append("### Most frequent rules\n")
    out.append(table(["Rule", "Description", "Count", "Files"], rule_rows,
                     ["---", "---", "---:", "---"]))
    return "\n".join(out)


# ------------------------------------------------------------- kubescape
def kubescape_findings(data):
    """-> (findings, location map). A finding = (controlID, name, severity, resourceID)."""
    locations = {}
    for res in data.get("resources") or []:
        obj = res.get("object") or {}
        # A resource either points straight at its manifest
        # (object.sourcePath, for file-scanned objects) or relates to objects
        # that do (object.relatedObjects[].sourcePath). Normalise both shapes.
        paths = []
        if obj.get("sourcePath"):
            paths.append(obj["sourcePath"])
        related = obj.get("relatedObjects") or []
        if isinstance(related, dict):
            related = [related]
        paths += [r["sourcePath"] for r in related
                  if isinstance(r, dict) and r.get("sourcePath")]
        if paths:
            locations[res.get("resourceID")] = sorted({rel_path(p) for p in paths})

    findings = []
    for res in data.get("results") or []:
        rid = res.get("resourceID")
        for c in res.get("controls") or []:
            if (c.get("status") or {}).get("status") != "failed":
                continue
            findings.append({
                "control": c.get("controlID"),
                "name": c.get("name"),
                "severity": c.get("severity") or "?",
                "resource": rid,
                "files": locations.get(rid, []),
            })
    return findings, locations


def kubescape_section(data):
    summary = data.get("summaryDetails") or {}
    controls = summary.get("controls") or {}
    controls_list = list(controls.values()) if isinstance(controls, dict) else list(controls)
    failed = [c for c in controls_list if c.get("status") == "failed"]
    passed = [c for c in controls_list if c.get("status") == "passed"]
    skipped = [c for c in controls_list if c.get("status") == "skipped"]
    score = summary.get("complianceScore")
    res_sev = summary.get("resourcesSeverityCounters") or {}

    out = ["## Kubescape - NIST framework controls\n"]
    out.append(f"**Compliance score: {round(score) if score is not None else 'n/a'} / 100** "
               f"- failed {len(failed)}, passed {len(passed)}, skipped {len(skipped)} "
               f"controls\n")
    out.append(table(
        ["Resource findings", "count"],
        [["critical", res_sev.get("criticalSeverity", 0)],
         ["high", res_sev.get("highSeverity", 0)],
         ["medium", res_sev.get("mediumSeverity", 0)],
         ["low", res_sev.get("lowSeverity", 0)]],
        ["---", "---:"]))

    if failed:
        rows = []
        for c in sorted(failed, key=lambda c: -(c.get("ResourceCounters") or {}).get("failedResources", 0)):
            rows.append([
                c.get("controlID"), c.get("name"),
                ((c.get("category") or {}).get("name") or "-"),
                (c.get("ResourceCounters") or {}).get("failedResources", 0),
            ])
        out.append(f"### Failing controls ({len(failed)})\n")
        out.append(table(["Control", "Name", "Category", "Resources failing"], rows,
                         ["---", "---", "---", "---:"]))

    findings, _ = kubescape_findings(data)
    if findings:
        sev_rank = {"High": 0, "Medium": 1, "Low": 2, "unknown": 3}
        findings.sort(key=lambda f: (sev_rank.get(f["severity"], 3), f["control"]))
        rows = []
        for f in findings[:60]:
            loc = ", ".join(f"`{p}`" for p in f["files"][:2]) or "-"
            rows.append([f["severity"], f["control"], f["name"], loc, f["resource"]])
        out.append(f"### Failing findings per resource ({len(findings)})\n")
        out.append(table(["Severity", "Control", "Name", "Location", "Resource"], rows,
                         ["---", "---", "---", "---", "---"]))
        if len(findings) > 60:
            out.append(f"_{len(findings) - 60} more - see kubescape.json_\n")

        per_file = collections.Counter()
        examples = collections.defaultdict(list)
        for f in findings:
            for path in f["files"]:
                per_file[path] += 1
                if f["control"] not in examples[path]:
                    examples[path].append(f["control"])
        rows = [[f"`{p}`", n, ", ".join(examples[p][:4])]
                for p, n in sorted(per_file.items(), key=lambda kv: -kv[1])[:20]]
        out.append("### Files with the most kubescape findings\n")
        out.append(table(["File", "Findings", "Controls"], rows, ["---", "---:", "---"]))

    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trivy", help="trivy JSON results")
    ap.add_argument("--kubescape", help="kubescape JSON results")
    ap.add_argument("--title", default="Security scan report")
    ap.add_argument("-o", "--output", help="write here instead of stdout")
    args = ap.parse_args()

    used = [name for name, path in
            (("trivy.json", args.trivy), ("kubescape.json", args.kubescape)) if path]

    parts = [f"# {args.title}\n"]
    if args.trivy and load(args.trivy):
        parts.append(trivy_section(load(args.trivy)))
    if args.kubescape and load(args.kubescape):
        parts.append(kubescape_section(load(args.kubescape)))
    if used:
        parts.append(f"Raw results: {', '.join(used)}.\n"
                     "Intentionally unfixed findings are listed in "
                     "[security-hardening.md](docs/security-hardening.md).\n")
    report = "\n".join(parts)

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(report)
        print(f"wrote {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()