#!/usr/bin/env python3
"""
Check that .env.example is up to date with .env.staging.
Ensures all required environment variables are documented.
"""

import re
import sys
from pathlib import Path


def parse_env_file(filepath: Path) -> dict[str, str]:
    """Parse an env file and return a dict of keys (without values for security)."""
    env_vars = {}

    if not filepath.exists():
        return env_vars

    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            # Extract key
            match = re.match(r"^([A-Z_][A-Z0-9_]*)=", line)
            if match:
                key = match.group(1)
                env_vars[key] = True

    return env_vars


def main():
    """Check .env.example against .env.staging."""
    project_root = Path(__file__).parent.parent

    env_example = project_root / ".env.example"
    env_staging = project_root / ".env.staging"

    if not env_example.exists():
        print("[WARNING] .env.example not found, skipping check")
        sys.exit(0)

    if not env_staging.exists():
        print("[WARNING] .env.staging not found, skipping check")
        sys.exit(0)

    print("[INFO] Checking .env.example is up to date...")

    example_vars = parse_env_file(env_example)
    staging_vars = parse_env_file(env_staging)

    # Find variables in staging but not in example
    missing_in_example = set(staging_vars.keys()) - set(example_vars.keys())

    # Exclude deployment-specific variables that shouldn't be in example
    deployment_specific = {
        "STAGING_SSH_HOST",
        "STAGING_SSH_USERNAME",
        "STAGING_SSH_PASSWORD",
        "STAGING_SSH_PORT",
        "STAGING_DEPLOY_PATH",
        "STAGING_BACKUP_PATH",
        "STAGING_TEAMS_WEBHOOK_URL",
    }

    missing_in_example = missing_in_example - deployment_specific

    if missing_in_example:
        print("\n[ERROR] The following variables are in .env.staging but missing from .env.example:\n")
        for var in sorted(missing_in_example):
            print(f"  - {var}")
        print("\nPlease add these variables to .env.example with placeholder values.")
        print("This ensures all developers know what environment variables are needed.")
        print("\nTo skip this check: git commit --no-verify")
        sys.exit(1)

    print("[PASS] .env.example is up to date")
    sys.exit(0)


if __name__ == "__main__":
    main()
