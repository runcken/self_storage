import threading
import time
from django.core.management import call_command
from django.db import connections
import logging
import atexit
import signal
import sys

logger = logging.getLogger(__name__)

running = True
timer_thread = None


def send_emails_periodically():
    """Отправляет письма с заданной периодичностью"""
    global running, timer_thread
    
    def job():
        time.sleep(60)
        
        while running:
            try:
                connections.close_all()
                
                call_command('send_email')
                logger.info("Периодическая отправка писем выполнена")
            except Exception as e:
                logger.error(f"Ошибка при отправке писем: {e}")
            
            for _ in range(3600*5):
                if not running:
                    break
                time.sleep(1)
    
    timer_thread = threading.Thread(target=job, daemon=True)
    timer_thread.start()
    logger.info("Таймер для периодической отправки писем запущен (интервал: 1 минута)")
    
    return timer_thread


def stop_timer(signum=None, frame=None):
    """Останавливает таймер"""
    global running
    logger.info("Получен сигнал остановки таймера")
    running = False


def cleanup():
    """Очистка при выходе"""
    stop_timer()
    if timer_thread and timer_thread.is_alive():
        timer_thread.join(timeout=2)


signal.signal(signal.SIGINT, stop_timer)
signal.signal(signal.SIGTERM, stop_timer)

atexit.register(cleanup)