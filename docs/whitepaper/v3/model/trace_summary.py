"""Summarize a TLC log of TurnHandoff.tla.

Usage: python -X utf8 trace_summary.py <tlc.log>

Prints the TLC verdict and statistics, then one line per state of the error
trace with the action and the variables that matter for the handoff
properties: running turns, leases, each node's Binding view (owner/generation
@createdAt), route-change state, messages in flight, links and turn starts.
"""
import re
import sys
from pathlib import Path


def split_states(text: str):
    blocks = re.split(r"^State (\d+): (.*)$", text, flags=re.M)
    # blocks = [prefix, num, header, body, num, header, body, ...]
    for index in range(1, len(blocks) - 2, 3):
        yield int(blocks[index]), blocks[index + 1].strip(), blocks[index + 2]


def variables(body: str) -> dict:
    result = {}
    for match in re.finditer(r"^/\\ (\w+) = (.*?)(?=^/\\ |\Z)", body, flags=re.M | re.S):
        result[match.group(1)] = " ".join(match.group(2).split())
    return result


def seq_values(value: str):
    inner = value.strip()
    if inner.startswith("<<") and inner.endswith(">>"):
        inner = inner[2:-2]
    return [item.strip() for item in inner.split(",") if item.strip()]


def action_name(header: str) -> str:
    match = re.match(r"<(\w+)", header)
    return match.group(1) if match else header


def views(value: str):
    found = re.findall(r'owner \|-> (\d+), gen \|-> (\d+), ts \|-> (\d+), origin \|-> (\d+), kind \|-> "(\w+)"', value)
    return [f"{owner}/g{gen}@{ts}" for owner, gen, ts, _origin, _kind in found]


def top_level_records(value: str):
    """Splits a printed TLA+ set or sequence of records into its records."""
    records, depth, start = [], 0, None
    for index, char in enumerate(value):
        if char == "[":
            if depth == 0:
                start = index
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0 and start is not None:
                records.append(value[start:index + 1])
    return records


def turn_starts(value: str):
    starts = []
    for record in top_level_records(value):
        flat = re.sub(r"hist \|-> \{[^{}]*\}", "", record)
        node = re.search(r"node \|-> (\d+)", flat)
        gen = re.search(r"gen \|-> (\d+)", flat)
        kind = re.search(r'kind \|-> "(\w+)"', flat)
        if node and gen and kind:
            starts.append((node.group(1), gen.group(1), kind.group(1)))
    return starts


def summarize(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    for pattern in [r"Error: Invariant \w+ is violated\.", r"Model checking completed\. No error has been found\.",
                    r"\d+ states generated, \d+ distinct states found, \d+ states left on queue\.",
                    r"The depth of the complete state graph search is \d+\.",
                    r"Finished in .*"]:
        for match in re.findall(pattern, text):
            print(match)
    for number, header, body in split_states(text):
        values = variables(body)
        run = seq_values(values.get("run", ""))
        lease = ["L" if item == "TRUE" else "-" for item in seq_values(values.get("lease", ""))]
        view = views(values.get("cache", ""))
        handoff = re.findall(r'st \|-> "(\w+)"', values.get("ho", ""))
        messages = re.findall(r'type \|-> "(\w+)"', values.get("msgs", ""))
        destinations = re.findall(r"dst \|-> (\d+)", values.get("msgs", ""))
        starts = turn_starts(values.get("execs", ""))
        print(f"{number:>2} {action_name(header):<14} run={','.join(run)} lease={''.join(lease)} "
              f"view={' '.join(view)} ho={','.join(handoff)} "
              f"msgs={[f'{kind}->{dst}' for kind, dst in zip(messages, destinations)]} "
              f"up={values.get('up', '')} cut={values.get('cut', '')} clock={values.get('clock', '')} "
              f"starts={sorted(set(f'n{n}g{g}:{k}' for n, g, k in starts))}")


if __name__ == "__main__":
    summarize(Path(sys.argv[1]))
