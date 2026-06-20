#!/usr/bin/env python3
"""Compatibility wrapper for the internal GSAP workflow script."""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from gsap_workflow import main  # noqa: E402


if __name__ == "__main__":
    main()
