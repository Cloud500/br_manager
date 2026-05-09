"""Views for resolutions app."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)

from apps.agendas.models import Agenda, AgendaItem
from apps.committees.models import Committee, Membership
from apps.resolutions.forms import ResolutionForm, ResolutionStatusForm
from apps.resolutions.models import Resolution, ResolutionAgendaItem


def _user_has_agenda_permission(user, agenda, permission_codename: str) -> bool:
    """Check agenda permission using the same MAIN/BA rule as agenda views."""
    if user.is_superuser or user.is_staff:
        return True

    committee = agenda.meeting.committee
    if Membership.objects.filter(
        user=user,
        committee=committee,
        is_active=True,
        role__permissions__codename=permission_codename,
    ).exists():
        return True

    if committee.committee_type == 'MAIN':
        return Membership.objects.filter(
            user=user,
            committee__parent=committee,
            committee__committee_type='COMMITTEE',
            committee__is_active=True,
            is_active=True,
            role__permissions__codename=permission_codename,
        ).exists()

    return False


class ResolutionPermissionMixin:
    """Mixin for resolution permission checks."""
    
    def get_user_permission(self, resolution, permission_codename):
        """
        Check if user has specific permission for resolution.
        
        Args:
            resolution: Resolution instance
            permission_codename: Permission to check (e.g., 'resolution.edit')
        
        Returns:
            True if user has permission
        """
        user = self.request.user
        
        # Superuser/staff always has permission
        if user.is_superuser or user.is_staff:
            return True
        
        # Get user's memberships in this committee
        memberships = Membership.objects.filter(
            user=user,
            committee=resolution.committee,
            is_active=True
        ).select_related('role')
        
        for membership in memberships:
            if membership.role and membership.role.permissions.filter(
                codename=permission_codename
            ).exists():
                return True
        
        return False


class ResolutionListView(LoginRequiredMixin, ListView):
    """List view for resolutions."""
    
    model = Resolution
    template_name = 'resolutions/resolution_list.html'
    context_object_name = 'resolutions'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter resolutions user can view."""
        user = self.request.user
        
        # Superuser sees all
        if user.is_superuser or user.is_staff:
            queryset = Resolution.objects.all()
        else:
            # Get committees where user has view permission
            memberships = Membership.objects.filter(
                user=user,
                is_active=True
            ).select_related('committee', 'role')
            
            committee_ids = []
            for membership in memberships:
                if membership.role and membership.role.permissions.filter(
                    codename='resolution.view'
                ).exists():
                    committee_ids.append(membership.committee.id)
            
            queryset = Resolution.objects.filter(committee_id__in=committee_ids)
        
        # Filter by committee if specified
        committee_id = self.request.GET.get('committee')
        if committee_id:
            queryset = queryset.filter(committee_id=committee_id)
        
        # Filter by status if specified
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.select_related('committee', 'created_by').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        """Add filter context."""
        context = super().get_context_data(**kwargs)
        
        # Get committees for filter
        user = self.request.user
        if user.is_superuser or user.is_staff:
            committees = Committee.objects.filter(can_create_resolutions=True, is_active=True)
        else:
            memberships = Membership.objects.filter(
                user=user,
                is_active=True
            ).select_related('committee', 'role')
            
            committee_ids = []
            for membership in memberships:
                if membership.role and membership.role.permissions.filter(
                    codename='resolution.view'
                ).exists():
                    committee_ids.append(membership.committee.id)
            
            committees = Committee.objects.filter(
                id__in=committee_ids,
                can_create_resolutions=True,
                is_active=True
            )
        
        context['committees'] = committees
        context['status_choices'] = Resolution.STATUS_CHOICES
        context['selected_committee'] = self.request.GET.get('committee', '')
        context['selected_status'] = self.request.GET.get('status', '')
        
        return context


