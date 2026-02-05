from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from accounts.models import User
from employees.models import Employee, LeaveRequest, RegularizationRequest

from .models import Notification


@receiver(post_save, sender=LeaveRequest)
def create_leave_request_notification(sender, instance, created, **kwargs):
    """
    Create notification when a new leave request is submitted
    """
    if created and instance.status == "PENDING":
        recipients = []
        # Add manager if exists
        if instance.employee.manager:
            recipients.append(instance.employee.manager)

        # Add all company admins
        company_admins = User.objects.filter(
            company=instance.employee.company, role=User.Role.COMPANY_ADMIN, is_active=True
        )
        recipients.extend(list(company_admins))

        # Add HR department users (some might be employees but handle HR tasks)
        hr_users = User.objects.filter(
            company=instance.employee.company,
            employee_profile__department__iexact="HR",
            is_active=True,
        )
        recipients.extend(list(hr_users))

        # Remove duplicates
        recipients = list(set(recipients))

        # Create notification for each recipient
        content_type = ContentType.objects.get_for_model(LeaveRequest)

        for recipient in recipients:
            message = f"{instance.employee.user.get_full_name()} has requested {instance.get_leave_type_display()} from {instance.start_date} to {instance.end_date}"

            Notification.objects.create(
                recipient=recipient,
                notification_type="LEAVE_REQUEST",
                message=message,
                content_type=content_type,
                object_id=instance.id,
            )


@receiver(post_save, sender=RegularizationRequest)
def create_regularization_request_notification(sender, instance, created, **kwargs):
    """
    Create notification when a new regularization request is submitted
    """
    if created and instance.status == "PENDING":
        recipients = []
        # Add manager if exists
        if instance.employee.manager:
            recipients.append(instance.employee.manager)

        # Add all company admins
        company_admins = User.objects.filter(
            company=instance.employee.company, role=User.Role.COMPANY_ADMIN, is_active=True
        )
        recipients.extend(list(company_admins))

        # Add HR department users
        hr_users = User.objects.filter(
            company=instance.employee.company,
            employee_profile__department__iexact="HR",
            is_active=True,
        )
        recipients.extend(list(hr_users))

        # Remove duplicates
        recipients = list(set(recipients))

        # Create notification for each recipient
        content_type = ContentType.objects.get_for_model(RegularizationRequest)

        for recipient in recipients:
            message = (
                f"{instance.employee.user.get_full_name()} has requested attendance regularization for {instance.date}"
            )

            Notification.objects.create(
                recipient=recipient,
                notification_type="REGULARIZATION_REQUEST",
                message=message,
                content_type=content_type,
                object_id=instance.id,
            )


@receiver(post_save, sender=RegularizationRequest)
def handle_regularization_approval(sender, instance, created, **kwargs):
    """
    Handle post-approval tasks for regularization requests
    """
    # Only process if this is an update (not creation) and status is APPROVED
    if not created and instance.status == "APPROVED":
        try:
            # Get or create attendance record for the regularized date
            from employees.models import Attendance

            attendance, _ = Attendance.objects.get_or_create(employee=instance.employee, date=instance.date)

            # Recalculate working hours to ensure they're up to date
            attendance.calculate_total_working_hours()
            attendance.save(update_fields=["total_working_hours"])

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error handling regularization approval for {instance.id}: {str(e)}")


@receiver(pre_save, sender=Employee)
def track_shift_changes(sender, instance, **kwargs):
    """
    Track shift changes before saving to detect modifications
    """
    if instance.pk:  # Only for existing employees
        try:
            old_employee = Employee.objects.get(pk=instance.pk)
            # Store old shift info for comparison in post_save
            instance._old_shift = old_employee.assigned_shift
        except Employee.DoesNotExist:
            instance._old_shift = None
    else:
        instance._old_shift = None


@receiver(post_save, sender=Employee)
def notify_shift_change(sender, instance, created, **kwargs):
    """
    Send email notification and create system notification when employee shift is changed
    """
    if not created and hasattr(instance, "_old_shift"):
        old_shift = instance._old_shift
        new_shift = instance.assigned_shift

        # Check if shift actually changed
        if old_shift != new_shift:
            from .email_utils import send_shift_change_notification

            # Send email notification to employee
            try:
                send_shift_change_notification(instance, old_shift, new_shift)
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(
                    f"Failed to send shift change notification email for {instance.user.get_full_name()}: {str(e)}"
                )

            # Create system notification for HR and managers
            try:
                from django.contrib.contenttypes.models import ContentType

                recipients = []

                # Add manager if exists
                if instance.manager:
                    recipients.append(instance.manager)

                # Add all company admins
                company_admins = User.objects.filter(
                    company=instance.company, role=User.Role.COMPANY_ADMIN, is_active=True
                )
                recipients.extend(list(company_admins))

                # Add HR department users
                hr_users = User.objects.filter(
                    company=instance.company,
                    employee_profile__department__iexact="HR",
                    is_active=True,
                )
                recipients.extend(list(hr_users))

                # Remove duplicates
                recipients = list(set(recipients))

                # Create notification for each recipient
                content_type = ContentType.objects.get_for_model(Employee)

                old_shift_name = old_shift.name if old_shift else "No Shift"
                new_shift_name = new_shift.name if new_shift else "No Shift"

                for recipient in recipients:
                    message = f"Shift assignment changed for {instance.user.get_full_name()} from '{old_shift_name}' to '{new_shift_name}'"

                    Notification.objects.create(
                        recipient=recipient,
                        notification_type="SHIFT_CHANGE",
                        message=message,
                        content_type=content_type,
                        object_id=instance.id,
                    )

            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(
                    f"Failed to create shift change system notification for {instance.user.get_full_name()}: {str(e)}"
                )

        # Clean up the temporary attribute
        if hasattr(instance, "_old_shift"):
            delattr(instance, "_old_shift")
