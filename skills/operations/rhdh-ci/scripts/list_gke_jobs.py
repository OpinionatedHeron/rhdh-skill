#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["rhdh-common[yaml]"]
#
# [tool.uv.sources]
# rhdh-common = { git = "https://github.com/redhat-developer/rhdh-skill", subdirectory = "packages/rhdh-common" }
# ///
"""List GKE test entries in RHDH CI config files."""

import sys

from rhdh_prow.k8s_configs import main

if __name__ == "__main__":
    main(["--pattern", "^e2e-gke-", *sys.argv[1:]])
