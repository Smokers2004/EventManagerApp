import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EventManagerApp.settings")

import django

django.setup()

from django.db import connection
from django.utils import timezone

from main.models import Contractor, Employee, Event, Message, Order, Participant, Place, Report, Task


@dataclass
class BenchmarkContext:
    prefix: str
    admin: Employee
    manager: Employee
    assistant: Employee
    teamlead: Employee
    contractor_id: int | None = None
    place_id: int | None = None
    event_ids: list[int] | None = None
    participant_ids: list[int] | None = None
    task_ids: list[int] | None = None
    order_ids: list[int] | None = None
    message_ids: list[int] | None = None
    report_ids: list[int] | None = None


def get_users():
    admin = Employee.objects.filter(position=Employee.ROLE_ADMIN).first() or Employee.objects.first()
    if not admin:
        raise RuntimeError("No users found in the database.")

    manager = (
        Employee.objects.filter(position=Employee.ROLE_MANAGER)
        .exclude(pk=admin.pk)
        .first()
        or admin
    )
    assistant = (
        Employee.objects.filter(position=Employee.ROLE_ASSISTANT)
        .exclude(pk__in={admin.pk, manager.pk})
        .first()
        or admin
    )
    teamlead = (
        Employee.objects.filter(position=Employee.ROLE_TEAMLEAD)
        .exclude(pk__in={admin.pk, manager.pk, assistant.pk})
        .first()
        or admin
    )
    return admin, manager, assistant, teamlead


def create_dataset(
    *,
    events_count: int,
    participants_per_event: int,
    tasks_per_event: int,
    orders_per_event: int,
    messages_count: int,
) -> BenchmarkContext:
    prefix = f"bench_{uuid.uuid4().hex[:8]}"
    admin, manager, assistant, teamlead = get_users()

    contractor = Contractor.objects.create(
        name=f"{prefix}_contractor",
        fullname="Benchmark Contractor",
        email=f"{prefix}@test.local",
        phone="+79991112233",
        type=Contractor.TYPE_RENT_SPACE,
        description="Temporary contractor for benchmark scripts.",
    )

    place = Place.objects.create(
        c=contractor,
        address=f"{prefix}_address",
        description="Temporary benchmark place.",
    )

    event_ids = []
    participant_ids = []
    task_ids = []
    order_ids = []
    message_ids = []

    for event_index in range(events_count):
        event = Event.objects.create(
            title=f"{prefix}_event_{event_index}",
            description="Benchmark event",
            time="20.04.2026 10:00",
            status=Event.STATUS_PREPARATION,
            p=place,
        )
        event_ids.append(event.pk)

        for participant_index in range(participants_per_event):
            participant = Participant.objects.create(
                event=event,
                fullname=f"{prefix}_participant_{event_index}_{participant_index}",
                gender=Participant.GENDER_MALE if participant_index % 2 == 0 else Participant.GENDER_FEMALE,
                phone=f"+7999{event_index:02d}{participant_index:04d}",
                email=f"{prefix}_{event_index}_{participant_index}@test.local",
            )
            participant_ids.append(participant.pk)

        for task_index in range(tasks_per_event):
            task = Task.objects.create(
                event=event,
                e=manager,
                operator=teamlead,
                title=f"{prefix}_task_{event_index}_{task_index}",
                description="Temporary benchmark task.",
                deadline="25.04.2026",
                status=Task.STATUS_IN_PROGRESS,
            )
            task_ids.append(task.pk)

        for order_index in range(orders_per_event):
            order = Order.objects.create(
                event=event,
                c=contractor,
                product=f"{prefix}_order_{event_index}_{order_index}",
                quantity=2 + order_index,
                price=1000.0 + order_index * 100,
                date="20.04.2026",
            )
            order_ids.append(order.pk)

        for employee in {admin, manager, assistant, teamlead}:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO employee_on_event (e_id, event_id) VALUES (%s, %s)",
                    [employee.pk, event.pk],
                )

    for message_index in range(messages_count):
        message = Message.objects.create(
            sender=manager,
            receiver=assistant,
            subject=f"{prefix}_message_{message_index}",
            body="Temporary benchmark message.",
            sent_at=timezone.now(),
            is_read=message_index % 3 == 0,
        )
        message_ids.append(message.pk)

    return BenchmarkContext(
        prefix=prefix,
        admin=admin,
        manager=manager,
        assistant=assistant,
        teamlead=teamlead,
        contractor_id=contractor.pk,
        place_id=place.pk,
        event_ids=event_ids,
        participant_ids=participant_ids,
        task_ids=task_ids,
        order_ids=order_ids,
        message_ids=message_ids,
        report_ids=[],
    )


def cleanup_dataset(ctx: BenchmarkContext) -> None:
    event_ids = ctx.event_ids or []
    report_queryset = Report.objects.filter(event_id__in=event_ids)
    if ctx.report_ids:
        report_queryset = report_queryset | Report.objects.filter(pk__in=ctx.report_ids)
    report_paths = list(report_queryset.values_list("rep_path", flat=True).distinct())
    for rep_path in report_paths:
        try:
            path = Path(rep_path)
            if path.exists() and path.is_file():
                path.unlink()
        except OSError:
            pass

    report_queryset.delete()
    Message.objects.filter(subject__startswith=f"{ctx.prefix}_load_post_").delete()
    Message.objects.filter(subject__startswith=f"{ctx.prefix}_message_").delete()
    Message.objects.filter(pk__in=ctx.message_ids or []).delete()
    Task.objects.filter(event_id__in=event_ids).delete()
    Participant.objects.filter(event_id__in=event_ids).delete()
    Order.objects.filter(event_id__in=event_ids).delete()

    with connection.cursor() as cursor:
        for event_id in ctx.event_ids or []:
            cursor.execute("DELETE FROM employee_on_event WHERE event_id = %s", [event_id])

    Event.objects.filter(pk__in=ctx.event_ids or []).delete()
    Place.objects.filter(pk=ctx.place_id).delete()
    Contractor.objects.filter(pk=ctx.contractor_id).delete()
