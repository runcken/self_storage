# users/models.py
from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь'
    )
    
    # Персональные данные
    first_name = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='Имя'
    )
    
    last_name = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='Фамилия'
    )
    
    # Контактные данные
    phone = models.CharField(
        max_length=15,
        blank=True,
        verbose_name='Телефон',
        help_text='Например: +79991234567'
    )
    
    address = models.TextField(
        blank=True,
        verbose_name='Адрес доставки',
        help_text='Адрес для бесплатной доставки вещей на склад'
    )
    
    # Аватар пользователя
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        verbose_name='Аватар',
        help_text='Изображение профиля (рекомендуемый размер 200x200px)'
    )
    
    # Согласие на обработку ПДн (только для хранения в БД, не отображаем в ЛК)
    pdn_accepted = models.BooleanField(
        default=False,
        verbose_name='Согласие на обработку персональных данных'
    )
    
    # Дата регистрации
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата регистрации'
    )
    
    # QR-код доступа
    qr_code = models.ImageField(
        upload_to='qr_codes/',
        null=True,
        blank=True,
        verbose_name='QR-код доступа'
    )
    
    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Профиль пользователя {self.user.username}'
    
    @property
    def avatar_url(self):
        # Возвращает URL аватара или аватар по умолчанию
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return '/static/img/avatar_default.png'
    
    @property
    def qr_code_url(self):
        # Возвращает URL QR-кода или пустую строку
        if self.qr_code and hasattr(self.qr_code, 'url'):
            return self.qr_code.url
        return ''