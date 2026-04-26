"""Admin configuration for committees app."""

from django.contrib import admin

from apps.committees.models import Committee, Membership


@admin.register(Committee)
class CommitteeAdmin(admin.ModelAdmin):
    """Admin interface for Committee model."""
    
    list_display = [
        'name',
        'committee_type',
        'parent',
        'total_seats',
        'is_active',
        'created_at',
        'is_deleted_display',
    ]
    
    list_filter = [
        'committee_type',
        'is_active',
        'quorum_type',
        'personnel_enabled',
        'substitute_logic_enabled',
        ('deleted_at', admin.EmptyFieldListFilter),
    ]
    
    search_fields = [
        'name',
        'description',
    ]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'committee_type', 'parent', 'description')
        }),
        ('Konfiguration', {
            'fields': ('total_seats', 'quorum_type', 'personnel_enabled')
        }),
        ('Nachrücklogik', {
            'fields': ('substitute_logic_enabled', 'minority_gender', 'minority_min_count')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at')
        }),
        ('Soft-Delete', {
            'fields': ('deleted_at', 'deleted_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'created_at',
        'deleted_at',
        'deleted_by',
    ]
    
    @admin.display(boolean=True, description='Gelöscht')
    def is_deleted_display(self, obj):
        """Display whether committee is deleted."""
        return obj.deleted_at is not None
    
    def get_queryset(self, request):
        """Return all committees including deleted ones for admin."""
        return Committee.all_objects.all_with_deleted().select_related('parent', 'deleted_by')


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """Admin interface for Membership model."""
    
    list_display = [
        'user',
        'committee',
        'role',
        'member_type',
        'is_active',
        'start_date',
        'end_date',
        'is_deleted_display',
    ]
    
    list_filter = [
        'member_type',
        'is_active',
        'committee__committee_type',
        'start_date',
        ('deleted_at', admin.EmptyFieldListFilter),
    ]
    
    search_fields = [
        'user__first_name',
        'user__last_name',
        'user__email',
        'committee__name',
    ]
    
    fieldsets = (
        (None, {
            'fields': ('user', 'committee', 'role', 'member_type')
        }),
        ('Zeitraum', {
            'fields': ('start_date', 'end_date', 'is_active')
        }),
        ('Wahlinfo', {
            'fields': ('election_list_name', 'election_list_position', 'election_votes'),
            'description': 'Nur für reguläre Mitglieder und Ersatzmitglieder relevant'
        }),
        ('Soft-Delete', {
            'fields': ('deleted_at', 'deleted_by'),
            'classes': ('collapse',)
        }),
    )
    
    autocomplete_fields = [
        'user',
        'committee',
        'role',
    ]
    
    readonly_fields = [
        'deleted_at',
        'deleted_by',
    ]
    
    @admin.display(boolean=True, description='Gelöscht')
    def is_deleted_display(self, obj):
        """Display whether membership is deleted."""
        return obj.deleted_at is not None
    
    def get_queryset(self, request):
        """Return all memberships including deleted ones for admin."""
        return Membership.all_objects.all_with_deleted().select_related(
            'user',
            'committee',
            'role',
            'deleted_by'
        )
