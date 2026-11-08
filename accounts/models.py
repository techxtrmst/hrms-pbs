from django.contrib.auth.models import AbstractUser
from django.db import models

from companies.models import Company


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPERADMIN = "SUPERADMIN", "Super Admin"
        COMPANY_ADMIN = "COMPANY_ADMIN", "Company Admin"
        EMPLOYEE_MANAGER = "EMPLOYEE_MANAGER", "HR"
        MANAGER = "MANAGER", "Manager"
        EMPLOYEE = "EMPLOYEE", "Employee"
        TECH_SUPPORT = "TECH_SUPPORT", "Tech Support"

    email = models.EmailField(unique=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="users", null=True, blank=True)
    role = models.CharField(max_length=50, choices=Role.choices, default=Role.EMPLOYEE)
    must_change_password = models.BooleanField(default=True)
    is_finance_manager = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    def __str__(self):
        return self.email


class LinkedAccount(models.Model):
    """
    Stores permanent links between user accounts across companies/roles for 1-click switching.
    """

    primary_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="linked_accounts")
    linked_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="linked_to_accounts")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("primary_user", "linked_user")
        verbose_name = "Linked Account"
        verbose_name_plural = "Linked Accounts"

    def __str__(self):
        return f"{self.primary_user.email} -> {self.linked_user.email}"
