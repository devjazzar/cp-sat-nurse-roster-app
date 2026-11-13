#!/usr/bin/env python3
"""Write a ticket session's brief and the prompt the user pastes (docs/guides/local-development.md, section 4.4).

The template is appendix A's fenced block in the guide, the one source of truth for it; this script only fills it in.
What only the main session can write, it takes from two files: the ticket's asks (its criteria, grouped, with the decisions
already taken and what earlier tickets left for it, the open points marked **Worth your review**) and its test seams.

    scripts/ticket-brief.py 56 --spec probation --asks asks-56.md --seams seams-56.md \\
        [--prev 55] [--peers 57 61] [--out DIR]

It reads the ticket at .scratch/*/issues/<NN>-*.md, its title from the first heading, and the base from origin/main (fetch
first). It writes DIR/brief-<NN>.txt and DIR/prompt-<NN>.txt (DIR defaults to the current directory) and prints both paths.
"""

import argparse
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
GUIDE = REPO / "docs/guides/local-development.md"


def template() -> str:
    text = GUIDE.read_text()
    section = text.split("## Appendix A", 1)[1]
    match = re.search(r"^```\n(.*?)^```$", section, re.DOTALL | re.MULTILINE)
    if not match:
        sys.exit("appendix A has no fenced brief")
    return match.group(1)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("nn")
    p.add_argument("--spec", required=True, help="the spec's name under <release>/specs/, without .md")
    p.add_argument("--asks", required=True, type=pathlib.Path)
    p.add_argument("--seams", required=True, type=pathlib.Path)
    p.add_argument("--prev", help="the ticket whose comment is the model (default NN-1)")
    p.add_argument("--peers", nargs="*", default=[], help="tickets whose sessions run at the same time")
    p.add_argument("--out", type=pathlib.Path, default=pathlib.Path("."))
    a = p.parse_args()

    tickets = sorted(REPO.glob(f".scratch/*/issues/{a.nn}-*.md"))
    if len(tickets) != 1:
        sys.exit(f"expected one ticket {a.nn}, found {[str(t) for t in tickets]}")
    ticket = tickets[0]
    release = ticket.parent.parent
    spec = release / "specs" / f"{a.spec}.md"
    if not spec.exists():
        sys.exit(f"no spec at {spec}")
    heading = ticket.read_text().splitlines()[0]
    title = re.sub(rf"^#\s*{a.nn}:\s*", "", heading)
    base = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "origin/main"],
                          check=True, capture_output=True, text=True).stdout.strip()
    rel = lambda path: str(path.relative_to(REPO))
    if a.peers:
        names = " and ".join(a.peers)
        who = "Another ticket session runs" if len(a.peers) == 1 else "Other ticket sessions run"
        peers = f"{who} at the same time ({names}), so `main` will move under you"
    else:
        peers = "No other ticket session runs at the same time, but the main session's `[skip ci]` commits still move `main`"

    fields = {
        "NN": a.nn, "path": rel(ticket), "title": title, "base": base, "main": str(REPO), "spec": rel(spec),
        "prev": a.prev or str(int(a.nn) - 1), "peers": peers,
        "asks": a.asks.read_text().strip(), "seams": a.seams.read_text().strip(),
    }
    brief = template()
    for key, value in fields.items():
        brief = brief.replace("{" + key + "}", value)
    left = re.findall(r"\{[A-Za-z]+\}", brief)
    if left:
        sys.exit(f"placeholders left unfilled: {left}")

    a.out.mkdir(parents=True, exist_ok=True)
    brief_path, prompt_path = a.out / f"brief-{a.nn}.txt", a.out / f"prompt-{a.nn}.txt"
    brief_path.write_text(brief)
    prompt_path.write_text(f"/implement-spec Ticket: {a.nn}, {rel(ticket)}. Spec: {rel(spec)}. "
                           "Follow the brief you were started with. Use the advisor when needed.\n")
    print(brief_path)
    print(prompt_path)


if __name__ == "__main__":
    main()
