from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class Contractor(models.Model):
    TYPE_RENT_SPACE = "аренда помещения"
    TYPE_RENT_EQUIPMENT = "аренда оборудования"
    TYPE_SUPPLIES = "расходники"

    TYPE_CHOICES = [
        (TYPE_RENT_SPACE, "Аренда помещения"),
        (TYPE_RENT_EQUIPMENT, "Аренда оборудования"),
        (TYPE_SUPPLIES, "Расходники"),
    ]

    c_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, verbose_name="Название организации")
    fullname = models.CharField(max_length=255, verbose_name="Контактное лицо")
    email = models.EmailField(verbose_name="Электронная почта")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, verbose_name="Тип контрагента")
    description = models.TextField(blank=True, verbose_name="Описание услуг")

    class Meta:
        managed = False
        db_table = "contractor"
        ordering = ["name"]

    def __str__(self):
        return self.name


class EmployeeManager(BaseUserManager):
    def create_user(self, login, password=None, **extra_fields):
        if not login:
            raise ValueError("Логин обязателен")

        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("fullname", extra_fields.get("fullname") or login)
        extra_fields.setdefault("position", extra_fields.get("position") or Employee.ROLE_ASSISTANT)

        user = self.model(login=login, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, login, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("position", Employee.ROLE_ADMIN)
        return self.create_user(login, password, **extra_fields)


class Employee(AbstractBaseUser, PermissionsMixin):
    ROLE_ADMIN = "admin"
    ROLE_MANAGER = "manager"
    ROLE_ASSISTANT = "assistant"
    ROLE_TEAMLEAD = "teamlead"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "Администратор"),
        (ROLE_MANAGER, "Менеджер"),
        (ROLE_ASSISTANT, "Ассистент"),
        (ROLE_TEAMLEAD, "Руководитель"),
    ]

    e_id = models.BigAutoField(primary_key=True)
    login = models.CharField(max_length=50, unique=True, verbose_name="Логин")
    position = models.CharField(max_length=50, choices=ROLE_CHOICES, verbose_name="Роль")
    fullname = models.CharField(max_length=255, verbose_name="ФИО")
    email = models.EmailField(blank=True, null=True, verbose_name="Почта")
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Телефон")
    age = models.IntegerField(blank=True, null=True, verbose_name="Возраст")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = EmployeeManager()

    USERNAME_FIELD = "login"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "employee"
        ordering = ["fullname", "login"]
        permissions = [
            ("can_create_task", "Can create task"),
            ("can_generate_report", "Can generate report"),
        ]

    def __str__(self):
        return self.fullname or self.login

    @property
    def role(self):
        return self.position

    @property
    def role_label(self):
        if self.is_superuser and not self.position:
            return "Администратор"
        return dict(self.ROLE_CHOICES).get(self.position, self.position)

    @property
    def is_admin(self):
        return self.position == self.ROLE_ADMIN or self.is_superuser

    @property
    def can_manage_users(self):
        return self.is_admin

    @property
    def can_generate_reports(self):
        return self.is_superuser or self.position in {self.ROLE_ADMIN, self.ROLE_TEAMLEAD}


class EmployeeOnEvent(models.Model):
    e = models.ForeignKey(Employee, models.DO_NOTHING, db_column="e_id")
    event = models.ForeignKey("Event", models.DO_NOTHING, db_column="event_id")

    class Meta:
        managed = False
        db_table = "employee_on_event"


class Place(models.Model):
    p_id = models.AutoField(primary_key=True)
    c = models.ForeignKey(Contractor, models.DO_NOTHING, blank=True, null=True, db_column="c_id")
    address = models.TextField(verbose_name="Адрес")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")

    class Meta:
        managed = False
        db_table = "place"
        ordering = ["address"]

    def __str__(self):
        return self.address


