"""
Migration Zero Management Command

This command implements the "migration zero" pattern to clean up migration files.
It deletes all existing migrations (except __init__.py) and recreates fresh initial migrations.

WARNING: This should only be run when:
1. All migrations have been applied to ALL environments (staging, production, etc.)
2. You have a backup of your database
3. You understand the implications

Usage:
    python manage.py migration_zero --dry-run  # Preview what will be deleted
    python manage.py migration_zero            # Actually perform the reset
    python manage.py migration_zero --apps accounts employees  # Only specific apps
"""

from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Reset all migrations to a single initial migration per app (migration zero pattern)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--apps",
            nargs="+",
            type=str,
            help="Only reset migrations for specific apps (space-separated)",
        )
        parser.add_argument(
            "--exclude-apps",
            nargs="+",
            type=str,
            default=[],
            help="Exclude specific apps from migration reset",
        )
        parser.add_argument(
            "--no-input",
            action="store_true",
            help="Skip confirmation prompts",
        )
        parser.add_argument(
            "--skip-check",
            action="store_true",
            help="Skip the check for unapplied migrations",
        )

    def get_local_apps(self):
        """Get list of local (project) apps, excluding third-party packages."""
        base_dir = Path(settings.BASE_DIR)
        local_apps = []

        for app_config in apps.get_app_configs():
            app_path = Path(app_config.path)
            # Check if app is within the project directory
            try:
                app_path.relative_to(base_dir)
                local_apps.append(app_config.label)
            except ValueError:
                # App is outside project directory (third-party)
                continue

        return local_apps

    def get_migration_files(self, app_label):
        """Get all migration files for an app, excluding __init__.py."""
        try:
            app_config = apps.get_app_config(app_label)
        except LookupError:
            return []

        migrations_dir = Path(app_config.path) / "migrations"
        if not migrations_dir.exists():
            return []

        migration_files = []
        for f in migrations_dir.glob("*.py"):
            if f.name != "__init__.py":
                migration_files.append(f)

        # Also get .pyc files
        pycache_dir = migrations_dir / "__pycache__"
        if pycache_dir.exists():
            for f in pycache_dir.glob("*.pyc"):
                if "__init__" not in f.name:
                    migration_files.append(f)

        return sorted(migration_files)

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        no_input = options["no_input"]
        skip_check = options["skip_check"]
        specified_apps = options.get("apps")
        exclude_apps = options.get("exclude_apps") or []

        # Determine which apps to process
        app_labels = specified_apps or self.get_local_apps()

        # Apply exclusions
        app_labels = [a for a in app_labels if a not in exclude_apps]

        if not app_labels:
            self.stdout.write(self.style.WARNING("No apps found to process."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Migration Zero Pattern ===\n"))

        # Check for unapplied migrations first
        if not skip_check:
            self.stdout.write("Checking for unapplied migrations...")
            try:
                from django.db import connection
                from django.db.migrations.executor import MigrationExecutor

                executor = MigrationExecutor(connection)
                plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

                if plan:
                    self.stdout.write(
                        self.style.ERROR("\n❌ There are unapplied migrations! Please run 'migrate' first.\n")
                    )
                    for migration, _ in plan:
                        self.stdout.write(f"  - {migration.app_label}.{migration.name}")
                    raise CommandError("Cannot reset migrations with unapplied migrations.")
                else:
                    self.stdout.write(self.style.SUCCESS("✅ All migrations are applied.\n"))
            except Exception as e:
                if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                    self.stdout.write(
                        self.style.WARNING(
                            "⚠️  Cannot check migration status (database not configured). Proceeding anyway...\n"
                        )
                    )
                else:
                    raise

        # Collect all migration files to delete
        files_to_delete = {}
        total_files = 0

        for app_label in app_labels:
            files = self.get_migration_files(app_label)
            if files:
                files_to_delete[app_label] = files
                total_files += len(files)

        if not files_to_delete:
            self.stdout.write(self.style.WARNING("No migration files found to delete."))
            return

        # Display what will be deleted
        self.stdout.write(f"\nApps to process: {', '.join(app_labels)}")
        self.stdout.write(f"Total migration files to delete: {total_files}\n")

        for app_label, files in files_to_delete.items():
            self.stdout.write(f"\n{self.style.MIGRATE_LABEL(app_label)}:")
            for f in files:
                self.stdout.write(f"  - {f.name}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("\n[DRY RUN] No files were deleted. Remove --dry-run to perform actual deletion.\n")
            )
            return

        # Confirm with user
        if not no_input:
            self.stdout.write("")
            confirm = input(
                self.style.WARNING(
                    "⚠️  This will DELETE all migration files listed above.\nAre you sure you want to continue? [y/N]: "
                )
            )
            if confirm.lower() not in ("y", "yes"):
                self.stdout.write(self.style.ERROR("Aborted."))
                return

        # Delete migration files
        self.stdout.write("\n🗑️  Deleting migration files...")

        deleted_count = 0
        for _app_label, files in files_to_delete.items():
            for f in files:
                try:
                    f.unlink()
                    deleted_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Failed to delete {f}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"✅ Deleted {deleted_count} files.\n"))

        # Recreate migrations
        self.stdout.write("🔄 Recreating initial migrations...")

        try:
            call_command("makemigrations", *app_labels, verbosity=1)
            self.stdout.write(self.style.SUCCESS("\n✅ Initial migrations created successfully!\n"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Failed to create migrations: {e}"))
            raise CommandError("Migration creation failed. Your migrations are in an inconsistent state!")

        # Final instructions
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Next Steps ===\n"))
        self.stdout.write(
            "1. Review the newly created migration files\n"
            "2. Commit the changes to your branch\n"
            "3. Before deploying, update the django_migrations table in your database:\n"
            "   - DELETE FROM django_migrations WHERE app IN (...);\n"
            "   - Then run 'python manage.py migrate --fake-initial'\n"
            "\n"
            "Or use the 'migration_zero_apply' command on your server to handle this.\n"
        )
