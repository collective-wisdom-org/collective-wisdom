"""Section pointers (`ship-loop` § Team mode, `reference.md` § Setup, a bare § Heading) name a real heading.

Moving or renaming a section must not leave a pointer to a heading that is gone.
A quoted subpart after the heading ("Failed handoff") must appear in that section.
"""

import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDORED = {"agent-security", "owasp-security"}
EXTERNAL = {"superpowers-project-memory"}  # a skill outside this tree

POINTER = re.compile(r"§\s*(?P<rest>[^§]*)")
# What sits just before the §: a markdown link, or a (backticked / bold) name.
BEFORE = re.compile(
    r"(?:\[[^\]]*\]\((?P<link>[^)\s]+)\)|[`*]*(?P<name>\w[\w./-]*)[`*]*)(?:\s+incl\.)?\s*$"
)
QUOTED = re.compile(r"""^\s*[(,]?\s*["“](?P<sub>[^"”]+)["”]""")


def sources(root):
    skills = root / ".claude" / "skills"
    files = [p for p in skills.rglob("*.md") if p.relative_to(skills).parts[0] not in VENDORED]
    files += (root / "docs" / "agents").rglob("*.md")
    files += (root / "templates").glob("*.md")
    return sorted(files)


def plain(text):
    return re.sub(r"[`*]", "", text)


def parse(path):
    """Return (headings, lines, pointer lines). Fenced code is skipped.

    A heading is (level, text, line index). A bold lead-in ("- **Own login.** ...") counts as level 7.
    """
    headings, lines, fenced, body = [], path.read_text().splitlines(), False, []
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced:
            body.append((i, line))
            m = re.match(r"(#{1,6})\s+(.*?)\s*#*$", line)
            lead = re.match(r"\s*(?:[-*]|\d+\.)?\s*\*\*(.+?)\*\*", line)
            if m:
                headings.append((len(m.group(1)), plain(m.group(2)), i))
            elif lead:
                headings.append((7, plain(lead.group(1)).rstrip(".:"), i))
    return headings, lines, body


def variants(heading):
    """The full heading, and the shortened forms pointers use: text before a colon or parenthetical."""
    return {heading, re.split(r"\s*[:(]", heading)[0]} - {""}


def resolve(root, src, ref, linked):
    """Find the file a pointer names, or None. Skill name, path, or file name."""
    skills = root / ".claude" / "skills"
    if (skills / ref / "SKILL.md").is_file():
        return skills / ref / "SKILL.md"
    ref = ref.removeprefix("docs/agents/")
    base = Path(ref).name
    skill_dir = next((p for p in src.parents if p.parent == skills), None)
    candidates = [(src.parent / ref).resolve(), root / "docs" / "agents" / ref, root / "templates" / base, skills / ref]
    if skill_dir and not linked:
        candidates[:0] = [skill_dir / ref, skill_dir / base]
    found = next((c for c in candidates if c.is_file()), None)
    return found or next((p for p in (root / "docs" / "agents").rglob(base) if p.is_file()), None)


def last_mention(root, src, text):
    """The file last named in text (`name`, **name** or a link target), or None."""
    for ref in reversed(re.findall(r"`([\w./-]+)`|\*\*([\w./-]+)\*\*|\]\(([^)\s]+)\)", text)):
        ref = next(r for r in ref if r).split("#")[0]
        if ref.endswith(".md") or (root / ".claude/skills" / ref).is_dir():
            return resolve(root, src, ref, False)
    return None


def section(lines, headings, n):
    level, _, start = headings[n]
    end = next((h[2] for h in headings[n + 1 :] if h[0] <= level), None)
    return plain("\n".join(lines[start:end]))


def broken_pointers(root):
    out, parsed = [], {}

    def get(path):
        if path not in parsed:
            parsed[path] = parse(path)
        return parsed[path]

    for src in sources(root):
        body = get(src)[2]
        skill_dir = next((p for p in src.parents if p.parent == root / ".claude" / "skills"), None)
        for i, line in body:
            last = prev_rest = None
            for m in POINTER.finditer(line):
                pre, rest = line[: m.start()], plain(m.group("rest"))
                b = BEFORE.search(pre)
                ref = b and (b.group("link") or b.group("name"))
                ref = ref and ref.split("#")[0]
                where = f"{src.relative_to(root)}:{i + 1}"
                target, sibling_ok = src, False
                if ref in EXTERNAL or re.match(r"name\b", rest):  # "every other § name" is prose
                    continue
                if ref and (ref.endswith(".md") or "/" in ref or (root / ".claude/skills" / ref).is_dir()):
                    target = resolve(root, src, ref, bool(b.group("link")))
                    if target is None:
                        out.append(f"{where}: file '{ref}' not found: § {rest[:40]}")
                        continue
                elif re.search(r"\bits?\s*$", pre, re.I) and (named := last_mention(root, src, pre)):
                    target = named
                elif last and re.search(r"(\band|\bor|[,;])\s*\(?$", prev_rest):
                    target = last
                else:
                    sibling_ok = True
                last, prev_rest = target, rest
                targets = [target]
                if sibling_ok and skill_dir:
                    targets += [p for p in sorted(skill_dir.glob("*.md")) if p != src]
                matched, failed = False, None
                for t in targets:
                    headings, tlines, _ = get(t)
                    for n, (_, text, _) in enumerate(headings):
                        for v in variants(text):
                            if not re.match(re.escape(v) + r"(?![\w-])", rest):
                                continue
                            q = QUOTED.match(rest[len(v) :])
                            if not q or q.group("sub") in section(tlines, headings, n):
                                matched = True
                            else:
                                failed = q.group("sub")
                if matched:
                    continue
                what = f' (no "{failed}" in section)' if failed else " (no such heading)"
                out.append(f"{where}: {target.name} § {rest[:40]}{what}")
    return out


def test_section_pointers_resolve():
    broken = broken_pointers(ROOT)
    assert not broken, "pointers to missing headings:\n" + "\n".join(broken)


def test_checker_reports_a_broken_pointer():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        skill = root / ".claude" / "skills" / "alpha"
        skill.mkdir(parents=True)
        (root / "docs" / "agents").mkdir(parents=True)
        (skill / "SKILL.md").write_text("# Alpha\n\n## Setup (once)\n\nSee `beta` § Team mode and § Gone.\n")
        (skill / "reference.md").write_text("## Take over\n\nBack in `alpha` § Setup, `alpha` § Nope.\n")
        (root / ".claude" / "skills" / "beta").mkdir()
        (root / ".claude" / "skills" / "beta" / "SKILL.md").write_text(
            '## Team mode\n\nMore text, "Failed handoff".\n\n## Other\n\nx\n'
        )
        (root / "docs" / "agents" / "x.md").write_text(
            '`beta` § Team mode "Failed handoff", `beta` § Team mode "Missing", `reference.md` § Take over\n'
            "```\n§ Ignored in fence\n```\n"
        )
        got = broken_pointers(root)
    assert [g.split(": ")[0] for g in got] == [
        ".claude/skills/alpha/SKILL.md:5",  # § Gone
        ".claude/skills/alpha/reference.md:3",  # `alpha` § Nope
        "docs/agents/x.md:1",  # § Team mode "Missing"
        "docs/agents/x.md:1",  # `reference.md` is not in docs/agents
    ]
