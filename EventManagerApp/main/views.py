from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .decorators import role_required
from .forms import (
    ContractorForm,
    EmployeeCreationForm,
    EventForm,
    LoginUserForm,
    ParticipantForm,
    TaskForm,
)
from .models import Contractor, Employee, Event, Order, Participant, Report, Task


def _fetch_event_employee_map(event_ids):
    if not event_ids:
        return {}

    placeholders = ", ".join(["%s"] * len(event_ids))
    sql = f"""
        SELECT ee.event_id, e.fullname
        FROM employee_on_event ee
        JOIN employee e ON e.e_id = ee.e_id
        WHERE ee.event_id IN ({placeholders})
        ORDER BY e.fullname
    """
    result = {event_id: [] for event_id in event_ids}
    with connection.cursor() as cursor:
        cursor.execute(sql, event_ids)
        for event_id, fullname in cursor.fetchall():
            result.setdefault(event_id, []).append(fullname)
    return result


def _fetch_selected_employee_ids(event_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT e_id FROM employee_on_event WHERE event_id = %s", [event_id])
        return [row[0] for row in cursor.fetchall()]


def _sync_event_employees(event_id, employee_ids):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM employee_on_event WHERE event_id = %s", [event_id])
        for employee_id in employee_ids:
            cursor.execute(
                "INSERT INTO employee_on_event (e_id, event_id) VALUES (%s, %s)",
                [employee_id, event_id],
            )


def _build_report_content(event, report_type):
    participants = Participant.objects.filter(event=event).count()
    tasks = Task.objects.filter(event=event).select_related("e", "operator")
    orders = Order.objects.filter(event=event).select_related("c")
    employees = _fetch_event_employee_map([event.pk]).get(event.pk, [])

    lines = [
        f"Мероприятие: {event.title}",
        f"Статус: {event.status}",
        f"Дата и время: {event.time or 'Не указано'}",
        f"Площадка: {event.p.address if event.p else 'Не указана'}",
        "",
    ]

    if report_type == Report.TYPE_EVENT:
        lines.extend(
            [
                "Сводная информация",
                f"Описание: {event.description or 'Нет описания'}",
                f"Ответственные сотрудники: {', '.join(employees) if employees else 'Не назначены'}",
                f"Количество участников: {participants}",
                f"Количество задач: {tasks.count()}",
                "",
                "Задачи",
            ]
        )
        if tasks:
            for task in tasks:
                lines.append(
                    f"- {task.title} | {task.status} | "
                    f"Ответственный: {task.e or 'Не назначен'} | Срок: {task.deadline or 'Не указан'}"
                )
        else:
            lines.append("- Задачи отсутствуют")
    else:
        total = 0
        lines.extend(["Расходы по мероприятию"])
        if orders:
            for order in orders:
                amount = order.quantity * order.price
                total += amount
                lines.append(
                    f"- {order.product} | {order.quantity} x {order.price:.2f} = {amount:.2f} | "
                    f"Контрагент: {order.c.name} | Дата: {order.date}"
                )
        else:
            lines.append("- Закупки отсутствуют")
        lines.extend(["", f"Итого затрат: {total:.2f}"])

    return "\n".join(lines)


def login_view(request):
    if request.user.is_authenticated:
        return redirect("main_page")

    form = LoginUserForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            login=form.cleaned_data["login"],
            password=form.cleaned_data["password"],
        )
        if user is not None and user.is_active:
            login(request, user)
            return redirect("main_page")
        messages.error(request, "Неверный логин или пароль.")

    return render(request, "main/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def main_page(request):
    events_qs = Event.objects.select_related("p")
    recent_events = list(events_qs[:5])
    employee_map = _fetch_event_employee_map([event.pk for event in recent_events])
    for event in recent_events:
        event.employee_names = employee_map.get(event.pk, [])

    context = {
        "events_count": events_qs.count(),
        "participants_count": Participant.objects.count(),
        "tasks_count": Task.objects.count(),
        "contractors_count": Contractor.objects.count(),
        "reports_count": Report.objects.count(),
        "recent_events": recent_events,
        "recent_tasks": Task.objects.select_related("event", "e")[:5],
    }
    return render(request, "main/mainpage.html", context)


@login_required
def contractors(request):
    query = request.GET.get("search", "").strip()
    object_list = Contractor.objects.all()
    if query:
        object_list = object_list.filter(Q(name__icontains=query) | Q(fullname__icontains=query))

    return render(
        request,
        "main/contractors.html",
        {
            "counterparties": object_list,
            "query": query,
        },
    )


@login_required
def add_contractor(request):
    form = ContractorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Контрагент добавлен.")
        return redirect("contractors")
    return render(request, "main/contractor_form.html", {"form": form, "title": "Новый контрагент"})


@login_required
def edit_contractor(request, pk):
    contractor = get_object_or_404(Contractor, pk=pk)
    form = ContractorForm(request.POST or None, instance=contractor)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Данные контрагента обновлены.")
        return redirect("contractors")
    return render(request, "main/contractor_form.html", {"form": form, "title": "Редактирование контрагента"})


@login_required
@require_POST
def delete_contractor(request, pk):
    contractor = get_object_or_404(Contractor, pk=pk)
    contractor.delete()
    messages.success(request, "Контрагент удален.")
    return redirect("contractors")


@login_required
def events(request):
    query = request.GET.get("search", "").strip()
    object_list = Event.objects.select_related("p")
    if query:
        object_list = object_list.filter(Q(title__icontains=query) | Q(description__icontains=query))

    events_list = list(object_list)
    employee_map = _fetch_event_employee_map([event.pk for event in events_list])
    participant_counts = {
        item["event"]: item["count"]
        for item in Participant.objects.values("event").order_by().annotate(count=Count("participant_id"))
    }
    task_counts = {
        item["event"]: item["count"]
        for item in Task.objects.values("event").order_by().annotate(count=Count("task_id"))
    }
    for event in events_list:
        event.employee_names = employee_map.get(event.pk, [])
        event.participant_count = participant_counts.get(event.pk, 0)
        event.task_count = task_counts.get(event.pk, 0)

    return render(request, "main/events.html", {"events": events_list, "query": query})


@login_required
def add_event(request):
    form = EventForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        event = form.save()
        _sync_event_employees(event.pk, list(form.cleaned_data["employees"].values_list("pk", flat=True)))
        messages.success(request, "Мероприятие создано.")
        return redirect("events")
    return render(request, "main/event_form.html", {"form": form, "title": "Новое мероприятие"})


@login_required
def edit_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    initial = {"employees": _fetch_selected_employee_ids(event.pk)}
    form = EventForm(request.POST or None, instance=event, initial=initial)
    if request.method == "POST" and form.is_valid():
        event = form.save()
        _sync_event_employees(event.pk, list(form.cleaned_data["employees"].values_list("pk", flat=True)))
        messages.success(request, "Мероприятие обновлено.")
        return redirect("events")
    return render(request, "main/event_form.html", {"form": form, "title": "Редактирование мероприятия"})


@login_required
@require_POST
def delete_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM employee_on_event WHERE event_id = %s", [pk])
        event.delete()
        messages.success(request, "Мероприятие удалено.")
    except Exception:
        messages.error(
            request,
            "Не удалось удалить мероприятие. Сначала удалите связанные задачи, участников, отчеты и закупки.",
        )
    return redirect("events")


@login_required
def participants(request):
    query = request.GET.get("search", "").strip()
    event_id = request.GET.get("event", "").strip()
    object_list = Participant.objects.select_related("event")

    if query:
        object_list = object_list.filter(Q(fullname__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query))
    if event_id:
        object_list = object_list.filter(event_id=event_id)

    return render(
        request,
        "main/participants.html",
        {
            "participants": object_list,
            "events": Event.objects.all(),
            "query": query,
            "selected_event": event_id,
        },
    )


@login_required
def add_participant(request):
    initial = {}
    if request.GET.get("event"):
        initial["event"] = request.GET["event"]
    form = ParticipantForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Участник добавлен.")
        return redirect("participants")
    return render(request, "main/participant_form.html", {"form": form, "title": "Новый участник"})


@login_required
def edit_participant(request, pk):
    participant = get_object_or_404(Participant, pk=pk)
    form = ParticipantForm(request.POST or None, instance=participant)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Данные участника обновлены.")
        return redirect("participants")
    return render(request, "main/participant_form.html", {"form": form, "title": "Редактирование участника"})


@login_required
@require_POST
def delete_participant(request, pk):
    participant = get_object_or_404(Participant, pk=pk)
    participant.delete()
    messages.success(request, "Участник удален.")
    return redirect("participants")


@login_required
def tasks(request):
    query = request.GET.get("search", "").strip()
    event_id = request.GET.get("event", "").strip()
    object_list = Task.objects.select_related("event", "e", "operator")
    if query:
        object_list = object_list.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if event_id:
        object_list = object_list.filter(event_id=event_id)

    return render(
        request,
        "main/tasks.html",
        {
            "tasks": object_list,
            "events": Event.objects.all(),
            "query": query,
            "selected_event": event_id,
        },
    )


@login_required
def add_task(request):
    form = TaskForm(request.POST or None, operator=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Задача создана.")
        return redirect("tasks")
    return render(request, "main/task_form.html", {"form": form, "title": "Новая задача"})


@login_required
def edit_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    form = TaskForm(request.POST or None, instance=task, operator=task.operator or request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Задача обновлена.")
        return redirect("tasks")
    return render(request, "main/task_form.html", {"form": form, "title": "Редактирование задачи"})


@login_required
@require_POST
def delete_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    task.delete()
    messages.success(request, "Задача удалена.")
    return redirect("tasks")


@login_required
def reports(request):
    object_list = Report.objects.select_related("event")
    events_list = Event.objects.all()
    return render(request, "main/reports.html", {"reports": object_list, "events": events_list})


@login_required
@require_POST
def generate_report(request, event_id, report_type):
    if not request.user.can_generate_reports:
        return HttpResponseForbidden("Недостаточно прав.")

    event = get_object_or_404(Event.objects.select_related("p"), pk=event_id)
    report_name = Report.TYPE_EVENT if report_type == "event" else Report.TYPE_EXPENSE
    reports_dir = Path(settings.BASE_DIR) / "generated_reports"
    reports_dir.mkdir(exist_ok=True)

    file_name = f"report_{event.pk}_{report_type}_{Report.objects.count() + 1}.txt"
    file_path = reports_dir / file_name
    file_path.write_text(_build_report_content(event, report_name), encoding="utf-8")

    Report.objects.create(event=event, type=report_name, rep_path=str(file_path))
    messages.success(request, "Отчет сформирован.")
    return redirect("reports")


@role_required(Employee.ROLE_ADMIN)
def employees(request):
    query = request.GET.get("search", "").strip()
    object_list = Employee.objects.all()
    if query:
        object_list = object_list.filter(Q(fullname__icontains=query) | Q(login__icontains=query) | Q(email__icontains=query))
    return render(request, "main/employees.html", {"employees": object_list, "query": query})


@role_required(Employee.ROLE_ADMIN)
def add_employee(request):
    form = EmployeeCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Новый пользователь добавлен.")
        return redirect("employees")
    return render(request, "main/employee_form.html", {"form": form, "title": "Новый пользователь"})
