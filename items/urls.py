"""
items/urls.py — URL patterns for the items app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('item/new/', views.create_item, name='create_item'),
    path('item/<int:pk>/', views.item_detail, name='item_detail'),
    path('item/<int:pk>/edit/', views.edit_item, name='edit_item'),
    path('item/<int:pk>/delete/', views.delete_item, name='delete_item'),
    path('item/<int:pk>/resolve/', views.resolve_item, name='resolve_item'),   # AJAX
    path('item/<int:pk>/claim/', views.claim_item, name='claim_item'),
    path('claim/<int:pk>/accept/', views.respond_claim, {'action': 'accept'}, name='accept_claim'),
    path('claim/<int:pk>/decline/', views.respond_claim, {'action': 'decline'}, name='decline_claim'),
    path('my-reports/', views.my_reports, name='my_reports'),
]
