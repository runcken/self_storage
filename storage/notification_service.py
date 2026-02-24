# notification_service.py
from .utils import send_telegram_notification 
from django.conf import settings
from django.utils import timezone
from datetime import date, timedelta
from .models import RentalAgreement, Client
import logging
from django.db import transaction

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """Сервис для отправки Telegram-уведомлений о договорах аренды"""
    
    @staticmethod
    def send_reminder_30d(agreement):
        """Отправка напоминания за 30 дней до окончания"""
        subject = 'Напоминание: до окончания аренды осталось 30 дней'
        message = f"""Здравствуйте, {agreement.client.full_name}!

Напоминаем, что срок аренды ваших боксов истекает через 30 дней ({agreement.end_date.strftime('%d.%m.%Y')}).

Арендуемые боксы: {', '.join([b.number for b in agreement.boxes.all()])}
Склад: {agreement.warehouse.address}

Пожалуйста, не забудьте забрать ваши вещи вовремя.

С уважением,
Администрация склада SelfStorage"""
        
        return TelegramNotificationService._send_telegram(agreement, subject, message, 'reminder_30d_sent')
    
    @staticmethod
    def send_reminder_14d(agreement):
        """Отправка напоминания за 14 дней до окончания"""
        subject = 'Напоминание: до окончания аренды осталось 14 дней'
        message = f"""Здравствуйте, {agreement.client.full_name}!

Напоминаем, что срок аренды ваших боксов истекает через 14 дней ({agreement.end_date.strftime('%d.%m.%Y')}).

Арендуемые боксы: {', '.join([b.number for b in agreement.boxes.all()])}
Склад: {agreement.warehouse.address}

Пожалуйста, не забудьте забрать ваши вещи вовремя.

С уважением,
Администрация склада SelfStorage"""
        
        return TelegramNotificationService._send_telegram(agreement, subject, message, 'reminder_14d_sent')
    
    @staticmethod
    def send_reminder_7d(agreement):
        """Отправка напоминания за 7 дней до окончания"""
        subject = 'Напоминание: до окончания аренды осталась неделя'
        message = f"""Здравствуйте, {agreement.client.full_name}!

Напоминаем, что срок аренды ваших боксов истекает через 7 дней ({agreement.end_date.strftime('%d.%m.%Y')}).

Арендуемые боксы: {', '.join([b.number for b in agreement.boxes.all()])}
Склад: {agreement.warehouse.address}

Пожалуйста, не забудьте забрать ваши вещи вовремя.

С уважением,
Администрация склада SelfStorage"""
        
        return TelegramNotificationService._send_telegram(agreement, subject, message, 'reminder_7d_sent')
    
    @staticmethod
    def send_reminder_3d(agreement):
        """Отправка напоминания за 3 дня до окончания"""
        subject = 'До окончания аренды осталось 3 дня'
        message = f"""Здравствуйте, {agreement.client.full_name}!

Срок аренды ваших боксов истекает через 3 дня ({agreement.end_date.strftime('%d.%m.%Y')}).

Арендуемые боксы: {', '.join([b.number for b in agreement.boxes.all()])}
Склад: {agreement.warehouse.address}

Если вы не заберете вещи вовремя, они будут храниться на складе по повышенному тарифу в течение 6 месяцев.

С уважением,
Администрация склада SelfStorage"""
        
        return TelegramNotificationService._send_telegram(agreement, subject, message, 'reminder_3d_sent')
    
    @staticmethod
    def send_overdue_notification(agreement):
        """Отправка уведомления о просрочке (первое)"""
        subject = 'Срок аренды истек'
        message = f"""Здравствуйте, {agreement.client.full_name}!

Срок аренды ваших боксов истек {agreement.end_date.strftime('%d.%m.%Y')}.

Арендуемые боксы: {', '.join([b.number for b in agreement.boxes.all()])}
Склад: {agreement.warehouse.address}

Ваши вещи будут храниться на складе еще 6 месяцев по повышенному тарифу.
По истечении 6 месяцев вещи будут утилизированы или отданы на благотворительность.

Пожалуйста, свяжитесь с нами для решения вопроса.

С уважением,
Администрация склада SelfStorage"""
        
        return TelegramNotificationService._send_telegram(agreement, subject, message, 'overdue_notification_sent')
    
    @staticmethod
    def send_monthly_overdue_reminder(agreement):
        """Отправка ежемесячного напоминания о просрочке"""
        months_overdue = (date.today() - agreement.end_date).days // 30
        months_left = 6 - months_overdue
        
        subject = f'Напоминание: вещи на складе ({months_overdue} месяц(ев) просрочки)'
        message = f"""Здравствуйте, {agreement.client.full_name}!

Ваши вещи находятся на складе с просрочкой {months_overdue} месяц(ев) по повышенному тарифу.

Арендуемые боксы: {', '.join([b.number for b in agreement.boxes.all()])}
Склад: {agreement.warehouse.address}

До окончания срока хранения осталось {months_left} месяц(ев).
После этого срока вещи будут утилизированы или отданы на благотворительность.

Пожалуйста, свяжитесь с нами для вывоза вещей.

С уважением,
Администрация склада SelfStorage"""
        
        success = TelegramNotificationService._send_telegram(agreement, subject, message, None)
        if success:
            agreement.last_overdue_reminder_sent = date.today()
            agreement.save(update_fields=['last_overdue_reminder_sent'])
        return success
    
    @staticmethod
    def send_grace_period_expired_notification(agreement):
        """Отправка уведомления об окончании льготного периода"""
        subject = 'Срочно: последний день хранения вещей'
        message = f"""Здравствуйте, {agreement.client.full_name}!

Срок хранения ваших вещей на складе истекает сегодня.
Если вы не заберете вещи сегодня, завтра они будут утилизированы или отданы на благотворительность.

Арендуемые боксы: {', '.join([b.number for b in agreement.boxes.all()])}
Склад: {agreement.warehouse.address}

Пожалуйста, немедленно свяжитесь с нами!

С уважением,
Администрация склада SelfStorage"""
        
        return TelegramNotificationService._send_telegram(agreement, subject, message, 'grace_period_notification_sent')
    
    @staticmethod
    def send_qr_code_for_access(agreement):
        """Отправляет QR-код для доступа к боксу по запросу"""
        if not agreement.client.telegram_chat_id or not agreement.client.telegram_linked:
            logger.warning(f"Telegram: клиент {agreement.client.full_name} не привязан")
            return False
        
        import qrcode
        from io import BytesIO
        import requests
        
        # Генерируем данные для QR
        qr_data = f"BOX_ACCESS:{agreement.id}:{agreement.client.id}:{agreement.warehouse.id}"
        
        # Создаём QR-код
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Сохраняем в буфер
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Отправляем в Telegram
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        chat_id = agreement.client.telegram_chat_id
        
        message = f"""🔑 <b>Доступ к вашему боксу</b>

📦 Бокс: {', '.join([b.number for b in agreement.boxes.all()])}
🏭 Склад: {agreement.warehouse}
📍 Адрес: {agreement.warehouse.address}

✅ Вы можете забрать часть вещей и вернуть их обратно до {agreement.end_date.strftime('%d.%m.%Y')}.

📱 Покажите этот QR-код на складе для доступа."""
        
        # Отправляем текст
        from .utils import send_telegram_notification
        send_telegram_notification(chat_id, message)
        
        # Отправляем QR как фото
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        files = {'photo': ('qr.png', buffer, 'image/png')}
        data = {'chat_id': chat_id, 'caption': '📱 Ваш QR-код для доступа'}
        
        try:
            response = requests.post(url, data=data, files=files, timeout=10)
            return response.json().get('ok', False)
        except Exception as e:
            logger.error(f"QR send error: {e}")
            return False
    
    
    
    @staticmethod
    def _send_telegram(agreement, subject, message, flag_field=None):
        """
        Базовый метод отправки уведомления в Telegram с обновлением флага
        """
        client = agreement.client
        
        # Проверка: привязан ли Telegram у клиента
        if not client.telegram_chat_id or not client.telegram_linked:
            logger.warning(
                f"[TELEGRAM] Клиент {client.full_name} (ID: {client.id}) не привязал Telegram"
            )
            return False
        
        # Формируем текст сообщения с заголовком
        full_text = f"<b>{subject}</b>\n\n{message}"
        
        logger.info(
            f"[TELEGRAM] Попытка отправки:\n"
            f"  -> Кому: {client.full_name} (chat_id: {client.telegram_chat_id})\n"
            f"  -> Тема: {subject}\n"
            f"  -> Договор: #{agreement.id}"
        )
        
        try:
            # Вызываем функцию из utils.py для реальной отправки
            from .utils import send_telegram_notification
            
            success = send_telegram_notification(
                chat_id=client.telegram_chat_id,
                text=full_text,
                parse_mode='HTML'
            )
            
            # Если указан флаг — обновляем его в базе
            if success and flag_field and hasattr(agreement, flag_field):
                setattr(agreement, flag_field, True)
                agreement.save(update_fields=[flag_field])
                logger.info(f"[TELEGRAM] Флаг '{flag_field}' обновлён")
            
            if success:
                logger.info(f"[TELEGRAM] Сообщение успешно отправлено")
            else:
                logger.error(f"[TELEGRAM] Ошибка при отправке (API вернул failure)")
            
            return success
            
        except Exception as e:
            logger.error(f"[TELEGRAM] Исключение при отправке: {type(e).__name__}: {e}")
            return False