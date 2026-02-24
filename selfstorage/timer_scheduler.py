# storage/timer_scheduler.py
import threading
import time
from django.core.management import call_command
from django.db import connections
from django.conf import settings
import logging
import atexit
import signal
import sys

logger = logging.getLogger(__name__)

running = True
timer_thread = None


def send_telegrams_periodically(interval_minutes=1):  # Добавь параметр!
    """
    Отправляет Telegram-уведомления с заданной периодичностью
    interval_minutes: как часто проверять (по умолчанию 1 минута для тестов)
    """
    global running, timer_thread
    
    interval_seconds = interval_minutes * 60  # Переводим минуты в секунды
    
    def job():
        # Ждём 10 секунд после запуска сервера
        time.sleep(10)
        
        while running:
            try:
                connections.close_all()
                
                # Вызываем Telegram-команду
                call_command('send_telegram_reminders', verbosity=0)
                
                logger.info(f"Telegram-проверка выполнена (следующая через {interval_minutes} мин)")
                
            except Exception as e:
                logger.error(f"Ошибка при отправке Telegram: {e}")
            
            # Ждём интервал перед следующей проверкой
            for _ in range(interval_seconds):
                if not running:
                    break
                time.sleep(1)
    
    timer_thread = threading.Thread(target=job, daemon=True)
    timer_thread.start()
    
    logger.info(f"🤖 Telegram-планировщик запущен (интервал: {interval_minutes} минут)")
    return timer_thread


def stop_timer(signum=None, frame=None):
    """Останавливает таймер при получении сигнала"""
    global running
    logger.info(" Получен сигнал остановки Telegram-планировщика")
    running = False


def cleanup():
    """Очистка при выходе из приложения"""
    stop_timer()
    if timer_thread and timer_thread.is_alive():
        timer_thread.join(timeout=2)


# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, stop_timer)   # Ctrl+C
signal.signal(signal.SIGTERM, stop_timer)  # kill процессу

# Регистрируем очистку при нормальном выходе
atexit.register(cleanup)