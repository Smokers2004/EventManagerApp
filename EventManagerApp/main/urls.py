from django.urls import path

from . import views


urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.main_page, name="main_page"),
    path("contractors/", views.contractors, name="contractors"),
    path("contractors/add/", views.add_contractor, name="add_contractor"),
    path("contractors/<int:pk>/edit/", views.edit_contractor, name="edit_contractor"),
    path("contractors/<int:pk>/delete/", views.delete_contractor, name="delete_contractor"),
    path("events/", views.events, name="events"),
    path("events/add/", views.add_event, name="add_event"),
    path("events/<int:pk>/edit/", views.edit_event, name="edit_event"),
    path("events/<int:pk>/delete/", views.delete_event, name="delete_event"),
    path("participants/", views.participants, name="participants"),
    path("participants/add/", views.add_participant, name="add_participant"),
    path("participants/<int:pk>/edit/", views.edit_participant, name="edit_participant"),
    path("participants/<int:pk>/delete/", views.delete_participant, name="delete_participant"),
    path("tasks/", views.tasks, name="tasks"),
    path("tasks/add/", views.add_task, name="add_task"),
    path("tasks/<int:pk>/edit/", views.edit_task, name="edit_task"),
    path("tasks/<int:pk>/delete/", views.delete_task, name="delete_task"),
    path("reports/", views.reports, name="reports"),
    path("reports/generate/<int:event_id>/<str:report_type>/", views.generate_report, name="generate_report"),
    path("employees/", views.employees, name="employees"),
    path("employees/add/", views.add_employee, name="add_employee"),
]
