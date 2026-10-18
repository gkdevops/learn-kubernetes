#!/usr/bin/env python3
"""Render Trivy / Kubescape results for humans.

Three output modes:

  (default)      full markdown to stdout - used by scripts/scan.sh locally.
  --summary      GitHub Actions step summary: emoji severity headers, long
                 tables collapsed behind <details>, narrow columns; plus a
                 compact colourised console block for the job log.
  --console      only the compact colourised console block.

Examples:
    python3 scripts/report.py --trivy trivy.json --kubescape kubescape.json
    python3 scripts/report.py --trivy trivy.json --summary
"""
import argparse
import collections
import json
import os
import re
import sys

SEV_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]
SEV_EMOJI = {"CRITICAL": "🔴", "HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡",
             "UNKNOWN": "⚪"}
ANSI = {"RED": "\033[31m", "YELLOW": "\033[33m", "GREEN": "\033[32m",
        "CYAN": "\033[36m", "BOLD": "\033[1m", "DIM": "\033[2m",
        "RESET": "\033[0m"}


def colour(text, name, enabled):
    return f"{ANSI[name]}{text}{ANSI['RESET']}" if enabled else text


# kubescape sometimes records absolute paths and a "0" line number. Reduce
# every path to a repo-relative "file[:line]".
REPO_MARKER = re.compile(r"(?:^|/)(?:\d\d-[^/]+|docs|scripts|\.github)(?:/|$)")


def rel_path(raw):
    path = str(raw).replace("\\", "/")
    line = ""
    if ":" in path:
        head, _, tail = path.rpartition(":")
        if tail.isdigit():
            path, line = head, ("" if tail == "0" else f":{tail}")
    match = REPO_MARKER.search(path)
    if match:
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
    return str(text).replace("|", "\\|").replace("\n", " ")


def short(text, limit=58):
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def table(headers, rows, aligns=None):
    if not rows:
        return "_none_\n"
    aligns = aligns or ["---"] * len(headers)
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join(aligns) + " |"]
    for row in rows:
        out.append("| " + " | ".join(esc(c) for c in row) + " |")
    return "\n".join(out) + "\n"


def details(summary, body, open_by_default=False):
    """A collapsible block - GitHub only renders markdown inside when the
    <summary> and </details> tags are separated by blank lines."""
    if not body or body.strip() == "_none_":
        return ""
    tag = " open" if open_by_default else ""
    return (f"<details{tag}>\n<summary><b>{summary}</b></summary>\n\n"
            f"{body.strip()}\n\n</details>\n")


# ----------------------------------------------------------------- trivy
def trivy_stats(data):
    findings = []
    for result in data.get("Results") or []:
        target = result.get("Target") or "?"
        for m in result.get("Misconfigurations") or []:
            cause = m.get("CauseMetadata") or {}
            findings.append({
                "severity": (m.get("Severity") or "UNKNOWN").upper(),
                "rule": m.get("ID") or "?",
                "title": m.get("Title") or m.get("Message") or "",
                "file": target,
                "line": cause.get("StartLine"),
                "resource": cause.get("Resource") or "",
            })
    counts = collections.Counter(f["severity"] for f in findings)
    per_file = collections.defaultdict(collections.Counter)
    for f in findings:
        per_file[f["file"]][f["severity"]] += 1
    rules = collections.defaultdict(list)
    for f in findings:
        rules[(f["rule"], f["title"])].append(f)
    return {"findings": findings, "counts": counts, "per_file": per_file,
            "rules": rules}


def location(f):
    return f"`{f['file']}:{f['line']}`" if f.get("line") else f"`{f['file']}`"


