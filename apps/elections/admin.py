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
        'agenda_item_created_at',
    ]
    list_filter = ['status', 'election_type', 'majority_type', 'agenda_item__agenda__meeting__committee']
    search_fields = ['agenda_item__title', 'agenda_item__description', 'candidates__name', 'agenda_item__agenda__meeting__title']
    readonly_fields = ['item_number', 'title', 'agenda', 'description']
    ordering = ['agenda_item__agenda', 'agenda_item__sort_order']
    inlines = [ElectionCandidateInline]

    fieldsets = [
        ('Tagesordnung', {'fields': ['agenda_item', 'agenda', 'item_number', 'title', 'description']}),
        ('Wahl', {'fields': ['election_type', 'majority_type', 'status']}),
    ]

    def agenda_item_created_at(self, obj):
        """Display agenda item creation timestamp."""
        return obj.agenda_item.created_at
    agenda_item_created_at.short_description = 'Erstellt am'


@admin.register(ElectionCandidate)
class ElectionCandidateAdmin(admin.ModelAdmin):
    """Admin interface for election candidates."""

    list_display = ['name', 'election', 'sort_order']
    list_filter = ['election__status', 'election__agenda_item__agenda__meeting__committee']
    search_fields = ['name', 'election__agenda_item__title']
    ordering = ['election', 'sort_order', 'name']
