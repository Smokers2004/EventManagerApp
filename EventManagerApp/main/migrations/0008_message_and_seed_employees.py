# Generated manually for messaging and test employee seeding.

from django.contrib.auth.hashers import make_password
from django.db import migrations


def seed_employees(apps, schema_editor):
    Employee = apps.get_model("main", "Employee")

    defaults = [
        {
            "login": "demo_admin",
            "fullname": "Тестовый Администратор",
            "position": "admin",
            "email": "demo_admin@example.com",
            "phone": "+79990000010",
            "is_staff": True,
            "is_superuser": True,
        },
        {
            "login": "demo_manager",
            "fullname": "Тестовый Менеджер",
            "position": "manager",
            "email": "demo_manager@example.com",
            "phone": "+79990000011",
            "is_staff": False,
            "is_superuser": False,
        },
        {
            "login": "demo_assistant",
            "fullname": "Тестовый Ассистент",
            "position": "assistant",
            "email": "demo_assistant@example.com",
            "phone": "+79990000012",
            "is_staff": False,
            "is_superuser": False,
        },
        {
            "login": "demo_teamlead",
            "fullname": "Тестовый Руководитель",
            "position": "teamlead",
            "email": "demo_teamlead@example.com",
            "phone": "+79990000013",
            "is_staff": False,
            "is_superuser": False,
        },
    ]

    for data in defaults:
        Employee.objects.update_or_create(
            login=data["login"],
            defaults={
                **data,
                "password": make_password("TestPass123!"),
                "is_active": True,
                "age": 30,
            },
        )

    Employee.objects.filter(login="admin").update(
        fullname="Администратор системы",
        position="admin",
        is_staff=True,
        is_superuser=True,
        is_active=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0007_remove_employee_department_remove_employee_post_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS message (
                    msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER NOT NULL REFERENCES employee(e_id),
                    receiver_id INTEGER NOT NULL REFERENCES employee(e_id),
                    subject VARCHAR(255),
                    body TEXT NOT NULL,
                    sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    is_read BOOL NOT NULL DEFAULT 0
                );
            """,
            reverse_sql="DROP TABLE IF EXISTS message;",
        ),
        migrations.RunPython(seed_employees, migrations.RunPython.noop),
    ]
