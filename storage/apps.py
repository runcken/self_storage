from django.apps import AppConfig
import sys
import os

class StorageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "storage"

    def ready(self):
        import storage.signals
        
    _initialized = False
        
    
    def ready(self):
        # Подключаем сигналы
        import storage.signals
        
        # Запускаем планировщик только при runserver
        if 'runserver' not in sys.argv:
            return
        if os.environ.get('RUN_MAIN') != 'true':
            return
        if StorageConfig._initialized:
            return
        
        StorageConfig._initialized = True
        
        # try:
        #     from .timer_scheduler import send_telegrams_periodically
        #     # Для тестов: 2 минуты, для продакшена: 60 минут
        #     from django.conf import settings
        #     interval = getattr(settings, 'TELEGRAM_CHECK_INTERVAL_MINUTES', 2)
        #     send_telegrams_periodically(interval_minutes=interval)
        # except ImportError:
        #     pass
        # except Exception as e:
        #     print(f"Ошибка запуска планировщика: {e}")    
