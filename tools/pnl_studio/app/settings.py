"""Filesystem paths and tunables shared by the whole app."""

from __future__ import annotations

import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))
TOOL_DIR = os.path.dirname(APP_DIR)
REPO_ROOT = os.path.dirname(os.path.dirname(TOOL_DIR))

STATIC_DIR = os.path.join(TOOL_DIR, "static")
CONFIG_PATH = os.path.join(TOOL_DIR, "config", "catalog.json")
UPLOAD_DIR = os.path.join(TOOL_DIR, "uploads")

# Folders scanned for platform payment/settlement exports.
DATA_ROOTS = [
    os.path.join(REPO_ROOT, "Finance"),
    UPLOAD_DIR,
]

ALLOWED_UPLOAD_EXT = {".xlsx", ".xls", ".csv"}
