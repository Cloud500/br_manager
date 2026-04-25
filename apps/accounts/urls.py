"""URL configuration for accounts app."""

from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_update'),
    path('profile/password/', views.ProfilePasswordChangeView.as_view(), name='password_change'),
    
    # 2FA URLs
    path('2fa/setup/', views.TwoFactorSetupView.as_view(), name='2fa_setup'),
    path('2fa/verify/', views.TwoFactorVerifyView.as_view(), name='2fa_verify'),
    path('2fa/recovery-codes/', views.RecoveryCodesView.as_view(), name='2fa_recovery_codes'),
    path('2fa/disable/', views.TwoFactorDisableView.as_view(), name='2fa_disable'),
    
    # User Management URLs (Admin only)
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/invite/', views.UserInviteView.as_view(), name='user_invite'),
    path('users/<uuid:pk>/edit/', views.UserUpdateView.as_view(), name='user_update'),
    path('users/<uuid:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('invitations/<uuid:pk>/delete/', views.UserInvitationDeleteView.as_view(), name='invitation_delete'),
    path('register/<str:token>/', views.UserRegistrationView.as_view(), name='register'),
]
