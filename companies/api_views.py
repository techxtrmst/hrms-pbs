"""API views for company-related data"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import Company, Location


@require_http_methods(["GET"])
def get_company_locations(request, company_id):
    """Get all active locations for a company"""
    try:
        company = Company.objects.get(id=company_id)
        locations = Location.objects.filter(company=company, is_active=True).values(
            "id", "name", "city", "state", "country_code"
        )

        return JsonResponse({"status": "success", "locations": list(locations)})
    except Company.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Company not found"}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@require_http_methods(["GET"])
def get_company_policies(request, company_id):
    """Get applicable policies for a company and location"""
    try:
        company = Company.objects.get(id=company_id)
        location_id = request.GET.get("location_id")

        policies = []

        # Get company-specific policies
        company_name = company.name.lower()

        # Leave policies
        if "bluebix" in company_name or "softstandard" in company_name:
            policies.append("Combined Sick/Casual Leave: 12 days per year")
            policies.append("Sick Leave can only be taken as Half Day (0.5 days)")
        else:
            policies.append("Casual Leave: 12 days per year")
            policies.append("Sick Leave: 6 days per year")

        # Location-specific policies
        if location_id:
            try:
                location = Location.objects.get(id=location_id, company=company)

                # Add location-specific info
                if location.country_code == "US":
                    policies.append("US Labor Laws Apply")
                    policies.append("Social Security/FICA contributions enabled")
                elif location.country_code == "BD":
                    policies.append("Bangladesh Labor Laws Apply")
                    policies.append("TIN required for tax purposes")
                else:
                    policies.append("PF/ESI contributions as per Indian laws")

                # Week-off configuration
                from .models import LocationWeekOff

                week_offs = LocationWeekOff.objects.filter(location=location)
                if week_offs.exists():
                    days = ", ".join([wo.get_day_display() for wo in week_offs])
                    policies.append(f"Week Off: {days}")
                else:
                    policies.append("Week Off: Saturday, Sunday (Default)")

            except Location.DoesNotExist:
                pass

        # Shift policies
        from .models import ShiftSchedule

        shifts = ShiftSchedule.objects.filter(company=company, is_active=True)
        if shifts.exists():
            policies.append(f"Available Shifts: {shifts.count()} shift schedule(s)")

        return JsonResponse({"status": "success", "policies": policies})
    except Company.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Company not found"}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@require_http_methods(["GET"])
def get_employee_id_format(request, company_id):
    """Get employee ID format for a company and location"""
    try:
        company = Company.objects.get(id=company_id)
        location_id = request.GET.get("location_id")

        # Determine company prefix
        company_name = company.name.lower()
        if "petabytz" in company_name or "petabytes" in company_name:
            company_prefix = "PBT"
        elif "softstandard" in company_name:
            company_prefix = "SSS"
        elif "bluebix" in company_name:
            company_prefix = "BBS"
        else:
            company_prefix = company.name[:3].upper()

        # Determine location code
        location_code = "XXX"
        if location_id:
            try:
                location = Location.objects.get(id=location_id, company=company)
                # Special handling for India location - use HYD
                if location.name and "india" in location.name.lower():
                    location_code = "HYD"
                # Special handling for Dhaka location - use DHAKA
                elif location.name and ("dhaka" in location.name.lower() or "bangladesh" in location.name.lower()):
                    location_code = "DHAKA"
                elif location.city:
                    location_code = location.city[:3].upper()
                else:
                    location_code = location.name[:3].upper() if location.name else "LOC"
            except Location.DoesNotExist:
                pass

        # Calculate next sequence number
        import re

        from employees.models import Employee

        existing_ids = Employee.objects.filter(company=company).values_list("badge_id", flat=True)
        max_number = 0

        for bid in existing_ids:
            if bid:
                numbers = re.findall(r"\d+", bid)
                if numbers:
                    try:
                        num = int(numbers[-1])
                        if num > max_number:
                            max_number = num
                    except ValueError:
                        continue

        next_sequence = f"{max_number + 1:03d}"

        # Format: COMPANY-LOCATION-SEQUENCE
        format_example = f"{company_prefix}-{location_code}-{next_sequence}"
        explanation = (
            f"Format: {company_prefix} (Company) - {location_code} (Location) - {next_sequence} (Next Available)"
        )

        return JsonResponse(
            {
                "status": "success",
                "format": format_example,
                "explanation": explanation,
                "company_prefix": company_prefix,
                "location_code": location_code,
                "next_sequence": next_sequence,
            }
        )
    except Company.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Company not found"}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
