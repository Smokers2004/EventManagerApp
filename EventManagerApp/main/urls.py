from django.contrib import admin
from django.urls import path

from . import views


urlpatterns = [
    path('', views.main_page, name='main_page'),
    path('contractors', views.contractors, name='contractors'),
    path('events', views.events, name='events'),
    path('tasks', views.events, name='tasks'),
    path('reports', views.events, name='reports'),
    path('add_contractor', views.add_contractor, name='add_contractor'),
    path('delete_contractor/<int:pk>/', views.delete_contractor, name='delete_contractor'),
    path('login', views.login_view, name='login'),
]
