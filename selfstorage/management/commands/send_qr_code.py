# storage/management/commands/send_qr_code.py
from django.core.management.base import BaseCommand, CommandError
from storage.models import RentalAgreement
from storage.notification_service import TelegramNotificationService

class Command(BaseCommand):
    help = 'Отправляет QR-код для доступа к боксу'
    
    def add_arguments(self, parser):
        parser.add_argument('agreement_id', type=int, help='ID договора')
    
    def handle(self, *args, **options):
        agreement_id = options['agreement_id']
        
        try:
            agreement = RentalAgreement.objects.get(id=agreement_id)
        except RentalAgreement.DoesNotExist:
            raise CommandError(f'Договор #{agreement_id} не найден')
        
        self.stdout.write(f'Отправка QR-кода для договора #{agreement_id}...')
        
        success = TelegramNotificationService.send_qr_code_for_access(agreement)
        
        if success:
            self.stdout.write(self.style.SUCCESS('QR-код отправлен'))
        else:
            self.stdout.write(self.style.ERROR('Ошибка отправки'))