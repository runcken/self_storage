from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import date, timedelta
from storage.models import Client, RentalAgreement
from storage.notification_service import EmailNotificationService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Отправляет уведомления клиентам о статусе аренды'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Начинаем проверку и отправку уведомлений...'))
        
        today = date.today()
        
        # 1. Обрабатываем активные договоры, которые еще не истекли
        active_agreements = RentalAgreement.objects.filter(
            status='active',
            end_date__isnull=False
        )
        
        for agreement in active_agreements:
            days_until_end = (agreement.end_date - today).days
            
            # Проверяем и отправляем напоминания в зависимости от оставшихся дней
            if days_until_end > 0:
                self._check_and_send_reminders(agreement, days_until_end)
            
            # Если договор просрочен, но статус еще активный
            elif days_until_end < 0:
                self._handle_overdue_agreement(agreement, abs(days_until_end))
        
        # 2. Обрабатываем договоры со статусом 'overdue'
        overdue_agreements = RentalAgreement.objects.filter(status='overdue')
        for agreement in overdue_agreements:
            days_overdue = (today - agreement.end_date).days if agreement.end_date else 0
            self._handle_overdue_agreement(agreement, days_overdue)
        
        self.stdout.write(self.style.SUCCESS('Проверка и отправка уведомлений завершена'))
    
    def _check_and_send_reminders(self, agreement, days_until_end):
        """Проверяет и отправляет напоминания для активных договоров"""
        
        reminder_checks = [
            (30, 'reminder_30d_sent', EmailNotificationService.send_reminder_30d),
            (14, 'reminder_14d_sent', EmailNotificationService.send_reminder_14d),
            (7, 'reminder_7d_sent', EmailNotificationService.send_reminder_7d),
            (3, 'reminder_3d_sent', EmailNotificationService.send_reminder_3d),
        ]
        
        for days, flag_field, send_func in reminder_checks:
            if days_until_end <= days and not getattr(agreement, flag_field):
                self.stdout.write(
                    self.style.WARNING(
                        f"Отправка напоминания за {days} дней для договора #{agreement.id}"
                    )
                )
                send_func(agreement)
    
    def _handle_overdue_agreement(self, agreement, days_overdue):
        """Обрабатывает просроченные договоры"""
        
        # Если договор активный, но просрочен - меняем статус на overdue
        if agreement.status == 'active' and days_overdue > 0:
            agreement.status = 'overdue'
            agreement.save(update_fields=['status'])
            self.stdout.write(
                self.style.WARNING(
                    f"Статус договора #{agreement.id} изменен на 'overdue'"
                )
            )
        
        # Отправляем первое уведомление о просрочке, если еще не отправляли
        if not agreement.overdue_notification_sent:
            self.stdout.write(
                self.style.WARNING(
                    f"Отправка первого уведомления о просрочке для договора #{agreement.id}"
                )
            )
            EmailNotificationService.send_overdue_notification(agreement)
        
        # Отправляем ежемесячные напоминания
        if days_overdue > 0:
            self._send_monthly_reminder_if_needed(agreement, days_overdue)
        
        # Проверяем окончание льготного периода
        if agreement.is_grace_period_expired and not agreement.grace_period_notification_sent:
            self.stdout.write(
                self.style.WARNING(
                    f"Отправка уведомления об окончании льготного периода для договора #{agreement.id}"
                )
            )
            EmailNotificationService.send_grace_period_expired_notification(agreement)
    
    def _send_monthly_reminder_if_needed(self, agreement, days_overdue):
        """Отправляет ежемесячное напоминание, если прошло больше месяца с последнего"""
        
        # Отправляем напоминание раз в месяц
        if days_overdue >= 30:
            # Проверяем, когда было последнее напоминание
            last_reminder = agreement.last_overdue_reminder_sent
            
            if not last_reminder:
                # Если ни разу не отправляли ежемесячное напоминание, но первое уже было
                self.stdout.write(
                    self.style.WARNING(
                        f"Отправка первого ежемесячного напоминания для договора #{agreement.id}"
                    )
                )
                EmailNotificationService.send_monthly_overdue_reminder(agreement)
            else:
                # Проверяем, прошло ли больше месяца с последнего напоминания
                days_since_last = (date.today() - last_reminder).days
                if days_since_last >= 30:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Отправка ежемесячного напоминания для договора #{agreement.id}"
                        )
                    )
                    EmailNotificationService.send_monthly_overdue_reminder(agreement)