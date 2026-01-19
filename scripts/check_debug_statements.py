#!/usr/bin/env python3
"""
Check for debug statements, print statements, and sensitive logging in Python files.
This script is used as a pre-commit hook to prevent debugging code from being committed.
"""

import re
import sys
from pathlib import Path

# Patterns to detect
PATTERNS = [
    # Print statements (but allow logger.info, logger.debug, etc.)
    (r"^\s*print\s*\(", "print() statement found"),
    # pdb debugger
    (r"import\s+pdb", "pdb import found"),
    (r"pdb\.set_trace\(\)", "pdb.set_trace() found"),
    # ipdb debugger
    (r"import\s+ipdb", "ipdb import found"),
    (r"ipdb\.set_trace\(\)", "ipdb.set_trace() found"),
    # breakpoint()
    (r"^\s*breakpoint\s*\(", "breakpoint() found"),
    # console.log equivalent
    (r"console\.log\(", "console.log() found (JavaScript)"),
    # Sensitive data patterns in logs
    (
        r"logger\.(info|debug|warning|error)\([^)]*password[^)]*\)",
        "Potential password in log",
    ),
    (
        r"logger\.(info|debug|warning|error)\([^)]*secret[^)]*\)",
        "Potential secret in log",
    ),
    (
        r"logger\.(info|debug|warning|error)\([^)]*token[^)]*\)",
        "Potential token in log",
    ),
    (
        r"logger\.(info|debug|warning|error)\([^)]*api[_-]?key[^)]*\)",
        "Potential API key in log",
    ),
    # TODO/FIXME with security implications
    (r"#\s*TODO.*security", "Security-related TODO found"),
    (r"#\s*FIXME.*security", "Security-related FIXME found"),
]

# Files to exclude
EXCLUDE_PATTERNS = [
    r"__pycache__",
    r"\.pyc$",
    r"migrations/",
    r"\.venv/",
    r"venv/",
    r"node_modules/",
    r"scripts/check_debug_statements\.py$",  # Exclude this script itself
    r"scripts/check_migrations\.py$",  # Exclude check scripts
    r"scripts/check_env_example\.py$",  # Exclude check scripts
    r"scripts/django_checks\.py$",  # Exclude check scripts
    r"scripts/setup_precommit\.py$",  # Exclude setup script
]


def should_exclude(filepath: str) -> bool:
    """Check if file should be excluded from checks."""
    return any(re.search(pattern, filepath) for pattern in EXCLUDE_PATTERNS)


def check_file(filepath: str) -> list[tuple[int, str, str]]:
    """
    Check a single file for debug statements.
    Returns list of (line_number, line_content, issue_description) tuples.
    """
    issues = []

    try:
        with open(filepath, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                for pattern, description in PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append((line_num, line.strip(), description))
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)

    return issues


def main():
    """Main function to check all provided files."""
    if len(sys.argv) < 2:
        print("Usage: check_debug_statements.py <file1> <file2> ...")
        sys.exit(0)

    files_to_check = [f for f in sys.argv[1:] if not should_exclude(f)]

    if not files_to_check:
        sys.exit(0)

    all_issues = {}

    for filepath in files_to_check:
        if not Path(filepath).exists():
            continue

        issues = check_file(filepath)
        if issues:
            all_issues[filepath] = issues

    if all_issues:
        print("\n[ERROR] Debug/Print statements or sensitive logging detected:\n")
        for filepath, issues in all_issues.items():
            print(f"  {filepath}:")
            for line_num, line_content, description in issues:
                print(f"    Line {line_num}: {description}")
                print(f"      -> {line_content}")
            print()

        print("Please remove debug statements before committing.")
        print("If you need to keep them temporarily, use: git commit --no-verify")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
