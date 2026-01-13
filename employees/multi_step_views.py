from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from .multi_step_forms import PersonalInfoForm, JobDetailsForm, FinanceDetailsForm
from .models import Employee

User = get_user_model()


@login_required
def add_employee_step1(request):
    """Step 1: Personal Information"""
    if request.method == "POST":
        form = PersonalInfoForm(request.POST, user=request.user)
        if form.is_valid():
            # Collect emergency contacts from POST data
            emergency_contacts = []
            contact_index = 0
            while True:
                name_key = f"emergency_contact_name_{contact_index}"
                phone_key = f"emergency_contact_phone_{contact_index}"
                relationship_key = f"emergency_contact_relationship_{contact_index}"
                primary_key = f"emergency_contact_primary_{contact_index}"

                if name_key not in request.POST:
                    break

                name = request.POST.get(name_key, "").strip()
                phone = request.POST.get(phone_key, "").strip()
                relationship = request.POST.get(relationship_key, "").strip()
                is_primary = primary_key in request.POST

                # Only add if at least name and phone are provided
                if name and phone:
                    emergency_contacts.append(
                        {
                            "name": name,
                            "phone_number": phone,
                            "relationship": relationship,
                            "is_primary": is_primary,
                        }
                    )

                contact_index += 1

            # Save personal info to session
            request.session["employee_personal_data"] = {
                "first_name": form.cleaned_data["first_name"],
                "last_name": form.cleaned_data["last_name"],
                "email": form.cleaned_data["email"],
                "mobile_number": form.cleaned_data.get("mobile_number", ""),
                "gender": form.cleaned_data.get("gender", ""),
                "marital_status": form.cleaned_data.get("marital_status", ""),
                "dob": str(form.cleaned_data.get("dob", ""))
                if form.cleaned_data.get("dob")
                else "",
                "permanent_address": form.cleaned_data.get("permanent_address", ""),
                "emergency_contact": form.cleaned_data.get("emergency_contact", ""),
                "badge_id": form.cleaned_data["badge_id"],
                "role": form.cleaned_data["role"],
                "company_id": form.cleaned_data["company_selection"].id,
                "location_id": form.cleaned_data["location"].id
                if form.cleaned_data.get("location")
                else None,
            }

            # Save emergency contacts to session
            request.session["employee_emergency_contacts"] = emergency_contacts

            messages.success(
                request, "Personal information saved! Now add job details."
            )
            return redirect("add_employee_step2")
    else:
        # Pre-fill from session if available
        initial_data = request.session.get("employee_personal_data", {})
        form = PersonalInfoForm(initial=initial_data, user=request.user)

    # Calculate Company Prefix for ID generation
    company_prefix = "EMP"
    if request.user.company:
        c_name = request.user.company.name.lower()
        if "petabytz" in c_name or "petabytes" in c_name:
            company_prefix = "PBT"
        elif "softstandard" in c_name:
            company_prefix = "SSS"
        else:
            company_prefix = request.user.company.name[:3].upper()

    return render(
        request,
        "employees/add_employee_step1.html",
        {"form": form, "step": 1, "company_prefix": company_prefix},
    )


@login_required
def add_employee_step2(request):
    """Step 2: Job Details"""
    # Check if step 1 is completed
    if "employee_personal_data" not in request.session:
        messages.warning(request, "Please complete personal information first.")
        return redirect("add_employee_step1")

    personal_data = request.session["employee_personal_data"]
    company_id = personal_data.get("company_id")

    if request.method == "POST":
        form = JobDetailsForm(request.POST, user=request.user, company_id=company_id)
        if form.is_valid():
            # Extract objects from form data
            desig_obj = form.cleaned_data["designation"]
            dept_obj = form.cleaned_data["department"]
            shift_obj = form.cleaned_data.get("shift_schedule")

            # Save job details to session
            request.session["employee_job_data"] = {
                "designation_id": desig_obj.id if desig_obj else None,
                "designation": desig_obj.name if desig_obj else "",
                "department_id": dept_obj.id if dept_obj else None,
                "department": dept_obj.name if dept_obj else "",
                "manager_id": form.cleaned_data.get("manager_selection").user.id
                if form.cleaned_data.get("manager_selection")
                else None,
                "work_type": form.cleaned_data.get("work_type", "FT"),
                "shift_schedule": shift_obj.name if shift_obj else "",
                "shift_schedule_id": shift_obj.id if shift_obj else None,
                "date_of_joining": str(form.cleaned_data.get("date_of_joining", ""))
                if form.cleaned_data.get("date_of_joining")
                else "",
            }
            messages.success(
                request, "Job details saved! Now add financial information."
            )
            return redirect("add_employee_step3")
    else:
        # Pre-fill from session if available
        initial_data = request.session.get("employee_job_data", {})
        form = JobDetailsForm(
            initial=initial_data, user=request.user, company_id=company_id
        )

    return render(
        request,
        "employees/add_employee_step2.html",
        {"form": form, "step": 2, "company_id": company_id},
    )


