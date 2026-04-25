"""
Middleware for enforcing Two-Factor Authentication (2FA).

This module contains middleware that enforces 2FA setup for users
who require it based on their role or permissions.
"""

from typing import Callable

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import resolve, reverse, Resolver404


class Require2FAMiddleware:
    """
    Middleware to enforce 2FA setup for users who require it.
    
    Users who need 2FA:
    - Superusers
    - Users with system.manage_users permission
    - Users with role.manage_roles permission
    
    Exempted URLs:
    - Login/Logout pages
    - 2FA setup/verify pages
    - Static/media files
    - Admin pages (has own 2FA enforcement)
    """
    
    # URLs that are exempt from 2FA enforcement
    EXEMPT_URLS = [
        'accounts:login',
        'accounts:logout',
        'accounts:2fa_setup',
        'accounts:2fa_verify',
        'accounts:2fa_disable',
        'accounts:2fa_recovery_codes',
        'accounts:register',  # Registration flow handles 2FA separately
    ]
    
    # URL paths that are exempt (prefix matching)
    EXEMPT_PATHS = [
        '/admin/',
        '/static/',
        '/media/',
    ]
    
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """
        Initialize the middleware.
        
        Args:
            get_response: The next middleware or view in the chain
        """
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Process the request and enforce 2FA if required.
        
        Args:
            request: The HTTP request object
            
        Returns:
            HTTP response (either from next middleware or redirect to 2FA setup)
        """
        # Skip if user is not authenticated
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Skip if path is exempt
        if any(request.path.startswith(path) for path in self.EXEMPT_PATHS):
            return self.get_response(request)
        
        # Skip if URL name is exempt
        try:
            current_url = resolve(request.path).url_name
            namespace = resolve(request.path).namespace
            full_url_name = f"{namespace}:{current_url}" if namespace else current_url
            
            if full_url_name in self.EXEMPT_URLS:
                return self.get_response(request)
        except Resolver404:
            # URL doesn't resolve, let it continue (will be 404)
            pass
        
        # Check if user requires 2FA
        if self._user_requires_2fa(request.user):
            # Check if user has 2FA enabled
            if not request.user.two_factor_enabled:
                messages.warning(
                    request,
                    "Als Administrator müssen Sie die Zwei-Faktor-Authentifizierung "
                    "aktivieren, um fortfahren zu können."
                )
                return redirect('accounts:2fa_setup')
        
        return self.get_response(request)
    
    def _user_requires_2fa(self, user: 'User') -> bool:
        """
        Check if a user requires 2FA.
        
        Args:
            user: The user to check
            
        Returns:
            True if user requires 2FA, False otherwise
        """
        # Superusers always require 2FA
        if user.is_superuser:
            return True
        
        # Users with specific permissions require 2FA
        if user.has_perm('system.manage_users'):
            return True
        
        if user.has_perm('role.manage_roles'):
            return True
        
        return False
