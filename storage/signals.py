from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import RentalAgreement, Warehouse


def recalculate_warehouse_units(warehouse):
    if not warehouse:
        return

    total_occupied = sum(
        agreement.units_count 
        for agreement in warehouse.agreements.filter(status='active')
    )
    
    warehouse.occupied_units = total_occupied
    warehouse.save(update_fields=['occupied_units'])


@receiver(post_save, sender=RentalAgreement)
def on_agreement_save(sender, instance, created, **kwargs):
    recalculate_warehouse_units(instance.warehouse)


@receiver(post_delete, sender=RentalAgreement)
def on_agreement_delete(sender, instance, **kwargs):
    if instance.status == 'active':
        warehouse = instance.warehouse
        warehouse.occupied_units = max(0, warehouse.occupied_units - instance.units_count)
        warehouse.save(update_fields=['occupied_units'])
        