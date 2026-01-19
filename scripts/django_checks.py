#!/usr/bin/env python3
"""
Run Django system checks before commit.
This ensures the Django project configuration is valid.
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    """Run Django system checks."""
    # Ensure we're in the project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Check if manage.py exists
    if not Path("manage.py").exists():
        print("[ERROR] manage.py not found. Are you in the project root?")
        sys.exit(1)

    print("[INFO] Running Django system checks...")

    try:
        # Run Django check command
        result = subprocess.run(
            [sys.executable, "manage.py", "check", "--deploy"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Check if Django is not available
        if "No module named 'django'" in result.stderr or "No module named 'django'" in result.stdout:
            print("[WARNING] Django not available in current environment")
            print("[INFO] Skipping Django checks (run manually with: python manage.py check)")
            sys.exit(0)

        if result.returncode != 0:
            print("\n[ERROR] Django system check failed:\n")
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            print("\nPlease fix the issues before committing.")
            print("To skip this check: git commit --no-verify")
            sys.exit(1)

        # Check for warnings
        if "WARNING" in result.stdout or "WARNING" in result.stderr:
            print("\n[WARNING] Django system check passed with warnings:\n")
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            # Don't fail on warnings, just display them
        else:
            print("[PASS] Django system check passed")

        sys.exit(0)

    except subprocess.TimeoutExpired:
        print("[ERROR] Django check timed out after 30 seconds")
        sys.exit(1)
    except Exception as e:
        print(f"[WARNING] Error running Django check: {e}")
        print("[INFO] Skipping Django checks")
        sys.exit(0)


if __name__ == "__main__":
    main()
