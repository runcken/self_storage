import os
import requests
from django.conf import settings
from django.db.models import Q 
from .models import Client

def handle_telegram_start(chat_id, user_input):
    """
    Обработчик команды /start
    user_input: email или телефон, который ввёл пользователь
    """
    # Ищем клиента по email или телефону
    client = Client.objects.filter(
        Q(email=user_input) | Q(phone=user_input)  #  Q без models.
    ).first()
    
    if client:
        client.telegram_chat_id = str(chat_id)
        client.telegram_linked = True
        client.save(update_fields=['telegram_chat_id', 'telegram_linked'])
        return f"Привет, {client.full_name}! Telegram привязан к вашему аккаунту."
    else:
        return "Клиент с такими данными не найден. Проверьте email или телефон в личном кабинете."