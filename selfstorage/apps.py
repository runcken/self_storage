from django.apps import AppConfig
import sys
import logging
import os
from django.conf import settings 


logger = logging.getLogger(__name__)


class StorageConfig(AppConfig):  #  Убедись, что имя совпадает с папкой
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'selfstorage'
    
    _initialized = False

    def ready(self):
        # Запускаем только при runserver и в основном процессе
        if 'runserver' not in sys.argv:
            return
        if os.environ.get('RUN_MAIN') != 'true':
            return
        if StorageConfig._initialized:
            return
        
        StorageConfig._initialized = True
        
        #  Запускаем Telegram-планировщик
        self.start_periodic_sending()
    
    def start_periodic_sending(self):
        """Запускает периодическую отправку Telegram-уведомлений"""
        try:
            from .timer_scheduler import send_telegrams_periodically
            
            # ✅ Для тестов: 1 минута, для продакшена: 60 минут
            interval = 1 if settings.DEBUG else 60
            
            # ✅ Передаём interval_minutes (не interval_hours!)
            send_telegrams_periodically(interval_minutes=interval)
            
            logger.info("✅ Telegram-планировщик успешно запущен")
            
        except ImportError as e:
            logger.warning(f"⚠️ timer_scheduler.py не найден: {e}")
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске планировщика: {e}")
