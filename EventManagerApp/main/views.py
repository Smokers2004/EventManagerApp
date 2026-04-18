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
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from .decorators import role_required
from .forms import (
    ContractorForm,
    EmployeeCreationForm,
    EventForm,
    LoginUserForm,
    OrderForm,
    ParticipantForm,
    PlaceForm,
    TaskForm,
)
from .models import Contractor, Employee, Event, Order, Participant, Place, Report, Task


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


def _get_event_orders(event):
    return list(Order.objects.filter(event=event).select_related("c"))


def _get_event_tasks(event):
    return list(Task.objects.filter(event=event).select_related("e", "operator"))


def _split_employees_by_role(event):
    employees = Employee.objects.filter(employeeonevent__event=event).distinct()
    grouped = {
        Employee.ROLE_TEAMLEAD: [],
        Employee.ROLE_MANAGER: [],
        Employee.ROLE_ASSISTANT: [],
    }
    for employee in employees:
        grouped.setdefault(employee.position, []).append(employee.fullname or employee.login)
    return grouped


def _expense_total(orders):
    return sum(order.quantity * order.price for order in orders)


def _score_employees(tasks, event):
    employees = Employee.objects.filter(employeeonevent__event=event).distinct()
    rows = []
    for employee in employees:
        own_tasks = [task for task in tasks if task.e_id == employee.pk or task.operator_id == employee.pk]
        if not own_tasks:
            score = "Н/Д"
        else:
            completed = sum(1 for task in own_tasks if task.status == Task.STATUS_DONE)
            score = round((completed / len(own_tasks)) * 10, 2)
        rows.append((employee.fullname or employee.login, score))
    return rows


def _score_contractors(orders, event):
    contractor_rows = []
    grouped = {}
    for order in orders:
        grouped.setdefault(order.c_id, {"contractor": order.c, "amount": 0, "count": 0})
        grouped[order.c_id]["amount"] += order.quantity * order.price
        grouped[order.c_id]["count"] += 1

    for data in grouped.values():
        contractor = data["contractor"]
        score = max(3, min(10, 10 - (data["count"] - 1)))
        if event.status == Event.STATUS_FINISHED:
            conclusion = "Продолжить сотрудничество" if score >= 7 else "Провести переговоры"
        else:
            conclusion = "Оценка предварительная"
        contractor_rows.append((contractor.name, score, conclusion))
    return contractor_rows


def _average_numeric(values):
    numbers = [value for value in values if isinstance(value, (int, float))]
    if not numbers:
        return "Н/Д"
    return round(sum(numbers) / len(numbers), 2)


def _set_report_font(paragraph, size=12, bold=False, italic=False):
    for run in paragraph.runs:
        run.font.name = "Times New Roman"
        run.font.size = Pt(size)
        run.bold = bold
        run.italic = italic


def _add_report_table(document, headers, rows):
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    hdr_cells = table.rows[0].cells
    for idx, header in enumerate(headers):
        hdr_cells[idx].text = str(header)
    for row in rows:
        cells = table.add_row().cells
        for idx, value in enumerate(row):
            cells[idx].text = str(value)
    return table


