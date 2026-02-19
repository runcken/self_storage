from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    # Автоматическое создание профиля при регистрации пользователя
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Автоматическое сохранение профиля при сохранении пользователя

    # Проверяем наличие профиля перед сохранением
    if hasattr(instance, 'profile'):
        instance.profile.save()