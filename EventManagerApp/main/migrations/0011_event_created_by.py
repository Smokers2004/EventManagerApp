from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0010_event_end_date_participant_attended"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE event ADD COLUMN created_by_id INTEGER REFERENCES employee(e_id);",
                    reverse_sql=migrations.RunSQL.noop,
                )
            ],
            state_operations=[
                migrations.AddField(
                    model_name="event",
                    name="created_by",
                    field=models.ForeignKey(
                        blank=True,
                        db_column="created_by_id",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="created_events",
                        to="main.employee",
                        verbose_name="Создатель",
                    ),
                ),
            ],
        ),
    ]
