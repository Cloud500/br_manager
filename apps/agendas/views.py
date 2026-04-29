"""Views for agendas app."""

import json
from typing import Any, Dict
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, UpdateView

from .forms import AgendaItemRegularForm, AgendaItemResolutionForm
from .mixins import AgendaPermissionMixin
from .models import (
    Agenda,
    AgendaItemRegular,
    AgendaItemResolution,
    get_concrete_agenda_item_models,
    get_item_key,
    get_parent_key,
)


class AgendaItemCreateView(LoginRequiredMixin, AgendaPermissionMixin, CreateView):
    """
    Create new agenda item.
    
    Requires 'agenda.add_item_regular' permission.
    """
    
    model = AgendaItemRegular
    form_class = AgendaItemRegularForm
    template_name = 'agendas/item_form.html'
    required_permission = 'agenda.add_item_regular'
    
    def get_agenda(self) -> Agenda:
        """Get agenda from URL parameter."""
        agenda_id = self.request.GET.get('agenda') or self.kwargs.get('agenda_id')
        return get_object_or_404(Agenda, pk=agenda_id)
    
    def get_form_kwargs(self) -> Dict[str, Any]:
        """Add agenda to form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs['agenda'] = self.get_agenda()
        return kwargs
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add agenda to context."""
        context = super().get_context_data(**kwargs)
        context['agenda'] = self.get_agenda()
        context['is_create'] = True
        return context
    
    def form_valid(self, form):
        """
        Handle valid form submission.
        
        Calculates sort_order, saves item, and triggers item number recalculation.
        """
        agenda = self.get_agenda()
        
        # Check if agenda is editable
        if not agenda.is_editable:
            messages.error(
                self.request,
                f'Tagesordnung kann nicht bearbeitet werden. '
                f'Sitzungsstatus: {agenda.meeting.get_status_display()}'
            )
            return redirect('meetings:meeting_detail', pk=agenda.meeting.pk)
        
        form.instance.sort_order = agenda.next_sort_order()
        
        # Save item (agenda is already set by form.save())
        # This will trigger recalculate_item_numbers via model save()
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            f'Tagesordnungspunkt "{form.instance.title}" wurde erstellt.'
        )
        
        return response
    
    def get_success_url(self) -> str:
        """Redirect to meeting detail page."""
        return reverse('meetings:meeting_detail', kwargs={'pk': self.object.agenda.meeting.pk})


class AgendaItemResolutionCreateView(LoginRequiredMixin, AgendaPermissionMixin, CreateView):
    """
    Create new resolution agenda item.
    
    Requires 'agenda.add_item_resolution' permission.
    """
    
    model = AgendaItemResolution
    form_class = AgendaItemResolutionForm
    template_name = 'agendas/item_resolution_form.html'
    required_permission = 'agenda.add_item_resolution'
    
    def get_agenda(self) -> Agenda:
        """Get agenda from URL parameter."""
        agenda_id = self.request.GET.get('agenda') or self.kwargs.get('agenda_id')
        return get_object_or_404(Agenda, pk=agenda_id)
    
    def get_form_kwargs(self) -> Dict[str, Any]:
        """Add agenda to form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs['agenda'] = self.get_agenda()
        return kwargs
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add agenda to context."""
        context = super().get_context_data(**kwargs)
        context['agenda'] = self.get_agenda()
        context['is_create'] = True
        return context
    
    def form_valid(self, form):
        """
        Handle valid form submission.
        
        Calculates sort_order, saves item, and triggers item number recalculation.
        """
        agenda = self.get_agenda()
        
        # Check if agenda is editable
        if not agenda.is_editable:
            messages.error(
                self.request,
                f'Tagesordnung kann nicht bearbeitet werden. '
                f'Sitzungsstatus: {agenda.meeting.get_status_display()}'
            )
            return redirect('meetings:meeting_detail', pk=agenda.meeting.pk)
        
        form.instance.sort_order = agenda.next_sort_order()
        
        # Save item (agenda is already set by form.save())
        # This will trigger recalculate_item_numbers via model save()
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            f'Beschluss "{form.instance.resolution.proposal[:50]}..." wurde zur Tagesordnung hinzugefügt.'
        )
        
        return response
    
    def get_success_url(self) -> str:
        """Redirect to meeting detail page."""
        return reverse('meetings:meeting_detail', kwargs={'pk': self.object.agenda.meeting.pk})


