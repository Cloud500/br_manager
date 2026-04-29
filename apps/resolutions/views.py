"""Views for resolutions app."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)

from apps.committees.models import Committee, Membership
from apps.resolutions.forms import ResolutionForm, ResolutionStatusForm
from apps.resolutions.models import Resolution


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
            self.get_user_permission(resolution, 'resolution.propose')
        )
        context['can_withdraw'] = (
            resolution.can_be_withdrawn and 
            self.get_user_permission(resolution, 'resolution.propose')
        )
        
        return context


class ResolutionCreateView(LoginRequiredMixin, CreateView):
    """Create view for resolution."""
    
    model = Resolution
    form_class = ResolutionForm
    template_name = 'resolutions/resolution_form.html'
    
    def get_form_kwargs(self):
        """Pass user to form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        """Set created_by and validate permissions."""
        resolution = form.save(commit=False)
        resolution.created_by = self.request.user
        
        # Validate user can create for this committee
        if not Resolution.user_can_create(self.request.user, resolution.committee):
            messages.error(
                self.request,
                'Sie haben keine Berechtigung Beschlüsse für dieses Gremium zu erstellen'
            )
            return self.form_invalid(form)
        
        resolution.save()
        self.object = resolution
        
        messages.success(
            self.request,
            f'Beschluss "{resolution.proposal[:50]}..." wurde erstellt'
        )
        
        return HttpResponseRedirect(self.get_success_url())
    
    def get_success_url(self):
        """Redirect to resolution detail."""
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
            f'Beschluss wurde aktualisiert'
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
        if not self.get_user_permission(resolution, 'resolution.propose'):
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
