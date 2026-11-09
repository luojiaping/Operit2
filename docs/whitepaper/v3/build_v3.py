"""Build the v3 whitepaper Markdown from its source and check its consistency.

Usage: python -X utf8 build_v3.py [--allow-placeholders]

Reads Operit2-Whitepaper-zh-v3.src.md, references.json and model/experiments.txt and
writes Operit2-Whitepaper-zh-v3.md:
  * [@Key] and [@Key1; @Key2] citations become numbers in order of first appearance;
  * the reference list replaces <!-- references -->;
  * EXPERIMENT_ROWS becomes the experiment table of Appendix B.
Checks: unknown citation keys, unused references, C-evidence ids used but not defined
in Appendix A (and defined but unused), missing figure files, tables with unequal
column counts, and leftover placeholders.  Exits with status 1 on any error.
This is a document tool; it does not build or test the project.
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
SOURCE = BASE / "Operit2-Whitepaper-zh-v3.src.md"
OUTPUT = BASE / "Operit2-Whitepaper-zh-v3.md"
REFERENCES = BASE / "references.json"
EXPERIMENTS = BASE / "model" / "experiments.txt"
PLACEHOLDERS = ["TAKEOVER_SAFE_RESULT", "EXPERIMENT_ROWS"]


def experiment_rows() -> str:
    rows = []
    for line in EXPERIMENTS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        name, n, mg, mts, ms, mh, mc, mcut, md, proto, tk, ag, us, sk, hl, inv = line.split("|")
        scale = f"N={n}，代次≤{mg}，发送≤{ms}，交接≤{mh}"
        faults = f"崩溃≤{mc}，断链≤{mcut}，重复≤{md}，时钟偏差{'有' if sk == 'TRUE' else '无'}"
        options = [proto]
        if tk == "user":
            options.append("用户接管")
        if ag == "TRUE":
            options.append("模型切换")
        if us == "TRUE":
            options.append("用户切换")
        if hl == "TRUE":
            options.append("HoldLease")
        rows.append(f"| `{name}` | {scale} | {faults} | {'，'.join(options)} | {'、'.join(f'`{x}`' for x in inv.split())} |")
    header = "| 实验 | 规模 | 故障 | 协议与选项 | 检查的性质 |\n| --- | --- | --- | --- | --- |"
    return header + "\n" + "\n".join(rows)


def main() -> int:
    allow = "--allow-placeholders" in sys.argv
    text = SOURCE.read_text(encoding="utf-8")
    refs = json.loads(REFERENCES.read_text(encoding="utf-8"))
    errors, warnings = [], []

    # Appendix B experiment table (replaces the header row and the placeholder).
    text = re.sub(r"\| 实验 \| 节点 \|.*\n\| ---( \| ---)+ \|\nEXPERIMENT_ROWS", lambda _m: experiment_rows(), text)

    # Citations.
    order = []
    def cite(match):
        keys = [k.strip().lstrip("@") for k in match.group(1).split(";")]
        numbers = []
        for key in keys:
            if key not in refs:
                errors.append(f"unknown citation key: {key}")
                continue
            if key not in order:
                order.append(key)
            numbers.append(order.index(key) + 1)
        return "[" + ", ".join(str(n) for n in numbers) + "]"
    text = re.sub(r"\[(@[A-Za-z0-9]+(?:;\s*@[A-Za-z0-9]+)*)\]", cite, text)
    unused = [k for k in refs if k not in order]
    if unused:
        warnings.append("references never cited: " + ", ".join(unused))
    ref_lines = "\n\n".join(f"[{i + 1}] {refs[key]}" for i, key in enumerate(order))
    if "<!-- references -->" not in text:
        errors.append("missing <!-- references --> marker")
    text = text.replace("<!-- references -->", ref_lines)

    # Evidence ids.
    appendix = text.split("## 附录 A 源码证据", 1)
    if len(appendix) != 2:
        errors.append("missing Appendix A")
    else:
        body, rest = appendix
        defined = set(re.findall(r"^\| (C\d+) \|", rest, flags=re.M))
        used = set()
        for group in re.findall(r"\[(C\d+(?:,\s*C\d+)*)\]", body):
            used.update(x.strip() for x in group.split(","))
        for cid in sorted(used - defined, key=lambda x: int(x[1:])):
            errors.append(f"evidence {cid} used but not defined in Appendix A")
        for cid in sorted(defined - used, key=lambda x: int(x[1:])):
            warnings.append(f"evidence {cid} defined but never cited in the body")

    # Figures.
    for caption, path in re.findall(r"^!\[([^\]]+)\]\(([^)]+)\)", text, flags=re.M):
        if not (BASE / path).exists():
            errors.append(f"missing figure file: {path}")

    # Tables: equal column counts per table.
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        if lines[index].strip().startswith("|"):
            start = index
            counts = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                counts.append(len(lines[index].strip().strip("|").split("|")))
                index += 1
            if len(set(counts)) != 1:
                errors.append(f"table at line {start + 1} has unequal column counts {sorted(set(counts))}")
        index += 1

    # Placeholders.
    for marker in PLACEHOLDERS:
        if marker in text:
            (warnings if allow else errors).append(f"placeholder left in text: {marker}")

    OUTPUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUTPUT.name}: {len(order)} references, {len(text)} characters")
    for warning in warnings:
        print("WARNING:", warning)
    for error in errors:
        print("ERROR:", error)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