def trivy_markdown(stats, rich=False):
    findings, counts = stats["findings"], stats["counts"]
    out = ["## 🛡️ Trivy — IaC misconfiguration\n"]
    if not findings:
        return "\n".join(out + ["✅ No findings.\n"])

    if rich:
        headline = " · ".join(
            f"{SEV_EMOJI[s]} {counts.get(s, 0)} {s.lower()}" for s in SEV_ORDER)
        out.append(f"**{len(findings)} findings** — {headline}\n")
    else:
        rows = [["**total**", f"**{len(findings)}**"]] + \
               [[s.lower(), counts.get(s, 0)] for s in SEV_ORDER]
        out.append(table(["Severity", "Findings"], rows, ["---", "---:"]))
        out.append("\n")

    # per-severity detail, collapsed unless it is high severity
    for sev in SEV_ORDER:
        items = sorted((f for f in findings if f["severity"] == sev),
                       key=lambda f: (f["file"], f["rule"]))
        if not items:
            continue
        limit = None if (not rich or sev in ("CRITICAL", "HIGH")) else 25
        rows = [[f["rule"], short(f["title"]), location(f)] for f in items[:limit]]
        body = table(["Rule", "Finding", "Location"], rows, ["---", "---", "---"])
        if limit and len(items) > limit:
            body += f"\n_… and {len(items) - limit} more low/medium findings._\n"
        label = f"{SEV_EMOJI[sev]} {sev.title()} ({len(items)})"
        if rich:
            out.append(details(label, body, open_by_default=sev in ("CRITICAL", "HIGH")))
        else:
            out.append(f"### {sev.title()} ({len(items)})\n")
            out.append(body + "\n")

    # where the findings live
    rows = []
    for path, c in sorted(stats["per_file"].items(),
                           key=lambda kv: -sum(kv[1].values()))[:15]:
        rows.append([f"`{path}`", c.get("HIGH", 0), c.get("MEDIUM", 0),
                     c.get("LOW", 0), sum(c.values())])
    files_body = table(["File", "high", "medium", "low", "total"], rows,
                       ["---", "---:", "---:", "---:", "---:"])
    # the rules behind them
    rows = []
    for (rule, title), fs in sorted(stats["rules"].items(),
                                    key=lambda kv: -len(kv[1]))[:12]:
        files = sorted({f["file"] for f in fs})
        rows.append([rule, short(title, 48), len(fs),
                     ", ".join(f"`{p}`" for p in files[:2]) +
                     (f" +{len(files) - 2}" if len(files) > 2 else "")])
    rules_body = table(["Rule", "Description", "Count", "Where"], rows,
                       ["---", "---", "---:", "---"])
    if rich:
        out.append(details("📁 Files with the most findings", files_body))
        out.append(details("📖 Most frequent rules", rules_body))
    else:
        out.append("### Files with the most findings\n")
        out.append(files_body + "\n")
        out.append("### Most frequent rules\n")
        out.append(rules_body + "\n")
    return "\n".join(out)


def trivy_console(stats, c):
    findings, counts = stats["findings"], stats["counts"]
    print(c("TRIVY", "BOLD") + c("  IaC misconfiguration", "DIM"))
    if not findings:
        print("  " + c("✅ no findings", "GREEN"))
        return
    print("  " + c(f"{len(findings)} findings", "BOLD") + "  " + "  ".join(
        c(f"{SEV_EMOJI[s]} {counts.get(s, 0)}", tone)
        for s, tone in (("CRITICAL", "RED"), ("HIGH", "RED"),
                        ("MEDIUM", "YELLOW"), ("LOW", "CYAN"))))
    for (rule, title), fs in sorted(stats["rules"].items(),
                                    key=lambda kv: -len(kv[1]))[:5]:
        print(f"    {c(str(len(fs)).rjust(4), 'YELLOW')}  {rule:<10} {short(title, 52)}")
    print()


# ------------------------------------------------------------- kubescape
def kubescape_stats(data):
    summary = data.get("summaryDetails") or {}
    controls = summary.get("controls") or {}
    controls_list = list(controls.values()) if isinstance(controls, dict) else list(controls)
    locations = {}
    for res in data.get("resources") or []:
        obj = res.get("object") or {}
        paths = [obj["sourcePath"]] if obj.get("sourcePath") else []
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
        for ctl in res.get("controls") or []:
            if (ctl.get("status") or {}).get("status") != "failed":
                continue
            findings.append({"control": ctl.get("controlID"),
                             "name": ctl.get("name"),
                             "severity": ctl.get("severity") or "?",
                             "resource": rid,
                             "files": locations.get(rid, [])})
    return {"summary": summary, "controls": controls_list, "findings": findings,
            "severity": summary.get("resourcesSeverityCounters") or {}}


def score_emoji(score):
    if score is None:
        return "⚪"
    return "🟢" if score >= 90 else ("🟡" if score >= 70 else "🔴")


def kubescape_markdown(stats, rich=False):
    summary, controls = stats["summary"], stats["controls"]
    score = summary.get("complianceScore")
    failed = [c for c in controls if c.get("status") == "failed"]
    passed = [c for c in controls if c.get("status") == "passed"]
    skipped = [c for c in controls if c.get("status") == "skipped"]

    out = ["## 🛡️ Kubescape — NIST framework controls\n"]
    if rich:
        out.append(f"**{score_emoji(score)} {round(score) if score is not None else 'n/a'} / 100** "
                   f"compliance · 🔴 {len(failed)} failed · 🟢 {len(passed)} passed · "
                   f"⚪ {len(skipped)} skipped\n")
    else:
        out.append(f"**Compliance score: {round(score) if score is not None else 'n/a'} / 100** "
                   f"- failed {len(failed)}, passed {len(passed)}, skipped {len(skipped)} "
                   f"controls\n")
        sev = stats["severity"]
        out.append(table(["Resource findings", "count"],
                         [["critical", sev.get("criticalSeverity", 0)],
                          ["high", sev.get("highSeverity", 0)],
                          ["medium", sev.get("mediumSeverity", 0)],
                          ["low", sev.get("lowSeverity", 0)]], ["---", "---:"]))
        out.append("\n")

    if failed:
        rows = []
        for ctl in sorted(failed, key=lambda c: -(
                (c.get("ResourceCounters") or {}).get("failedResources", 0))):
            rows.append([ctl.get("controlID"), short(ctl.get("name"), 44),
                         (ctl.get("category") or {}).get("name") or "-",
                         (ctl.get("ResourceCounters") or {}).get("failedResources", 0)])
        body = table(["Control", "Name", "Category", "Resources failing"], rows,
                     ["---", "---", "---", "---:"])
        label = f"🔴 Failing controls ({len(failed)}) — ranked by blast radius"
        out.append(details(label, body, open_by_default=True) if rich
                   else f"### Failing controls ({len(failed)})\n" + body + "\n")

    findings = stats["findings"]
    if findings:
        rank = {"High": 0, "Medium": 1, "Low": 2}
        findings.sort(key=lambda f: (rank.get(f["severity"], 3), f["control"]))
        per_file = collections.Counter()
        examples = collections.defaultdict(list)
        for f in findings:
            for path in f["files"]:
                per_file[path] += 1
                if f["control"] not in examples[path]:
                    examples[path].append(f["control"])
        rows = [[f"`{p}`", n, ", ".join(examples[p][:3])]
                for p, n in sorted(per_file.items(), key=lambda kv: -kv[1])[:20]]
        body = table(["File", "Findings", "Controls"], rows, ["---", "---:", "---"])
        out.append(details(f"📁 Files with the most findings ({len(per_file)} files)",
                           body) if rich
                   else "### Files with the most kubescape findings\n" + body + "\n")
    return "\n".join(out)


