from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0011_event_created_by"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE event ADD COLUMN planned_budget REAL DEFAULT 0;",
                    reverse_sql=migrations.RunSQL.noop,
                )
            ],
            state_operations=[
                migrations.AddField(
                    model_name="event",
                    name="planned_budget",
                    field=models.FloatField(
                        blank=True,
                        default=0,
                        null=True,
                        validators=[MinValueValidator(0)],
                        verbose_name="Планируемый бюджет",
                    ),
                ),
            ],
        ),
    ]
