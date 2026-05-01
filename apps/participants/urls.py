"""URL routes for participants app."""

from django.urls import path

from apps.participants import views

app_name = "participants"

urlpatterns = [
    path(
        "meetings/<uuid:meeting_pk>/add/",
        views.ParticipantAddView.as_view(),
        name="participant_add",
    ),
    path(
        "<uuid:pk>/absent/",
        views.ParticipantMarkAbsentView.as_view(),
        name="participant_mark_absent",
    ),
    path(
        "<uuid:pk>/remove-substitute/",
        views.ParticipantRemoveSubstituteView.as_view(),
        name="participant_remove_substitute",
    ),
    path(
        "<uuid:pk>/remove-absence/",
        views.ParticipantRemoveAbsenceView.as_view(),
        name="participant_remove_absence",
    ),
]
