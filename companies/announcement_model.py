from django.db import models


class Announcement(models.Model):
    """
    Model for company announcements with optional location targeting.
    """

    company = models.ForeignKey(
        "companies.Company", on_delete=models.CASCADE, related_name="announcements"
    )
    location = models.ForeignKey(
        "companies.Location",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="announcements",
        help_text="Specific location for this announcement. Leave empty for all locations.",
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
