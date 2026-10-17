import re
from pathlib import Path

PYPROJECT_PATH = Path(__file__).resolve().parent.parent / "pyproject.toml"
DIRECT_URL_REQUIREMENT_PATTERN = re.compile(r'^\s*"[^"]+\s@\s[a-z+]+://[^"]*"', re.MULTILINE)


def test_no_declared_dependency_uses_a_direct_url_reference():
    pyproject_text = PYPROJECT_PATH.read_text(encoding="utf-8")
    direct_url_requirements = DIRECT_URL_REQUIREMENT_PATTERN.findall(pyproject_text)
    assert direct_url_requirements == [], (
        "PyPI rejects uploads whose metadata contains direct URL dependencies: "
        f"{direct_url_requirements}"
    )


def test_pattern_detects_the_rejected_requirement_shape():
    rejected_line = '  "en-core-web-sm @ https://example.com/model-1.0-py3-none-any.whl",'
    assert DIRECT_URL_REQUIREMENT_PATTERN.findall(rejected_line) != []
