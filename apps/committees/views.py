"""Views for committees app."""

from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, QuerySet
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.committees.forms import MembershipForm
from apps.committees.mixins import CommitteeContextMixin, CommitteePermissionMixin
from apps.committees.models import Committee, Membership
from apps.committees.utils import get_substitute_suggestions


class CommitteeListView(LoginRequiredMixin, CommitteePermissionMixin, ListView):
    """Display list of all committees."""
    
    model = Committee
    template_name = 'committees/committee_list.html'
    context_object_name = 'committees'
    required_permission = 'committee.view'
    paginate_by = 20
    
    def get_queryset(self) -> QuerySet:
        """Return active committees."""
        return Committee.objects.filter(
            is_active=True
        ).select_related('parent').order_by('committee_type', 'name')
    
    def get_context_data(self, **kwargs) -> dict:
        """Add grouped committees to context."""
        context = super().get_context_data(**kwargs)
        
        # Get all committees (not paginated) for grouping
        all_committees = self.get_queryset()
        context['main_committees'] = all_committees.filter(committee_type='MAIN')
        context['subcommittees'] = all_committees.exclude(committee_type='MAIN')
        
        return context


class CommitteeDetailView(
    LoginRequiredMixin,
    CommitteePermissionMixin,
    CommitteeContextMixin,
    DetailView
):
    """Display committee details."""
    
    model = Committee
    template_name = 'committees/committee_detail.html'
    context_object_name = 'committee'
    required_permission = 'committee.view'
    
    def get_context_data(self, **kwargs) -> dict:
        """Add member statistics to context."""
        context = super().get_context_data(**kwargs)
        
        committee = self.object
        
        context['active_members_count'] = committee.get_active_members().count()
        context['substitute_count'] = committee.get_active_substitutes().count()
        context['external_count'] = committee.get_external_members().count()
        context['recent_members'] = committee.get_active_members()[:5]
        
        return context


class CommitteeCreateView(LoginRequiredMixin, CommitteePermissionMixin, CreateView):
    """Create new committee."""
    
    model = Committee
    template_name = 'committees/committee_form.html'
    required_permission = 'committee.create'
    fields = [
        'name',
        'committee_type',
        'parent',
        'description',
        'total_seats',
        'quorum_type',
        'personnel_enabled',
        'substitute_logic_enabled',
        'minority_gender',
        'minority_min_count',
    ]
    
    def get_form(self, form_class=None):
        """Filter parent committee choices."""
        form = super().get_form(form_class)
        
        # Filter parent to only MAIN committees
        form.fields['parent'].queryset = Committee.objects.filter(
            committee_type='MAIN',
            is_active=True
        )
        
        return form
    
    def get_success_url(self) -> str:
        """Redirect to committee detail."""
        messages.success(
            self.request,
            f'Gremium "{self.object.name}" wurde erfolgreich erstellt.'
        )
        return reverse('committees:committee_detail', kwargs={'pk': self.object.pk})


class CommitteeUpdateView(
    LoginRequiredMixin,
    CommitteePermissionMixin,
    CommitteeContextMixin,
    UpdateView
):
    """Update committee."""
    
    model = Committee
    template_name = 'committees/committee_form.html'
    required_permission = 'committee.edit'
    fields = [
        'name',
        'description',
        'total_seats',
        'quorum_type',
        'personnel_enabled',
        'substitute_logic_enabled',
        'minority_gender',
        'minority_min_count',
        'is_active',
    ]
    
    def get_success_url(self) -> str:
        """Redirect to committee detail."""
        messages.success(
            self.request,
            f'Gremium "{self.object.name}" wurde erfolgreich aktualisiert.'
        )
        return reverse('committees:committee_detail', kwargs={'pk': self.object.pk})


class CommitteeDeleteView(
    LoginRequiredMixin,
    CommitteePermissionMixin,
    CommitteeContextMixin,
    DeleteView
):
    """Soft-delete committee."""
    
    model = Committee
    template_name = 'committees/committee_confirm_delete.html'
    required_permission = 'committee.delete'
    success_url = reverse_lazy('committees:committee_list')
    
    def get_context_data(self, **kwargs) -> dict:
        """Add memberships count to context."""
        context = super().get_context_data(**kwargs)
        context['memberships_count'] = self.object.memberships.filter(
            deleted_at__isnull=True
        ).count()
        return context
    
    def delete(self, request, *args, **kwargs):
        """Soft-delete committee."""
        self.object = self.get_object()
        
        # Soft-delete with user tracking
        deleted_count, details = self.object.delete(user=request.user)
        
        committee_count = details.get('committees.Committee', 0)
        membership_count = details.get('committees.Membership', 0)
        
        messages.success(
            request,
            f'Gremium "{self.object.name}" wurde gelöscht '
            f'({committee_count} Gremium, {membership_count} Mitgliedschaften).'
        )
        
        return redirect(self.success_url)


class MemberListView(
    LoginRequiredMixin,
    CommitteePermissionMixin,
    CommitteeContextMixin,
    ListView
):
    """Display list of committee members."""
    
    model = Membership
    template_name = 'committees/member_list.html'
    context_object_name = 'memberships'
    required_permission = 'committee.view_members'
    paginate_by = 50
    
    def get_queryset(self) -> QuerySet:
        """Return active memberships for committee."""
        committee = self.get_committee()
        return Membership.objects.filter(
            committee=committee,
            is_active=True
        ).select_related('user', 'role').order_by('member_type', 'user__last_name')
    
    def get_context_data(self, **kwargs) -> dict:
        """Add grouped memberships to context."""
        context = super().get_context_data(**kwargs)
        
        memberships = context['memberships']
        context['regular_members'] = memberships.filter(member_type='REGULAR')
        context['substitute_members'] = memberships.filter(member_type='SUBSTITUTE')
        context['external_members'] = memberships.filter(member_type='EXTERNAL')
        
        return context


