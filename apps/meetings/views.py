"""Views for meetings app."""

from datetime import date
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView
from django.http import JsonResponse

from apps.meetings.forms import MeetingFilterForm, MeetingForm, MeetingSendInvitationForm
from apps.meetings.mixins import MeetingCreatePermissionMixin, MeetingPermissionMixin
from apps.meetings.models import Meeting


class MeetingListView(LoginRequiredMixin, ListView):
    """List view for meetings with filtering."""
    
    model = Meeting
    template_name = 'meetings/meeting_list.html'
    context_object_name = 'meetings'
    paginate_by = 20
    
    def get_queryset(self):
        """Get filtered queryset based on filter form."""
        queryset = Meeting.objects.select_related(
            'committee', 'chair', 'clerk', 'created_by'
        ).all()
        
        # Apply filters from MeetingFilterForm
        committee = self.request.GET.get('committee')
        status = self.request.GET.get('status')
        meeting_type = self.request.GET.get('meeting_type')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if committee:
            queryset = queryset.filter(committee_id=committee)
        if status:
            queryset = queryset.filter(status=status)
        if meeting_type:
            queryset = queryset.filter(meeting_type=meeting_type)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        return queryset.order_by('-date', '-start_time')
    
    def get_context_data(self, **kwargs):
        """Add filter form and grouped meetings to context."""
        context = super().get_context_data(**kwargs)
        
        # Add filter form
        context['filter_form'] = MeetingFilterForm(self.request.GET)
        
        # Group meetings
        today = date.today()
        
        context['upcoming_meetings'] = self.get_queryset().filter(date__gte=today)
        context['past_meetings'] = self.get_queryset().filter(date__lt=today)
        
        return context


class MeetingDetailView(LoginRequiredMixin, MeetingPermissionMixin, DetailView):
    """Detail view for a single meeting."""
    
    model = Meeting
    template_name = 'meetings/meeting_detail.html'
    context_object_name = 'meeting'
    permission_required = 'view'
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        
        # TODO: Add agenda items count when agendas app is implemented
        # context['agenda_items_count'] = self.object.agenda_items.count()
        
        # TODO: Add attendance statistics when attendance app is implemented
        # context['attendees_count'] = self.object.attendance_records.filter(status='PRESENT').count()
        
        return context


