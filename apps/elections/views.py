"""Views for elections app."""

from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.agendas.models import Agenda
from apps.committees.models import Membership
from apps.elections.forms import ElectionCandidateFormSetFactory, ElectionForm
from apps.elections.mixins import ElectionPermissionMixin
from apps.elections.models import Election


class ElectionListView(LoginRequiredMixin, ListView):
    """Display elections visible to the current user."""

    model = Election
    template_name = 'elections/election_list.html'
    context_object_name = 'elections'
    paginate_by = 25

    def get_queryset(self):
        """Return elections from committees where the user can view elections."""
        queryset = (
            Election.objects.select_related('agenda_item__agenda__meeting__committee')
            .prefetch_related('candidates', 'result__candidate_results__candidate')
            .order_by(
                '-agenda_item__agenda__meeting__date',
                'agenda_item__agenda__meeting__meeting_number',
                'agenda_item__sort_order',
            )
        )
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return queryset

        visible_committee_ids = Membership.objects.filter(
            user=user,
            is_active=True,
            role__permissions__codename='election.view',
        ).values('committee_id')
        return queryset.filter(agenda_item__agenda__meeting__committee_id__in=visible_committee_ids).distinct()


class ElectionCreateView(LoginRequiredMixin, ElectionPermissionMixin, CreateView):
    """Create an election from an agenda context."""

    model = Election
    form_class = ElectionForm
    template_name = 'elections/election_form.html'
    required_permission = 'election.create'

    def get_agenda(self) -> Agenda:
        """Get agenda from URL."""
        return get_object_or_404(Agenda, pk=self.kwargs['agenda_id'])

    def dispatch(self, request, *args, **kwargs):
        """Block election creation when the meeting agenda is locked."""
        agenda = self.get_agenda()
        if not agenda.is_editable:
            messages.error(
                request,
                f'Tagesordnung kann nicht bearbeitet werden. Sitzungsstatus: {agenda.meeting.get_status_display()}'
            )
            return redirect('meetings:meeting_detail', pk=agenda.meeting.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self) -> Dict[str, Any]:
        """Pass agenda into election form."""
        kwargs = super().get_form_kwargs()
        kwargs['agenda'] = self.get_agenda()
        return kwargs

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add agenda and candidate formset to context."""
        context = super().get_context_data(**kwargs)
        context['agenda'] = self.get_agenda()
        context['is_create'] = True
        if self.request.POST:
            context['candidate_formset'] = ElectionCandidateFormSetFactory(self.request.POST)
        else:
            context['candidate_formset'] = ElectionCandidateFormSetFactory()
        return context

    def form_valid(self, form):
        """Save election and candidates atomically."""
        agenda = self.get_agenda()
        if not agenda.is_editable:
            messages.error(
                self.request,
                f'Tagesordnung kann nicht bearbeitet werden. Sitzungsstatus: {agenda.meeting.get_status_display()}'
            )
            return redirect('meetings:meeting_detail', pk=agenda.meeting.pk)

        context = self.get_context_data(form=form)
        candidate_formset = context['candidate_formset']
        if not candidate_formset.is_valid():
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save()
            candidate_formset.instance = self.object
            candidates = candidate_formset.save(commit=False)
            for index, candidate in enumerate(candidates):
                candidate.sort_order = index
                candidate.save()

        messages.success(self.request, f'Wahl "{self.object.title}" wurde erstellt.')
        return redirect(self.get_success_url())

    def get_success_url(self) -> str:
        """Redirect to meeting detail."""
        return reverse('meetings:meeting_detail', kwargs={'pk': self.object.agenda.meeting.pk})


class ElectionDetailView(LoginRequiredMixin, ElectionPermissionMixin, DetailView):
    """Display an election agenda item."""

    model = Election
    template_name = 'elections/election_detail.html'
    context_object_name = 'election'
    required_permission = 'election.view'

    def get_election(self) -> Election:
        """Return current election object."""
        if not hasattr(self, 'object') or self.object is None:
            self.object = self.get_object()
        return self.object

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add action permissions to context."""
        context = super().get_context_data(**kwargs)
        context['can_edit'] = self.object.is_editable and self._has_permission('election.edit')
        context['can_delete'] = self.object.is_deletable and self._has_permission('election.delete')
        context['can_publish'] = self.object.is_publishable and self._has_permission('election.edit')
        context['result'] = getattr(self.object, 'result', None)
        return context

    def _has_permission(self, permission_codename: str) -> bool:
        """Check an election permission for the current user."""
        previous = self.required_permission
        self.required_permission = permission_codename
        try:
            return self.test_func()
        finally:
            self.required_permission = previous


