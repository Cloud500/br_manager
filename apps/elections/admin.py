"""Admin configuration for elections app."""

from django.contrib import admin

from apps.elections.models import Election, ElectionCandidate


class ElectionCandidateInline(admin.TabularInline):
    """Inline admin for election candidates."""

    model = ElectionCandidate
    extra = 1
    fields = ['name', 'sort_order']
    ordering = ['sort_order', 'name']


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    """Admin interface for elections."""

    list_display = [
        'item_number',
        'title',
        'agenda',
        'election_type',
        'majority_type',
        'status',
        'created_at',
    ]
    list_filter = ['status', 'election_type', 'majority_type', 'agenda__meeting__committee']
    search_fields = ['title', 'description', 'candidates__name', 'agenda__meeting__title']
    readonly_fields = ['id', 'item_number', 'item_type', 'created_at', 'updated_at']
    ordering = ['agenda', 'sort_order']
    inlines = [ElectionCandidateInline]

    fieldsets = [
        ('Tagesordnung', {'fields': ['agenda', 'parent']}),
        ('Wahl', {'fields': ['title', 'description', 'election_type', 'majority_type', 'status']}),
        ('Sortierung', {'fields': ['sort_order']}),
        ('System-Informationen', {
            'fields': ['id', 'item_number', 'item_type', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(ElectionCandidate)
class ElectionCandidateAdmin(admin.ModelAdmin):
    """Admin interface for election candidates."""

    list_display = ['name', 'election', 'sort_order']
    list_filter = ['election__status', 'election__agenda__meeting__committee']
    search_fields = ['name', 'election__title']
    ordering = ['election', 'sort_order', 'name']
