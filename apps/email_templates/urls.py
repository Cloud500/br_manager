"""URL configuration for e-mail templates app."""

from django.urls import path

from apps.email_templates import views

app_name = "email_templates"

urlpatterns = [
    path("", views.EmailTemplateListView.as_view(), name="email_template_list"),
    path("<uuid:pk>/edit/", views.EmailTemplateUpdateView.as_view(), name="email_template_update"),
]
