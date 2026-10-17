from pathlib import Path

import tomllib

PYPROJECT_PATH = Path(__file__).resolve().parent.parent / "pyproject.toml"


def collect_all_declared_dependency_requirements() -> list[str]:
    project_table = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]
    requirements = list(project_table.get("dependencies", []))
    for extra_requirements in project_table.get("optional-dependencies", {}).values():
        requirements.extend(extra_requirements)
    return requirements


def test_no_declared_dependency_uses_a_direct_url_reference():
    direct_url_requirements = [
        requirement
        for requirement in collect_all_declared_dependency_requirements()
        if " @ " in requirement
    ]
    assert direct_url_requirements == [], (
        "PyPI rejects uploads whose metadata contains direct URL dependencies: "
        f"{direct_url_requirements}"
    )
