"""URL configuration for protocols app."""

from django.urls import path

from apps.protocols import views

app_name = "protocols"

urlpatterns = [
    path("", views.ProtocolListView.as_view(), name="protocol_list"),
    path("<uuid:pk>/", views.ProtocolDetailView.as_view(), name="protocol_detail"),
    path(
        "meetings/<uuid:meeting_pk>/items/<uuid:item_pk>/note/",
        views.ProtocolAgendaItemNoteUpdateView.as_view(),
        name="agenda_item_note_update",
    ),
]
