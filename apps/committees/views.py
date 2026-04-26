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
        """
        Return active committees based on user permissions.
        
        - If user has 'committee.view_all': Show all committees
        - Otherwise: Only show committees where user is a member (+ children)
        """
        base_queryset = Committee.objects.filter(is_active=True).select_related('parent')
        
        # Check if user has view_all permission
        if self.has_view_all_permission():
            # User can see all committees
            return base_queryset.order_by('committee_type', 'name')
        else:
            # User can only see their own committees and children
            allowed_committees = self.get_user_committees_with_children()
            return base_queryset.filter(
                id__in=allowed_committees.values_list('id', flat=True)
            ).order_by('committee_type', 'name')
    
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
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user has access to this specific committee."""
        # First run parent dispatch (checks login + basic permission)
        response = super().dispatch(request, *args, **kwargs)
        
        # If user is superuser or has view_all, allow access
        if request.user.is_superuser or self.has_view_all_permission():
            return response
        
        # Otherwise, check if committee is in user's allowed committees
        committee = self.get_object()
        allowed_committees = self.get_user_committees_with_children()
        
        if committee not in allowed_committees:
            # User doesn't have access to this committee
            messages.error(
                request,
                f'Sie haben keine Berechtigung, das Gremium "{committee.name}" anzuzeigen.'
            )
            return redirect('committees:committee_list')
        
        return response
    
    def get_context_data(self, **kwargs) -> dict:
        """Add member statistics to context."""
        context = super().get_context_data(**kwargs)
        
        committee = self.object
        
        context['active_members_count'] = committee.get_active_members().count()
        context['substitute_count'] = committee.get_active_substitutes().count()
        context['external_count'] = committee.get_external_members().count()
        
        # Show all regular and external members on overview
        context['regular_members'] = committee.get_active_members()
        context['external_members'] = committee.get_external_members()
        
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
        """Return substitute memberships for committee."""
        committee = self.get_committee()
        return Membership.objects.filter(
            committee=committee,
            member_type='SUBSTITUTE',
            is_active=True
        ).select_related('user', 'role')
    
    def get_context_data(self, **kwargs) -> dict:
        """Add substitute memberships to context with fair rotation order."""
        context = super().get_context_data(**kwargs)
        
        # Get all substitutes
        all_substitutes = list(self.get_queryset())
        
        # Group by election list and find max position per list to determine current state
        lists_data = {}
        for sub in all_substitutes:
            list_name = sub.election_list_name or 'Ohne Liste'
            if list_name not in lists_data:
                lists_data[list_name] = {
                    'members': [],
                    'current_max_position': 0
                }
            lists_data[list_name]['members'].append(sub)
        
        # Sort members within each list by position
        for list_name, data in lists_data.items():
            data['members'].sort(key=lambda x: (
                x.election_list_position if x.election_list_position else float('inf'),
                x.user.last_name
            ))
        
        # Find current highest position per list (those already in committee)
        committee = self.get_committee()
        current_members = Membership.objects.filter(
            committee=committee,
            member_type='REGULAR',
            is_active=True
        ).select_related('user')
        
        for member in current_members:
            list_name = member.election_list_name or 'Ohne Liste'
            if list_name in lists_data and member.election_list_position:
                if member.election_list_position > lists_data[list_name]['current_max_position']:
                    lists_data[list_name]['current_max_position'] = member.election_list_position
        
        # Build rotation order: alternating next candidate from each list
        sorted_substitutes = []
        list_names = sorted(lists_data.keys())
        list_indices = {name: 0 for name in list_names}
        
        # Continue until all substitutes are added
        while len(sorted_substitutes) < len(all_substitutes):
            added_in_round = False
            
            for list_name in list_names:
                data = lists_data[list_name]
                idx = list_indices[list_name]
                
                # Find next substitute from this list after current_max_position
                while idx < len(data['members']):
                    sub = data['members'][idx]
                    # Only add if position is after current max (i.e., not already in committee)
                    if sub.election_list_position and sub.election_list_position > data['current_max_position']:
                        sorted_substitutes.append(sub)
                        list_indices[list_name] = idx + 1
                        added_in_round = True
                        break
                    idx += 1
                    list_indices[list_name] = idx
            
            # If no member was added in this round, we're done
            if not added_in_round:
                break
        
        # Add any remaining substitutes without proper position at the end
        remaining = [s for s in all_substitutes if s not in sorted_substitutes]
        sorted_substitutes.extend(sorted(remaining, key=lambda x: x.user.last_name))
        
        context['substitute_members'] = sorted_substitutes
        
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
        """Redirect to committee detail."""
        messages.success(
            self.request,
            f'Mitgliedschaft von {self.object.user.get_full_name()} wurde aktualisiert.'
        )
        return reverse(
            'committees:committee_detail',
            kwargs={'pk': self.get_committee().pk}
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
