"""Check explicit stable Python versions against a local pyproject declaration."""

import json
import ntpath
import operator
import os
import re
import stat
import sys
import tomllib


MAX_BYTES = 256 * 1024
MAX_ITEMS = 64
NUMBER = r"(?:0|[1-9][0-9]{0,8})"
MINOR = rf"{NUMBER}\.{NUMBER}"
RELEASE = re.compile(rf"{MINOR}(?:\.{NUMBER})?")
PREFIX = re.compile(rf"{MINOR}\.\*")
CLAUSE = re.compile(r"(<=|>=|==|!=|<|>) *(.+)")
COMPARE = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}
ABSOLUTE_DRIVE = re.compile(r"[A-Za-z]:\\(?!\\)")
NATIVE_ROOTS = {"??", "device", "dosdevices", "global??", "systemroot", "globalroot"}
DEVICE = re.compile(r"con|prn|aux|nul|clock\$|conin\$|conout\$|(?:com|lpt)[1-9¹²³]")
HELP = (
    "Usage: python python_floor_check.py PYPROJECT VERSION [VERSION ...]\n"
    "\n"
    "Check explicit stable Python versions against project.requires-python.\n"
    "Exit 0 for all matches, 1 for any mismatch, and 2 for invalid input or I/O.\n"
)


def validate_path(path):
    spelling = path.replace("/", "\\")
    if not spelling or any(ord(char) < 32 for char in spelling):
        raise ValueError
    if spelling.startswith("\\\\"):
        raise ValueError
    if spelling.startswith("\\"):
        for rooted in (spelling, ntpath.normpath(spelling)):
            root = rooted.split("\\", 2)[1]
            if root.rstrip(" .").casefold() in NATIVE_ROOTS:
                raise ValueError

    remainder = spelling[3:] if ABSOLUTE_DRIVE.match(spelling) else spelling
    if ":" in remainder:
        raise ValueError
    for component in remainder.split("\\"):
        stem = component.split(".", 1)[0].rstrip(" ").casefold()
        if DEVICE.fullmatch(stem):
            raise ValueError


def read_requirement(path):
    validate_path(path)
    info = os.stat(path)
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
        raise ValueError

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as file:
        info = os.fstat(file.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise ValueError
        payload = file.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError

    project = tomllib.loads(payload.decode("utf-8")).get("project")
    if not isinstance(project, dict) or not isinstance(project.get("requires-python"), str):
        raise ValueError
    return project["requires-python"]


def parse_version(token):
    token = token.strip(" ")
    if not RELEASE.fullmatch(token):
        raise ValueError
    parts = tuple(map(int, token.split(".")))
    return parts if len(parts) == 3 else (*parts, 0)


def parse_clauses(expression):
    tokens = expression.split(",", MAX_ITEMS)
    if len(tokens) > MAX_ITEMS:
        raise ValueError
    clauses = []
    for token in tokens:
        clause = CLAUSE.fullmatch(token.strip(" "))
        if clause is None:
            raise ValueError
        comparison, version = clause.groups()
        if comparison in ("==", "!=") and PREFIX.fullmatch(version):
            bound = tuple(map(int, version[:-2].split(".")))
        else:
            bound = parse_version(version)
        clauses.append((COMPARE[comparison], bound))
    return clauses


def evaluate(argv):
    if not 2 <= len(argv) <= MAX_ITEMS + 1:
        raise ValueError
    candidates = [parse_version(token) for token in argv[1:]]
    clauses = parse_clauses(read_requirement(argv[0]))
    results = []
    for ordinal, version in enumerate(candidates, 1):
        failures = [
            index
            for index, (compare, bound) in enumerate(clauses, 1)
            if not compare(version[:len(bound)], bound)
        ]
        results.append({"ordinal": ordinal, "match": not failures, "failed_clauses": failures})
    return results


def main(argv):
    if argv == ["--help"] or argv == ["-h"]:
        output, code = HELP, 0
    else:
        try:
            results = evaluate(argv)
            report = {"candidates": results}
            code = int(any(not result["match"] for result in results))
        except (OSError, ValueError, RecursionError):
            report, code = {"error": "invalid_input"}, 2
        output = json.dumps(report, separators=(",", ":")) + "\n"

    # Direct descriptor writes avoid a second, buffered flush at interpreter exit.
    pending = memoryview(output.encode("ascii"))
    try:
        while pending:
            written = os.write(1, pending)
            if not written:
                return 2
            pending = pending[written:]
    except OSError:
        return 2
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
