from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from main.models import Contractor, Employee, Event, Feedback, Order, Participant, Report, Task


DEMO_PREFIX = "[Демо аналитика]"


class Command(BaseCommand):
    help = "Создает логичные тестовые данные для проверки графиков и метрик аналитики."

    def handle(self, *args, **options):
        employees = list(Employee.objects.filter(is_active=True).order_by("position", "fullname", "login"))
        responsible_pool = [employee for employee in employees if not employee.is_admin] or employees
        if not responsible_pool:
            raise CommandError("В базе нет сотрудников. Новые сотрудники не создаются по условию задачи.")

        contractor = Contractor.objects.first()
        if contractor is None:
            contractor = Contractor.objects.create(
                name="ООО Демо-Сервис",
                fullname="Петров Петр Петрович",
                email="demo-service@example.com",
                phone="+79990000000",
                type=Contractor.TYPE_RENT_SPACE,
                description="Демо-контрагент для тестовых расходов аналитики.",
            )

        creator = next((employee for employee in employees if employee.is_admin), employees[0])
        scenarios = self._build_scenarios(responsible_pool, creator)

        with transaction.atomic():
            self._clear_existing_demo_events()
            created_events = []
            for scenario in scenarios:
                event = Event.objects.create(
                    title=scenario["title"],
                    description=scenario["description"],
                    time=scenario["time"],
                    end_date=scenario["end_date"],
                    planned_budget=scenario["planned_budget"],
                    status=Event.STATUS_FINISHED,
                    p=None,
                    created_by=creator,
                )
                created_events.append(event)
                self._bind_responsible(event, scenario["responsible"])
                self._create_participants(event, scenario["participants"], scenario["attended"])
                self._create_feedback(event, scenario["ratings"], scenario["reviews"])
                self._create_expense(event, contractor, scenario["actual_expenses"])
                self._create_tasks(event, creator, scenario["responsible"], scenario["task_date"], scenario["task_pattern"])

        self.stdout.write(self.style.SUCCESS(f"Создано тестовых мероприятий: {len(created_events)}."))
        self.stdout.write("Новые сотрудники не создавались; использованы существующие пользователи.")

    def _build_scenarios(self, employees, creator):
        def pick(*indexes):
            return [employees[index % len(employees)] for index in indexes]

        return [
            {
                "title": f"{DEMO_PREFIX} Январский бизнес-завтрак",
                "description": "Короткая встреча с ключевыми клиентами: презентация планов и сбор ожиданий.",
                "time": "16.01.2026 09:00",
                "end_date": "16.01.2026 12:00",
                "planned_budget": 120000,
                "actual_expenses": 112000,
                "participants": 24,
                "attended": 22,
                "ratings": [9, 8, 9, 8, 9],
                "reviews": [
                    "Хороший темп, понятная программа, удобно было общаться с командой.",
                    "Понравилась организация регистрации и короткие выступления.",
                    "Хотелось бы больше времени на вопросы после презентации.",
                ],
                "responsible": pick(0, 1),
                "task_date": "18.01.2026",
                "task_pattern": [Task.STATUS_DONE, Task.STATUS_DONE, Task.STATUS_DONE, Task.STATUS_NEW],
            },
            {
                "title": f"{DEMO_PREFIX} Февральский воркшоп продукта",
                "description": "Рабочая сессия по обновлению продукта для отдела продаж и поддержки.",
                "time": "18.02.2026 11:00",
                "end_date": "18.02.2026 17:00",
                "planned_budget": 220000,
                "actual_expenses": 236000,
                "participants": 36,
                "attended": 29,
                "ratings": [7, 8, 7, 8, 6],
                "reviews": [
                    "Материалы полезные, но блок практики стоило сделать длиннее.",
                    "Были задержки с оборудованием, зато спикеры хорошо держали внимание.",
                    "Не хватило навигации по залам и заранее разосланной программы.",
                ],
                "responsible": pick(1, 2),
                "task_date": "20.02.2026",
                "task_pattern": [Task.STATUS_DONE, Task.STATUS_DONE, Task.STATUS_IN_PROGRESS, Task.STATUS_NEW],
            },
            {
                "title": f"{DEMO_PREFIX} Мартовская клиентская конференция",
                "description": "Двухдневная конференция с докладами, стендами партнеров и вечерним нетворкингом.",
                "time": "12.03.2026 10:00",
                "end_date": "14.03.2026 18:00",
                "planned_budget": 780000,
                "actual_expenses": 760000,
                "participants": 128,
                "attended": 116,
                "ratings": [10, 9, 9, 8, 9, 10],
                "reviews": [
                    "Сильная программа и хорошо организованная зона партнеров.",
                    "Очень понравилось приложение с расписанием и быстрые ответы ассистентов.",
                    "Очереди на кофе были заметны, но общее впечатление отличное.",
                ],
                "responsible": pick(0, 2, 3),
                "task_date": "16.03.2026",
                "task_pattern": [Task.STATUS_DONE, Task.STATUS_DONE, Task.STATUS_DONE, Task.STATUS_DONE, Task.STATUS_IN_PROGRESS],
            },
            {
                "title": f"{DEMO_PREFIX} Апрельское обучение регионов",
                "description": "Интенсив для региональных команд с разбором типовых сценариев мероприятий.",
                "time": "09.04.2026 13:00",
                "end_date": "09.04.2026 17:30",
                "planned_budget": 180000,
                "actual_expenses": 198000,
                "participants": 52,
                "attended": 38,
                "ratings": [6, 7, 7, 6, 8],
                "reviews": [
                    "Контент полезный, но начало задержалось почти на полчаса.",
                    "Не всем хватило раздаточных материалов.",
                    "Практические задания помогли, хотелось бы больше обратной связи от тренеров.",
                ],
                "responsible": pick(1, 3),
                "task_date": "11.04.2026",
                "task_pattern": [Task.STATUS_DONE, Task.STATUS_IN_PROGRESS, Task.STATUS_NEW, Task.STATUS_NEW],
            },
            {
                "title": f"{DEMO_PREFIX} Майский партнерский форум",
                "description": "Форум для партнеров с демонстрациями, круглыми столами и закрывающей дискуссией.",
                "time": "02.05.2026 10:00",
                "end_date": "03.05.2026 19:00",
                "planned_budget": 560000,
                "actual_expenses": 532000,
                "participants": 90,
                "attended": 82,
                "ratings": [9, 9, 8, 9, 10],
                "reviews": [
                    "Очень сильный состав участников, все площадки были готовы вовремя.",
                    "Понравилась скорость регистрации и помощь ассистентов на месте.",
                    "Хороший баланс деловой программы и неформального общения.",
                ],
                "responsible": pick(0, 1, 2),
                "task_date": "04.05.2026",
                "task_pattern": [Task.STATUS_DONE, Task.STATUS_DONE, Task.STATUS_DONE, Task.STATUS_IN_PROGRESS],
            },
        ]

    def _clear_existing_demo_events(self):
        demo_events = list(Event.objects.filter(title__startswith=DEMO_PREFIX))
        demo_event_ids = [event.pk for event in demo_events]
        if not demo_event_ids:
            return

        Participant.objects.filter(event_id__in=demo_event_ids).delete()
        Feedback.objects.filter(event_id__in=demo_event_ids).delete()
        Order.objects.filter(event_id__in=demo_event_ids).delete()
        Task.objects.filter(event_id__in=demo_event_ids).delete()
        Report.objects.filter(event_id__in=demo_event_ids).delete()
        with connection.cursor() as cursor:
            placeholders = ", ".join(["%s"] * len(demo_event_ids))
            cursor.execute(f"DELETE FROM employee_on_event WHERE event_id IN ({placeholders})", demo_event_ids)
        Event.objects.filter(pk__in=demo_event_ids).delete()

    def _bind_responsible(self, event, employees):
        unique_employee_ids = []
        for employee in employees:
            if employee.pk not in unique_employee_ids:
                unique_employee_ids.append(employee.pk)

        with connection.cursor() as cursor:
            for employee_id in unique_employee_ids:
                cursor.execute(
                    "INSERT INTO employee_on_event (e_id, event_id) VALUES (%s, %s)",
                    [employee_id, event.pk],
                )

    def _create_participants(self, event, total_count, attended_count):
        participants = []
        for index in range(1, total_count + 1):
            participants.append(
                Participant(
                    event=event,
                    fullname=f"Участник {index:02d} - {event.title.replace(DEMO_PREFIX, '').strip()}",
                    gender=Participant.GENDER_FEMALE if index % 2 else Participant.GENDER_MALE,
                    phone=f"+7999{event.pk:03d}{index:04d}",
                    email=f"demo-event-{event.pk}-{index}@example.com",
                    attended=index <= attended_count,
                )
            )
        Participant.objects.bulk_create(participants)

    def _create_feedback(self, event, ratings, reviews):
        feedback_items = []
        for index, rating in enumerate(ratings):
            review = reviews[index % len(reviews)]
            feedback_items.append(Feedback(event=event, rating=rating, review=review))
        Feedback.objects.bulk_create(feedback_items)

    def _create_expense(self, event, contractor, amount):
        Order.objects.create(
            event=event,
            c=contractor,
            product="Комплексная организация мероприятия",
            quantity=1,
            price=amount,
            date=event.end_date.split()[0],
        )

    def _create_tasks(self, event, creator, responsible, task_date, statuses):
        task_items = []
        for index, status in enumerate(statuses, start=1):
            assignee = responsible[(index - 1) % len(responsible)]
            closed_at = None
            if status == Task.STATUS_DONE:
                closed_at = timezone.make_aware(datetime.strptime(f"{task_date} 18:00", "%d.%m.%Y %H:%M"))
            task_items.append(
                Task(
                    event=event,
                    operator=creator,
                    e=assignee,
                    title=f"{event.title.replace(DEMO_PREFIX, '').strip()}: задача {index}",
                    description="Демо-задача для проверки месячной метрики качества сотрудника.",
                    deadline=task_date,
                    status=status,
                    closed_at=closed_at,
                )
            )
        Task.objects.bulk_create(task_items)
