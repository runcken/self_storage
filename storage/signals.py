from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import date
from .models import RentalAgreement, Box, BoxType
from .notification_service import TelegramNotificationService


@receiver(pre_save, sender=BoxType)
def calculate_box_properties(sender, instance, **kwargs):
    if instance.length and instance.width and instance.height:
        instance.volume = instance.length * instance.width * instance.height
        
        if instance.volume <= 3:
            instance.category = 'small'
        elif instance.volume <= 10:
            instance.category = 'medium'
        else:
            instance.category = 'large'
    else:
        instance.volume = 0
        instance.category = 'small'


@receiver(m2m_changed, sender=RentalAgreement.boxes.through)
def handle_boxes_m2m_change(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in ['post_add', 'post_remove', 'post_clear']:
        return

    if instance.status != 'active':
        if action == 'post_clear':
            instance.boxes.update(status='free', current_agreement=None)
        elif pk_set:
            Box.objects.filter(pk__in=pk_set).update(status='free', current_agreement=None)
        return

    if action == 'post_add' and pk_set:
        affected_boxes = Box.objects.filter(pk__in=pk_set)
        affected_boxes.update(status='occupied', current_agreement=instance)
        
    elif action == 'post_remove' and pk_set:
        affected_boxes = Box.objects.filter(pk__in=pk_set)
        affected_boxes.update(status='free', current_agreement=None)
        
    elif action == 'post_clear':
        instance.boxes.update(status='free', current_agreement=None)

@receiver(post_save, sender=RentalAgreement)
def handle_status_change(sender, instance, created, **kwargs):
    if created:
        return

    if instance.status == 'active':
        instance.boxes.filter(status='free').update(status='occupied', current_agreement=instance)
    
    else:
        instance.boxes.filter(current_agreement=instance).update(status='free', current_agreement=None)
        
        
@receiver(pre_save, sender=RentalAgreement)
def check_agreement_date_change(sender, instance, **kwargs):
    """Проверяет уведомления при изменении даты окончания договора"""
    if not instance.pk:  # Новый договор
        return
    
    try:
        old_instance = RentalAgreement.objects.get(pk=instance.pk)
    except RentalAgreement.DoesNotExist:
        return
    
    # Проверяем, изменилась ли дата окончания
    if old_instance.end_date != instance.end_date and instance.end_date:
        today = date.today()
        days_until_end = (instance.end_date - today).days
        
        # Проверяем каждый интервал
        if days_until_end <= 30 and not instance.reminder_30d_sent:
            TelegramNotificationService.send_reminder_30d(instance)
        if days_until_end <= 14 and not instance.reminder_14d_sent:
            TelegramNotificationService.send_reminder_14d(instance)
        if days_until_end <= 7 and not instance.reminder_7d_sent:
            TelegramNotificationService.send_reminder_7d(instance)
        if days_until_end <= 3 and not instance.reminder_3d_sent:
            TelegramNotificationService.send_reminder_3d(instance)
        if days_until_end < 0 and not instance.overdue_notification_sent:
            TelegramNotificationService.send_overdue_notification(instance)        
        