#!/usr/bin/env python3
"""
Setup script for pre-commit hooks.
This script installs and configures pre-commit hooks for the project.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"[INFO] {description}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print(f"[PASS] {description} - Success")
            return True
        else:
            print(f"[ERROR] {description} - Failed")
            if result.stderr:
                print(f"   Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] {description} - Error: {e}")
        return False


def check_uv_installed() -> bool:
    """Check if uv is installed."""
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def main():
    """Main setup function."""
    print("=" * 60)
    print("HRMS PBS Pre-commit Hooks Setup")
    print("=" * 60)
    print()

    project_root = Path(__file__).parent.parent

    # Check if we're in the right directory
    if not (project_root / "manage.py").exists():
        print("[ERROR] manage.py not found. Please run from project root.")
        sys.exit(1)

    # Install pre-commit
    print("\n[INFO] Installing pre-commit...")
    if check_uv_installed():
        success = run_command(["uv", "pip", "install", "pre-commit"], "Installing pre-commit with uv")
    else:
        success = run_command(
            [sys.executable, "-m", "pip", "install", "pre-commit"],
            "Installing pre-commit with pip",
        )

    if not success:
        print("\n[ERROR] Failed to install pre-commit")
        sys.exit(1)

    # Install pre-commit hooks
    print("\n[INFO] Installing pre-commit hooks...")
    success = run_command(["pre-commit", "install"], "Installing git hooks")

    if not success:
        print("\n[ERROR] Failed to install pre-commit hooks")
        sys.exit(1)

    # Install commit-msg hook for additional checks
    run_command(
        ["pre-commit", "install", "--hook-type", "commit-msg"],
        "Installing commit-msg hook",
    )

    # Update hooks to latest versions
    print("\n[INFO] Updating hooks to latest versions...")
    run_command(["pre-commit", "autoupdate"], "Updating hook versions")

    # Make scripts executable
    print("\n[INFO] Making scripts executable...")
    scripts_dir = project_root / "scripts"
    for script in scripts_dir.glob("*.py"):
        script.chmod(0o755)
        print(f"   [PASS] {script.name}")

    print("\n" + "=" * 60)
    print("[SUCCESS] Pre-commit hooks setup complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("   1. Test hooks: pre-commit run --all-files")
    print("   2. Hooks will now run automatically on git commit")
    print("   3. To skip hooks: git commit --no-verify")
    print("\nTips:")
    print("   - Update hooks: pre-commit autoupdate")
    print("   - Run specific hook: pre-commit run <hook-id>")
    print("   - Uninstall hooks: pre-commit uninstall")
    print()


if __name__ == "__main__":
    main()
