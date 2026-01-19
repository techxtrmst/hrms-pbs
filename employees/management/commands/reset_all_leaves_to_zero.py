from django.core.management.base import BaseCommand
from employees.models import Employee, LeaveBalance


class Command(BaseCommand):
    help = 'Reset all employees leave allocations and used leaves to 0'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making actual changes',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to reset ALL employee leaves to 0',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        confirm = options['confirm']
        
        if not confirm and not dry_run:
            self.stdout.write(
                self.style.ERROR(
                    'This command will reset ALL employee leaves to 0. '
                    'Use --confirm to proceed or --dry-run to see what would be changed.'
                )
            )
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get all employees
        employees = Employee.objects.all()
        
        if not employees.exists():
            self.stdout.write(self.style.ERROR('No employees found'))
            return
            
        self.stdout.write(f'Processing {employees.count()} employees...\n')
        
        updated_count = 0
        
        for employee in employees:
            # Get or create leave balance
            leave_balance, created = LeaveBalance.objects.get_or_create(
                employee=employee,
                defaults={
                    'casual_leave_allocated': 0.0,
                    'sick_leave_allocated': 0.0,
                    'casual_leave_used': 0.0,
                    'sick_leave_used': 0.0,
                    'unpaid_leave': 0.0,
                }
            )
            
            # Check if any changes are needed
            needs_update = (
                leave_balance.casual_leave_allocated != 0.0 or
                leave_balance.sick_leave_allocated != 0.0 or
                leave_balance.casual_leave_used != 0.0 or
                leave_balance.sick_leave_used != 0.0 or
                leave_balance.unpaid_leave != 0.0
            )
            
            if needs_update or created:
                self.stdout.write(
                    f'{employee.user.get_full_name()} ({employee.badge_id or f"EMP-{employee.id}"}): '
                    f'CL: {leave_balance.casual_leave_allocated}/{leave_balance.casual_leave_used} → 0/0, '
                    f'SL: {leave_balance.sick_leave_allocated}/{leave_balance.sick_leave_used} → 0/0, '
                    f'UL: {leave_balance.unpaid_leave} → 0'
                )
                
                if not dry_run:
                    # Reset all leave values to 0
                    leave_balance.casual_leave_allocated = 0.0
                    leave_balance.sick_leave_allocated = 0.0
                    leave_balance.casual_leave_used = 0.0
                    leave_balance.sick_leave_used = 0.0
                    leave_balance.unpaid_leave = 0.0
                    leave_balance.carry_forward_leave = 0.0
                    leave_balance.lapsed_leave = 0.0
                    leave_balance.save()
                    
                    self.stdout.write(self.style.SUCCESS('  ✓ Reset to 0'))
                else:
                    self.stdout.write(self.style.WARNING('  (would be reset to 0)'))
                
                updated_count += 1
        
        if updated_count == 0:
            self.stdout.write(self.style.SUCCESS('\nAll employees already have 0 leaves.'))
        else:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'\nFound {updated_count} employees that would be reset to 0 leaves.'
                    )
                )
                self.stdout.write('Run with --confirm to apply changes.')
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\nSuccessfully reset {updated_count} employees to 0 leaves.'
                    )
                )
                self.stdout.write(
                    self.style.WARNING(
                        'Note: You can now manually allocate leaves to employees as needed '
                        'through the admin panel or by running allocation commands.'
                    )
                )