class MemberAddView(
    LoginRequiredMixin,
    CommitteePermissionMixin,
    CommitteeContextMixin,
    CreateView
):
    """Add member to committee."""
    
    model = Membership
    template_name = 'committees/member_form.html'
    form_class = MembershipForm
    required_permission = 'committee.manage_members'
    
    def get_form_kwargs(self):
        """Pass committee to form."""
        kwargs = super().get_form_kwargs()
        kwargs['committee'] = self.get_committee()
        return kwargs
    
    def form_valid(self, form):
        """Set committee before saving."""
        form.instance.committee = self.get_committee()
        
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            f'{form.instance.user.get_full_name()} wurde zum Gremium hinzugefügt.'
        )
        
        return response
    
    def get_success_url(self) -> str:
        """Redirect to member list."""
        return reverse(
            'committees:member_list',
            kwargs={'committee_id': self.get_committee().pk}
        )


class MemberEditView(
    LoginRequiredMixin,
    CommitteePermissionMixin,
    CommitteeContextMixin,
    UpdateView
):
    """Edit membership."""
    
    model = Membership
    template_name = 'committees/member_form.html'
    form_class = MembershipForm
    required_permission = 'committee.manage_members'
    
    def get_queryset(self) -> QuerySet:
        """Filter to committee."""
        return Membership.objects.filter(committee=self.get_committee())
    
    def get_form_kwargs(self):
        """Pass committee to form."""
        kwargs = super().get_form_kwargs()
        kwargs['committee'] = self.get_committee()
        return kwargs
    
    def get_success_url(self) -> str:
        """Redirect to member list."""
        messages.success(
            self.request,
            f'Mitgliedschaft von {self.object.user.get_full_name()} wurde aktualisiert.'
        )
        return reverse(
            'committees:member_list',
            kwargs={'committee_id': self.get_committee().pk}
        )


class MemberRemoveView(
    LoginRequiredMixin,
    CommitteePermissionMixin,
    CommitteeContextMixin,
    DeleteView
):
    """Remove member from committee (soft-delete)."""
    
    model = Membership
    template_name = 'committees/member_confirm_remove.html'
    required_permission = 'committee.manage_members'
    
    def get_queryset(self) -> QuerySet:
        """Filter to committee."""
        return Membership.objects.filter(committee=self.get_committee())
    
    def delete(self, request, *args, **kwargs):
        """Soft-delete membership."""
        self.object = self.get_object()
        user_name = self.object.user.get_full_name()
        
        # Soft-delete
        self.object.delete(user=request.user)
        
        messages.success(
            request,
            f'{user_name} wurde aus dem Gremium entfernt.'
        )
        
        return redirect(self.get_success_url())
    
    def get_success_url(self) -> str:
        """Redirect to member list."""
        return reverse(
            'committees:member_list',
            kwargs={'committee_id': self.get_committee().pk}
        )


class SubstituteListView(
    LoginRequiredMixin,
    CommitteePermissionMixin,
    CommitteeContextMixin,
    ListView
):
    """Display substitute members grouped by election list."""
    
    model = Membership
    template_name = 'committees/substitute_list.html'
    context_object_name = 'substitutes'
    required_permission = 'committee.view_members'
    
    def get_queryset(self) -> QuerySet:
        """Return substitute members."""
        committee = self.get_committee()
        return Membership.objects.filter(
            committee=committee,
            member_type='SUBSTITUTE',
            is_active=True
        ).select_related('user', 'role').order_by(
            'election_list_name',
            'election_list_position',
            '-election_votes'
        )
    
    def get_context_data(self, **kwargs) -> dict:
        """Add grouped substitutes to context."""
        context = super().get_context_data(**kwargs)
        
        # Group by election list
        grouped = {}
        for substitute in context['substitutes']:
            list_name = substitute.election_list_name or 'Ohne Liste'
            if list_name not in grouped:
                grouped[list_name] = []
            grouped[list_name].append(substitute)
        
        context['grouped_substitutes'] = grouped
        
        return context


class MemberSearchView(
    LoginRequiredMixin,
    CommitteePermissionMixin,
    CommitteeContextMixin,
    ListView
):
    """Live search for members (HTMX)."""
    
    model = Membership
    template_name = 'committees/_member_list_rows.html'
    context_object_name = 'memberships'
    required_permission = 'committee.view_members'
    
    def get_queryset(self) -> QuerySet:
        """Filter members by search query."""
        committee = self.get_committee()
        query = self.request.GET.get('q', '')
        
        queryset = Membership.objects.filter(
            committee=committee,
            is_active=True
        ).select_related('user', 'role')
        
        if query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(user__email__icontains=query)
            )
        
        return queryset.order_by('member_type', 'user__last_name')


class MemberInlineEditView(
    LoginRequiredMixin,
    CommitteePermissionMixin,
    CommitteeContextMixin,
    UpdateView
):
    """Inline edit for membership (HTMX)."""
    
    model = Membership
    form_class = MembershipForm
    required_permission = 'committee.manage_members'
    
    def get_queryset(self) -> QuerySet:
        """Filter to committee."""
        return Membership.objects.filter(committee=self.get_committee())
    
    def get_template_names(self):
        """Return appropriate template based on request method."""
        if self.request.method == 'GET':
            return ['committees/_member_edit_form.html']
        return ['committees/_member_row.html']
    
    def form_valid(self, form):
        """Save and return updated row."""
        self.object = form.save()
        return self.render_to_response(self.get_context_data(form=form))
