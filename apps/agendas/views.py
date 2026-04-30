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

from .forms import (
    AgendaItemRegularForm,
    AgendaItemResolutionForm,
    AgendaItemResolutionUpdateForm,
)
from .mixins import AgendaPermissionMixin
from .models import Agenda, AgendaItem


class AgendaItemCreateView(LoginRequiredMixin, AgendaPermissionMixin, CreateView):
    """
    Create new agenda item.
    
    Requires 'agenda.add_item_regular' permission.
    """
    
    model = AgendaItem
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
    
    model = AgendaItem
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
            'Beschluss wurde zur Tagesordnung hinzugefügt.'
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
    
    model = AgendaItem
    form_class = AgendaItemRegularForm
    template_name = 'agendas/item_form.html'
    required_permission = 'agenda.edit_item_regular'

    def test_func(self) -> bool:
        """Check the permission matching the agenda item type."""
        item = self.get_object()
        if item.item_type == AgendaItem.TYPE_RESOLUTION:
            self.required_permission = 'agenda.edit_item_resolution'
        return super().test_func()

    def get_queryset(self):
        """Limit editing to regular and resolution agenda items."""
        return super().get_queryset().filter(
            item_type__in=[AgendaItem.TYPE_REGULAR, AgendaItem.TYPE_RESOLUTION]
        )

    def get_form_class(self):
        """Use the matching form for the agenda item type."""
        if self.object.item_type == AgendaItem.TYPE_RESOLUTION:
            return AgendaItemResolutionUpdateForm
        return AgendaItemRegularForm
    
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
    
    model = AgendaItem
    template_name = 'agendas/item_confirm_delete.html'
    required_permission = 'agenda.delete_item_regular'

    def test_func(self) -> bool:
        """Check the permission matching the agenda item type."""
        item = self.get_object()
        if item.item_type == AgendaItem.TYPE_RESOLUTION:
            self.required_permission = 'agenda.delete_item_resolution'
        return super().test_func()

    def get_queryset(self):
        """Limit deletion to regular and resolution agenda items."""
        return super().get_queryset().filter(
            item_type__in=[AgendaItem.TYPE_REGULAR, AgendaItem.TYPE_RESOLUTION]
        )
    
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
    
    existing_items = {str(item.id): item for item in agenda.all_items}
    existing_positions = {str(item.id): index for index, item in enumerate(agenda.all_items)}
    existing_ids = set(existing_items)
    submitted_ids = {str(item_data.get('id')) for item_data in item_order if item_data.get('id')}
    if submitted_ids != existing_ids:
        return JsonResponse({
            'status': 'error',
            'message': 'Die übermittelte TOP-Reihenfolge ist unvollständig oder ungültig.'
        }, status=400)

    requested_parents = {
        str(item_data.get('id')): str(item_data.get('parent_id')) if item_data.get('parent_id') else None
        for item_data in item_order
    }

    if any(item.is_published_election for item in existing_items.values()):
        for index, item_data in enumerate(item_order):
            item_id = str(item_data.get('id'))
            parent_id = str(item_data.get('parent_id')) if item_data.get('parent_id') else None
            item = existing_items[item_id]
            if existing_positions[item_id] != index or str(item.parent_id) != str(parent_id):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Tagesordnungen mit veröffentlichten Wahlen können nicht neu angeordnet werden.'
                }, status=400)

    def has_cycle(item_id: str, parent_id: str | None) -> bool:
        """Return whether requested parent assignment creates a cycle."""
        seen = {item_id}
        current_parent = parent_id
        while current_parent:
            if current_parent in seen:
                return True
            seen.add(current_parent)
            current_parent = requested_parents.get(current_parent)
        return False

    items_to_update = []
    for index, item_data in enumerate(item_order):
        item_id = str(item_data.get('id'))
        parent_id = str(item_data.get('parent_id')) if item_data.get('parent_id') else None
        item = existing_items.get(item_id)

        if item is None:
            continue

        if item.is_published_election:
            original_index = existing_positions.get(item_id)
            if original_index != index or str(item.parent_id) != str(parent_id):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Veröffentlichte Wahlen können nicht neu angeordnet werden.'
                }, status=400)

        if parent_id:
            parent = existing_items.get(parent_id)
            if parent is None:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Übergeordneter TOP wurde nicht gefunden.'
                }, status=400)
            if item_id == parent_id or has_cycle(item_id, parent_id):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Ungültige TOP-Hierarchie: zirkuläre Unterordnung ist nicht erlaubt.'
                }, status=400)

        item.sort_order = float(index)
        item.parent_id = parent_id
        items_to_update.append(item)

    if items_to_update:
        AgendaItem.objects.bulk_update(
            items_to_update,
            fields=['sort_order', 'parent_id'],
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
