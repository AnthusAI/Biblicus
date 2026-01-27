"""
Sphinx configuration for Biblicus documentation.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = PROJECT_ROOT / "src"

project = "Biblicus"
author = "Biblicus Contributors"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "myst_parser",
]
templates_path = ["_templates"]
exclude_patterns = ["_build"]
autodoc_typehints = "description"
html_theme = "alabaster"

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

import sys

sys.path.insert(0, str(SOURCE_ROOT))
