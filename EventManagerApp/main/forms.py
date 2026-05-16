from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Contractor, Employee, EmployeeOnEvent, Event, Message, Order, Participant, Place, Task


class StyledFormMixin:
    def apply_base_styles(self):
        for field in self.fields.values():
            widget = field.widget
            css_class = "form-control"
            if isinstance(widget, forms.Select):
                css_class = "form-select"
            if isinstance(widget, forms.CheckboxSelectMultiple):
                css_class = "checkbox-list"
            if isinstance(widget, forms.CheckboxInput):
                css_class = "form-check-input"
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing} {css_class}".strip()


class LoginUserForm(forms.Form, StyledFormMixin):
    login = forms.CharField(
        label="Логин",
        widget=forms.TextInput(attrs={"placeholder": "Введите логин", "autofocus": True}),
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={"placeholder": "Введите пароль"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_base_styles()


class ContractorForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = Contractor
        fields = ["name", "fullname", "email", "phone", "type", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "ООО Сфера"}),
            "fullname": forms.TextInput(attrs={"placeholder": "Иванов Иван Иванович"}),
            "email": forms.EmailInput(attrs={"placeholder": "partner@example.com"}),
            "phone": forms.TextInput(attrs={"placeholder": "+7 (999) 000-00-00"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Какие услуги оказывает контрагент"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_base_styles()


class PlaceForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = Place
        fields = ["c", "address", "description"]
        widgets = {
            "c": forms.Select(),
            "address": forms.TextInput(attrs={"placeholder": "г. Москва, ул. Тверская, д. 1"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Вместимость, особенности площадки, оснащение"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["c"].queryset = Contractor.objects.all()
        self.fields["c"].required = False
        self.apply_base_styles()


class EmployeeCreationForm(forms.ModelForm, StyledFormMixin):
    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={"placeholder": "Введите пароль"}),
        help_text="Пароль будет сохранен в защищенном виде.",
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(attrs={"placeholder": "Повторите пароль"}),
    )

    class Meta:
        model = Employee
        fields = ["fullname", "login", "email", "phone", "age", "position", "is_active"]
        widgets = {
            "fullname": forms.TextInput(attrs={"placeholder": "Петрова Мария Сергеевна"}),
            "login": forms.TextInput(attrs={"placeholder": "m.petrova"}),
            "email": forms.EmailInput(attrs={"placeholder": "employee@example.com"}),
            "phone": forms.TextInput(attrs={"placeholder": "+7 (999) 000-00-00"}),
            "age": forms.NumberInput(attrs={"placeholder": "30", "min": 18}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_base_styles()

    def clean_login(self):
        login = self.cleaned_data["login"]
        qs = Employee.objects.filter(login=login)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Пользователь с таким логином уже существует.")
        return login

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 or password2:
            if password1 != password2:
                raise ValidationError("Пароли не совпадают.")
            validate_password(password1)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data["password1"]
        user.is_staff = user.position == Employee.ROLE_ADMIN or user.is_staff
        user.is_superuser = user.position == Employee.ROLE_ADMIN or user.is_superuser
        user.set_password(password)
        if commit:
            user.save()
        return user


class EmployeeUpdateForm(forms.ModelForm, StyledFormMixin):
    password1 = forms.CharField(
        label="Новый пароль",
        required=False,
        widget=forms.PasswordInput(attrs={"placeholder": "Оставьте пустым, если менять не нужно"}),
        help_text="Если поле пустое, текущий пароль сохранится.",
    )
    password2 = forms.CharField(
        label="Подтверждение нового пароля",
        required=False,
        widget=forms.PasswordInput(attrs={"placeholder": "Повторите новый пароль"}),
    )

    class Meta:
        model = Employee
        fields = ["fullname", "login", "email", "phone", "age", "position", "is_active"]
        widgets = {
            "fullname": forms.TextInput(attrs={"placeholder": "Петрова Мария Сергеевна"}),
            "login": forms.TextInput(attrs={"placeholder": "m.petrova"}),
            "email": forms.EmailInput(attrs={"placeholder": "employee@example.com"}),
            "phone": forms.TextInput(attrs={"placeholder": "+7 (999) 000-00-00"}),
            "age": forms.NumberInput(attrs={"placeholder": "30", "min": 18}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_base_styles()

    def clean_login(self):
        login = self.cleaned_data["login"]
        qs = Employee.objects.filter(login=login).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Пользователь с таким логином уже существует.")
        return login

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 or password2:
            if password1 != password2:
                raise ValidationError("Пароли не совпадают.")
            validate_password(password1, self.instance)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        user.is_staff = user.position == Employee.ROLE_ADMIN or user.is_superuser or user.is_staff
        user.is_superuser = user.position == Employee.ROLE_ADMIN or user.is_superuser
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class EventForm(forms.ModelForm, StyledFormMixin):
    employees = forms.ModelMultipleChoiceField(
        label="Ответственные сотрудники",
        queryset=Employee.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Event
        fields = ["title", "description", "time", "end_date", "planned_budget", "status", "p"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Корпоративный форум 2026"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Краткое описание мероприятия"}),
            "time": forms.TextInput(attrs={"placeholder": "25.05.2026 10:00"}),
            "end_date": forms.TextInput(attrs={"placeholder": "25.05.2026 18:00"}),
            "planned_budget": forms.NumberInput(attrs={"min": 0, "step": "0.01", "placeholder": "150000"}),
            "status": forms.Select(choices=Event.STATUS_CHOICES),
            "p": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["p"].queryset = Place.objects.all()
        self.apply_base_styles()


class EventEmployeeBindingForm(forms.Form, StyledFormMixin):
    employees = forms.ModelMultipleChoiceField(
        label="Сотрудники мероприятия",
        queryset=Employee.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_base_styles()


class ParticipantForm(forms.Form, StyledFormMixin):
    event = forms.ModelChoiceField(label="Мероприятие", queryset=Event.objects.all())
    fullname = forms.CharField(label="ФИО", required=False)
    gender = forms.ChoiceField(
        label="Пол",
        required=False,
        choices=[
            ("", "Не указан"),
            ("male", "Мужской"),
            ("female", "Женский"),
        ],
    )
    phone = forms.CharField(label="Телефон", required=False)
    email = forms.EmailField(label="Почта", required=False)
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop("instance", None)
        event_queryset = kwargs.pop("event_queryset", None)
        super().__init__(*args, **kwargs)
        self.fields["event"].queryset = event_queryset if event_queryset is not None else Event.objects.all()
        self.fields["fullname"].widget.attrs["placeholder"] = "Смирнов Алексей Олегович"
        self.fields["phone"].widget.attrs["placeholder"] = "+7 (999) 000-00-00"
        self.fields["email"].widget.attrs["placeholder"] = "participant@example.com"
        if self.instance is not None:
            self.initial.setdefault("event", self.instance.event_id)
            self.initial.setdefault("fullname", self.instance.fullname)
            self.initial.setdefault("phone", self.instance.phone)
            self.initial.setdefault("email", self.instance.email)
            current_gender = self.instance.gender
            if current_gender in (Participant.GENDER_MALE, memoryview(Participant.GENDER_MALE)):
                self.initial["gender"] = "male"
            elif current_gender in (Participant.GENDER_FEMALE, memoryview(Participant.GENDER_FEMALE)):
                self.initial["gender"] = "female"
        self.apply_base_styles()

    def clean_gender(self):
        value = self.cleaned_data["gender"]
        if value == "male":
            return Participant.GENDER_MALE
        if value == "female":
            return Participant.GENDER_FEMALE
        return None

    def save(self, commit=True):
        participant = self.instance if self.instance is not None else Participant()
        participant.event = self.cleaned_data["event"]
        participant.fullname = self.cleaned_data["fullname"]
        participant.gender = self.cleaned_data["gender"]
        participant.phone = self.cleaned_data["phone"]
        participant.email = self.cleaned_data["email"]
        if commit:
            participant.save()
        return participant


class ParticipantCsvUploadForm(forms.Form, StyledFormMixin):
    event = forms.ModelChoiceField(label="Мероприятие", queryset=Event.objects.all())
    file = forms.FileField(
        label="CSV файл",
        help_text="Поддерживаются колонки: fullname/ФИО, gender/пол, phone/телефон/номер телефона, email/почта. Посещение отмечается вручную после мероприятия.",
    )

    def __init__(self, *args, **kwargs):
        event_queryset = kwargs.pop("event_queryset", None)
        super().__init__(*args, **kwargs)
        self.fields["event"].queryset = event_queryset if event_queryset is not None else Event.objects.all()
        self.fields["file"].widget.attrs["accept"] = ".csv,text/csv"
        self.apply_base_styles()

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        if not uploaded_file.name.lower().endswith(".csv"):
            raise ValidationError("Загрузите файл в формате CSV.")
        return uploaded_file


class FeedbackCsvUploadForm(forms.Form, StyledFormMixin):
    event = forms.ModelChoiceField(label="Мероприятие", queryset=Event.objects.all())
    file = forms.FileField(
        label="CSV файл",
        help_text="Поддерживаются колонки: rating/оценка и review/отзыв. Без заголовков: оценка, отзыв.",
    )

    def __init__(self, *args, **kwargs):
        event_queryset = kwargs.pop("event_queryset", None)
        super().__init__(*args, **kwargs)
        self.fields["event"].queryset = event_queryset if event_queryset is not None else Event.objects.all()
        self.fields["file"].widget.attrs["accept"] = ".csv,text/csv"
        self.apply_base_styles()

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        if not uploaded_file.name.lower().endswith(".csv"):
            raise ValidationError("Загрузите файл в формате CSV.")
        return uploaded_file


class TaskForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = Task
        fields = ["event", "e", "title", "description", "deadline", "status"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Подготовить список гостей"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Что именно нужно сделать"}),
            "deadline": forms.TextInput(attrs={"placeholder": "24.05.2026"}),
            "status": forms.Select(choices=Task.STATUS_CHOICES),
        }

    def __init__(self, *args, operator=None, event_queryset=None, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.operator = operator
        self.actor = actor or operator
        self.fields["event"].queryset = event_queryset if event_queryset is not None else Event.objects.all()
        self.fields["e"].queryset = self._get_assignee_queryset(event_queryset)
        self.apply_base_styles()

    def _get_selected_event_id(self):
        if self.data:
            return self.data.get(self.add_prefix("event")) or self.data.get("event")
        if self.initial.get("event"):
            event = self.initial["event"]
            return getattr(event, "pk", event)
        if self.instance and self.instance.pk:
            return self.instance.event_id
        return None

    def _get_assignee_queryset(self, event_queryset):
        queryset = Employee.objects.filter(is_active=True)
        if self.actor and self.actor.position == Employee.ROLE_MANAGER:
            queryset = queryset.filter(position=Employee.ROLE_ASSISTANT)

        event_id = self._get_selected_event_id()
        if event_id:
            queryset = queryset.filter(employeeonevent__event_id=event_id)
        elif event_queryset is not None:
            queryset = queryset.filter(employeeonevent__event__in=event_queryset)

        return queryset.distinct()

    def clean(self):
        cleaned_data = super().clean()
        event = cleaned_data.get("event")
        assignee = cleaned_data.get("e")
        if not event or not assignee:
            return cleaned_data

        if self.actor and self.actor.position == Employee.ROLE_MANAGER and assignee.position != Employee.ROLE_ASSISTANT:
            self.add_error("e", "Менеджер может назначать задачи только ассистентам.")

        is_linked = EmployeeOnEvent.objects.filter(event=event, e=assignee).exists()
        if not is_linked:
            self.add_error("e", "Ответственный должен быть привязан к выбранному мероприятию.")

        return cleaned_data

    def save(self, commit=True):
        task = super().save(commit=False)
        if self.operator:
            task.operator = self.operator
        if task.status == Task.STATUS_DONE and not task.closed_at:
            task.closed_at = timezone.now()
        elif task.status != Task.STATUS_DONE:
            task.closed_at = None
        if commit:
            task.save()
        return task


class OrderForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = Order
        fields = ["event", "c", "product", "quantity", "price", "date"]
        widgets = {
            "event": forms.Select(),
            "c": forms.Select(),
            "product": forms.TextInput(attrs={"placeholder": "Аренда оборудования / услуги кейтеринга"}),
            "quantity": forms.NumberInput(attrs={"min": 1, "step": 1}),
            "price": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
            "date": forms.TextInput(attrs={"placeholder": "20.05.2026"}),
        }

    def __init__(self, *args, event_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["event"].queryset = event_queryset if event_queryset is not None else Event.objects.all()
        self.fields["c"].queryset = Contractor.objects.all()
        self.apply_base_styles()


class MessageForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = Message
        fields = ["receiver", "subject", "body"]
        widgets = {
            "receiver": forms.Select(),
            "subject": forms.TextInput(attrs={"placeholder": "Тема сообщения"}),
            "body": forms.Textarea(attrs={"rows": 6, "placeholder": "Введите текст сообщения"}),
        }

    def __init__(self, *args, sender=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Employee.objects.filter(is_active=True)
        if sender is not None:
            queryset = queryset.exclude(pk=sender.pk)
        self.fields["receiver"].queryset = queryset
        self.apply_base_styles()
