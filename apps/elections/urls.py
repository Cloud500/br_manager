"""URL configuration for elections app."""

from django.urls import path

from apps.elections import views

app_name = 'elections'

urlpatterns = [
    path('', views.ElectionListView.as_view(), name='election_list'),
    path('<uuid:agenda_id>/add/', views.ElectionCreateView.as_view(), name='election_create'),
    path('<uuid:pk>/', views.ElectionDetailView.as_view(), name='election_detail'),
    path('<uuid:pk>/edit/', views.ElectionUpdateView.as_view(), name='election_update'),
    path('<uuid:pk>/delete/', views.ElectionDeleteView.as_view(), name='election_delete'),
    path('<uuid:pk>/publish/', views.ElectionPublishView.as_view(), name='election_publish'),
]
