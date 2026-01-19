"""
Migration Zero Apply Management Command

This command updates the django_migrations table after a migration zero reset.
It removes old migration records and fakes the new initial migrations.

This should be run on the server BEFORE regular migrations when deploying
a migration zero reset.

Usage:
    python manage.py migration_zero_apply --dry-run  # Preview changes
    python manage.py migration_zero_apply            # Apply changes
"""

import os
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = (
        "Apply migration zero changes to the database (update django_migrations table)"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without actually doing it",
        )
        parser.add_argument(
            "--apps",
            nargs="+",
            type=str,
            help="Only apply for specific apps (space-separated)",
        )
        parser.add_argument(
            "--no-input",
            action="store_true",
            help="Skip confirmation prompts",
        )

    def get_local_apps(self):
        """Get list of local (project) apps."""
        base_dir = Path(settings.BASE_DIR)
        local_apps = []

        for app_config in apps.get_app_configs():
            app_path = Path(app_config.path)
            try:
                app_path.relative_to(base_dir)
                local_apps.append(app_config.label)
            except ValueError:
                continue

        return local_apps

    def get_current_migrations(self, app_label):
        """Get current migration files for an app."""
        try:
            app_config = apps.get_app_config(app_label)
        except LookupError:
            return []

        migrations_dir = Path(app_config.path) / "migrations"
        if not migrations_dir.exists():
            return []

        migrations = []
        for f in migrations_dir.glob("*.py"):
            if f.name != "__init__.py":
                migrations.append(f.stem)

        return sorted(migrations)

    def get_applied_migrations(self, app_label):
        """Get list of migrations recorded in django_migrations table."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT name FROM django_migrations WHERE app = %s ORDER BY name",
                [app_label],
            )
            return [row[0] for row in cursor.fetchall()]

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        no_input = options["no_input"]
        specified_apps = options.get("apps")

        # Determine which apps to process
        if specified_apps:
            app_labels = specified_apps
        else:
            app_labels = self.get_local_apps()

        if not app_labels:
            self.stdout.write(self.style.WARNING("No apps found to process."))
            return

        self.stdout.write(
            self.style.MIGRATE_HEADING("\n=== Migration Zero Apply ===\n")
        )

        changes_needed = {}

        for app_label in app_labels:
            current_migrations = self.get_current_migrations(app_label)
            applied_migrations = self.get_applied_migrations(app_label)

            if not current_migrations:
                continue

            # Check if this looks like a migration zero reset
            # (typically just one 0001_initial migration)
            is_reset = (
                len(current_migrations) == 1
                and current_migrations[0].startswith("0001")
                and len(applied_migrations) > 1
            )

            if is_reset or set(current_migrations) != set(applied_migrations):
                changes_needed[app_label] = {
                    "current": current_migrations,
                    "applied": applied_migrations,
                    "to_remove": [
                        m for m in applied_migrations if m not in current_migrations
                    ],
                    "to_add": [
                        m for m in current_migrations if m not in applied_migrations
                    ],
                }

        if not changes_needed:
            self.stdout.write(
                self.style.SUCCESS("✅ All apps are in sync. No changes needed.\n")
            )
            return

        # Display changes
        self.stdout.write("Changes detected:\n")

        for app_label, changes in changes_needed.items():
            self.stdout.write(f"\n{self.style.MIGRATE_LABEL(app_label)}:")

            if changes["to_remove"]:
                self.stdout.write(f"  Records to remove from django_migrations:")
                for m in changes["to_remove"]:
                    self.stdout.write(f"    - {m}")

            if changes["to_add"]:
                self.stdout.write(f"  Records to add to django_migrations:")
                for m in changes["to_add"]:
                    self.stdout.write(f"    + {m}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\n[DRY RUN] No changes were made. Remove --dry-run to apply changes.\n"
                )
            )
            return

        # Confirm with user
        if not no_input:
            self.stdout.write("")
            confirm = input(
                self.style.WARNING(
                    "⚠️  This will modify the django_migrations table.\n"
                    "Are you sure you want to continue? [y/N]: "
                )
            )
            if confirm.lower() not in ("y", "yes"):
                self.stdout.write(self.style.ERROR("Aborted."))
                return

        # Apply changes
        self.stdout.write("\n🔄 Applying changes to django_migrations table...")

        with connection.cursor() as cursor:
            for app_label, changes in changes_needed.items():
                # Remove old migration records
                if changes["to_remove"]:
                    placeholders = ", ".join(["%s"] * len(changes["to_remove"]))
                    cursor.execute(
                        f"DELETE FROM django_migrations WHERE app = %s AND name IN ({placeholders})",
                        [app_label] + changes["to_remove"],
                    )
                    self.stdout.write(
                        f"  Removed {len(changes['to_remove'])} records from {app_label}"
                    )

                # Add new migration records (fake them)
                for migration_name in changes["to_add"]:
                    cursor.execute(
                        "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())",
                        [app_label, migration_name],
                    )

                if changes["to_add"]:
                    self.stdout.write(
                        f"  Added {len(changes['to_add'])} records to {app_label}"
                    )

        self.stdout.write(
            self.style.SUCCESS("\n✅ Migration history updated successfully!\n")
        )
        self.stdout.write(
            "You can now run 'python manage.py migrate' to apply any remaining migrations.\n"
        )
