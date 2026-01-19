#!/usr/bin/env python3
"""
Check for unapplied or missing Django migrations.
This ensures models and migrations are in sync.
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    """Check for missing migrations."""
    # Ensure we're in the project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Check if manage.py exists
    if not Path("manage.py").exists():
        print("[ERROR] manage.py not found. Are you in the project root?")
        sys.exit(1)

    print("[INFO] Checking for missing migrations...")

    try:
        # Check for missing migrations
        result = subprocess.run(
            [sys.executable, "manage.py", "makemigrations", "--check", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Check if Django is not available
        if "No module named 'django'" in result.stderr or "No module named 'django'" in result.stdout:
            print("[WARNING] Django not available in current environment")
            print("[INFO] Skipping migration checks (run manually with: python manage.py makemigrations --check)")
            sys.exit(0)

        if result.returncode != 0:
            print("\n[ERROR] Missing migrations detected:\n")
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            print("\nPlease create migrations with: python manage.py makemigrations")
            print("Then add them to your commit.")
            print("\nTo skip this check: git commit --no-verify")
            sys.exit(1)

        print("[PASS] No missing migrations")

        # Also check for unapplied migrations (informational only)
        print("[INFO] Checking for unapplied migrations...")
        result = subprocess.run(
            [sys.executable, "manage.py", "showmigrations", "--plan"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if "[ ]" in result.stdout:
            print("\n[WARNING] There are unapplied migrations:")
            for line in result.stdout.split("\n"):
                if "[ ]" in line:
                    print(f"  {line}")
            print("\nConsider running: python manage.py migrate")
            print("(This is just a warning, not blocking the commit)")

        sys.exit(0)

    except subprocess.TimeoutExpired:
        print("[ERROR] Migration check timed out after 30 seconds")
        sys.exit(1)
    except Exception as e:
        print(f"[WARNING] Error checking migrations: {e}")
        # Don't fail if database is not available
        print("[INFO] Skipping migration check")
        sys.exit(0)


if __name__ == "__main__":
    main()
