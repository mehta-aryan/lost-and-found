"""
items/urls.py — URL patterns for the items app.

Maps URLs to view functions.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),           # Home / dashboard
    path('login/', views.login_view, name='login'),        # Landing page
    path('item/<int:pk>/', views.item_detail, name='item_detail'),
    path('item/new/', views.create_item, name='create_item'),
    path('item/<int:pk>/edit/', views.edit_item, name='edit_item'),
    path('item/<int:pk>/delete/', views.delete_item, name='delete_item'),
    path('item/<int:pk>/resolve/', views.resolve_item, name='resolve_item'),  # AJAX
    path('my-reports/', views.my_reports, name='my_reports'),
]

