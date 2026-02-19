"""
Модель профиля пользователя
"""
from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    """
    Расширенный профиль пользователя
    Связан один-к-одному со стандартной моделью User
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь'
    )
    
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
    
    # Согласие на обработку ПДн
    pdn_accepted = models.BooleanField(
        default=False,
        verbose_name='Согласие на обработку персональных данных'
    )
    
    # Дата регистрации
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата регистрации'
    )
    
    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Профиль пользователя {self.user.username}'