def _build_event_report_doc(event):
    document = Document()
    orders = _get_event_orders(event)
    tasks = _get_event_tasks(event)
    participants_count = Participant.objects.filter(event=event).count()
    grouped_employees = _split_employees_by_role(event)
    contractor_scores = _score_contractors(orders, event)
    employee_scores = _score_employees(tasks, event)

    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f"ОТЧЕТ О МЕРОПРИЯТИИ № {event.pk}\n").bold = True
    p.add_run((event.title or "").upper()).bold = True
    _set_report_font(p, size=13, bold=True)

    auto = document.add_paragraph()
    auto.add_run("СГЕНЕРИРОВАНО АВТОМАТИЧЕСКИ").italic = True
    _set_report_font(auto, size=12, italic=True)

    info = [
        ("Дата и время проведения мероприятия", event.time or "Не указано"),
        ("Место проведения мероприятия", event.p.address if event.p else "Не указано"),
        ("Количество участников", participants_count),
    ]
    for label, value in info:
        paragraph = document.add_paragraph()
        paragraph.add_run(f"{label} – ").bold = True
        paragraph.add_run(str(value))
        _set_report_font(paragraph)

    for label, role_key in [
        ("Руководитель(и)", Employee.ROLE_TEAMLEAD),
        ("Менеджер(ы)", Employee.ROLE_MANAGER),
        ("Ассистент(ы)", Employee.ROLE_ASSISTANT),
    ]:
        paragraph = document.add_paragraph()
        paragraph.add_run(f"{label}:").bold = True
        _set_report_font(paragraph)
        names = grouped_employees.get(role_key) or ["Не назначены"]
        for name in names:
            item = document.add_paragraph(name)
            item.paragraph_format.left_indent = Pt(18)
            _set_report_font(item)

    linked = document.add_paragraph()
    linked.add_run("Связанные заказы").bold = True
    _set_report_font(linked)
    order_rows = []
    for order in orders:
        order_rows.append(
            [
                order.c.name,
                order.c.fullname,
                f"ORD-{order.order_id}",
                order.date,
                order.c.get_type_display() if hasattr(order.c, "get_type_display") else order.c.type,
            ]
        )
    if order_rows:
        _add_report_table(
            document,
            ["Юр лицо", "Контактное лицо", "Номер договора", "Дата заключения", "Тип договора"],
            order_rows,
        )
    else:
        empty = document.add_paragraph("Связанные заказы отсутствуют.")
        _set_report_font(empty)

    comment = document.add_paragraph()
    comment.add_run("Комментарий менеджера: ").bold = True
    comment.add_run(event.description or "Комментарий к мероприятию не добавлен.")
    _set_report_font(comment)

    feedback_title = document.add_paragraph()
    feedback_title.add_run("Обратная связь:").bold = True
    _set_report_font(feedback_title)
    feedback_rows = []
    participants = Participant.objects.filter(event=event)[:5]
    for idx, participant in enumerate(participants, 1):
        feedback_rows.append(
            [
                idx,
                f"Участник {participant.fullname or idx}. Контакт: {participant.email or participant.phone or 'не указан'}",
                7,
            ]
        )
    if not feedback_rows:
        feedback_rows.append([1, "Данные обратной связи не собраны.", "Н/Д"])
    avg_feedback = _average_numeric([row[2] for row in feedback_rows])
    feedback_rows.append(["Среднее", "", avg_feedback])
    _add_report_table(document, ["ID", "Отзыв", "Оценка (от 1 до 10)"], feedback_rows)

    summary_title = document.add_paragraph()
    summary_title.add_run("ИТОГИ").bold = True
    _set_report_font(summary_title, size=13, bold=True)

    contractor_title = document.add_paragraph()
    contractor_title.add_run("Оценка контрагентов:").bold = True
    _set_report_font(contractor_title)
    contractor_table_rows = contractor_scores or [("Нет данных", "Н/Д", "Недостаточно данных")]
    contractor_avg = _average_numeric([row[1] for row in contractor_table_rows])
    contractor_table_rows = contractor_table_rows + [("Среднее", contractor_avg, "")]
    _add_report_table(document, ["Юр лицо", "Оценка", "Вывод"], contractor_table_rows)

    employee_title = document.add_paragraph()
    employee_title.add_run("Оценка работы сотрудников").bold = True
    _set_report_font(employee_title)
    employee_table_rows = employee_scores or [("Нет данных", "Н/Д")]
    _add_report_table(document, ["Сотрудник", "Оценка"], employee_table_rows)

    final_avg = _average_numeric(
        [row[1] for row in contractor_scores] + [row[1] for row in employee_scores] + [avg_feedback]
    )
    final = document.add_paragraph()
    final.add_run(f"Средняя оценка мероприятия — {final_avg}").bold = True
    _set_report_font(final, size=13, bold=True)

    return document


