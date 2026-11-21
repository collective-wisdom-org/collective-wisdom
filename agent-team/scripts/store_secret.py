"""Store a secret in the macOS keychain without it passing through a thread, and keep a list of the stored names.

Every team entry uses the keychain service `collective-wisdom`. The registry ~/.config/collective-wisdom/secrets.md holds names
and notes, never values. A name matches [A-Za-z0-9][A-Za-z0-9._-]{0,63}; a note is one line of at most 120 characters without a
backtick or `|`.

    store_secret.py store <name>                  print the `security` line the user pastes into their own Terminal
    store_secret.py record <name> --note <text>   add the name to the registry once the keychain holds it
    store_secret.py list                          print `<name>` and `<note>` separated by a tab, one line per registry row
"""

import os
import re
import subprocess
import sys
from pathlib import Path

SERVICE = "collective-wisdom"
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
NOTE = re.compile(r"[^\x00-\x1f\x7f-\x9f\u2028\u2029\u200b-\u200f\u202a-\u202e`|]{1,120}")
ROW = re.compile(r"`([^`]*)`")
HEADER = """# collective-wisdom secrets

Names of the secrets this machine keeps in the macOS keychain under the service `collective-wisdom`. Never values.

| Name | Note |
|---|---|
"""


class SecretError(Exception):
    pass


def path():
    return Path.home() / ".config" / "collective-wisdom" / "secrets.md"


def _shown(text):
    return ascii(text)[1:-1]


def _rows(file):
    """[(name, note)] in file order; [] with no file. Raises SecretError on an unreadable file or a row that is not `name` | note."""
    try:
        lines = file.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as e:
        raise SecretError(f"cannot read {file}: {type(e).__name__}")
    rows = []
    for n, line in enumerate(lines, 1):
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells[0] == "Name" or re.fullmatch(r":?-+:?", cells[0]):
            continue
        m = len(cells) == 2 and ROW.fullmatch(cells[0])
        if not m or not NAME.fullmatch(m[1]) or not NOTE.fullmatch(cells[1]):
            raise SecretError(f"{file}:{n}: a row must be `<safe name>` | <note>")
        rows.append((m[1], cells[1]))
    return rows


def _write(file, rows):
    text = HEADER + "".join(f"| `{name}` | {note} |\n" for name, note in rows)
    tmp = file.with_name(f"{file.name}.tmp")
    try:
        file.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(tmp, 0o600)
        os.replace(tmp, file)
    except OSError as e:
        raise SecretError(f"cannot write {file}: {type(e).__name__}")


def in_keychain(name):
    """True when the keychain holds the item. No -w, so no value is read; the output is discarded."""
    cmd = ["security", "find-generic-password", "-s", SERVICE, "-a", name]
    try:
        code = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30).returncode
    except FileNotFoundError:
        raise SecretError("the security command is not on PATH (macOS only)")
    except subprocess.SubprocessError:
        raise SecretError("security did not answer")
    if code not in (0, 44):  # 44: item not found; anything else is a locked keychain or similar, not a missing item
        raise SecretError(f"security exited {code}; check that the keychain is unlocked")
    return code == 0


def record(name, note):
    """Add name with note to the registry, or replace its note. Returns False, writing nothing, when the keychain lacks the item."""
    if not in_keychain(name):
        return False
    file = path()
    rows = _rows(file)
    new = [(n, note if n == name else old) for n, old in rows]
    _write(file, new if any(n == name for n, _ in rows) else new + [(name, note)])
    return True


def main(argv):
    cmd, args = (argv[:1] or [""])[0], argv[1:]
    try:
        if cmd == "list" and not args:
            for name, note in _rows(path()):
                print(f"{name}\t{note}")
        elif (cmd, len(args)) in (("store", 1), ("record", 3)) and args[1:2] in ([], ["--note"]):
            name = args[0]
            if not NAME.fullmatch(name):
                raise SecretError(f"{_shown(name)} is not a safe secret name")
            if cmd == "store":
                print(f"security add-generic-password -U -s {SERVICE} -a {name} -w")
                return 0
            note = args[2].strip()
            if not NOTE.fullmatch(note):
                raise SecretError("a note is one line of 1 to 120 characters without a backtick or |")
            if not record(name, note):
                print(f"store_secret: {name} is not in the keychain; run the store line first", file=sys.stderr)
                return 1
            print(f"recorded {name}")
        else:
            raise SecretError("usage: store_secret.py store <name> | record <name> --note <text> | list")
    except SecretError as e:
        print(f"store_secret: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
