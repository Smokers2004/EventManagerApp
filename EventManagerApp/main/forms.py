from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy
from .models import Contractor, Employee
from django import forms


class ContractorForm(forms.ModelForm):
    class Meta:
        model = Contractor
        fields = ['name', 'fullname', 'email', 'phone', 'type', 'description']
        widgets = {
            'org_name': forms.TextInput(attrs={'placeholder': 'Введите название'}),
            'contact_fio': forms.TextInput(attrs={'placeholder': 'Иванов Иван Иванович'}),
            'email': forms.EmailInput(attrs={'placeholder': 'example@mail.com'}),
            'phone': forms.TextInput(attrs={'placeholder': '+7 (___) ___-__-__'}),
            'agent_type': forms.Select(),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Дополнительная информация'}),
        }


class LoginUserForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['login', 'password']
        widgets = {
            'login': forms.TextInput(attrs={'placeholder': 'Введите логин'}),
            'password': forms.TextInput(attrs={'placeholder': 'Введите пароль'}),
        }