class MeetingCreateView(LoginRequiredMixin, MeetingCreatePermissionMixin, CreateView):
    """Create view for meetings."""
    
    model = Meeting
    template_name = 'meetings/meeting_form.html'
    form_class = MeetingForm
    
    def get_context_data(self, **kwargs):
        """Add committee_members to context."""
        context = super().get_context_data(**kwargs)
        if hasattr(context['form'], 'chair_candidates'):
            context['chair_candidates'] = context['form'].chair_candidates
        if hasattr(context['form'], 'clerk_candidates'):
            context['clerk_candidates'] = context['form'].clerk_candidates
        return context
    
    def form_valid(self, form):
        """Set created_by and status on new meeting."""
        form.instance.created_by = self.request.user
        form.instance.status = 'DRAFT'
        messages.success(
            self.request,
            f'Sitzung "{form.instance.title}" wurde erstellt.'
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to meeting detail page."""
        return reverse('meetings:meeting_detail', kwargs={'pk': self.object.pk})


class MeetingUpdateView(LoginRequiredMixin, MeetingPermissionMixin, UpdateView):
    """Update view for meetings."""
    
    model = Meeting
    template_name = 'meetings/meeting_form.html'
    form_class = MeetingForm
    permission_required = 'edit'
    
    def get_context_data(self, **kwargs):
        """Add committee_members to context."""
        context = super().get_context_data(**kwargs)
        if hasattr(context['form'], 'chair_candidates'):
            context['chair_candidates'] = context['form'].chair_candidates
        if hasattr(context['form'], 'clerk_candidates'):
            context['clerk_candidates'] = context['form'].clerk_candidates
        return context
    
    def dispatch(self, request, *args, **kwargs):
        """Check if meeting is editable before allowing update."""
        meeting = self.get_object()
        if not meeting.is_editable:
            messages.error(
                request,
                'Sitzung kann nicht mehr bearbeitet werden (Status ist nicht DRAFT).'
            )
            return redirect('meetings:meeting_detail', pk=meeting.pk)
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """Show success message on update."""
        messages.success(
            self.request,
            f'Sitzung "{form.instance.title}" wurde aktualisiert.'
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to meeting detail page."""
        return reverse('meetings:meeting_detail', kwargs={'pk': self.object.pk})


class MeetingDeleteView(LoginRequiredMixin, MeetingPermissionMixin, DeleteView):
    """Delete view for meetings."""
    
    model = Meeting
    template_name = 'meetings/meeting_confirm_delete.html'
    permission_required = 'delete'
    success_url = reverse_lazy('meetings:meeting_list')
    
    def dispatch(self, request, *args, **kwargs):
        """Check if meeting is deletable before allowing deletion."""
        meeting = self.get_object()
        if not meeting.is_deletable:
            messages.error(
                request,
                'Nur Entwürfe können gelöscht werden.'
            )
            return redirect('meetings:meeting_detail', pk=meeting.pk)
        return super().dispatch(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        """Show success message on deletion."""
        meeting = self.get_object()
        meeting_title = meeting.title
        response = super().delete(request, *args, **kwargs)
        messages.success(
            request,
            f'Sitzung "{meeting_title}" wurde gelöscht.'
        )
        return response


class MeetingSendInvitationView(LoginRequiredMixin, MeetingPermissionMixin, FormView):
    """View for sending meeting invitations."""
    
    template_name = 'meetings/meeting_send_invitation.html'
    form_class = MeetingSendInvitationForm
    permission_required = 'send_invitation'
    
    def get_meeting(self):
        """Get meeting object from URL."""
        if not hasattr(self, '_meeting'):
            self._meeting = Meeting.objects.get(pk=self.kwargs['pk'])
        return self._meeting
    
    def get_object(self):
        """Get meeting object for permission mixin."""
        return self.get_meeting()
    
    def dispatch(self, request, *args, **kwargs):
        """Check if invitation can be sent before displaying form."""
        meeting = self.get_meeting()
        if not meeting.can_send_invitation:
            messages.error(
                request,
                'Einladung kann nur für Entwürfe versendet werden.'
            )
            return redirect('meetings:meeting_detail', pk=meeting.pk)
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Add meeting to context."""
        context = super().get_context_data(**kwargs)
        context['meeting'] = self.get_meeting()
        return context
    
    def form_valid(self, form):
        """Send invitation and update meeting status."""
        meeting = self.get_meeting()
        
        # TODO: Send email invitations when email functionality is implemented
        # message = form.cleaned_data.get('message', '')
        # include_agenda = form.cleaned_data.get('include_agenda', True)
        # send_meeting_invitations(meeting, message, include_agenda)
        
        # Update meeting status
        meeting.status = 'SENT'
        meeting.sent_at = timezone.now()
        meeting.save()
        
        messages.success(
            self.request,
            f'Einladung für "{meeting.title}" wurde versendet.'
        )
        return redirect('meetings:meeting_detail', pk=meeting.pk)


class MeetingStartView(LoginRequiredMixin, MeetingPermissionMixin, DetailView):
    """View for starting a meeting."""
    
    model = Meeting
    permission_required = 'start'
    
    def get(self, request, *args, **kwargs):
        """Handle GET request (should not be used, redirect to detail)."""
        meeting = self.get_object()
        return redirect('meetings:meeting_detail', pk=meeting.pk)
    
    def post(self, request, *args, **kwargs):
        """Start the meeting."""
        meeting = self.get_object()
        
        # Check if meeting can be started
        if meeting.status != 'SENT':
            messages.error(
                request,
                'Sitzung kann nur aus dem Status SENT gestartet werden.'
            )
            return redirect('meetings:meeting_detail', pk=meeting.pk)
        
        # Update meeting status
        meeting.status = 'IN_PROGRESS'
        meeting.actual_start_time = timezone.now().time()
        meeting.save()
        
        messages.success(
            request,
            f'Sitzung "{meeting.title}" wurde gestartet.'
        )
        return redirect('meetings:meeting_detail', pk=meeting.pk)


class MeetingCompleteView(LoginRequiredMixin, MeetingPermissionMixin, DetailView):
    """View for completing a meeting."""
    
    model = Meeting
    permission_required = 'complete'
    
    def get(self, request, *args, **kwargs):
        """Handle GET request (should not be used, redirect to detail)."""
        meeting = self.get_object()
        return redirect('meetings:meeting_detail', pk=meeting.pk)
    
    def post(self, request, *args, **kwargs):
        """Complete the meeting."""
        meeting = self.get_object()
        
        # Check if meeting can be completed
        if not meeting.can_complete:
            messages.error(
                request,
                'Sitzung kann nur aus dem Status IN_PROGRESS abgeschlossen werden.'
            )
            return redirect('meetings:meeting_detail', pk=meeting.pk)
        
        # Update meeting status
        meeting.status = 'COMPLETED'
        meeting.actual_end_time = timezone.now().time()
        meeting.save()
        
        messages.success(
            request,
            f'Sitzung "{meeting.title}" wurde abgeschlossen.'
        )
        return redirect('meetings:meeting_detail', pk=meeting.pk)


def get_committee_members_ajax(request, committee_id):
    """AJAX view to get committee members for dropdowns."""
    try:
        from apps.committees.models import Committee, Membership
        from apps.roles.models import Permission
        
        committee = get_object_or_404(Committee, pk=committee_id)
        
        # Get permissions
        is_chair_perm = Permission.objects.filter(codename='meeting.is_chair').first()
        is_clerk_perm = Permission.objects.filter(codename='meeting.is_clerk').first()
        
        # Get active memberships ordered by role sort_order
        memberships = Membership.objects.filter(
            committee=committee,
            is_active=True
        ).select_related('user', 'user__profile', 'role').prefetch_related('role__permissions').order_by('role__sort_order', 'user__last_name', 'user__first_name')
        
        # Build separate lists for chair and clerk
        chair_candidates = []
        clerk_candidates = []
        
        for m in memberships:
            member_data = {
                'id': m.user.id,
                'name': m.user.get_full_name(),
                'role': m.role.name if m.role else '',
            }
            
            # Check if role has is_chair permission
            if m.role and is_chair_perm and m.role.permissions.filter(id=is_chair_perm.id).exists():
                chair_candidates.append(member_data)
            
            # Check if role has is_clerk permission
            if m.role and is_clerk_perm and m.role.permissions.filter(id=is_clerk_perm.id).exists():
                clerk_candidates.append(member_data)
        
        return JsonResponse({
            'chair_candidates': chair_candidates,
            'clerk_candidates': clerk_candidates
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
