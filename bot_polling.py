import os, django, time, requests
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'selfstorage.settings')
django.setup()

from django.conf import settings
from storage.telegram_bot import handle_telegram_start

TOKEN = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
LAST_UPDATE_ID = 0

print("🤖 Бот запущен (Polling)...")

while True:
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={LAST_UPDATE_ID + 1}&timeout=10"
        updates = requests.get(url).json().get('result', [])
        for update in updates:
            LAST_UPDATE_ID = update['update_id']
            if 'message' in update and 'text' in update['message']:
                chat_id = update['message']['chat']['id']
                text = update['message']['text'].strip()
                if text.startswith('/start'):
                    user_input = text.replace('/start', '').strip()
                    msg = handle_telegram_start(chat_id, user_input) if user_input else "❌ Введите email после /start"
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                data={'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'})
        time.sleep(1)
    except KeyboardInterrupt:
        print("\nОстановлен")
        break
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(5)