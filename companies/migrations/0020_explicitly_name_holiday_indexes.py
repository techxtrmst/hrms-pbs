# Generated manually to handle index naming inconsistencies between environments

from django.db import migrations


def ensure_holiday_indexes_exist(apps, schema_editor):
    """
    Ensure Holiday indexes exist with the correct names.
    This handles different possible source index names across environments.
    """
    if schema_editor.connection.vendor != "postgresql":
        return  # Only PostgreSQL needs this handling

    # Map of new index name -> list of possible old names to rename from
    index_renames = {
        "holiday_company_year_idx": [
            "companies_h_company_5715bf_idx",
            "companies_h_company_a18c66_idx",
            "companies_holiday_company_year_idx",
        ],
        "holiday_company_loc_idx": [
            "companies_h_company_f6931c_idx",
            "companies_h_company_location_idx",
            "companies_holiday_company_loc_idx",
        ],
        "holiday_date_idx": [
            "companies_h_date_caf000_idx",
            "companies_h_date_idx",
            "companies_holiday_date_idx",
        ],
    }

    with schema_editor.connection.cursor() as cursor:
        for new_name, old_names in index_renames.items():
            # Check if new index already exists
            cursor.execute(
                "SELECT indexname FROM pg_indexes WHERE indexname = %s",
                [new_name],
            )
            if cursor.fetchone():
                continue  # New index already exists, skip

            # Try to find and rename from any of the old names
            renamed = False
            for old_name in old_names:
                cursor.execute(
                    "SELECT indexname FROM pg_indexes WHERE indexname = %s",
                    [old_name],
                )
                if cursor.fetchone():
                    cursor.execute(f'ALTER INDEX "{old_name}" RENAME TO "{new_name}"')
                    renamed = True
                    break

            # If no old index was found to rename, create the index
            if not renamed:
                # Create the index if it doesn't exist at all
                table_name = "companies_holiday"
                if new_name == "holiday_company_year_idx":
                    cursor.execute(
                        f"""
                        CREATE INDEX IF NOT EXISTS "{new_name}"
                        ON "{table_name}" (company_id, year)
                        """
                    )
                elif new_name == "holiday_company_loc_idx":
                    cursor.execute(
                        f"""
                        CREATE INDEX IF NOT EXISTS "{new_name}"
                        ON "{table_name}" (company_id, location_id)
                        """
                    )
                elif new_name == "holiday_date_idx":
                    cursor.execute(
                        f"""
                        CREATE INDEX IF NOT EXISTS "{new_name}"
                        ON "{table_name}" (date)
                        """
                    )


def noop(apps, schema_editor):
    """No-op for reverse migration."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0019_auto_20260128_1715"),
    ]

    operations = [
        # First, safely rename indexes using raw SQL
        migrations.RunPython(ensure_holiday_indexes_exist, noop),
        # Then, tell Django's migration state tracker about the new names
        # These are SeparateDatabaseAndState operations that only update state
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameIndex(
                    model_name="holiday",
                    new_name="holiday_company_year_idx",
                    old_name="companies_h_company_5715bf_idx",
                ),
            ],
            database_operations=[],
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameIndex(
                    model_name="holiday",
                    new_name="holiday_company_loc_idx",
                    old_name="companies_h_company_f6931c_idx",
                ),
            ],
            database_operations=[],
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameIndex(
                    model_name="holiday",
                    new_name="holiday_date_idx",
                    old_name="companies_h_date_caf000_idx",
                ),
            ],
            database_operations=[],
        ),
    ]
