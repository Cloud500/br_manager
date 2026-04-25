"""Views for roles app."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.roles.models import Permission, Role


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require admin permissions for role management."""
    
    def test_func(self) -> bool:
        """Check if user has admin permissions."""
        return (
            self.request.user.is_superuser or
            self.request.user.has_perm('role.view') or
            self.request.user.has_perm('system.admin')
        )


class RoleListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """
    Display list of all roles.
    
    Shows both system and custom roles with filter options.
    """
    
    model = Role
    template_name = 'roles/role_list.html'
    context_object_name = 'roles'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter roles based on search and type."""
        queryset = Role.objects.all().order_by('role_type', 'name')
        
        # Filter by type
        role_type = self.request.GET.get('type', '')
        if role_type:
            queryset = queryset.filter(role_type=role_type)
        
        # Search
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(codename__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add filters to context."""
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['role_type'] = self.request.GET.get('type', '')
        context['role_types'] = Role.ROLE_TYPE_CHOICES
        return context


class RoleCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Create new custom role."""
    
    model = Role
    template_name = 'roles/role_form.html'
    fields = ['name', 'codename', 'description', 'role_type']
    success_url = reverse_lazy('roles:role_list')
    
    def form_valid(self, form):
        """Set role as non-system role and current user as creator."""
        form.instance.is_system_role = False
        form.instance.created_by = self.request.user
        
        messages.success(
            self.request,
            f'Rolle "{form.instance.name}" wurde erstellt.'
        )
        
        return super().form_valid(form)


class RoleUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Update existing role."""
    
    model = Role
    template_name = 'roles/role_form.html'
    fields = ['name', 'description']
    success_url = reverse_lazy('roles:role_list')
    
    def get_form(self, form_class=None):
        """Prevent editing system role codename."""
        form = super().get_form(form_class)
        
        # System roles cannot change codename or type
        if self.object.is_system_role:
            form.fields['name'].disabled = True
            form.fields['name'].help_text = 'System-Rollen können nicht umbenannt werden.'
        
        return form
    
    def form_valid(self, form):
        """Save changes."""
        messages.success(
            self.request,
            f'Rolle "{self.object.name}" wurde aktualisiert.'
        )
        
        return super().form_valid(form)


class RoleDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Delete custom role (system roles cannot be deleted)."""
    
    model = Role
    template_name = 'roles/role_confirm_delete.html'
    success_url = reverse_lazy('roles:role_list')
    
    def dispatch(self, request, *args, **kwargs):
        """Check if role can be deleted."""
        self.object = self.get_object()
        
        if self.object.is_system_role:
            messages.error(
                request,
                f'System-Rolle "{self.object.name}" kann nicht gelöscht werden.'
            )
            return redirect('roles:role_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        """Delete role."""
        role_name = self.object.name
        
        messages.success(
            request,
            f'Rolle "{role_name}" wurde gelöscht.'
        )
        
        return super().post(request, *args, **kwargs)


class RolePermissionsView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Manage permissions for a role."""
    
    model = Role
    template_name = 'roles/role_permissions.html'
    fields = []  # We'll handle permissions manually
    success_url = reverse_lazy('roles:role_list')
    
    def get_context_data(self, **kwargs):
        """Add all permissions grouped by category."""
        context = super().get_context_data(**kwargs)
        
        # Group permissions by category
        permissions_by_category = {}
        for perm in Permission.objects.all().order_by('category', 'name'):
            if perm.category not in permissions_by_category:
                permissions_by_category[perm.category] = []
            permissions_by_category[perm.category].append(perm)
        
        context['permissions_by_category'] = permissions_by_category
        context['role_permissions'] = set(
            self.object.permissions.values_list('id', flat=True)
        )
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Update role permissions."""
        self.object = self.get_object()
        
        # Get selected permission IDs
        permission_ids = request.POST.getlist('permissions')
        
        # Clear existing permissions
        self.object.permissions.clear()
        
        # Add selected permissions
        for perm_id in permission_ids:
            try:
                perm = Permission.objects.get(id=perm_id)
                self.object.permissions.add(perm)
            except Permission.DoesNotExist:
                pass
        
        messages.success(
            request,
            f'Berechtigungen für Rolle "{self.object.name}" wurden aktualisiert.'
        )
        
        return redirect(self.success_url)
