import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "python_floor_check.py"
LIMIT = 256 * 1024


class CommandTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "private-project-name.toml"

    def write_expression(self, expression):
        declaration = json.dumps(expression, ensure_ascii=False)
        self.path.write_text(
            f"[project]\nrequires-python = {declaration}\n", encoding="utf-8"
        )

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            capture_output=True,
            timeout=8,
        )

    def check_results(self, expression, candidates, expected, exit_code):
        self.write_expression(expression)
        result = self.run_cli(self.path, *candidates)
        self.assertEqual(result.returncode, exit_code, result.stderr)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(
            json.loads(result.stdout),
            {"candidates": [
                {"ordinal": index, "match": match, "failed_clauses": failures}
                for index, (match, failures) in enumerate(expected, 1)
            ]},
        )

    def assert_invalid(self, result):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout), {"error": "invalid_input"})

    def test_zero_padding_and_exact_operators(self):
        self.check_results(
            " == 3.11.0 , != 3.11.1 ",
            [" 3.11 ", "3.11.0", "3.11.1", "3.11.2"],
            [(True, []), (True, []), (False, [1, 2]), (False, [1])],
            1,
        )

    def test_inclusive_and_exclusive_ordered_edges(self):
        self.check_results(
            ">=3.11,<=3.12.2,>3.11.0,<3.13",
            ["3.10.9", "3.11", "3.11.1", "3.12.2", "3.13"],
            [(False, [1, 3]), (False, [3]), (True, []), (True, []), (False, [2, 4])],
            1,
        )

    def test_wildcard_equality_and_inequality(self):
        self.check_results(
            "==3.11.*,!=3.12.*",
            ["3.11", "3.11.999999999", "3.12.0", "3.110"],
            [(True, []), (True, []), (False, [1, 2]), (False, [1])],
            1,
        )
        self.check_results("!=3.11.*", ["3.12"], [(True, [])], 0)

    def test_all_matching_candidates_at_count_limit(self):
        self.check_results(
            ",".join(["<=999999999.999999999.999999999"] * 64),
            ["0.0"] * 64,
            [(True, [])] * 64,
            0,
        )

    def test_invalid_clauses_invalidate_whole_expression(self):
        invalid = (
            "", " ", ",>=3.11", ">=3.11,", ">=3.11,,<4.0", ">=3.11,~=4.0",
            "===3.11", "==3", "==03.11", "==3.011", "==3.11.00", "==3.11.0.0",
            "==3.11rc1", "==3.11+local", "==1!3.11", "==v3.11", "==３.１１",
            ">=3.11.*", "==3.*", "==3.11.0.*", "==3.11 . *", "==3. 11",
            "==\t3.11", "==3.11\n", "==\u00a03.11", "==1000000000.0",
            ",".join(["==3.11"] * 65),
        )
        for expression in invalid:
            with self.subTest(expression=expression):
                self.write_expression(expression)
                self.assert_invalid(self.run_cli(self.path, "3.0"))

    def test_invalid_later_candidate_invalidates_all_results(self):
        self.write_expression(">=3.11")
        for candidate in ("", "3", "3.11.*", "3.11rc1", "03.11", "３.１１", "3.11\t", "3.1000000000"):
            with self.subTest(candidate=candidate):
                self.assert_invalid(self.run_cli(self.path, "3.10", candidate))
        self.assert_invalid(self.run_cli(self.path, *(["3.11"] * 65)))
        self.assert_invalid(self.run_cli(self.path))

    def test_malformed_toml_or_missing_string_is_private(self):
        for content in (
            b"",
            b"[project\nPRIVATE_TOKEN",
            b'[tool.example]\nrequires-python = ">=3.11"\n',
            b'project = "PRIVATE_TOKEN"\n',
            b"[project]\nrequires-python = 311\n",
            b"[project]\nrequires-python = [\xff]\n",
            b"data = " + (b"[" * 3000) + (b"]" * 3000),
        ):
            with self.subTest(content=content[:70]):
                self.path.write_bytes(content)
                self.assert_invalid(self.run_cli(self.path, "3.11"))

    def test_byte_limit_inclusive(self):
        prefix = b'[project]\nrequires-python = ">=3.11"\n#'
        self.path.write_bytes(prefix + b"x" * (LIMIT - len(prefix)))
        result = self.run_cli(self.path, "3.11")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {"candidates": [{"ordinal": 1, "match": True, "failed_clauses": []}]},
        )
        with self.path.open("ab") as file:
            file.write(b"x")
        self.assert_invalid(self.run_cli(self.path, "3.11"))

    def test_missing_and_directory_inputs_are_private(self):
        self.assert_invalid(self.run_cli(self.path, "3.11"))
        self.assert_invalid(self.run_cli(self.path.parent, "3.11"))

    def test_unsafe_spellings_rejected_before_file_access(self):
        wrapper = r"""
import os
import runpy
import sys
from unittest.mock import patch

main = runpy.run_path(sys.argv[1])["main"]

def fail(*args, **kwargs):
    raise AssertionError("filesystem accessed")

with patch("os.stat", fail), patch("os.open", fail), patch("builtins.open", fail):
    raise SystemExit(main(sys.argv[2:]))
"""
        unsafe_paths = (
            "https://example.invalid/private.toml", "file:private.toml",
            "a://example.invalid/private.toml", "C:private.toml", "x/private.toml:ads",
            "//host/share/private.toml", r"\\host\share\private.toml",
            r"\/host/share/private.toml", r"/\host/share/private.toml",
            r"\\?\C:\private.toml", r"\\.\pipe\private.toml",
            r"\??\C:\private.toml", "/Device/HarddiskVolume1/private.toml",
            r"\DosDevices\private.toml", "/Global??/private.toml",
            r"\SystemRoot\private.toml", "/GlobalRoot/private.toml",
            r"\Device\..\private.toml", "/GlobalRoot/../private.toml",
            r"\??\..\private.toml", r"\SystemRoot\..\private.toml",
            "/./Device/HarddiskVolume1/private.toml",
            "NUL", "tmp/con.txt", "tmp/AuX .toml", "tmp/PRN.../private.toml",
            r"C:\tmp\CoM1.txt", "tmp/LPT².txt", "tmp/CONIN$.txt", "tmp/CONOUT$",
        )
        for path in unsafe_paths:
            with self.subTest(path=path):
                self.assert_invalid(subprocess.run(
                    [sys.executable, "-c", wrapper, str(SCRIPT), path, "3.11"],
                    capture_output=True,
                    timeout=8,
                ))

    def test_report_is_reproducible_and_omits_inputs(self):
        self.write_expression(">=987654321.999999999")
        first = self.run_cli(self.path, "123456789.123456789")
        second = self.run_cli(self.path, "123456789.123456789")
        self.assertEqual(first.returncode, 1, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(first.stderr, b"")
        for raw in (b"private-project-name", b"987654321", b"123456789"):
            self.assertNotIn(raw, first.stdout)

    def test_help_is_available(self):
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn(b"PYPROJECT VERSION", result.stdout)
        self.assertEqual(result.stderr, b"")

    def test_real_closed_stdout_pipe_returns_two_quietly(self):
        self.write_expression(">=3.11")
        for args in (("--help",), (str(self.path), "3.11"), (str(self.path), "3.0"), ()):
            with self.subTest(args=args):
                read_fd, write_fd = os.pipe()
                os.close(read_fd)
                try:
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), *args],
                        stdout=write_fd,
                        stderr=subprocess.PIPE,
                        timeout=8,
                    )
                finally:
                    os.close(write_fd)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stderr, b"")
