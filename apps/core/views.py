"""Views for the core app."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Main dashboard view for authenticated users.
    
    Displays welcome message, user profile summary, and quick links
    to meetings, protocols, and documents.
    """
    
    template_name = 'core/dashboard.html'
    login_url = '/accounts/login/'
