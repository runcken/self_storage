from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db.models import F, Sum
from datetime import date, timedelta
from django.utils.html import format_html
from decimal import Decimal


class Warehouse(models.Model):
    town = models.CharField(max_length=255, verbose_name="Расположение")
    address = models.CharField(max_length=255, verbose_name="Адрес склада")    
    description = models.TextField(verbose_name="Описание склада", blank=True)
    directions = models.TextField(verbose_name="Инструкция по проезду", blank=True)
    contacts = models.TextField(verbose_name="Контакты склада", blank=True)
    temperature = models.CharField(
        max_length=50,
        verbose_name="Температурный режим",
        default="17 °С",
        help_text="Например: 17 °С или 15-20 °С"
    )
    ceiling_height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Высота потолка всего зала (м)"
    )

    class Meta:
        verbose_name = "Склад"
        verbose_name_plural = "Склады"
        ordering = ['town', 'address']

    def __str__(self):
        return f"{self.town}, {self.address}"

    @property
    def total_units(self):
        from .models import Box
        return Box.objects.filter(box_type__warehouse=self).count()

    @property
    def occupied_units(self):
        from .models import Box
        return Box.objects.filter(box_type__warehouse=self, status='occupied').count()

    @property
    def free_units(self):
        from .models import Box
        return Box.objects.filter(box_type__warehouse=self, status='free').count()

    @property
    def min_price(self):
        free_box = Box.objects.filter(box_type__warehouse=self, status='free').order_by('box_type__price').first()
        return free_box.box_type.price if free_box else 0


class BoxType(models.Model):
    SIZE_CATEGORY_CHOICES = [
        ('small', 'До 3м³'),
        ('medium', 'До 10м³'),
        ('large', 'Свыше 10м³'),
    ]

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='box_types',
        verbose_name='Склад'
    )
    length = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Длина (м)",
        validators=[MinValueValidator(0.1)]
    )
    width = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Ширина (м)",
        validators=[MinValueValidator(0.1)]
    )
    height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Высота (м)",
        validators=[MinValueValidator(0.1)]
    )
    volume = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name="Объем (м³)",
        editable=False
    )
    category = models.CharField(
        max_length=10,
        choices=SIZE_CATEGORY_CHOICES,
        verbose_name="Категория объема",
        editable=False
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Стоимость аренды (руб/мес)",
        validators=[MinValueValidator(0)]
    )
    total_count = models.PositiveIntegerField(default=0)
    occupied_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Тип бокса"
        verbose_name_plural = "Типы боксов"
        ordering = ['volume']

    def __str__(self):
        return f"{self.volume}м³ ({self.length}x{self.width}x{self.height}м)"


class Box(models.Model):
    STATUS_CHOICES = [
        ('free', 'Свободен'),
        ('occupied', 'Занят'),
        ('maintenance', 'На обслуживании'),
    ]

    box_type = models.ForeignKey(
        BoxType,
        on_delete=models.CASCADE,
        related_name='boxes',
        verbose_name="Тип бокса")
    number = models.CharField(max_length=10, verbose_name="Номер бокса")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='free',
        verbose_name="Статус"
    )
    
    current_agreement = models.ForeignKey(
        'RentalAgreement', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='boxes_rented',
        verbose_name="Текущий договор"
    )

    class Meta:
        verbose_name = "Бокс"
        verbose_name_plural = "Боксы"
        ordering = ['number']
        unique_together = ('box_type', 'number')

    def __str__(self):
        return f"Бокс №{self.number} ({self.box_type.volume}м³) - {self.get_status_display()}"


class WarehouseImage(models.Model):
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="Склад"
    )
    image = models.ImageField(
        upload_to='warehouses/',
        verbose_name="Изображение"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок отображения"
    )

    class Meta:
        ordering = ['order']
        verbose_name = "Фотография склада"
        verbose_name_plural = "Фотографии складов"

    def __str__(self):
        return f"Фото для {self.warehouse.address}"


class Client(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='client_profile',
        verbose_name="Пользователь",
        null=True,
        blank=True
    )
    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    address = models.CharField(max_length=255, verbose_name="Адрес клиента")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    email = models.EmailField(null=True, blank=True ,verbose_name="Email")

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ['full_name']

    def __str__(self):
        return self.full_name

    @property
    def total_active_units(self):
        active_agreements = self.agreements.filter(status='active')
        total = 0
        for agreement in active_agreements:
            total += agreement.boxes.count()
        return total


class PromoCode(models.Model):
    """
    Модель для управления промокодами
    """
    code = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Промокод",
        help_text="Уникальный код для ввода пользователем"
    )
    discount_percent = models.PositiveIntegerField(
        verbose_name="Скидка (%)",
        help_text="Размер скидки в процентах (от 1 до 100)",
        validators=[MinValueValidator(1)]
    )
    max_uses = models.PositiveIntegerField(
        default=1,
        verbose_name="Максимальное количество использований",
        help_text="Сколько раз можно применить этот промокод (0 - без ограничений)"
    )
    used_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Количество использований",
        editable=False
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен"
    )
    valid_from = models.DateField(
        verbose_name="Действует с",
        default=date.today
    )
    valid_until = models.DateField(
        verbose_name="Действует до",
        null=True,
        blank=True,
        help_text="Оставьте пустым для бессрочного действия"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )

    class Meta:
        verbose_name = "Промокод"
        verbose_name_plural = "Промокоды"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} (-{self.discount_percent}%)"

    def is_valid(self):
        """Проверяет, можно ли использовать промокод"""
        today = date.today()
        if not self.is_active:
            return False
        if self.valid_from and today < self.valid_from:
            return False
        if self.valid_until and today > self.valid_until:
            return False
        if self.max_uses > 0 and self.used_count >= self.max_uses:
            return False
        return True

    def apply(self):
        """Увеличивает счетчик использований"""
        if self.is_valid():
            self.used_count += 1
            self.save()
            return True
        return False


