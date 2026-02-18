"""
Вьюхи для аутентификации и личного кабинета
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import UserRegistrationForm, UserLoginForm
from .models import Profile


def home_view(request):
    """Главная страница сайта"""
    return render(request, 'index.html')


def boxes_view(request):
    """Страница выбора боксов для хранения"""
    return render(request, 'boxes.html')


def faq_view(request):
    """Страница правил хранения"""
    return render(request, 'faq.html')


def register_view(request):
    """
    Вьюха регистрации нового пользователя
    После успешной регистрации происходит автоматический вход
    и редирект в личный кабинет
    """
    # Если пользователь уже авторизован — перенаправляем в ЛК
    if request.user.is_authenticated:
        return redirect('cabinet')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Создаём профиль вручную (без сигналов)
            Profile.objects.create(
                user=user,
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address'],
                pdn_accepted=form.cleaned_data['pdn_accepted']
            )
            
            login(request, user)
            messages.success(
                request,
                f'Добро пожаловать, {user.username}! Вы успешно зарегистрировались.'
            )
            return redirect('cabinet')
        else:
            messages.error(
                request,
                'Пожалуйста, исправьте ошибки в форме регистрации.'
            )
    else:
        form = UserRegistrationForm()
    
    return render(request, 'register.html', {'form': form})


def login_view(request):
    """
    Вьюха входа пользователя
    Поддерживает вход по имени пользователя или email
    """
    # Если пользователь уже авторизован — перенаправляем в ЛК
    if request.user.is_authenticated:
        return redirect('cabinet')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(
                    request,
                    f'С возвращением, {user.username}!'
                )
                return redirect('cabinet')
            else:
                messages.error(request, 'Неверные данные для входа.')
        else:
            messages.error(request, 'Неверные данные для входа.')
    else:
        form = UserLoginForm()
    
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    """
    Вьюха выхода пользователя из системы
    """
    logout(request)
    messages.info(request, 'Вы успешно вышли из системы.')
    return redirect('home')


@login_required
def cabinet_view(request):
    """
    Вьюха личного кабинета
    Доступна только авторизованным пользователям
    """
    profile = request.user.profile
    
    context = {
        'profile': profile,
        'user': request.user,
    }
    return render(request, 'cabinet.html', context)