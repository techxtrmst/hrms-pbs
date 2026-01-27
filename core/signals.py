from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import User
from employees.models import LeaveRequest, RegularizationRequest

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
