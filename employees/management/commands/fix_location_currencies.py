"""
Django management command to fix location currencies
Usage: python manage.py fix_location_currencies
"""

from django.core.management.base import BaseCommand
from companies.models import Location


class Command(BaseCommand):
    help = 'Fix location currencies based on country codes'

    def handle(self, *args, **options):
        # Currency mapping based on country codes
        currency_map = {
            'BD': 'BDT',  # Bangladesh
            'US': 'USD',  # United States
            'IN': 'INR',  # India
        }
        
        updated_count = 0
        
        for location in Location.objects.all():
            country_code = location.country_code.upper()
            correct_currency = currency_map.get(country_code, 'INR')  # Default to INR
            
            if location.currency != correct_currency:
                old_currency = location.currency
                location.currency = correct_currency
                location.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Updated {location.name} ({location.company.name}): {old_currency} → {correct_currency}'
                    )
                )
                updated_count += 1
            else:
                self.stdout.write(
                    f'✓ {location.name} ({location.company.name}): {location.currency} (already correct)'
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 Updated {updated_count} locations with correct currencies')
        )