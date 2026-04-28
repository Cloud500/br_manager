"""URL configuration for agendas app."""

from django.urls import path

from . import views

app_name = 'agendas'

urlpatterns = [
    # Agenda item CRUD
    path('<uuid:agenda_id>/items/add/', views.AgendaItemCreateView.as_view(), name='item_create'),
    path('items/<uuid:pk>/edit/', views.AgendaItemUpdateView.as_view(), name='item_update'),
    path('items/<uuid:pk>/delete/', views.AgendaItemDeleteView.as_view(), name='item_delete'),
    
    # AJAX endpoints
    path('<uuid:agenda_id>/reorder/', views.reorder_items, name='reorder_items'),
]
