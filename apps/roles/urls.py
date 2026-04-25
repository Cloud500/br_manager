"""URL configuration for roles app."""

from django.urls import path

from . import views

app_name = 'roles'

urlpatterns = [
    path('', views.RoleListView.as_view(), name='role_list'),
    path('create/', views.RoleCreateView.as_view(), name='role_create'),
    path('<uuid:pk>/edit/', views.RoleUpdateView.as_view(), name='role_update'),
    path('<uuid:pk>/delete/', views.RoleDeleteView.as_view(), name='role_delete'),
    path('<uuid:pk>/permissions/', views.RolePermissionsView.as_view(), name='role_permissions'),
]
