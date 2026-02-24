from django.core.management.base import BaseCommand
from django.conf import settings
import requests

class Command(BaseCommand):
    help = 'Устанавливает webhook для Telegram бота'

    def handle(self, *args, **options):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        if not token:
            self.stdout.write(self.style.ERROR('TELEGRAM_BOT_TOKEN не настроен!'))
            return

        # URL твоего сайта на PythonAnywhere
        webhook_url = f"https://antoxaboss.pythonanywhere.com/storage/telegram/webhook/"
        
        # Удаляем старый webhook и ставим новый
        url = f"https://api.telegram.org/bot{token}/setWebhook"
        response = requests.post(url, data={'url': webhook_url})
        
        if response.json().get('ok'):
            self.stdout.write(self.style.SUCCESS(f'Webhook установлен: {webhook_url}'))
        else:
            self.stdout.write(self.style.ERROR(f'Ошибка: {response.json()}'))