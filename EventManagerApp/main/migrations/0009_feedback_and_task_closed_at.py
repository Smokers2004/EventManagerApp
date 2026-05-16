from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0008_message_and_seed_employees"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=[
                        """
                        CREATE TABLE IF NOT EXISTS feedback (
                            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            event_id INTEGER NOT NULL REFERENCES event(event_id),
                            rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 10),
                            review TEXT NOT NULL
                        );
                        """,
                        "ALTER TABLE task ADD COLUMN closed_at DATETIME;",
                    ],
                    reverse_sql=migrations.RunSQL.noop,
                )
            ],
            state_operations=[
                migrations.CreateModel(
                    name="Message",
                    fields=[
                        ("msg_id", models.AutoField(primary_key=True, serialize=False)),
                        ("subject", models.CharField(blank=True, max_length=255, verbose_name="Тема")),
                        ("body", models.TextField(verbose_name="Сообщение")),
                        ("sent_at", models.DateTimeField(verbose_name="Отправлено")),
                        ("is_read", models.BooleanField(default=False, verbose_name="Прочитано")),
                    ],
                    options={
                        "db_table": "message",
                        "ordering": ["-sent_at", "-msg_id"],
                        "managed": False,
                    },
                ),
                migrations.CreateModel(
                    name="Feedback",
                    fields=[
                        ("feedback_id", models.AutoField(primary_key=True, serialize=False)),
                        (
                            "rating",
                            models.PositiveSmallIntegerField(
                                validators=[MinValueValidator(1), MaxValueValidator(10)],
                                verbose_name="Оценка",
                            ),
                        ),
                        ("review", models.TextField(verbose_name="Отзыв")),
                        (
                            "event",
                            models.ForeignKey(
                                db_column="event_id",
                                on_delete=django.db.models.deletion.DO_NOTHING,
                                to="main.event",
                                verbose_name="Мероприятие",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "feedback",
                        "ordering": ["-feedback_id"],
                        "managed": False,
                    },
                ),
                migrations.AddField(
                    model_name="task",
                    name="closed_at",
                    field=models.DateTimeField(blank=True, null=True, verbose_name="Дата закрытия"),
                ),
                migrations.AlterModelOptions(
                    name="contractor",
                    options={"managed": False, "ordering": ["name"]},
                ),
                migrations.AlterModelOptions(
                    name="employee",
                    options={
                        "ordering": ["fullname", "login"],
                        "permissions": [
                            ("can_create_task", "Can create task"),
                            ("can_generate_report", "Can generate report"),
                        ],
                    },
                ),
                migrations.AlterModelOptions(
                    name="event",
                    options={"managed": False, "ordering": ["-event_id"]},
                ),
                migrations.AlterModelOptions(
                    name="participant",
                    options={"managed": False, "ordering": ["fullname"]},
                ),
                migrations.AlterModelOptions(
                    name="place",
                    options={"managed": False, "ordering": ["address"]},
                ),
                migrations.AlterModelOptions(
                    name="report",
                    options={"managed": False, "ordering": ["-rep_id"]},
                ),
                migrations.AlterModelOptions(
                    name="task",
                    options={"managed": False, "ordering": ["deadline", "task_id"]},
                ),
                migrations.AlterField(
                    model_name="employee",
                    name="email",
                    field=models.EmailField(blank=True, max_length=254, null=True, verbose_name="Почта"),
                ),
                migrations.AlterField(
                    model_name="employee",
                    name="fullname",
                    field=models.CharField(max_length=255, verbose_name="ФИО"),
                ),
                migrations.AlterField(
                    model_name="employee",
                    name="phone",
                    field=models.CharField(blank=True, max_length=50, null=True, verbose_name="Телефон"),
                ),
                migrations.AlterField(
                    model_name="employee",
                    name="position",
                    field=models.CharField(
                        choices=[
                            ("admin", "Администратор"),
                            ("manager", "Менеджер"),
                            ("assistant", "Ассистент"),
                            ("teamlead", "Руководитель"),
                        ],
                        max_length=50,
                        verbose_name="Роль",
                    ),
                ),
            ],
        ),
    ]
