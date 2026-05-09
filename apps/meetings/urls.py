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
    path('<uuid:pk>/live/', views.MeetingLiveView.as_view(), name='meeting_live'),
    path('<uuid:pk>/live/reconfirm/', views.MeetingReconfirmView.as_view(), name='meeting_reconfirm'),
    path('<uuid:pk>/live/status/', views.MeetingLiveStatusPartialView.as_view(), name='meeting_live_status'),
    path('<uuid:pk>/live/agenda/', views.MeetingLiveAgendaPartialView.as_view(), name='meeting_live_agenda'),
    path('<uuid:pk>/live/participants/', views.MeetingLiveParticipantsPartialView.as_view(), name='meeting_live_participants'),
    path('<uuid:pk>/live/version/', views.MeetingLiveVersionView.as_view(), name='meeting_live_version'),
    path('<uuid:pk>/live/events/', views.MeetingLiveEventsView.as_view(), name='meeting_live_events'),
    path('<uuid:pk>/live/self/left/', views.MeetingSelfLeftView.as_view(), name='meeting_self_left'),
    path('<uuid:pk>/live/self/returned/', views.MeetingSelfReturnedView.as_view(), name='meeting_self_returned'),
    path('<uuid:pk>/live/current/<uuid:item_pk>/', views.MeetingSetCurrentAgendaItemView.as_view(), name='meeting_set_current_item'),
    path('<uuid:pk>/live/resolution/<uuid:item_pk>/result/', views.MeetingRecordResolutionResultView.as_view(), name='meeting_record_resolution_result'),
    path('<uuid:pk>/live/election/<uuid:item_pk>/result/', views.MeetingRecordElectionResultView.as_view(), name='meeting_record_election_result'),
    
    # Workflow actions
    path('<uuid:pk>/send-invitation/', views.MeetingSendInvitationView.as_view(), name='meeting_send_invitation'),
    path('<uuid:pk>/reset-to-draft/', views.MeetingResetToDraftView.as_view(), name='meeting_reset_to_draft'),
    path('<uuid:pk>/start/', views.MeetingStartView.as_view(), name='meeting_start'),
    path('<uuid:pk>/complete/', views.MeetingCompleteView.as_view(), name='meeting_complete'),
]
