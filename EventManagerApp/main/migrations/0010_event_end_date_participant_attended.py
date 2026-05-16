from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0009_feedback_and_task_closed_at"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=[
                        "ALTER TABLE event ADD COLUMN end_date TEXT;",
                        "ALTER TABLE participant ADD COLUMN attended BOOL NOT NULL DEFAULT 0;",
                    ],
                    reverse_sql=migrations.RunSQL.noop,
                )
            ],
            state_operations=[
                migrations.AddField(
                    model_name="event",
                    name="end_date",
                    field=models.TextField(blank=True, null=True, verbose_name="Дата окончания"),
                ),
                migrations.AddField(
                    model_name="participant",
                    name="attended",
                    field=models.BooleanField(default=False, verbose_name="Посещение"),
                ),
            ],
        ),
    ]