class AgendaItemUpdateView(LoginRequiredMixin, AgendaPermissionMixin, UpdateView):
    """
    Update existing agenda item.
    
    Requires 'agenda.edit_item_regular' permission.
    """
    
    model = AgendaItemRegular
    form_class = AgendaItemRegularForm
    template_name = 'agendas/item_form.html'
    required_permission = 'agenda.edit_item_regular'
    
    def get_form_kwargs(self) -> Dict[str, Any]:
        """Add agenda to form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs['agenda'] = self.object.agenda
        return kwargs
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add agenda to context."""
        context = super().get_context_data(**kwargs)
        context['agenda'] = self.object.agenda
        context['is_create'] = False
        return context
    
    def form_valid(self, form):
        """
        Handle valid form submission.
        
        Checks if agenda is editable, saves item, and triggers recalculation.
        """
        agenda = self.object.agenda
        
        # Check if agenda is editable
        if not agenda.is_editable:
            messages.error(
                self.request,
                f'Tagesordnung kann nicht bearbeitet werden. '
                f'Sitzungsstatus: {agenda.meeting.get_status_display()}'
            )
            return redirect('meetings:meeting_detail', pk=agenda.meeting.pk)
        
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            f'Tagesordnungspunkt "{form.instance.title}" wurde aktualisiert.'
        )
        
        return response
    
    def get_success_url(self) -> str:
        """Redirect to meeting detail page."""
        return reverse('meetings:meeting_detail', kwargs={'pk': self.object.agenda.meeting.pk})


