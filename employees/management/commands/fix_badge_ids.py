from django.core.management.base import BaseCommand
from django.db.models import Value
from django.db.models.functions import Replace

from employees.models import Employee


class Command(BaseCommand):
    help = "Removes hyphens from all existing employee badge IDs"

    def handle(self, *args, **options):
        self.stdout.write("Starting cleanup of badge IDs...")

        # Method 1: Bulk update
        try:
            updated_count = Employee.objects.filter(badge_id__contains="-").update(
                badge_id=Replace("badge_id", Value("-"), Value(""))
            )
            self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated_count} employee IDs using bulk mode."))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Bulk update failed: {e}. Falling back to safe mode..."))

            # Method 2: Safe line-by-line fallback
            updated = 0
            conflicts = 0
            for employee in Employee.objects.filter(badge_id__contains="-"):
                old_id = employee.badge_id
                new_id = old_id.replace("-", "")

                # Check for uniqueness conflicts before saving
                if not Employee.objects.filter(badge_id=new_id).exclude(id=employee.id).exists():
                    employee.badge_id = new_id
                    employee.save(update_fields=["badge_id"])
                    updated += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(f"Conflict: Cannot update {old_id} to {new_id} (already exists)")
                    )
                    conflicts += 1

            self.stdout.write(
                self.style.SUCCESS(f"Finished safe mode cleanup: {updated} updated, {conflicts} conflicts.")
            )
