from django.core.management.base import BaseCommand
from django.utils import timezone
from companies.models import Company, Location, Holiday
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Setup sample holidays for companies and locations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            help='Setup holidays for specific company ID'
        )
        parser.add_argument(
            '--year',
            type=int,
            default=date.today().year,
            help='Year to setup holidays for (default: current year)'
        )

    def handle(self, *args, **options):
        company_id = options.get('company_id')
        year = options['year']
        
        # Get companies
        if company_id:
            companies = Company.objects.filter(id=company_id)
        else:
            companies = Company.objects.all()
        
        if not companies.exists():
            self.stdout.write(self.style.WARNING('No companies found'))
            return
        
        # Sample holidays for India
        india_holidays = [
            {'name': 'Republic Day', 'date': date(year, 1, 26), 'type': 'MANDATORY'},
            {'name': 'Holi', 'date': date(year, 3, 14), 'type': 'MANDATORY'},
            {'name': 'Good Friday', 'date': date(year, 3, 29), 'type': 'OPTIONAL'},
            {'name': 'Independence Day', 'date': date(year, 8, 15), 'type': 'MANDATORY'},
            {'name': 'Gandhi Jayanti', 'date': date(year, 10, 2), 'type': 'MANDATORY'},
            {'name': 'Diwali', 'date': date(year, 10, 31), 'type': 'MANDATORY'},
            {'name': 'Christmas', 'date': date(year, 12, 25), 'type': 'MANDATORY'},
        ]
        
        # Sample holidays for USA
        usa_holidays = [
            {'name': 'New Year Day', 'date': date(year, 1, 1), 'type': 'MANDATORY'},
            {'name': 'Martin Luther King Jr. Day', 'date': date(year, 1, 20), 'type': 'MANDATORY'},
            {'name': 'Presidents Day', 'date': date(year, 2, 17), 'type': 'MANDATORY'},
            {'name': 'Memorial Day', 'date': date(year, 5, 26), 'type': 'MANDATORY'},
            {'name': 'Independence Day', 'date': date(year, 7, 4), 'type': 'MANDATORY'},
            {'name': 'Labor Day', 'date': date(year, 9, 1), 'type': 'MANDATORY'},
            {'name': 'Thanksgiving', 'date': date(year, 11, 27), 'type': 'MANDATORY'},
            {'name': 'Christmas', 'date': date(year, 12, 25), 'type': 'MANDATORY'},
        ]
        
        # Sample holidays for Bangladesh
        bangladesh_holidays = [
            {'name': 'International Mother Language Day', 'date': date(year, 2, 21), 'type': 'MANDATORY'},
            {'name': 'Independence Day', 'date': date(year, 3, 26), 'type': 'MANDATORY'},
            {'name': 'Bengali New Year', 'date': date(year, 4, 14), 'type': 'MANDATORY'},
            {'name': 'Victory Day', 'date': date(year, 12, 16), 'type': 'MANDATORY'},
        ]
        
        total_created = 0
        
        for company in companies:
            self.stdout.write(f'\nSetting up holidays for: {company.name}')
            
            # Get locations for this company
            locations = Location.objects.filter(company=company, is_active=True)
            
            for location in locations:
                location_name = location.name.lower()
                
                # Determine which holiday set to use
                if 'india' in location_name:
                    holiday_set = india_holidays
                elif 'usa' in location_name or 'america' in location_name:
                    holiday_set = usa_holidays
                elif 'bangladesh' in location_name:
                    holiday_set = bangladesh_holidays
                else:
                    # Default to India holidays
                    holiday_set = india_holidays
                
                location_created = 0
                
                for holiday_data in holiday_set:
                    # Check if holiday already exists
                    existing = Holiday.objects.filter(
                        company=company,
                        location=location,
                        name=holiday_data['name'],
                        date=holiday_data['date']
                    ).exists()
                    
                    if not existing:
                        Holiday.objects.create(
                            company=company,
                            location=location,
                            name=holiday_data['name'],
                            date=holiday_data['date'],
                            holiday_type=holiday_data['type'],
                            year=holiday_data['date'].year,
                            description=f"{holiday_data['name']} - {holiday_data['type']} holiday",
                            is_active=True,
                            created_by=f"System Setup - {self.__class__.__name__}"
                        )
                        location_created += 1
                        total_created += 1
                
                if location_created > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  Created {location_created} holidays for {location.name}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  No new holidays created for {location.name} (may already exist)'
                        )
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Total holidays created: {total_created} for year {year}'
            )
        )
        
        # Show next steps
        self.stdout.write(
            self.style.SUCCESS(
                f'\n📋 Next Steps:'
                f'\n1. Run: python manage.py mark_holidays --days 365'
                f'\n2. Run: python manage.py mark_week_offs --days 365'
                f'\n3. Check attendance report to see holidays marked as "H"'
            )
        )