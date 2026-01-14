from django.contrib import admin
from .models import HandbookSection, Handbook, HandbookAcknowledgment, HandbookAttachment


class HandbookAttachmentInline(admin.TabularInline):
    model = HandbookAttachment
    extra = 1
    fields = ['title', 'file', 'file_type', 'file_size']
    readonly_fields = ['file_type', 'file_size']


@admin.register(HandbookSection)
class HandbookSectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'icon', 'order', 'is_active', 'updated_at']
    list_filter = ['company', 'is_active']
    search_fields = ['title']
    ordering = ['company', 'order', 'title']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If user is company admin, show only their company's sections
        if request.user.role == 'COMPANY_ADMIN' and request.user.company:
            return qs.filter(company=request.user.company)
        return qs


@admin.register(Handbook)
class HandbookAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'location',
        'section',
        'version',
        'is_published',
        'effective_date',
        'created_by',
        'updated_at'
    ]
    list_filter = ['company', 'location', 'section', 'is_published', 'effective_date']
    search_fields = ['title', 'subtitle', 'content']
    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']
    inlines = [HandbookAttachmentInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'location', 'section', 'title', 'subtitle')
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('wide',)
        }),
        ('Publishing', {
            'fields': ('version', 'is_published', 'effective_date', 'requires_acknowledgment')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If user is company admin, show only their company's handbooks
        if request.user.role == 'COMPANY_ADMIN' and request.user.company:
            # Further filter by location if admin has a specific location
            if hasattr(request.user, 'employee_profile') and request.user.employee_profile.location:
                return qs.filter(
                    company=request.user.company,
                    location=request.user.employee_profile.location
                )
            return qs.filter(company=request.user.company)
        return qs

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new handbook
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(HandbookAcknowledgment)
class HandbookAcknowledgmentAdmin(admin.ModelAdmin):
    list_display = [
        'employee',
        'handbook',
        'acknowledged',
        'acknowledged_at',
        'ip_address'
    ]
    list_filter = ['acknowledged', 'acknowledged_at', 'handbook__location']
    search_fields = [
        'employee__user__first_name',
        'employee__user__last_name',
        'employee__user__email',
        'handbook__title'
    ]
    readonly_fields = ['acknowledged_at', 'ip_address', 'user_agent']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Company admins see only their company's acknowledgments
        if request.user.role == 'COMPANY_ADMIN' and request.user.company:
            if hasattr(request.user, 'employee_profile') and request.user.employee_profile.location:
                return qs.filter(
                    handbook__company=request.user.company,
                    handbook__location=request.user.employee_profile.location
                )
            return qs.filter(handbook__company=request.user.company)
        return qs


@admin.register(HandbookAttachment)
class HandbookAttachmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'handbook', 'file_type', 'file_size', 'uploaded_by', 'uploaded_at']
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['title', 'handbook__title']
    readonly_fields = ['file_type', 'file_size', 'uploaded_by', 'uploaded_at']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Company admins see only their company's attachments
        if request.user.role == 'COMPANY_ADMIN' and request.user.company:
            if hasattr(request.user, 'employee_profile') and request.user.employee_profile.location:
                return qs.filter(
                    handbook__company=request.user.company,
                    handbook__location=request.user.employee_profile.location
                )
            return qs.filter(handbook__company=request.user.company)
        return qs

    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
