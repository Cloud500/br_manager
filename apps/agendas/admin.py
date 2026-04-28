"""Admin configuration for agendas app."""

from django.contrib import admin
from django.utils.html import format_html

from .models import Agenda, AgendaItemRegular


class AgendaItemInline(admin.TabularInline):
    """Inline admin for agenda items."""
    
    model = AgendaItemRegular
    extra = 0
    fields = ['title', 'parent', 'sort_order', 'item_number']
    readonly_fields = ['item_number']
    ordering = ['sort_order']


@admin.register(Agenda)
class AgendaAdmin(admin.ModelAdmin):
    """Admin interface for Agenda model."""
    
    list_display = ['meeting', 'item_count_display', 'is_editable_display', 'is_finalized_display', 'created_at']
    list_filter = ['meeting__status', 'created_at']
    search_fields = ['meeting__title', 'meeting__meeting_number']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [AgendaItemInline]
    
    fieldsets = [
        ('Sitzung', {
            'fields': ['meeting']
        }),
        ('Audit-Informationen', {
            'fields': ['id', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def item_count_display(self, obj: Agenda) -> int:
        """Display item count."""
        return obj.item_count
    item_count_display.short_description = 'Anzahl TOPs'
    
    def is_editable_display(self, obj: Agenda) -> str:
        """Display editable status with icon."""
        if obj.is_editable:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    is_editable_display.short_description = 'Editierbar'
    
    def is_finalized_display(self, obj: Agenda) -> str:
        """Display finalized status with icon."""
        if obj.is_finalized:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    is_finalized_display.short_description = 'Finalisiert'


@admin.register(AgendaItemRegular)
class AgendaItemRegularAdmin(admin.ModelAdmin):
    """Admin interface for AgendaItemRegular model."""
    
    list_display = ['item_number', 'title', 'parent', 'agenda', 'sort_order', 'created_at']
    list_filter = ['created_at', 'agenda__meeting__committee']
    search_fields = ['title', 'description', 'agenda__meeting__title']
    readonly_fields = ['id', 'item_number', 'item_type', 'created_at', 'updated_at']
    ordering = ['agenda', 'sort_order']
    
    fieldsets = [
        ('Tagesordnung', {
            'fields': ['agenda', 'parent']
        }),
        ('Inhalt', {
            'fields': ['title', 'description']
        }),
        ('Sortierung', {
            'fields': ['sort_order']
        }),
        ('System-Informationen', {
            'fields': ['id', 'item_number', 'item_type', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
