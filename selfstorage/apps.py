from django.apps import AppConfig
import sys
import logging
import os

logger = logging.getLogger(__name__)


class SelfStorageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'selfstorage'
    
    _initialized = False

    def ready(self):
        if 'runserver' not in sys.argv:
            return
        
        if os.environ.get('RUN_MAIN') != 'true':
            return
        
        if SelfStorageConfig._initialized:
            return
        
        SelfStorageConfig._initialized = True
        
        self.start_periodic_sending()
    
    def start_periodic_sending(self):
        """Запускает периодическую отправку писем"""
        try:
            from .timer_scheduler import send_emails_periodically
            send_emails_periodically()
            logger.info("Периодическая отправка писем успешно запущена")
        except Exception as e:
            logger.error(f'Ошибка при запуске периодической отправки: {e}')