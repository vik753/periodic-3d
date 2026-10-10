#!/usr/bin/env python3
"""Validate that all workflow YAML files parse. Skips if PyYAML is missing."""

import glob
import sys

try:
    import yaml
except ImportError:  # pragma: no cover - depends on the machine
    print("yaml: skipped (PyYAML not installed)")
    sys.exit(0)

failed = False
for path in sorted(glob.glob(".github/workflows/*.yml")):
    try:
        with open(path, encoding="utf-8") as handle:
            yaml.safe_load(handle)
    except yaml.YAMLError as error:
        failed = True
        print(f"yaml: {path}: {error}")
print("yaml: failed" if failed else "yaml: ok")
sys.exit(1 if failed else 0)
