"""URL configuration for meetings app."""

from django.urls import path

from apps.meetings import views

app_name = 'meetings'

urlpatterns = [
    # AJAX endpoints
    path('ajax/committee/<uuid:committee_id>/members/', views.get_committee_members_ajax, name='ajax_committee_members'),
    
    # List and filter
    path('', views.MeetingListView.as_view(), name='meeting_list'),
    
    # CRUD operations
    path('create/', views.MeetingCreateView.as_view(), name='meeting_create'),
    path('<uuid:pk>/', views.MeetingDetailView.as_view(), name='meeting_detail'),
    path('<uuid:pk>/edit/', views.MeetingUpdateView.as_view(), name='meeting_edit'),
    path('<uuid:pk>/delete/', views.MeetingDeleteView.as_view(), name='meeting_delete'),
    
    # Workflow actions
    path('<uuid:pk>/send-invitation/', views.MeetingSendInvitationView.as_view(), name='meeting_send_invitation'),
    path('<uuid:pk>/start/', views.MeetingStartView.as_view(), name='meeting_start'),
    path('<uuid:pk>/complete/', views.MeetingCompleteView.as_view(), name='meeting_complete'),
]
