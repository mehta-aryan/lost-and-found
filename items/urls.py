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
    path('item/<int:pk>/chat/', views.start_chat, name='start_chat'),
    path('messages/', views.inbox, name='inbox'),
    path('chat/<int:pk>/', views.chat_detail, name='chat_detail'),
    path('chat/<int:pk>/send/', views.send_message, name='send_message'),
    path('chat/<int:pk>/poll/', views.poll_chat, name='poll_chat'),
    path('my-reports/', views.my_reports, name='my_reports'),
]
