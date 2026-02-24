# storage/management/commands/send_telegram_reminders.py
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from datetime import date, timedelta
from storage.models import Client, RentalAgreement
from storage.notification_service import TelegramNotificationService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Отправляет Telegram-уведомления клиентам о статусе аренды'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать что было бы отправлено, без реальной отправки',
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        self.stdout.write(self.style.SUCCESS('═' * 60))
        self.stdout.write(self.style.SUCCESS('Начинаем проверку и отправку Telegram-уведомлений...'))
        self.stdout.write(self.style.SUCCESS(f'Дата: {date.today()}'))
        self.stdout.write(self.style.SUCCESS(f'Dry run: {dry_run}'))
        self.stdout.write(self.style.SUCCESS('═' * 60))
        
        today = date.today()
        stats = {
            'active_checked': 0,
            'overdue_checked': 0,
            'reminders_sent': 0,
            'overdue_notifications': 0,
            'errors': 0,
            'no_telegram': 0,
        }
        
        # 1. Обрабатываем активные договоры
        active_agreements = RentalAgreement.objects.filter(
            status='active',
            end_date__isnull=False
        ).select_related('client', 'warehouse').prefetch_related('boxes')
        
        self.stdout.write(f"\n📋 Проверка активных договоров: {active_agreements.count()} шт.")
        
        for agreement in active_agreements:
            stats['active_checked'] += 1
            
            if not self._check_client_telegram(agreement):
                stats['no_telegram'] += 1
                continue
            
            days_until_end = (agreement.end_date - today).days
            
            if days_until_end > 0:
                reminders = self._check_and_send_reminders(agreement, days_until_end, dry_run)
                stats['reminders_sent'] += reminders
            
            elif days_until_end < 0:
                overdue = self._handle_overdue_agreement(agreement, abs(days_until_end), dry_run)
                stats['overdue_notifications'] += overdue
        
        # 2. Обрабатываем просроченные договоры
        overdue_agreements = RentalAgreement.objects.filter(
            status='overdue'
        ).select_related('client', 'warehouse').prefetch_related('boxes')
        
        self.stdout.write(f"\n📋 Проверка просроченных договоров: {overdue_agreements.count()} шт.")
        
        for agreement in overdue_agreements:
            stats['overdue_checked'] += 1
            
            if not self._check_client_telegram(agreement):
                stats['no_telegram'] += 1
                continue
            
            days_overdue = (today - agreement.end_date).days if agreement.end_date else 0
            overdue = self._handle_overdue_agreement(agreement, days_overdue, dry_run)
            stats['overdue_notifications'] += overdue
        
        # Вывод статистики
        self.stdout.write(self.style.SUCCESS('\n' + '═' * 60))
        self.stdout.write(self.style.SUCCESS('СТАТИСТИКА:'))
        self.stdout.write(f"  Активных проверено: {stats['active_checked']}")
        self.stdout.write(f"  Просроченных проверено: {stats['overdue_checked']}")
        self.stdout.write(f"  Напоминаний отправлено: {stats['reminders_sent']}")
        self.stdout.write(f"  Уведомлений о просрочке: {stats['overdue_notifications']}")
        self.stdout.write(self.style.WARNING(f"  Клиентов без Telegram: {stats['no_telegram']}"))
        self.stdout.write(self.style.ERROR(f"  Ошибок: {stats['errors']}"))
        self.stdout.write(self.style.SUCCESS('═' * 60))
        self.stdout.write(self.style.SUCCESS('Проверка и отправка уведомлений завершена'))
    
    def _check_client_telegram(self, agreement):
        """Проверяет наличие Telegram у клиента"""
        if not agreement.client.telegram_chat_id or not agreement.client.telegram_linked:
            self.stdout.write(self.style.WARNING(
                f"⚠️  Договор #{agreement.id}: клиент {agreement.client.full_name} не привязал Telegram"
            ))
            return False
        
        self.stdout.write(f"✓ Договор #{agreement.id}: Telegram = {agreement.client.telegram_chat_id}")
        return True
    
    def _check_and_send_reminders(self, agreement, days_until_end, dry_run=False):
        """Проверяет и отправляет напоминания для активных договоров"""
        sent_count = 0
        
        reminder_checks = [
            (30, 'reminder_30d_sent', TelegramNotificationService.send_reminder_30d),
            (14, 'reminder_14d_sent', TelegramNotificationService.send_reminder_14d),
            (7, 'reminder_7d_sent', TelegramNotificationService.send_reminder_7d),
            (3, 'reminder_3d_sent', TelegramNotificationService.send_reminder_3d),
        ]
        
        for days, flag_field, send_func in reminder_checks:
            if days_until_end <= days and not getattr(agreement, flag_field):
                self.stdout.write(
                    self.style.WARNING(
                        f"📧 Отправка напоминания за {days} дней для договора #{agreement.id} "
                        f"(клиент: {agreement.client.full_name})"
                    )
                )
                
                if not dry_run:
                    try:
                        success = send_func(agreement)
                        if success:
                            sent_count += 1
                        else:
                            self.stdout.write(self.style.ERROR(f"   ❌ Ошибка отправки"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"   ❌ Исключение: {e}"))
                else:
                    self.stdout.write(f"   [DRY RUN] Письмо не отправлено")
                    sent_count += 1
        
        return sent_count
    
    def _handle_overdue_agreement(self, agreement, days_overdue, dry_run=False):
        """Обрабатывает просроченные договоры"""
        sent_count = 0
        
        if agreement.status == 'active' and days_overdue > 0:
            agreement.status = 'overdue'
            if not dry_run:
                agreement.save(update_fields=['status'])
            self.stdout.write(
                self.style.WARNING(
                    f"📝 Статус договора #{agreement.id} изменен на 'overdue'"
                )
            )
        
        if not agreement.overdue_notification_sent:
            self.stdout.write(
                self.style.WARNING(
                    f"📧 Отправка первого уведомления о просрочке для договора #{agreement.id}"
                )
            )
            
            if not dry_run:
                try:
                    success = TelegramNotificationService.send_overdue_notification(agreement)
                    if success:
                        sent_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ Исключение: {e}"))
        
        if days_overdue > 0:
            monthly = self._send_monthly_reminder_if_needed(agreement, days_overdue, dry_run)
            sent_count += monthly
        
        if agreement.is_grace_period_expired and not agreement.grace_period_notification_sent:
            self.stdout.write(
                self.style.WARNING(
                    f"📧 Отправка уведомления об окончании льготного периода для договора #{agreement.id}"
                )
            )
            
            if not dry_run:
                try:
                    TelegramNotificationService.send_grace_period_expired_notification(agreement)
                    sent_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ Исключение: {e}"))
        
        return sent_count
    
    def _send_monthly_reminder_if_needed(self, agreement, days_overdue, dry_run=False):
        """Отправляет ежемесячное напоминание"""
        sent_count = 0
        
        if days_overdue >= 30:
            last_reminder = agreement.last_overdue_reminder_sent
            
            if not last_reminder:
                self.stdout.write(
                    self.style.WARNING(
                        f"📧 Отправка первого ежемесячного напоминания для договора #{agreement.id}"
                    )
                )
                
                if not dry_run:
                    try:
                        success = TelegramNotificationService.send_monthly_overdue_reminder(agreement)
                        if success:
                            sent_count += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"   ❌ Исключение: {e}"))
            else:
                days_since_last = (date.today() - last_reminder).days
                if days_since_last >= 30:
                    self.stdout.write(
                        self.style.WARNING(
                            f"📧 Отправка ежемесячного напоминания для договора #{agreement.id}"
                        )
                    )
                    
                    if not dry_run:
                        try:
                            success = TelegramNotificationService.send_monthly_overdue_reminder(agreement)
                            if success:
                                sent_count += 1
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"   ❌ Исключение: {e}"))
        
        return sent_count