def kubescape_console(stats, c):
    summary, controls = stats["summary"], stats["controls"]
    score = summary.get("complianceScore")
    failed = [x for x in controls if x.get("status") == "failed"]
    sev = stats["severity"]
    print(c("KUBESCAPE", "BOLD") + c("  NIST framework controls", "DIM"))
    print("  " + c(f"{score_emoji(score)} {round(score) if score is not None else 'n/a'}/100",
                   "GREEN" if (score or 0) >= 70 else "RED") +
          "  " + c(f"{len(failed)} controls failed", "RED"))
    print("  resource findings: " + "  ".join(
        c(f"{label} {sev.get(key, 0)}", tone)
        for label, key, tone in (("critical", "criticalSeverity", "RED"),
                                 ("high", "highSeverity", "RED"),
                                 ("medium", "mediumSeverity", "YELLOW"),
                                 ("low", "lowSeverity", "CYAN"))))
    for ctl in sorted(failed, key=lambda x: -((x.get("ResourceCounters") or {})
                                               .get("failedResources", 0)))[:5]:
        n = (ctl.get("ResourceCounters") or {}).get("failedResources", 0)
        print(f"    {c(str(n).rjust(4), 'YELLOW')}  {ctl.get('controlID'):<8} "
              f"{short(ctl.get('name'), 52)}")
    print()


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trivy", help="trivy JSON results")
    ap.add_argument("--kubescape", help="kubescape JSON results")
    ap.add_argument("--title", help="override the top-level heading")
    ap.add_argument("--summary", action="store_true",
                    help="append rich markdown to $GITHUB_STEP_SUMMARY and "
                         "print a compact console block")
    ap.add_argument("--console", action="store_true",
                    help="print only the compact console block")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("-o", "--output", help="write markdown here instead of stdout")
    args = ap.parse_args()

    # emoji / box characters: never let a legacy console codepage crash a run
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    colour_on = (not args.no_color) and (args.summary or args.console)

    trivy = trivy_stats(load(args.trivy)) if args.trivy else None
    kub = kubescape_stats(load(args.kubescape)) if args.kubescape else None

    if args.summary:
        target = os.environ.get("GITHUB_STEP_SUMMARY")
        if not target:
            print("warning: $GITHUB_STEP_SUMMARY is not set; writing to stdout",
                  file=sys.stderr)
            target = None
        chunks = []
        if trivy:
            chunks.append(trivy_markdown(trivy, rich=True))
        if kub:
            chunks.append(kubescape_markdown(kub, rich=True))
        chunks.append("_Intentionally unfixed findings are documented in "
                      "[security-hardening.md](../docs/security-hardening.md)._")
        if target:
            with open(target, "a", encoding="utf-8") as fh:
                fh.write("\n" + "\n".join(chunks) + "\n")
            print(f"appended {len(chunks) - 1} report(s) to the run summary")
        else:
            print("\n".join(chunks))

    def c(text, name):
        return colour(text, name, colour_on)

    if trivy:
        trivy_console(trivy, c)
    if kub:
        kubescape_console(kub, c)
    if args.console:
        return

    if args.summary and not args.output:
        return

    parts = []
    if args.title:
        parts.append(f"# {args.title}\n")
    if trivy:
        parts.append(trivy_markdown(trivy))
    if kub:
        parts.append(kubescape_markdown(kub))
    used = [n for n, p in (("trivy.json", args.trivy),
                           ("kubescape.json", args.kubescape)) if p]
    if used:
        parts.append(f"Raw results: {', '.join(used)}.\n")
    report = "\n".join(parts)

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(report)
        print(f"wrote {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()