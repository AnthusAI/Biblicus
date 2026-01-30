"""
Sphinx configuration for Biblicus documentation.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from pygments.lexers.special import TextLexer
from sphinx.highlighting import lexers

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = PROJECT_ROOT / "src"

project = "Biblicus"
author = "Biblicus Contributors"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "myst_parser",
    "sphinx_rtd_theme",
]
templates_path = ["_templates"]
exclude_patterns = ["_build"]
autodoc_typehints = "description"
html_theme = "sphinx_rtd_theme"

html_theme_options = {
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "navigation_depth": 4,
}

# ReadTheDocs integration - canonical URL for SEO
if os.environ.get("READTHEDOCS"):
    rtd_version = os.environ.get("READTHEDOCS_VERSION", "latest")
    rtd_project = os.environ.get("READTHEDOCS_PROJECT", "biblicus")
    html_baseurl = f"https://{rtd_project}.readthedocs.io/{rtd_version}/"

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

suppress_warnings = ["misc.highlighting_failure"]
sys.path.insert(0, str(SOURCE_ROOT))

lexers["mermaid"] = TextLexer()