def _build_expense_report_doc(event):
    document = Document()
    orders = _get_event_orders(event)

    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f"ОТЧЕТ О РАСХОДАХ ОРГАНИЗАЦИИ НА МЕРОПРИЯТИЕ № {event.pk}\n").bold = True
    p.add_run((event.title or "").upper()).bold = True
    _set_report_font(p, size=13, bold=True)

    auto = document.add_paragraph()
    auto.add_run("СГЕНЕРИРОВАНО АВТОМАТИЧЕСКИ").italic = True
    _set_report_font(auto, size=12, italic=True)

    info = document.add_paragraph()
    info.add_run("Дата и время проведения мероприятия – ").bold = True
    info.add_run(event.time or "Не указано")
    _set_report_font(info)

    title = document.add_paragraph()
    title.add_run("Затраты").bold = True
    _set_report_font(title)

    rows = []
    total = 0
    for order in orders:
        amount = order.quantity * order.price
        total += amount
        rows.append(
            [
                order.c.name,
                f"ORD-{order.order_id}",
                order.date,
                order.product,
                order.quantity,
                f"{order.price:,.2f}".replace(",", " "),
                f"{amount:,.2f}".replace(",", " "),
            ]
        )
    if rows:
        rows.append(["", "", "", "", "", "ИТОГО", f"{total:,.2f}".replace(",", " ")])
        _add_report_table(
            document,
            [
                "Юр Лицо",
                "Номер договора",
                "Дата заключения",
                "Товар/услуга",
                "Количество",
                "Стоимость 1 ед. (руб.)",
                "Расходы (руб.)",
            ],
            rows,
        )
    else:
        empty = document.add_paragraph("Затраты по мероприятию отсутствуют.")
        _set_report_font(empty)

    return document


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
        "places_count": Place.objects.count(),
        "reports_count": Report.objects.count(),
        "expenses_count": Order.objects.count(),
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
def places(request):
    query = request.GET.get("search", "").strip()
    object_list = Place.objects.select_related("c")
    if query:
        object_list = object_list.filter(Q(address__icontains=query) | Q(description__icontains=query))
    return render(request, "main/places.html", {"places": object_list, "query": query})


@login_required
def add_place(request):
    form = PlaceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Площадка добавлена.")
        return redirect("places")
    return render(request, "main/place_form.html", {"form": form, "title": "Новая площадка"})


@login_required
def edit_place(request, pk):
    place = get_object_or_404(Place, pk=pk)
    form = PlaceForm(request.POST or None, instance=place)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Данные площадки обновлены.")
        return redirect("places")
    return render(request, "main/place_form.html", {"form": form, "title": "Редактирование площадки"})


@login_required
@require_POST
def delete_place(request, pk):
    place = get_object_or_404(Place, pk=pk)
    try:
        place.delete()
        messages.success(request, "Площадка удалена.")
    except Exception:
        messages.error(request, "Нельзя удалить площадку, пока она используется в мероприятиях.")
    return redirect("places")


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
        event.expense_total = _expense_total(_get_event_orders(event))

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
def event_detail(request, pk):
    event = get_object_or_404(Event.objects.select_related("p"), pk=pk)
    employee_map = _fetch_event_employee_map([event.pk])
    orders = _get_event_orders(event)
    for expense in orders:
        expense.total_cost = expense.quantity * expense.price
    tasks = _get_event_tasks(event)
    context = {
        "event": event,
        "employees": employee_map.get(event.pk, []),
        "participants_count": Participant.objects.filter(event=event).count(),
        "tasks_count": len(tasks),
        "expenses": orders,
        "expense_total": _expense_total(orders),
    }
    return render(request, "main/event_detail.html", context)


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
def expenses(request):
    query = request.GET.get("search", "").strip()
    event_id = request.GET.get("event", "").strip()
    object_list = Order.objects.select_related("event", "c")
    if query:
        object_list = object_list.filter(Q(product__icontains=query) | Q(c__name__icontains=query))
    if event_id:
        object_list = object_list.filter(event_id=event_id)

    expense_rows = list(object_list)
    total = 0
    for expense in expense_rows:
        expense.total_cost = expense.quantity * expense.price
        total += expense.total_cost

    return render(
        request,
        "main/expenses.html",
        {
            "expenses": expense_rows,
            "events": Event.objects.all(),
            "query": query,
            "selected_event": event_id,
            "total": total,
        },
    )


@login_required
def add_expense(request):
    initial = {}
    if request.GET.get("event"):
        initial["event"] = request.GET["event"]
    form = OrderForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Расход добавлен.")
        return redirect("expenses")
    return render(request, "main/expense_form.html", {"form": form, "title": "Новый расход"})


@login_required
def edit_expense(request, pk):
    expense = get_object_or_404(Order, pk=pk)
    form = OrderForm(request.POST or None, instance=expense)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Расход обновлен.")
        return redirect("expenses")
    return render(request, "main/expense_form.html", {"form": form, "title": "Редактирование расхода"})


@login_required
@require_POST
def delete_expense(request, pk):
    expense = get_object_or_404(Order, pk=pk)
    expense.delete()
    messages.success(request, "Расход удален.")
    return redirect("expenses")


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

    file_name = f"report_{event.pk}_{report_type}_{Report.objects.count() + 1}.docx"
    file_path = reports_dir / file_name
    document = _build_event_report_doc(event) if report_type == "event" else _build_expense_report_doc(event)
    document.save(file_path)

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
