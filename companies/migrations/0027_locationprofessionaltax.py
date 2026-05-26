from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0026_emaildomain'),
    ]

    operations = [
        migrations.CreateModel(
            name='LocationProfessionalTax',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pt_threshold', models.DecimalField(
                    decimal_places=2, default=20000.0, max_digits=12,
                    help_text='Gross salary threshold for PT slab (e.g. 20000)'
                )),
                ('pt_amount_below', models.DecimalField(
                    decimal_places=2, default=0.0, max_digits=10,
                    help_text='PT amount when gross < threshold'
                )),
                ('pt_amount_above', models.DecimalField(
                    decimal_places=2, default=0.0, max_digits=10,
                    help_text='PT amount when gross >= threshold'
                )),
                ('is_active', models.BooleanField(
                    default=True,
                    help_text='Uncheck to disable PT for this location'
                )),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('location', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='professional_tax_config',
                    to='companies.location',
                )),
            ],
            options={
                'verbose_name': 'Location Professional Tax',
                'verbose_name_plural': 'Location Professional Taxes',
            },
        ),
    ]
