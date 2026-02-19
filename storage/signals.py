from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver
from .models import RentalAgreement, Box, BoxType


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
        