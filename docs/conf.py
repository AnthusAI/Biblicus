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
exclude_patterns = ["_build", "index.md"]
autodoc_typehints = "description"
html_theme = "biblicus_rtd"
html_theme_path = [str(Path(__file__).resolve().parent / "_themes")]
html_static_path = ["_static"]
html_css_files = ["css/biblicus.css"]
html_context = {"contact_url": "https://anth.us/engage/?solution=Biblicus&cta=api-reference"}

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
    html_theme_options["canonical_url"] = html_baseurl

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

root_doc = "api"
suppress_warnings = ["misc.highlighting_failure", "toc.not_included"]
sys.path.insert(0, str(SOURCE_ROOT))

lexers["mermaid"] = TextLexer()
