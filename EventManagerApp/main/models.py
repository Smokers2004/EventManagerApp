from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class Contractor(models.Model):
    TYPE_CHOICES = [
        ('аренда помещения', 'Аренда помещения'),
        ('аренда оборудования', 'Аренда оборудования'),
        ('расходники', 'Расходники'),
    ]
    c_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, verbose_name="Название организации")
    fullname = models.CharField(max_length=255, verbose_name="ФИО контактного лица")
    email = models.EmailField(verbose_name="Электронная почта")
    phone = models.CharField(max_length=20, verbose_name="Номер телефона")
    type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        verbose_name="Тип контрагента"
    )
    description = models.TextField(blank=True, verbose_name="Описание")

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'contractor'


class EmployeeManager(BaseUserManager):
    def create_user(self, login, password=None, **extra_fields):
        if not login:
            raise ValueError('Логин обязателен')
        user = self.model(login=login, **extra_fields)
        user.set_password(password)# Хэширование пароля
        user.save(using=self._db)
        return user

    def create_superuser(self, login, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(login, password, **extra_fields)


class Employee(AbstractBaseUser, PermissionsMixin):
    # Роли для разграничения функционала
    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('manager', 'Менеджер'),
        ('assistant','Ассистент'),
        ('teamlead', 'Руководитель')
    ]
    e_id = models.BigAutoField(primary_key=True)
    login = models.CharField(max_length=50, unique=True, verbose_name="Логин")
    position = models.CharField(max_length=50, choices=ROLE_CHOICES, verbose_name="Должность")
    fullname = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    age = models.IntegerField(verbose_name="Возраст", blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = EmployeeManager()

    USERNAME_FIELD = "login"
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.fullname} ({self.position})"

    class Meta:
        db_table = "employee"
        permissions = [
            ("can_create_task", "Can create task"),
            ("can_generate_report", "Can generate report"),
        ]

    def __str__(self):
        return self.fullname or self.login

class EmployeeOnEvent(models.Model):
    e = models.ForeignKey(Employee, models.DO_NOTHING)
    event = models.ForeignKey('Event', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'employee_on_event'


class Event(models.Model):
    event_id = models.AutoField(primary_key=True, blank=True)
    p = models.ForeignKey('Place', models.DO_NOTHING, blank=True, null=True)
    title = models.TextField()
    description = models.TextField(blank=True, null=True)
    time = models.TextField(blank=True, null=True)
    status = models.TextField()

    class Meta:
        managed = False
        db_table = 'event'


class Order(models.Model):
    order_id = models.AutoField(primary_key=True, blank=True)
    event = models.ForeignKey(Event, models.DO_NOTHING)
    c = models.ForeignKey(Contractor, models.DO_NOTHING)
    product = models.TextField()
    quantity = models.IntegerField()
    price = models.FloatField()
    date = models.TextField()

    class Meta:
        managed = False
        db_table = 'order'


class Participant(models.Model):
    participant_id = models.AutoField(primary_key=True)
    event = models.ForeignKey(Event, models.DO_NOTHING)
    fullname = models.TextField(blank=True, null=True)
    gender = models.BinaryField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'participant'


class Place(models.Model):
    p_id = models.AutoField(primary_key=True)
    c = models.ForeignKey(Contractor, models.DO_NOTHING, blank=True, null=True)
    address = models.TextField()
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'place'


class Report(models.Model):
    rep_id = models.AutoField(primary_key=True)
    event = models.ForeignKey(Event, models.DO_NOTHING)
    type = models.TextField()
    rep_path = models.TextField()

    class Meta:
        managed = False
        db_table = 'report'


class Task(models.Model):
    task_id = models.AutoField(primary_key=True)
    event = models.ForeignKey(Event, models.DO_NOTHING)
    e = models.ForeignKey(Employee, models.DO_NOTHING, blank=True, null=True)
    operator = models.ForeignKey(Employee, models.DO_NOTHING, related_name='task_operator_set')
    title = models.TextField()
    description = models.TextField(blank=True, null=True)
    deadline = models.TextField(blank=True, null=True)
    status = models.TextField()

    class Meta:
        managed = False
        db_table = 'task'