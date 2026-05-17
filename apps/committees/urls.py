"""URL configuration for committees app."""

from django.urls import path

from apps.committees import views

app_name = 'committees'

urlpatterns = [
    path('seat-distribution/', views.SeatDistributionOverviewView.as_view(), name='seat_distribution_overview'),
    path('<uuid:committee_id>/seat-distribution/', views.CommitteeSeatDistributionView.as_view(), name='seat_distribution'),
    
    # Committee URLs
    path('', views.CommitteeListView.as_view(), name='committee_list'),
    path('create/', views.CommitteeCreateView.as_view(), name='committee_create'),
    path('<uuid:pk>/', views.CommitteeDetailView.as_view(), name='committee_detail'),
    path('<uuid:pk>/edit/', views.CommitteeUpdateView.as_view(), name='committee_update'),
    path('<uuid:pk>/delete/', views.CommitteeDeleteView.as_view(), name='committee_delete'),
    
    # Member URLs
    path('<uuid:committee_id>/members/', views.MemberListView.as_view(), name='member_list'),
    path('<uuid:committee_id>/members/add/', views.MemberAddView.as_view(), name='member_add'),
    path('<uuid:committee_id>/members/<uuid:pk>/edit/', views.MemberEditView.as_view(), name='member_edit'),
    path('<uuid:committee_id>/members/<uuid:pk>/remove/', views.MemberRemoveView.as_view(), name='member_remove'),
    path('<uuid:committee_id>/members/<uuid:pk>/replace/', views.MemberReplaceView.as_view(), name='member_replace'),
    
    # Substitute URLs
    path('<uuid:committee_id>/substitutes/', views.SubstituteListView.as_view(), name='substitute_list'),
    
    # HTMX URLs
    path('<uuid:committee_id>/members/search/', views.MemberSearchView.as_view(), name='member_search'),
    path('<uuid:committee_id>/members/<uuid:pk>/inline-edit/', views.MemberInlineEditView.as_view(), name='member_inline_edit'),
]
