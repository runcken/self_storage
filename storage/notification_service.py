# notification_service.py
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import date, timedelta
from .models import RentalAgreement, Client
import logging
from django.db import transaction

logger = logging.getLogger(__name__)


class EmailNotificationService:
    """Сервис для отправки email-уведомлений о договорах аренды"""
    
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
        
        return EmailNotificationService._send_email(agreement, subject, message, 'reminder_30d_sent')
    
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
        
        return EmailNotificationService._send_email(agreement, subject, message, 'reminder_14d_sent')
    
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
        
        return EmailNotificationService._send_email(agreement, subject, message, 'reminder_7d_sent')
    
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
        
        return EmailNotificationService._send_email(agreement, subject, message, 'reminder_3d_sent')
    
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
        
        return EmailNotificationService._send_email(agreement, subject, message, 'overdue_notification_sent')
    
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
        
        success = EmailNotificationService._send_email(agreement, subject, message, None)
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
        
        return EmailNotificationService._send_email(agreement, subject, message, 'grace_period_notification_sent')
    
    @staticmethod
    def _send_email(agreement, subject, message, flag_field=None):
        """
        Базовый метод отправки email с обновлением флага отправки
        """
        # ДЕТАЛЬНАЯ ПРОВЕРКА email клиента
        client_email = agreement.client.email
        
        if not client_email:
            logger.warning(
                f"[EMAIL] Клиент {agreement.client.full_name} (ID: {agreement.client.id}) "
                f"не имеет email! Договор #{agreement.id}"
            )
            # Пробуем получить email из связанного User
            if agreement.client.user and agreement.client.user.email:
                client_email = agreement.client.user.email
                logger.info(f"[EMAIL] Используем email из User: {client_email}")
                # Сохраняем в модель Client для будущего
                agreement.client.email = client_email
                agreement.client.save(update_fields=['email'])
            else:
                logger.error(
                    f"[EMAIL] Нет email для клиента {agreement.client.full_name}. "
                    f"Письмо НЕ отправлено."
                )
                return False
        
        # Логируем попытку отправки
        logger.info(
            f"[EMAIL] Попытка отправки письма:\n"
            f"  -> Кому: {client_email}\n"
            f"  -> Тема: {subject}\n"
            f"  -> Договор: #{agreement.id}\n"
            f"  -> Клиент: {agreement.client.full_name}"
        )
        
        try:
            result = send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[client_email],
                fail_silently=False,
            )
            
            # Если указан флаг, обновляем его
            if flag_field and hasattr(agreement, flag_field):
                setattr(agreement, flag_field, True)
                agreement.save(update_fields=[flag_field])
            
            logger.info(
                f"[EMAIL] Письмо успешно отправлено на {client_email} "
                f"(договор #{agreement.id}, result={result})"
            )
            return True
            
        except Exception as e:
            logger.error(
                f"[EMAIL] Ошибка отправки email на {client_email}: {type(e).__name__}: {e}"
            )
            return False