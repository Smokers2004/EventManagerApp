import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.db import connections
from django.test.runner import DiscoverRunner


class ExistingDatabaseTestRunner(DiscoverRunner):
    """
    Runs tests against a temporary copy of the current SQLite database.

    The project relies on an existing legacy schema with unmanaged models,
    so building the test database purely from migrations is not reliable.
    """

    def setup_databases(self, **kwargs):
        default_settings = settings.DATABASES["default"]
        engine = default_settings.get("ENGINE", "")
        if engine != "django.db.backends.sqlite3":
            return super().setup_databases(**kwargs)

        source_db = Path(default_settings["NAME"])
        self._temp_dir = Path(tempfile.mkdtemp(prefix="eventmanager-testdb-"))
        self._temp_db = self._temp_dir / "test_db.sqlite3"
        shutil.copy2(source_db, self._temp_db)

        self._original_db_name = default_settings["NAME"]
        settings.DATABASES["default"]["NAME"] = str(self._temp_db)

        connection = connections["default"]
        connection.close()
        connection.settings_dict["NAME"] = str(self._temp_db)

        return {
            "temp_dir": self._temp_dir,
            "original_name": self._original_db_name,
        }

    def teardown_databases(self, old_config, **kwargs):
        default_settings = settings.DATABASES["default"]
        if isinstance(old_config, dict) and "original_name" in old_config:
            default_settings["NAME"] = old_config["original_name"]
            connection = connections["default"]
            connection.close()
            connection.settings_dict["NAME"] = old_config["original_name"]
            shutil.rmtree(old_config["temp_dir"], ignore_errors=True)
            return

        super().teardown_databases(old_config, **kwargs)