class RentalAgreement(models.Model):
    STATUS_CHOICES = [
        ('active', 'Активен'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
        ('overdue', 'Просрочен')
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='agreements',
        verbose_name="Клиент"
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='agreements',
        verbose_name="Склад"
    )
    boxes = models.ManyToManyField(
        Box,
        related_name='agreements',
        verbose_name="Арендуемые боксы",
        # null=True,
        blank=True
    )
    start_date = models.DateField(
        verbose_name="Дата начала",
        default=date.today
    )
    end_date = models.DateField(
        verbose_name="Дата окончания",
        null=True,
        blank=True,
    )
    free_delivery = models.BooleanField(
        default=False,
        verbose_name="Бесплатный вывоз")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )

    reminder_30d_sent = models.BooleanField(
        default=False, 
        verbose_name="Напоминание за 30 дней отправлено"
    )
    reminder_14d_sent = models.BooleanField(
        default=False, 
        verbose_name="Напоминание за 14 дней отправлено"
    )
    reminder_7d_sent = models.BooleanField(
        default=False, 
        verbose_name="Напоминание за 7 дней отправлено"
    )
    reminder_3d_sent = models.BooleanField(
        default=False, 
        verbose_name="Напоминание за 3 дня отправлено"
    )
    
    # Для просроченных договоров
    overdue_notification_sent = models.BooleanField(
        default=False, 
        verbose_name="Уведомление о просрочке отправлено"
    )
    last_overdue_reminder_sent = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Дата последнего напоминания о просрочке"
    )
    grace_period_notification_sent = models.BooleanField(
        default=False, 
        verbose_name="Уведомление о льготном периоде отправлено"
    )

    promo_code = models.ForeignKey(
        PromoCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agreements',
        verbose_name="Примененный промокод"
    )

    class Meta:
        verbose_name = "Договор аренды"
        verbose_name_plural = "Договоры аренды"
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['client', 'promo_code'],
                name='unique_client_promo'
            )
        ]

    def __str__(self):
        boxes_info = ", ".join([b.number for b in self.boxes.all()[:3]])
        if self.boxes.count() > 3:
            boxes_info += "..."
        return f"{self.client.full_name} -> Боксы: {boxes_info}"

    @property
    def is_overdue(self):
        """Проверяет, просрочен ли договор"""
        if not self.end_date or self.status != 'active':
            return False
        return date.today() > self.end_date

    @property
    def is_grace_period_expired(self):
        if not self.end_date:
            return False
        grace_deadline = self.end_date + timedelta(days=180)
        return date.today() > grace_deadline

    def get_current_price_multiplier(self):
        if self.is_overdue and self.status == 'active':
            return Decimal('1.25')
        return Decimal('1.0')

    def get_total_monthly_cost(self):
        base_cost = sum(box.box_type.price for box in self.boxes.all())
        multiplier = self.get_current_price_multiplier()
        return base_cost * multiplier

    def get_total_monthly_cost_display(self):
        cost = self.get_total_monthly_cost()
        suffix = ""
        if self.is_overdue and not self.is_grace_period_expired:
            suffix = " (с наценкой 25%)"
        elif self.is_grace_period_expired:
            suffix = " (СРОЧНО ОСВОБОДИТЬ)"
        return f"{cost:.2f} руб{suffix}"
    
    def get_final_monthly_cost(self):
        """Возвращает стоимость с учетом промокода"""
        base_cost = self.get_total_monthly_cost()
        
        if self.promo_code and self.promo_code.is_valid():
            discount = base_cost * (self.promo_code.discount_percent / Decimal('100'))
            return base_cost - discount
        return base_cost

    def get_final_monthly_cost_display(self):
        """Отображает стоимость с промокодом для админки и шаблонов"""
        cost = self.get_final_monthly_cost()
        base_cost = self.get_total_monthly_cost()
        
        if self.promo_code and base_cost != cost:
            return format_html(
                '{} <span style="color:green;">(со скидкой {}% по промокоду {})</span>',
                f"{cost:.2f} руб",
                self.promo_code.discount_percent,
                self.promo_code.code
            )
        return f"{cost:.2f} руб"


class AdTransition(models.Model):
    SOURCE_CHOICES = [
        ('yandex', 'Яндекс.Директ'),
        ('google', 'Google Ads'),
        ('vk', 'VK Реклама'),
        ('telegram', 'Telegram')
    ]

    session_key = models.CharField(
        max_length=100, 
        db_index=True,
        help_text="ID сессии пользователя"
    )
    source = models.CharField(
        max_length=50,
        choices=SOURCE_CHOICES,
        verbose_name="Источник"
    )
    medium = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Тип трафика (utm_medium)"
    )
    campaign = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Компания (utm_campaign)"
    )
    term = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ключевое слово (utm_term)"
    )
    content = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Контент (utm_content)"
    )
    landing_page = models.URLField(verbose_name="Страница входа")
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата перехода"
    )
    client = models.ForeignKey(
        'Client',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ad_transitions'
        )

    class Meta:
        verbose_name = "Рекламный переход"
        verbose_name_plural = "Рекламные переходы"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_source_display()} -> {self.session_key} ({self.created_at})"
