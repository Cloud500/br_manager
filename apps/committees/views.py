"""Views for committees app."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, QuerySet
from django.http import Http404
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    View,
)

from apps.committees.forms import CommitteeForm, CommitteeUpdateForm, MembershipForm
from apps.committees.mixins import CommitteeContextMixin, CommitteePermissionMixin
from apps.committees.models import Committee, Membership
from apps.committees.seat_distribution import get_election_seat_distribution


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
        context['show_seat_distribution_link'] = committee.committee_type == 'MAIN'
        
        return context


class SeatDistributionOverviewView(LoginRequiredMixin, CommitteePermissionMixin, ListView):
    """Display election seat distribution cards for visible committees."""

    model = Committee
    template_name = 'committees/seat_distribution_overview.html'
    context_object_name = 'committees'
    required_permission = 'committee.view_members'

    def get_queryset(self) -> QuerySet:
        """Return active main committees visible to the current user."""
        base_queryset = Committee.objects.filter(
            is_active=True,
            committee_type='MAIN',
        ).select_related('parent')
        if self.has_view_all_permission():
            return base_queryset.order_by('name')
        allowed_committees = self.get_user_committees_with_children()
        return base_queryset.filter(
            id__in=allowed_committees.values_list('id', flat=True)
        ).order_by('name')

    def get_context_data(self, **kwargs) -> dict:
        """Add precomputed seat distributions for rendering."""
        context = super().get_context_data(**kwargs)
        context['committee_seat_distributions'] = [
            {
                'committee': committee,
                'groups': get_election_seat_distribution(committee),
            }
            for committee in context['committees']
        ]
        return context


class CommitteeSeatDistributionView(
    LoginRequiredMixin,
    CommitteePermissionMixin,
    CommitteeContextMixin,
    DetailView,
):
    """Display election seat distribution for one committee."""

    model = Committee
    template_name = 'committees/seat_distribution_detail.html'
    context_object_name = 'committee'
    required_permission = 'committee.view_members'

    def get_object(self, queryset=None):
        """Return main committee from the committee_id URL parameter."""
        committee = self.get_committee()
        if committee.committee_type != 'MAIN':
            raise Http404('Sitzverteilungen sind nur für Hauptgremien verfügbar.')
        return committee

    def get_context_data(self, **kwargs) -> dict:
        """Add election seat distribution rows."""
        context = super().get_context_data(**kwargs)
        context['election_seat_distribution'] = get_election_seat_distribution(self.object)
        return context


class CommitteeCreateView(LoginRequiredMixin, CommitteePermissionMixin, CreateView):
    """Create new committee."""
    
    model = Committee
    form_class = CommitteeForm
    template_name = 'committees/committee_form.html'
    required_permission = 'committee.create'
    
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
    form_class = CommitteeUpdateForm
    template_name = 'committees/committee_form.html'
    required_permission = 'committee.edit'
    
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
        """Redirect to committee detail."""
        return reverse(
            'committees:committee_detail',
            kwargs={'pk': self.get_committee().pk}
        )


class MemberReplaceView(
    LoginRequiredMixin,
    CommitteePermissionMixin,
    CommitteeContextMixin,
    View
):
    """Replace a member with a substitute member."""
    
    required_permission = 'committee.manage_members'
    template_name = 'committees/member_replace.html'
    
    def get_next_substitute(self, membership: Membership) -> Membership | None:
        """
        Get the next substitute member based on election list, position, and minority gender quota.
        
        Returns the substitute with the lowest position from the same list
        that is higher than the current member's position.
        Prioritizes minority gender if quota is not met.
        """
        committee = self.get_committee()
        
        # Get all substitutes from the same election list
        base_substitutes = Membership.objects.filter(
            committee=committee,
            member_type='SUBSTITUTE',
            is_active=True,
            election_list_name=membership.election_list_name
        ).exclude(
            user=membership.user
        ).select_related('user', 'role')
        
        if not base_substitutes.exists():
            return None
        
        # Find current max position from regular members (excluding the one being removed)
        from django.db.models import Max
        result = Membership.objects.filter(
            committee=committee,
            member_type='REGULAR',
            is_active=True,
            election_list_name=membership.election_list_name
        ).exclude(
            user=membership.user
        ).aggregate(
            max_pos=Max('election_list_position')
        )
        current_max_position = result.get('max_pos') or 0
        
        # Filter substitutes with position higher than current max
        eligible_substitutes = [
            sub for sub in base_substitutes
            if sub.election_list_position and sub.election_list_position > current_max_position
        ]
        
        if not eligible_substitutes:
            # If no position-based match, use all substitutes
            eligible_substitutes = list(base_substitutes)
        
        # Check minority gender quota
        if committee.minority_gender and committee.minority_min_count:
            # Count current minority gender members (excluding the one being removed)
            current_minority_count = Membership.objects.filter(
                committee=committee,
                member_type='REGULAR',
                is_active=True,
                user__gender=committee.minority_gender
            ).exclude(
                user=membership.user
            ).count()
            
            # If below quota, prioritize minority gender substitutes
            if current_minority_count < committee.minority_min_count:
                # Try to find minority gender substitute first
                minority_subs = [
                    sub for sub in eligible_substitutes
                    if sub.user.gender == committee.minority_gender
                ]
                
                if minority_subs:
                    # Sort by position and votes
                    minority_subs.sort(key=lambda x: (
                        x.election_list_position if x.election_list_position else float('inf'),
                        -(x.election_votes if x.election_votes else 0)
                    ))
                    return minority_subs[0]
        
        # Normal sorting: by position, then by votes
        eligible_substitutes.sort(key=lambda x: (
            x.election_list_position if x.election_list_position else float('inf'),
            -(x.election_votes if x.election_votes else 0)
        ))
        
        return eligible_substitutes[0] if eligible_substitutes else None
    
    def get_sorted_substitutes(self, membership: Membership) -> list:
        """
        Get substitutes sorted in fair rotation order.
        
        Same logic as MemberListView - alternates next candidate from each list
        respecting current positions in committee.
        """
        committee = self.get_committee()
        
        # Get all substitutes
        all_substitutes = list(Membership.objects.filter(
            committee=committee,
            member_type='SUBSTITUTE',
            is_active=True
        ).select_related('user', 'role'))
        
        if not all_substitutes:
            return []
        
        # Group by election list
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
        
        # Find current highest position per list (excluding the member being removed)
        current_members = Membership.objects.filter(
            committee=committee,
            member_type='REGULAR',
            is_active=True
        ).exclude(
            user=membership.user
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
                    # Only add if position is after current max
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
        
        return sorted_substitutes
    
    def get(self, request, *args, **kwargs):
        """Display replacement form."""
        membership = get_object_or_404(
            Membership,
            pk=kwargs.get('pk'),
            committee=self.get_committee()
        )
        
        # Only regular members can be replaced
        if membership.member_type != 'REGULAR':
            messages.error(request, 'Nur reguläre Mitglieder können ersetzt werden.')
            return redirect('committees:committee_detail', pk=self.get_committee().pk)
        
        # Get suggested substitute
        suggested_substitute = self.get_next_substitute(membership)
        
        # Get all available substitutes in fair rotation order
        all_substitutes = self.get_sorted_substitutes(membership)
        
        # Calculate minority gender status
        committee = self.get_committee()
        minority_info = None
        if committee.minority_gender and committee.minority_min_count:
            current_minority_count = Membership.objects.filter(
                committee=committee,
                member_type='REGULAR',
                is_active=True,
                user__gender=committee.minority_gender
            ).exclude(
                user=membership.user
            ).count()
            
            minority_info = {
                'gender': committee.minority_gender,
                'gender_display': committee.get_minority_gender_display(),
                'current_count': current_minority_count,
                'required_count': committee.minority_min_count,
                'quota_met': current_minority_count >= committee.minority_min_count
            }
        
        context = {
            'committee': self.get_committee(),
            'membership': membership,
            'suggested_substitute': suggested_substitute,
            'all_substitutes': all_substitutes,
            'minority_info': minority_info,
        }
        if committee.committee_type == 'MAIN':
            context['election_seat_distribution'] = get_election_seat_distribution(committee)
        
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        """Process replacement."""
        membership = get_object_or_404(
            Membership,
            pk=kwargs.get('pk'),
            committee=self.get_committee()
        )
        
        action = request.POST.get('action')
        
        if action == 'remove_only':
            # Just remove the member without replacement
            user_name = membership.user.get_full_name()
            membership.delete(user=request.user)
            
            messages.success(
                request,
                f'{user_name} wurde aus dem Gremium entfernt.'
            )
        
        elif action == 'replace':
            # Replace with selected substitute
            substitute_id = request.POST.get('substitute_id')
            
            if not substitute_id:
                messages.error(request, 'Bitte wählen Sie ein Ersatzmitglied aus.')
                return redirect('committees:member_replace', committee_id=self.get_committee().pk, pk=membership.pk)
            
            substitute = get_object_or_404(
                Membership,
                pk=substitute_id,
                committee=self.get_committee(),
                member_type='SUBSTITUTE'
            )
            
            # Store names for message
            old_name = membership.user.get_full_name()
            new_name = substitute.user.get_full_name()
            
            # Remove old member
            membership.delete(user=request.user)
            
            # Promote substitute to regular
            substitute.member_type = 'REGULAR'
            substitute.save()
            
            messages.success(
                request,
                f'{old_name} wurde durch {new_name} ersetzt.'
            )
        
        return redirect('committees:committee_detail', pk=self.get_committee().pk)


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
