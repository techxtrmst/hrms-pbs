# Generated manually

from django.db import migrations

def update_location_currencies(apps, schema_editor):
    Location = apps.get_model('companies', 'Location')
    
    # Update Dhaka locations to BDT
    # We update if name contains Dhaka or country code is BD
    dhaka_updated = Location.objects.filter(name__icontains='Dhaka').update(currency='BDT')
    bd_updated = Location.objects.filter(country_code__iexact='BD').update(currency='BDT')
    
    # Update US locations to USD
    us_updated = Location.objects.filter(name__icontains='United States').update(currency='USD')
    us_code_updated = Location.objects.filter(country_code__iexact='US').update(currency='USD')
    usa_updated = Location.objects.filter(name__icontains='USA').update(currency='USD')

    print(f"Updated currencies for existing locations: Dhaka/BD (to BDT), US/USA (to USD)")

def reverse_func(apps, schema_editor):
    # Cannot safely revert as we don't know original values
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0017_location_address_line1_location_address_line2_and_more'),
    ]

    operations = [
        migrations.RunPython(update_location_currencies, reverse_func),
    ]
