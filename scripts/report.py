#!/usr/bin/env python3
"""Render Trivy / Kubescape results for humans.

Output modes:

  (default)      full markdown to stdout - used by scripts/scan.sh locally.
  --summary      GitHub Actions step summary: emoji severity headers, colour
                 bars, long sections collapsed behind <details>, plus a compact
                 colourised console block for the job log.
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
BAR_WIDTH = 10


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
    text = str(text or "")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def bar(value, largest, width=BAR_WIDTH):
    filled = 0 if not largest else round(width * value / largest)
    return "█" * filled + "░" * (width - filled)


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
    """A collapsible block. GitHub only renders markdown inside when the tags
    are separated by blank lines."""
    if not body or body.strip() == "_none_":
        return ""
    tag = " open" if open_by_default else ""
    return (f"<details{tag}>\n<summary><b>{summary}</b></summary>\n\n"
            f"{body.strip()}\n\n</details>\n")


def rule_link(rule, url):
    return f"[`{rule}`]({url})" if url else f"`{rule}`"


# ----------------------------------------------------------------- trivy
def trivy_stats(data):
    findings = []
    files_scanned = 0
    for result in data.get("Results") or []:
        misconfig = result.get("Misconfigurations") or []
        if not misconfig:
            continue
        files_scanned += 1
        target = result.get("Target") or "?"
        for m in misconfig:
            cause = m.get("CauseMetadata") or {}
            code = [ln for ln in ((cause.get("Code") or {}).get("Lines") or [])
                    if ln.get("IsCause")]
            findings.append({
                "severity": (m.get("Severity") or "UNKNOWN").upper(),
                "rule": m.get("ID") or "?",
                "title": m.get("Title") or "",
                "message": m.get("Message") or "",
                "description": m.get("Description") or "",
                "resolution": m.get("Resolution") or "",
                "url": m.get("PrimaryURL") or "",
                "file": target,
                "line": cause.get("StartLine"),
                "resource": cause.get("Resource") or "",
                "code": code,
            })
    counts = collections.Counter(f["severity"] for f in findings)
    per_file = collections.defaultdict(collections.Counter)
    for f in findings:
        per_file[f["file"]][f["severity"]] += 1
    rules = collections.defaultdict(list)
    for f in findings:
        rules[(f["rule"], f["title"])].append(f)
    return {"findings": findings, "counts": counts, "per_file": per_file,
            "rules": rules, "files_scanned": files_scanned}


def location(f):
    return f"`{f['file']}:{f['line']}`" if f.get("line") else f"`{f['file']}`"


def trivy_fix_block(f):
    """Per-finding detail: what/where/how to fix, plus the offending YAML."""
    out = [f"#### {rule_link(f['rule'], f['url'])} — {esc(f['title'])}", ""]
    out.append(f"**Where:** {location(f)}")
    if f.get("message"):
        out.append(f"**What:** {esc(f['message'])}")
    if f.get("resolution"):
        out.append(f"**Fix:** {esc(f['resolution'])}")
    if f.get("code"):
        lines = [str(ln.get("Content", "")).rstrip()[:100] for ln in f["code"][:6]]
        out.append("")
        out.append("```yaml")
        out.extend(lines)
        out.append("```")
    if f.get("url"):
        out.append(f"\n<sub>reference: {f['url']}</sub>")
    return "\n".join(out) + "\n"


def trivy_markdown(stats, rich=False):
    findings, counts = stats["findings"], stats["counts"]
    out = ["## 🛡️ Trivy — IaC misconfiguration\n"]
    if not findings:
        return "\n".join(out + ["✅ No findings.\n"])

    total = len(findings)
    headline = " · ".join(
        f"{SEV_EMOJI[s]} {counts.get(s, 0)} {s.lower()}" for s in SEV_ORDER)
    out.append(f"**{total} findings** in {stats['files_scanned']} files — {headline}\n")

    if rich:
        rows = [[f"{SEV_EMOJI[s]} {s.lower()}", counts.get(s, 0),
                 f"{(100 * counts.get(s, 0) / total):.0f}%", bar(counts.get(s, 0), total)]
                for s in SEV_ORDER]
        out.append(table(["Severity", "Count", "Share", ""], rows,
                         ["---", "---:", "---:", "---"]))
        out.append("\n")

    # ---- per severity, high/critical expanded with fix guidance
    for sev in SEV_ORDER:
        items = sorted((f for f in findings if f["severity"] == sev),
                       key=lambda f: (f["file"], f["rule"]))
        if not items:
            continue
        detail = sev in ("CRITICAL", "HIGH")
        limit = None if detail or not rich else (40 if sev == "MEDIUM" else 30)
        rows = [[rule_link(f["rule"], f["url"]), short(f["title"]), location(f)]
                for f in items[:limit]]
        body = table(["Rule", "Finding", "Location"], rows, ["---", "---", "---"])
        if limit and len(items) > limit:
            body += f"\n_… and **{len(items) - limit}** more {sev.lower()} findings._\n"
        if detail:
            body += "\n" + "\n".join(trivy_fix_block(f) for f in items)
        label = f"{SEV_EMOJI[sev]} {sev.title()} ({len(items)})"
        out.append(details(label, body, open_by_default=detail) if rich
                   else f"### {sev.title()} ({len(items)})\n" + body + "\n")

    # ---- the rules behind the numbers
    largest = max((len(v) for v in stats["rules"].values()), default=0)
    rows = []
    for (rule, title), fs in sorted(stats["rules"].items(),
                                    key=lambda kv: -len(kv[1]))[:15]:
        files = sorted({f["file"] for f in fs})
        rows.append([f"`{rule}`", short(title, 46), len(fs),
                     bar(len(fs), largest),
                     ", ".join(f"`{p}`" for p in files[:2]) +
                     (f" +{len(files) - 2}" if len(files) > 2 else "")])
    rules_body = table(["Rule", "Description", "Count", "", "Where"], rows,
                       ["---", "---", "---:", "---", "---"])
    # ---- rule reference: what each rule means + how to fix it
    ref_rows = []
    for (rule, title), fs in sorted(stats["rules"].items(),
                                    key=lambda kv: -len(kv[1]))[:12]:
        sample = fs[0]
        ref_rows.append([
            f"`{rule}`", short(title, 44),
            short(sample.get("description") or sample.get("resolution") or "-", 150),
            short(sample.get("resolution") or "-", 70),
            len(fs)])
    ref_body = table(["Rule", "Title", "What it checks", "Fix", "Count"], ref_rows,
                     ["---", "---", "---", "---", "---:"])

    # ---- where the findings live
    rows = []
    for path, c in sorted(stats["per_file"].items(),
                           key=lambda kv: -sum(kv[1].values()))[:20]:
        worst = sorted((f for f in findings if f["file"] == path),
                       key=lambda f: SEV_ORDER.index(f["severity"]))[0]
        rows.append([f"`{path}`", c.get("HIGH", 0), c.get("MEDIUM", 0),
                     c.get("LOW", 0), sum(c.values()), f"`{worst['rule']}`"])
    files_body = table(["File", "high", "medium", "low", "total", "worst rule"],
                       rows, ["---", "---:", "---:", "---:", "---:", "---"])

    if rich:
        out.append(details("📖 Top 15 rules by volume", rules_body))
        out.append(details("📚 What each rule checks — and how to fix it", ref_body))
        out.append(details("📁 Top 20 files by findings", files_body))
    else:
        out.append("### Most frequent rules\n" + rules_body + "\n")
        out.append("### What each rule checks — and how to fix it\n" + ref_body + "\n")
        out.append("### Files with the most findings\n" + files_body + "\n")
    return "\n".join(out)


def trivy_console(stats, c):
    findings, counts = stats["findings"], stats["counts"]
    print(c("TRIVY", "BOLD") + c("  IaC misconfiguration", "DIM"))
    if not findings:
        print("  " + c("✅ no findings", "GREEN"))
        return
    print("  " + c(f"{len(findings)} findings", "BOLD") +
          f" in {stats['files_scanned']} files   " + "  ".join(
              c(f"{SEV_EMOJI[s]} {counts.get(s, 0)}", tone)
              for s, tone in (("CRITICAL", "RED"), ("HIGH", "RED"),
                              ("MEDIUM", "YELLOW"), ("LOW", "CYAN"))))
    for (rule, title), fs in sorted(stats["rules"].items(),
                                    key=lambda kv: -len(kv[1]))[:5]:
        print(f"    {c(str(len(fs)).rjust(4), 'YELLOW')}  {rule:<10} {short(title, 48)}")
    top_file, top_c = max(stats["per_file"].items(), key=lambda kv: sum(kv[1].values()))
    print(f"    {c('file', 'DIM')} {short(top_file, 60)} — {sum(top_c.values())} findings")
    fix = next((f for f in findings if f["severity"] in ("CRITICAL", "HIGH")
                and f.get("resolution")), None)
    if fix:
        print("    " + c(f"top fix: {fix['resolution']}", "DIM")[:118])
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

    by_category = collections.Counter()
    by_resource = collections.Counter()
    controls_at = collections.defaultdict(list)
    for ctl in controls_list:
        if ctl.get("status") != "failed":
            continue
        by_category[(ctl.get("category") or {}).get("name") or "-"] += 1
    for f in findings:
        by_resource[f["resource"]] += 1
        controls_at[f["resource"]].append(f["control"])
    return {"summary": summary, "controls": controls_list, "findings": findings,
            "severity": summary.get("resourcesSeverityCounters") or {},
            "categories": by_category, "by_resource": by_resource,
            "controls_at": controls_at}


def score_emoji(score):
    if score is None:
        return "⚪"
    return "🟢" if score >= 90 else ("🟡" if score >= 70 else "🔴")


def resource_label(rid):
    """'path=123/api=apps/v1//Deployment/nginx' -> 'Deployment/nginx'."""
    text = str(rid)
    tail = text.split("/api=")[-1]
    parts = [p for p in tail.split("/") if p]
    if not parts:
        return short(text, 40)
    return "/".join(parts[-2:]) if len(parts) >= 2 else parts[-1]


def kubescape_markdown(stats, rich=False):
    summary, controls = stats["summary"], stats["controls"]
    score = summary.get("complianceScore")
    failed = [c for c in controls if c.get("status") == "failed"]
    passed = [c for c in controls if c.get("status") == "passed"]
    skipped = [c for c in controls if c.get("status") == "skipped"]
    sev = stats["severity"]

    out = ["## 🛡️ Kubescape — NIST framework controls\n"]
    out.append(f"**{score_emoji(score)} {round(score) if score is not None else 'n/a'} / 100** "
               f"compliance · 🔴 {len(failed)} failed · 🟢 {len(passed)} passed · "
               f"⚪ {len(skipped)} skipped\n")

    rows = [[k, sev.get(key, 0)] for k, key in (
        ("critical", "criticalSeverity"), ("high", "highSeverity"),
        ("medium", "mediumSeverity"), ("low", "lowSeverity"))]
    out.append(table(["Resource findings", "count"], rows, ["---", "---:"]))
    out.append("\n")

    cat_rows = [[f"🟠 {name}", n] for name, n in
                sorted(stats["categories"].items(), key=lambda kv: -kv[1])]
    cat_body = table(["Category", "Failed controls"], cat_rows, ["---", "---:"])

    if failed:
        rows = []
        for ctl in sorted(failed, key=lambda c: -(
                (c.get("ResourceCounters") or {}).get("failedResources", 0))):
            rows.append([f"`{ctl.get('controlID')}`", short(ctl.get("name"), 46),
                         (ctl.get("category") or {}).get("name") or "-",
                         (ctl.get("ResourceCounters") or {}).get("failedResources", 0),
                         (ctl.get("ResourceCounters") or {}).get("passedResources", 0)])
        body = table(["Control", "Name", "Category", "Resources failing", "passing"],
                     rows, ["---", "---", "---", "---:", "---:"])
        out.append(details(f"🔴 Failing controls ({len(failed)}) — ranked by blast radius",
                           body, open_by_default=True) if rich
                   else f"### Failing controls ({len(failed)})\n" + body + "\n")

    findings = stats["findings"]
    if findings:
        # worst resources
        rows = []
        for rid, n in sorted(stats["by_resource"].items(), key=lambda kv: -kv[1])[:20]:
            files = next((f["files"] for f in findings if f["resource"] == rid), [])
            rows.append([resource_label(rid), n,
                         ", ".join(sorted(set(stats["controls_at"][rid]))[:4]),
                         f"`{files[0]}`" if files else "-"])
        res_body = table(["Resource", "Failed controls", "Control IDs", "Location"],
                         rows, ["---", "---:", "---", "---"])

        # per file
        per_file = collections.Counter()
        examples = collections.defaultdict(list)
        for f in findings:
            for path in f["files"]:
                per_file[path] += 1
                if f["control"] not in examples[path]:
                    examples[path].append(f["control"])
        rows = [[f"`{p}`", n, ", ".join(examples[p][:4])]
                for p, n in sorted(per_file.items(), key=lambda kv: -kv[1])[:25]]
        file_body = table(["File", "Findings", "Controls"], rows, ["---", "---:", "---"])

        if rich:
            out.append(details(f"📦 Worst-offending resources ({len(stats['by_resource'])})",
                               res_body))
            out.append(details(f"📁 Top 25 files by kubescape findings ({len(per_file)} files)",
                               file_body))
            out.append(details(f"🗂 Failed controls by category", cat_body))
        else:
            out.append("### Worst-offending resources\n" + res_body + "\n")
            out.append("### Files with the most kubescape findings\n" + file_body + "\n")
            out.append("### Failed controls by category\n" + cat_body + "\n")

    if passed:
        rows = [[f"`{c.get('controlID')}`", short(c.get("name"), 60),
                 (c.get("category") or {}).get("name") or "-"] for c in passed]
        body = table(["Control", "Name", "Category"], rows, ["---", "---", "---"])
        out.append(details(f"✅ Passing controls ({len(passed)})", body) if rich
                   else "### Passing controls\n" + body + "\n")
    return "\n".join(out)


def kubescape_console(stats, c):
    summary, controls = stats["summary"], stats["controls"]
    score = summary.get("complianceScore")
    failed = [x for x in controls if x.get("status") == "failed"]
    sev = stats["severity"]
    print(c("KUBESCAPE", "BOLD") + c("  NIST framework controls", "DIM"))
    print("  " + c(f"{score_emoji(score)} {round(score) if score is not None else 'n/a'}/100",
                   "GREEN" if (score or 0) >= 70 else "RED") +
          "  " + c(f"{len(failed)} controls failed", "RED") +
          f"  ({len(stats['findings'])} resource findings)")
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
              f"{short(ctl.get('name'), 48)}")
    print()


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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

    def c(text, name):
        return colour(text, name, colour_on)

    trivy = trivy_stats(load(args.trivy)) if args.trivy else None
    kub = kubescape_stats(load(args.kubescape)) if args.kubescape else None

    if args.summary:
        target = os.environ.get("GITHUB_STEP_SUMMARY")
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

    if trivy:
        trivy_console(trivy, c)
    if kub:
        kubescape_console(kub, c)
    if args.console or args.summary:
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