class Event(models.Model):
    STATUS_DRAFT = "Черновик"
    STATUS_PREPARATION = "Подготовка"
    STATUS_ACTIVE = "Проведение"
    STATUS_FINISHED = "Завершено"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Черновик"),
        (STATUS_PREPARATION, "Подготовка"),
        (STATUS_ACTIVE, "Проведение"),
        (STATUS_FINISHED, "Завершено"),
    ]

    event_id = models.AutoField(primary_key=True, blank=True)
    p = models.ForeignKey(Place, models.DO_NOTHING, blank=True, null=True, db_column="p_id", verbose_name="Площадка")
    title = models.TextField(verbose_name="Название")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    time = models.TextField(blank=True, null=True, verbose_name="Дата и время")
    status = models.TextField(verbose_name="Статус")

    class Meta:
        managed = False
        db_table = "event"
        ordering = ["-event_id"]

    def __str__(self):
        return self.title


class Order(models.Model):
    order_id = models.AutoField(primary_key=True, blank=True)
    event = models.ForeignKey(Event, models.DO_NOTHING, db_column="event_id")
    c = models.ForeignKey(Contractor, models.DO_NOTHING, db_column="c_id")
    product = models.TextField(verbose_name="Товар")
    quantity = models.IntegerField(verbose_name="Количество")
    price = models.FloatField(verbose_name="Цена")
    date = models.TextField(verbose_name="Дата")

    class Meta:
        managed = False
        db_table = "order"


class Participant(models.Model):
    GENDER_MALE = b"\x01"
    GENDER_FEMALE = b"\x00"

    participant_id = models.AutoField(primary_key=True)
    event = models.ForeignKey(Event, models.DO_NOTHING, db_column="event_id", verbose_name="Мероприятие")
    fullname = models.TextField(blank=True, null=True, verbose_name="ФИО")
    gender = models.BinaryField(blank=True, null=True, verbose_name="Пол")
    phone = models.TextField(blank=True, null=True, verbose_name="Телефон")
    email = models.TextField(blank=True, null=True, verbose_name="Почта")

    class Meta:
        managed = False
        db_table = "participant"
        ordering = ["fullname"]

    def __str__(self):
        return self.fullname or f"Участник #{self.participant_id}"

    @property
    def gender_display(self):
        if self.gender in (self.GENDER_MALE, memoryview(self.GENDER_MALE)):
            return "Мужской"
        if self.gender in (self.GENDER_FEMALE, memoryview(self.GENDER_FEMALE)):
            return "Женский"
        return "Не указан"


class Report(models.Model):
    TYPE_EVENT = "Отчет о мероприятии"
    TYPE_EXPENSE = "Отчет о расходах"

    TYPE_CHOICES = [
        (TYPE_EVENT, "Отчет о мероприятии"),
        (TYPE_EXPENSE, "Отчет о расходах"),
    ]

    rep_id = models.AutoField(primary_key=True)
    event = models.ForeignKey(Event, models.DO_NOTHING, db_column="event_id")
    type = models.TextField(verbose_name="Тип отчета")
    rep_path = models.TextField(verbose_name="Путь к файлу")

    class Meta:
        managed = False
        db_table = "report"
        ordering = ["-rep_id"]


class Task(models.Model):
    STATUS_NEW = "Новая"
    STATUS_IN_PROGRESS = "В работе"
    STATUS_DONE = "Завершена"

    STATUS_CHOICES = [
        (STATUS_NEW, "Новая"),
        (STATUS_IN_PROGRESS, "В работе"),
        (STATUS_DONE, "Завершена"),
    ]

    task_id = models.AutoField(primary_key=True)
    event = models.ForeignKey(Event, models.DO_NOTHING, db_column="event_id", verbose_name="Мероприятие")
    e = models.ForeignKey(
        Employee,
        models.DO_NOTHING,
        blank=True,
        null=True,
        db_column="e_id",
        related_name="assigned_tasks",
        verbose_name="Ответственный",
    )
    operator = models.ForeignKey(
        Employee,
        models.DO_NOTHING,
        db_column="operator_id",
        related_name="created_tasks",
        verbose_name="Постановщик",
    )
    title = models.TextField(verbose_name="Название")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    deadline = models.TextField(blank=True, null=True, verbose_name="Срок")
    status = models.TextField(verbose_name="Статус")

    class Meta:
        managed = False
        db_table = "task"
        ordering = ["deadline", "task_id"]

    def __str__(self):
        return self.title