@login_required
def add_employee_step3(request):
    """Step 3: Finance Details & Final Save"""
    # Check if previous steps are completed
    if (
        "employee_personal_data" not in request.session
        or "employee_job_data" not in request.session
    ):
        messages.warning(request, "Please complete all previous steps.")
        return redirect("add_employee_step1")

    if request.method == "POST":
        form = FinanceDetailsForm(request.POST)
        if form.is_valid():
            # Get all data from session
            personal_data = request.session["employee_personal_data"]
            job_data = request.session["employee_job_data"]
            finance_data = form.cleaned_data

            # Create User
            first_name = personal_data["first_name"]
            badge_id = personal_data["badge_id"]

            if not badge_id or len(badge_id) < 3:
                password = f"{first_name}123"
            else:
                password = f"{first_name}{badge_id[-3:]}"

            from companies.models import Company

            company = Company.objects.get(id=personal_data["company_id"])

            # Check if user already exists
            try:
                user = User.objects.get(email=personal_data["email"])
                # Check if this user has an employee profile
                if hasattr(user, "employee_profile"):
                    messages.error(
                        request,
                        f"Employee with email {personal_data['email']} already exists.",
                    )
                    return redirect("add_employee_step1")
                else:
                    # User exists but no employee profile - reuse this user (zombie record case)
                    user.username = personal_data["email"]
                    user.set_password(password)
                    user.first_name = first_name
                    user.last_name = personal_data["last_name"]
                    user.role = personal_data["role"]
                    user.company = company
                    user.save()
            except User.DoesNotExist:
                user = User.objects.create_user(
                    username=personal_data["email"],
                    email=personal_data["email"],
                    password=password,
                    first_name=first_name,
                    last_name=personal_data["last_name"],
                    role=personal_data["role"],
                    company=company,
                )

            # Create Employee
            from datetime import datetime

            employee = Employee.objects.create(
                user=user,
                company=company,
                # Personal
                mobile_number=personal_data.get("mobile_number"),
                gender=personal_data.get("gender"),
                marital_status=personal_data.get("marital_status"),
                dob=datetime.strptime(personal_data["dob"], "%Y-%m-%d").date()
                if personal_data.get("dob")
                else None,
                permanent_address=personal_data.get("permanent_address"),
                emergency_contact=personal_data.get("emergency_contact"),
                badge_id=badge_id,
                location_id=personal_data.get("location_id"),
                # Job
                designation=job_data["designation"],
                department=job_data["department"],
                manager_id=job_data.get("manager_id"),
                work_type=job_data.get("work_type", "FT"),
                shift_schedule=job_data.get("shift_schedule"),
                assigned_shift_id=job_data.get("shift_schedule_id"),
                date_of_joining=datetime.strptime(
                    job_data["date_of_joining"], "%Y-%m-%d"
                ).date()
                if job_data.get("date_of_joining")
                else None,
                # Finance
                bank_name=finance_data.get("bank_name"),
                account_number=finance_data.get("account_number"),
                ifsc_code=finance_data.get("ifsc_code"),
                uan=finance_data.get("uan"),
                pf_enabled=finance_data.get("pf_enabled", False),
            )



            # Create Emergency Contacts
            emergency_contacts = request.session.get("employee_emergency_contacts", [])
            if emergency_contacts:
                from .models import EmergencyContact

                for contact_data in emergency_contacts:
                    EmergencyContact.objects.create(
                        employee=employee,
                        name=contact_data["name"],
                        phone_number=contact_data["phone_number"],
                        relationship=contact_data.get("relationship", ""),
                        is_primary=contact_data.get("is_primary", False),
                    )

            # Send Activation Email
            from .utils import send_activation_email
            import logging

            logger = logging.getLogger(__name__)

            logger.info(
                f"Attempting to send activation email to {employee.user.email} for company {company.name}"
            )
            email_sent = send_activation_email(user, request)

            # Clear session
            del request.session["employee_personal_data"]
            del request.session["employee_job_data"]
            if "employee_emergency_contacts" in request.session:
                del request.session["employee_emergency_contacts"]

            # Prepare success message with email status
            msg = f"✓ Employee {employee.user.get_full_name()} created successfully!"
            if email_sent:
                msg += f" 📧 Activation email sent to {employee.user.email}."
                messages.success(request, msg)
                logger.info(
                    f"Employee created and activation email sent successfully to {employee.user.email}"
                )
            else:
                msg += " ⚠️ However, the activation email could not be sent. Please check email configuration."
                msg += f" Temporary password: {password}"
                messages.warning(request, msg)
                logger.warning(
                    f"Employee created but activation email failed for {employee.user.email}"
                )

            return redirect("employee_list")
    else:
        # Pre-fill from session if available
        initial_data = request.session.get("employee_finance_data", {})
        form = FinanceDetailsForm(initial=initial_data)

    return render(
        request, "employees/add_employee_step3.html", {"form": form, "step": 3}
    )
