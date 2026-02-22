"""
Вьюхи для аутентификации и личного кабинета
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.base import ContentFile
from io import BytesIO
import qrcode
import base64
from .forms import UserRegistrationForm, UserLoginForm
from .models import Profile


def home_view(request):
    """Главная страница сайта"""
    context = {}
    if request.user.is_authenticated:
        context['email'] = request.user.email
    return render(request, 'index.html', context)


def boxes_view(request):
    """Страница выбора боксов для хранения"""
    context = {}
    if request.user.is_authenticated:
        context['email'] = request.user.email
    return render(request, 'boxes.html', context)


def faq_view(request):
    """Страница правил хранения"""
    return render(request, 'faq.html')


def register_view(request):
    """
    Вьюха регистрации нового пользователя
    После успешной регистрации происходит автоматический вход
    и редирект в личный кабинет
    """
    if request.user.is_authenticated:
        return redirect('cabinet')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
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
    if request.user.is_authenticated:
        return redirect('cabinet')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.user_cache
            
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
    profile, created = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            'phone': '',
            'address': ''
        }
    )
    
    # Генерация или получение существующего QR-кода
    if not profile.qr_code:
        qr_data = f"user_id:{request.user.id};username:{request.user.username};access:storage"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Сохраняем в буфер
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Сохраняем в модель
        qr_image = ContentFile(buffer.getvalue(), name=f'qr_{request.user.id}.png')
        profile.qr_code.save(f'qr_{request.user.id}.png', qr_image, save=True)
    
    # Кодируем в base64 для отображения
    qr_base64 = None
    if profile.qr_code:
        with profile.qr_code.open('rb') as f:
            qr_base64 = base64.b64encode(f.read()).decode('utf-8')
    
    context = {
        'profile': profile,
        'user': request.user,
        'qr_code': qr_base64,
    }
    return render(request, 'cabinet.html', context)


@login_required
def edit_profile_view(request):
    """
    Вьюха редактирования профиля
    """
    profile = request.user.profile
    
    if request.method == 'POST':
        # Обновляем данные пользователя
        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.last_name = request.POST.get('last_name', request.user.last_name)
        request.user.email = request.POST.get('email', request.user.email)
        request.user.save()
        
        # Обновляем данные профиля
        profile.phone = request.POST.get('phone', profile.phone)
        profile.address = request.POST.get('address', profile.address)
        
        # Обновляем аватар, если загружен новый
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
        
        profile.save()
        
        messages.success(request, 'Данные профиля успешно обновлены.')
        return redirect('cabinet')
    
    context = {
        'profile': profile,
        'user': request.user,
    }
    return render(request, 'edit_profile.html', context)


@login_required
def my_rent_view(request):
    """
    Вьюха "Моя аренда" — показывает активные аренды или пустое состояние
    """
    from storage.models import RentalAgreement, Client
    
    # Получаем или создаем клиента для пользователя
    client, created = Client.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
            'email': request.user.email,
            'phone': getattr(request.user.profile, 'phone', ''),
            'address': getattr(request.user.profile, 'address', '')
        }
    )
    
    # Получаем активные аренды
    active_rentals = RentalAgreement.objects.filter(
        client=client
    ).exclude(status__in=['completed', 'cancelled']).select_related('warehouse').prefetch_related('boxes', 'boxes__box_type')
    
    if active_rentals.exists():
        return render(request, 'my-rent.html', {
            'rentals': active_rentals,
            'user': request.user,
            'profile': request.user.profile
        })
    
    # Если аренд нет — показываем пустое состояние
    return render(request, 'my-rent-empty.html', {
        'user': request.user,
        'profile': request.user.profile
    })