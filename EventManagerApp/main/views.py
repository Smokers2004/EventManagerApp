from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages
from .forms import ContractorForm, LoginUserForm
from .models import Contractor

# Create your views here.


def contractors(request):
    query = request.GET.get('search', '')
    if query:
        # Поиск по названию организации или ФИО контактного лица
        object_list = Contractor.objects.filter(
            Q(name__icontains=query) |
            Q(fullname__icontains=query)
        )
    else:
        object_list = Contractor.objects.all()

    return render(request, 'main/contractors.html', {
        'counterparties': object_list,
        'query': query
    })


@require_POST
def delete_contractor(request, pk):
    counterparty = get_object_or_404(Contractor, pk=pk)
    counterparty.delete()
    return redirect('contractors')


def events(request):
    return render(request, 'main/events.html')


def main_page(request):
    return render(request, 'main/mainpage.html')


def add_contractor(request):
    if request.method == 'POST':
        form = ContractorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('contractors')  # Перенаправление после успеха
    else:
        form = ContractorForm()

    return render(request, 'main/add_contractor.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        login_data = request.POST.get('login')
        password_data = request.POST.get('password')
        user = authenticate(request, login=login_data, password=password_data)

        if user is not None:
            login(request, user)
            return redirect('main_page')  # На главную после входа
        else:
            messages.error(request, "Неверный логин или пароль")

    return render(request, 'main/login.html')