class AgendaItemDeleteView(LoginRequiredMixin, AgendaPermissionMixin, DeleteView):
    """
    Delete agenda item.
    
    Requires 'agenda.delete_item_regular' permission.
    """
    
    model = AgendaItemRegular
    template_name = 'agendas/item_confirm_delete.html'
    required_permission = 'agenda.delete_item_regular'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add agenda to context."""
        context = super().get_context_data(**kwargs)
        context['agenda'] = self.object.agenda
        return context
    
    def post(self, request, *args, **kwargs):
        """
        Handle delete request.
        
        Checks if agenda is editable before deleting.
        """
        self.object = self.get_object()
        agenda = self.object.agenda
        
        # Check if agenda is editable
        if not agenda.is_editable:
            messages.error(
                self.request,
                f'Tagesordnung kann nicht bearbeitet werden. '
                f'Sitzungsstatus: {agenda.meeting.get_status_display()}'
            )
            return redirect('meetings:meeting_detail', pk=agenda.meeting.pk)
        
        # Store title for message
        title = self.object.title
        
        # Delete item (will trigger recalculation via signal/cascade)
        success_url = self.get_success_url()
        self.object.delete()
        
        # Recalculate item numbers
        agenda.recalculate_item_numbers()
        
        messages.success(
            self.request,
            f'Tagesordnungspunkt "{title}" wurde gelöscht.'
        )
        
        return redirect(success_url)
    
    def get_success_url(self) -> str:
        """Redirect to meeting detail page."""
        return reverse('meetings:meeting_detail', kwargs={'pk': self.object.agenda.meeting.pk})


@login_required
@require_POST
def reorder_items(request, agenda_id: UUID):
    """
    Reorder agenda items via AJAX.
    
    Handles drag-and-drop reordering. Updates sort_order and parent_id
    for all items, then recalculates item numbers.
    
    Args:
        request: HTTP request with JSON body containing 'item_order' array
        agenda_id: UUID of agenda
    
    Returns:
        JSON response with status and updated item_numbers
    """
    # Get agenda
    agenda = get_object_or_404(Agenda, pk=agenda_id)
    
    # Check permission
    from apps.committees.models import Membership
    
    user = request.user
    
    # Guard clause: Superuser/Staff
    if not (user.is_superuser or user.is_staff):
        # Check permission in committee
        committee = agenda.meeting.committee
        has_permission = False
        
        # Standard check
        memberships = Membership.objects.filter(
            user=user,
            committee=committee,
            is_active=True
        ).select_related('role')
        
        for membership in memberships:
            if membership.role and membership.role.permissions.filter(
                codename='agenda.reorder_items'
            ).exists():
                has_permission = True
                break
        
        # BA check (if not found yet)
        if not has_permission and committee.committee_type == 'MAIN':
            betriebsausschuss = committee.subcommittees.filter(
                committee_type='COMMITTEE',
                is_active=True
            ).first()
            
            if betriebsausschuss:
                ba_memberships = Membership.objects.filter(
                    user=user,
                    committee=betriebsausschuss,
                    is_active=True
                ).select_related('role')
                
                for membership in ba_memberships:
                    if membership.role and membership.role.permissions.filter(
                        codename='agenda.reorder_items'
                    ).exists():
                        has_permission = True
                        break
        
        if not has_permission:
            return JsonResponse({
                'status': 'error',
                'message': 'Sie haben keine Berechtigung für diese Aktion.'
            }, status=403)
    
    # Check if agenda is editable
    if not agenda.is_editable:
        return JsonResponse({
            'status': 'error',
            'message': f'Tagesordnung kann nicht bearbeitet werden. '
                      f'Sitzungsstatus: {agenda.meeting.get_status_display()}'
        }, status=400)
    
    # Parse JSON body
    try:
        data = json.loads(request.body)
        item_order = data.get('item_order', [])
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Ungültige JSON-Daten'
        }, status=400)
    
    # Update sort_order and parent references for each item, grouped by concrete model
    items_to_update = {}
    model_by_type = {
        item_model.__name__: item_model
        for item_model in get_concrete_agenda_item_models()
    }
    existing_items = {get_item_key(item): item for item in agenda.all_items}
    existing_items_by_id = {}
    for item in agenda.all_items:
        existing_items_by_id.setdefault(str(item.id), []).append(item)
    existing_positions = {
        get_item_key(item): index
        for index, item in enumerate(agenda.all_items)
    }

    def resolve_parent_key(parent_id: str | None, parent_type: str | None = None) -> tuple[str, str] | None:
        """Resolve a posted parent reference to a concrete agenda item key."""
        if not parent_id:
            return None
        if parent_type:
            parent_key = (parent_type, str(parent_id))
            return parent_key if parent_key in existing_items else None

        possible_parents = existing_items_by_id.get(str(parent_id), [])
        if len(possible_parents) == 1:
            return get_item_key(possible_parents[0])
        return None

    requested_parents = {}
    for item_data in item_order:
        item_type = item_data.get('type') or 'AgendaItemRegular'
        item_id = item_data.get('id')
        parent_id = item_data.get('parent_id')
        parent_type = item_data.get('parent_type')
        item_key = (item_type, str(item_id))
        requested_parents[item_key] = resolve_parent_key(parent_id, parent_type)

    def has_cycle(item_key: tuple[str, str], parent_key: tuple[str, str] | None) -> bool:
        """Return whether requested parent assignment creates a cycle."""
        seen = {item_key}
        current_parent = parent_key
        while current_parent:
            if current_parent in seen:
                return True
            seen.add(current_parent)
            current_parent = requested_parents.get(current_parent)
        return False
    
    for index, item_data in enumerate(item_order):
        item_id = item_data.get('id')
        parent_id = item_data.get('parent_id')
        parent_type = item_data.get('parent_type')
        item_type = item_data.get('type') or 'AgendaItemRegular'
        item_model = model_by_type.get(item_type, AgendaItemRegular)
        item_key = (item_type, str(item_id))
        item = existing_items.get(item_key)
        parent_key = resolve_parent_key(parent_id, parent_type)

        if item is None:
            continue

        if item_type == 'Election' and getattr(item, 'status', None) == 'PUBLISHED':
            original_index = existing_positions.get(item_key)
            if original_index != index or get_parent_key(item) != parent_key:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Veröffentlichte Wahlen können nicht neu angeordnet werden.'
                }, status=400)

        if parent_id:
            if parent_key is None or parent_key not in existing_items:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Übergeordneter TOP wurde nicht gefunden.'
                }, status=400)
            can_use_regular_parent = hasattr(item, 'parent_regular_id') and parent_key[0] == 'AgendaItemRegular'
            if item_type != parent_key[0] and not can_use_regular_parent:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Diese Unterordnung zwischen unterschiedlichen TOP-Typen wird nicht unterstützt.'
                }, status=400)
            if item_key == parent_key or has_cycle(item_key, parent_key):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Ungültige TOP-Hierarchie: zirkuläre Unterordnung ist nicht erlaubt.'
                }, status=400)
          
        item.sort_order = float(index)
        if hasattr(item, 'parent_regular_id') and parent_key and parent_key[0] == 'AgendaItemRegular':
            item.parent_id = None
            item.parent_regular_id = parent_key[1]
        else:
            item.parent_id = parent_key[1] if parent_key else None
            if hasattr(item, 'parent_regular_id'):
                item.parent_regular_id = None
        items_to_update.setdefault(item_model, []).append(item)
     
    # Bulk update
    for item_model, model_items in items_to_update.items():
        update_fields = ['sort_order', 'parent_id']
        if any(hasattr(item, 'parent_regular_id') for item in model_items):
            update_fields.append('parent_regular_id')
        item_model.objects.bulk_update(
            model_items,
            fields=update_fields,
            batch_size=100
        )
    
    # Recalculate item numbers
    agenda.recalculate_item_numbers()
    
    # Get updated item numbers
    item_numbers = {
        str(item.id): item.item_number
        for item in agenda.all_items
    }
    
    return JsonResponse({
        'status': 'success',
        'item_numbers': item_numbers
    })