class ElectionUpdateView(LoginRequiredMixin, ElectionPermissionMixin, UpdateView):
    """Update a draft election."""

    model = Election
    form_class = ElectionForm
    template_name = 'elections/election_form.html'
    required_permission = 'election.edit'

    def get_election(self) -> Election:
        """Return current election object."""
        if not hasattr(self, 'object') or self.object is None:
            self.object = self.get_object()
        return self.object

    def dispatch(self, request, *args, **kwargs):
        """Block updates for published or non-editable elections."""
        election = self.get_object()
        if not election.is_editable:
            raise PermissionDenied('Diese Wahl kann nicht mehr bearbeitet werden.')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self) -> Dict[str, Any]:
        """Pass agenda into form."""
        kwargs = super().get_form_kwargs()
        kwargs['agenda'] = self.object.agenda
        return kwargs

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add candidate formset to context."""
        context = super().get_context_data(**kwargs)
        context['agenda'] = self.object.agenda
        context['is_create'] = False
        if self.request.POST:
            context['candidate_formset'] = ElectionCandidateFormSetFactory(
                self.request.POST,
                instance=self.object
            )
        else:
            context['candidate_formset'] = ElectionCandidateFormSetFactory(instance=self.object)
        return context

    def form_valid(self, form):
        """Save election and candidates atomically."""
        context = self.get_context_data(form=form)
        candidate_formset = context['candidate_formset']
        if not candidate_formset.is_valid():
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save()
            candidates = candidate_formset.save(commit=False)
            for deleted in candidate_formset.deleted_objects:
                deleted.delete()
            for index, candidate in enumerate(candidates):
                candidate.sort_order = index
                candidate.save()
            candidate_formset.save_m2m()

        messages.success(self.request, 'Wahl wurde aktualisiert.')
        return redirect(self.get_success_url())

    def get_success_url(self) -> str:
        """Redirect to election detail."""
        return reverse('elections:election_detail', kwargs={'pk': self.object.pk})


class ElectionDeleteView(LoginRequiredMixin, ElectionPermissionMixin, DeleteView):
    """Delete a draft election."""

    model = Election
    template_name = 'elections/election_confirm_delete.html'
    required_permission = 'election.delete'

    def get_election(self) -> Election:
        """Return current election object."""
        if not hasattr(self, 'object') or self.object is None:
            self.object = self.get_object()
        return self.object

    def dispatch(self, request, *args, **kwargs):
        """Block deletes for published or non-editable elections."""
        election = self.get_object()
        if not election.is_deletable:
            raise PermissionDenied('Diese Wahl kann nicht gelöscht werden.')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Delete election and return to meeting detail."""
        self.object = self.get_object()
        success_url = self.get_success_url()
        title = self.object.title
        agenda = self.object.agenda
        self.object.delete()
        agenda.recalculate_item_numbers()
        messages.success(request, f'Wahl "{title}" wurde gelöscht.')
        return redirect(success_url)

    def get_success_url(self) -> str:
        """Redirect to meeting detail."""
        return reverse('meetings:meeting_detail', kwargs={'pk': self.object.agenda.meeting.pk})


class ElectionPublishView(LoginRequiredMixin, ElectionPermissionMixin, DetailView):
    """Publish a draft election."""

    model = Election
    http_method_names = ['post']
    required_permission = 'election.edit'

    def get_election(self) -> Election:
        """Return current election object."""
        if not hasattr(self, 'object') or self.object is None:
            self.object = self.get_object()
        return self.object

    def post(self, request, *args, **kwargs):
        """Publish election."""
        election = self.get_object()
        if not election.is_publishable:
            messages.error(request, 'Wahl kann nur mit mindestens einer kandidierenden Person veröffentlicht werden.')
            return redirect('elections:election_detail', pk=election.pk)

        try:
            election.publish()
        except ValidationError as exc:
            messages.error(request, exc.message if hasattr(exc, 'message') else str(exc))
            return redirect('elections:election_detail', pk=election.pk)

        messages.success(request, 'Wahl wurde veröffentlicht.')
        return redirect('elections:election_detail', pk=election.pk)
