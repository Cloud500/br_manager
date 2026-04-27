"""Admin configuration for meetings app."""

from django.contrib import admin

from apps.meetings.models import Meeting


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    """Admin interface for Meeting model."""
    
    list_display = [
        'meeting_number',
        'title',
        'committee',
        'date',
        'start_time',
        'meeting_type',
        'status',
        'is_quorate_display',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'meeting_type',
        'committee',
        'date',
        'is_quorate',
        ('sent_at', admin.EmptyFieldListFilter),
    ]
    
    search_fields = [
        'title',
        'meeting_number',
        'committee__name',
        'location_name',
        'location_city',
    ]
    
    fieldsets = (
        (None, {
            'fields': ('committee', 'title', 'meeting_number')
        }),
        ('Zeitplanung', {
            'fields': (
                'date',
                'start_time',
                'end_time',
                'actual_start_time',
                'actual_end_time'
            )
        }),
        ('Sitzungstyp & Ort', {
            'fields': (
                'meeting_type',
                'location_url',
                'location_name',
                'location_street',
                'location_zip',
                'location_city',
                'location_room'
            )
        }),
        ('Verantwortliche', {
            'fields': (
                'chair',
                'clerk'
            )
        }),
        ('Status', {
            'fields': (
                'status',
                'is_quorate',
                'sent_at'
            )
        }),
        ('Meta', {
            'fields': (
                'created_by',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'meeting_number',
        'created_at',
        'updated_at',
        'sent_at',
    ]
    
    autocomplete_fields = [
        'committee',
        'chair',
        'clerk',
        'created_by',
    ]
    
    @admin.display(boolean=True, description='Beschlussfähig')
    def is_quorate_display(self, obj):
        """Display quorum status with boolean icon."""
        if obj.is_quorate is None:
            return None
        return obj.is_quorate
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related(
            'committee',
            'chair',
            'clerk',
            'created_by'
        )
    
    def save_model(self, request, obj, form, change):
        """Set created_by when creating new meeting."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
