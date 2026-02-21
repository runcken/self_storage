from django.apps import AppConfig
import sys
import logging
import os

logger = logging.getLogger(__name__)


class SelfStorageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'selfstorage'
    
    # Добавляем флаг для отслеживания, был ли уже выполнен запуск
    _initialized = False

    def ready(self):
        # Запускаем только при команде runserver
        if 'runserver' not in sys.argv:
            return
        
        # Проверяем, что это основной процесс (не процесс перезагрузки)
        if os.environ.get('RUN_MAIN') != 'true':
            return
        
        # Проверяем, не был ли уже выполнен запуск
        if SelfStorageConfig._initialized:
            return
        
        SelfStorageConfig._initialized = True
        
        # Запускаем периодическую отправку
        self.start_periodic_sending()
    
    def start_periodic_sending(self):
        """Запускает периодическую отправку писем"""
        try:
            from .timer_scheduler import send_emails_periodically
            send_emails_periodically()
            logger.info("Периодическая отправка писем успешно запущена")
        except Exception as e:
            logger.error(f'Ошибка при запуске периодической отправки: {e}')