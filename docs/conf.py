from __future__ import annotations

import os
import sys
from importlib import metadata

sys.path.insert(0, os.path.abspath("../src"))

project = "gmocoin-client"
author = "GMO Coin"

try:
    release = metadata.version("gmocoin-client")
except metadata.PackageNotFoundError:
    release = "0.0.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autosummary_generate = True
autodoc_member_order = "bysource"
autodoc_typehints = "description"
napoleon_google_docstring = True
napoleon_numpy_docstring = False

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_title = f"{project} {release}"
