from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import requests
from .telegram_bot import handle_telegram_start

@csrf_exempt  # Отключаем CSRF для вебхука Telegram
def telegram_webhook_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        
        # Проверяем, что это сообщение с командой /start
        if 'message' in data and 'text' in data['message']:
            chat_id = data['message']['chat']['id']
            text = data['message']['text'].strip()
            
            # Если команда /start
            if text.startswith('/start'):
                # Получаем аргумент после /start (email или телефон)
                user_input = text.replace('/start', '').strip()
                
                if user_input:
                    # Запускаем функцию привязки
                    response_text = handle_telegram_start(chat_id, user_input)
                else:
                    response_text = "Пожалуйста, введите email или телефон после /start\nПример: `/start user@example.com`"
                
                # Отправляем ответ пользователю
                token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                requests.post(url, data={
                    'chat_id': chat_id,
                    'text': response_text,
                    'parse_mode': 'Markdown'
                })
        
        return JsonResponse({'ok': True})
    
    return JsonResponse({'ok': False})