class ResolutionDetailView(LoginRequiredMixin, ResolutionPermissionMixin, DetailView):
    """Detail view for resolution."""
    
    model = Resolution
    template_name = 'resolutions/resolution_detail.html'
    context_object_name = 'resolution'
    
    def get_object(self, queryset=None):
        """Get resolution and check view permission."""
        resolution = super().get_object(queryset)
        
        if not self.get_user_permission(resolution, 'resolution.view'):
            raise PermissionDenied('Sie haben keine Berechtigung diesen Beschluss anzusehen')
        
        return resolution
    
    def get_context_data(self, **kwargs):
        """Add permission context."""
        context = super().get_context_data(**kwargs)
        resolution = self.object
        
        context['can_edit'] = (
            resolution.is_editable and 
            self.get_user_permission(resolution, 'resolution.edit')
        )
        context['can_delete'] = (
            resolution.is_deletable and 
            self.get_user_permission(resolution, 'resolution.delete')
        )
        context['can_propose'] = (
            resolution.can_be_proposed and 
            Resolution.user_can_propose(self.request.user, resolution.committee)
        )
        context['can_withdraw'] = (
            resolution.can_be_withdrawn and 
            Resolution.user_can_propose(self.request.user, resolution.committee)
        )
        
        return context


class ResolutionCreateView(LoginRequiredMixin, CreateView):
    """Create view for resolution."""
    
    model = Resolution
    form_class = ResolutionForm
    template_name = 'resolutions/resolution_form.html'

    def get_source_agenda(self):
        """Return the agenda that initiated direct resolution creation, if any."""
        agenda_id = self.request.GET.get('agenda') or self.request.POST.get('agenda')
        if not agenda_id:
            return None
        if not hasattr(self, '_source_agenda'):
            self._source_agenda = get_object_or_404(
                Agenda.objects.select_related('meeting', 'meeting__committee'),
                pk=agenda_id,
            )
        return self._source_agenda

    def dispatch(self, request, *args, **kwargs):
        """Validate meeting-scoped direct creation permissions."""
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        agenda = self.get_source_agenda()
        if agenda is None:
            return super().dispatch(request, *args, **kwargs)

        meeting = agenda.meeting
        committee = meeting.committee
        if not agenda.is_editable:
            messages.error(request, 'Tagesordnung kann nicht bearbeitet werden.')
            return redirect('meetings:meeting_detail', pk=meeting.pk)
        if not _user_has_agenda_permission(request.user, agenda, 'agenda.add_item_resolution'):
            messages.error(request, 'Sie haben keine Berechtigung für diese Aktion.')
            return redirect('meetings:meeting_detail', pk=meeting.pk)
        if not committee.can_create_resolutions:
            messages.error(request, 'Dieses Gremium darf keine Beschlüsse erstellen')
            return redirect('meetings:meeting_detail', pk=meeting.pk)
        if not Resolution.user_can_create(request.user, committee):
            messages.error(
                request,
                'Sie haben keine Berechtigung Beschlüsse für dieses Gremium zu erstellen',
            )
            return redirect('meetings:meeting_detail', pk=meeting.pk)
        if not Resolution.user_can_propose(request.user, committee):
            messages.error(
                request,
                'Sie haben keine Berechtigung Beschlüsse für dieses Gremium vorzuschlagen',
            )
            return redirect('meetings:meeting_detail', pk=meeting.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Preselect the meeting committee when launched from an agenda."""
        initial = super().get_initial()
        agenda = self.get_source_agenda()
        if agenda is not None:
            initial['committee'] = agenda.meeting.committee
        return initial

    def get_form(self, form_class=None):
        """Limit committee selection to the meeting committee in agenda flow."""
        form = super().get_form(form_class)
        agenda = self.get_source_agenda()
        if agenda is not None:
            committee = agenda.meeting.committee
            form.fields['committee'].queryset = form.fields['committee'].queryset.filter(
                pk=committee.pk,
            )
            form.fields['committee'].initial = committee
            form.fields['committee'].help_text = 'Gremium der Sitzung'
        return form
    
    def get_form_kwargs(self):
        """Pass user to form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """Add meeting-scoped direct creation context."""
        context = super().get_context_data(**kwargs)
        agenda = self.get_source_agenda()
        context['source_agenda'] = agenda
        if agenda is not None:
            context['cancel_url'] = reverse(
                'agendas:item_resolution_create',
                kwargs={'agenda_id': agenda.pk},
            )
        return context
    
    def form_valid(self, form):
        """Set created_by and validate permissions."""
        agenda = self.get_source_agenda()
        resolution = form.save(commit=False)
        resolution.created_by = self.request.user
        if agenda is not None:
            resolution.committee = agenda.meeting.committee
            resolution.status = 'PROPOSED'
        
        # Validate user can create for this committee
        if not Resolution.user_can_create(self.request.user, resolution.committee):
            messages.error(
                self.request,
                'Sie haben keine Berechtigung Beschlüsse für dieses Gremium zu erstellen'
            )
            return self.form_invalid(form)
        
        if agenda is not None:
            with transaction.atomic():
                resolution.save()
                agenda_item = AgendaItem.objects.create(
                    agenda=agenda,
                    title=resolution.title,
                    description='',
                    sort_order=agenda.next_sort_order(),
                    item_type=AgendaItem.TYPE_RESOLUTION,
                )
                ResolutionAgendaItem.objects.create(
                    agenda_item=agenda_item,
                    resolution=resolution,
                )
        else:
            resolution.save()

        self.object = resolution
        
        messages.success(
            self.request,
            f'Beschluss "{resolution.title}" wurde erstellt'
            + (' und zur Tagesordnung hinzugefügt' if agenda is not None else '')
        )
        
        return HttpResponseRedirect(self.get_success_url())
    
    def get_success_url(self):
        """Redirect to resolution detail."""
        agenda = self.get_source_agenda()
        if agenda is not None:
            return reverse('meetings:meeting_detail', kwargs={'pk': agenda.meeting.pk})
        return reverse('resolutions:resolution_detail', kwargs={'pk': self.object.pk})


class ResolutionUpdateView(LoginRequiredMixin, ResolutionPermissionMixin, UpdateView):
    """Update view for resolution."""
    
    model = Resolution
    form_class = ResolutionForm
    template_name = 'resolutions/resolution_form.html'
    
    def get_object(self, queryset=None):
        """Get resolution and check edit permission."""
        resolution = super().get_object(queryset)
        
        if not resolution.is_editable:
            raise PermissionDenied('Dieser Beschluss kann nicht mehr bearbeitet werden')
        
        if not self.get_user_permission(resolution, 'resolution.edit'):
            raise PermissionDenied('Sie haben keine Berechtigung diesen Beschluss zu bearbeiten')
        
        return resolution
    
    def get_form_kwargs(self):
        """Pass user to form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        """Update resolution."""
        messages.success(
            self.request,
            'Beschluss wurde aktualisiert'
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to resolution detail."""
        return reverse('resolutions:resolution_detail', kwargs={'pk': self.object.pk})


class ResolutionDeleteView(LoginRequiredMixin, ResolutionPermissionMixin, DeleteView):
    """Delete view for resolution."""
    
    model = Resolution
    template_name = 'resolutions/resolution_confirm_delete.html'
    success_url = reverse_lazy('resolutions:resolution_list')
    
    def get_object(self, queryset=None):
        """Get resolution and check delete permission."""
        resolution = super().get_object(queryset)
        
        if not resolution.is_deletable:
            raise PermissionDenied('Dieser Beschluss kann nicht gelöscht werden')
        
        if not self.get_user_permission(resolution, 'resolution.delete'):
            raise PermissionDenied('Sie haben keine Berechtigung diesen Beschluss zu löschen')
        
        return resolution
    
    def delete(self, request, *args, **kwargs):
        """Delete resolution with message."""
        messages.success(request, 'Beschluss wurde gelöscht')
        return super().delete(request, *args, **kwargs)


class ResolutionStatusChangeView(LoginRequiredMixin, ResolutionPermissionMixin, DetailView):
    """View for changing resolution status (propose/withdraw)."""
    
    model = Resolution
    http_method_names = ['post']
    
    def post(self, request, *args, **kwargs):
        """Handle status change."""
        resolution = self.get_object()
        
        form = ResolutionStatusForm(resolution, request.POST)
        
        if not form.is_valid():
            messages.error(request, 'Aktion konnte nicht durchgeführt werden')
            return redirect('resolutions:resolution_detail', pk=resolution.pk)
        
        action = form.cleaned_data['action']
        
        # Check permission
        if not Resolution.user_can_propose(request.user, resolution.committee):
            raise PermissionDenied('Sie haben keine Berechtigung den Status zu ändern')
        
        # Perform action
        if action == 'propose':
            resolution.status = 'PROPOSED'
            resolution.save()
            messages.success(request, 'Beschluss wurde vorgeschlagen')
        elif action == 'withdraw':
            resolution.status = 'DRAFT'
            resolution.save()
            messages.success(request, 'Beschluss wurde zurückgezogen')
        
        return redirect('resolutions:resolution_detail', pk=resolution.pk)
