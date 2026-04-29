"""URL configuration for resolutions app."""

from django.urls import path

from apps.resolutions import views

app_name = 'resolutions'

urlpatterns = [
    # List and detail
    path('', views.ResolutionListView.as_view(), name='resolution_list'),
    path('<uuid:pk>/', views.ResolutionDetailView.as_view(), name='resolution_detail'),
    
    # CRUD operations
    path('create/', views.ResolutionCreateView.as_view(), name='resolution_create'),
    path('<uuid:pk>/edit/', views.ResolutionUpdateView.as_view(), name='resolution_edit'),
    path('<uuid:pk>/delete/', views.ResolutionDeleteView.as_view(), name='resolution_delete'),
    
    # Status changes
    path('<uuid:pk>/status/', views.ResolutionStatusChangeView.as_view(), name='resolution_status_change'),
]
