from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from datetime import date

class Warehouse(models.Model):
    SIZE_CHOICES = [
        ('small', 'До 3 м²'),
        ('medium', 'До 10 м²'),
        ('large', 'От 10 м²'),
    ]
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
    	verbose_name="Высота потолка (м)"
    )
    cost_per_unit = models.DecimalField(
        max_digits=10, decimal_places=2, 
        verbose_name="Стоимость одного места (руб.)",
        validators=[MinValueValidator(0)]
    )
    unit_size_category = models.CharField(
    	max_length=10,
    	choices=SIZE_CHOICES,
    	verbose_name="Категория размера места"
    )
    total_units = models.PositiveIntegerField(
    	default=0,
    	verbose_name="Общее количество мест"
    )
    occupied_units = models.PositiveIntegerField(
    	default=0,
    	verbose_name="Количество занятых мест"
    )

    class Meta:
        verbose_name = "Склад"
        verbose_name_plural = "Склады"
        ordering = ['address']

    def __str__(self):
        return self.address

    @property
    def free_units(self):
        return max(0, self.total_units - self.occupied_units)

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
    email = models.EmailField(verbose_name="Электронная почта")
    required_units = models.PositiveIntegerField(
    	default=0,
    	verbose_name="Количество занятых мест"
    )
    rent_start_date = models.DateField(
    	verbose_name="Дата начала аренды",
    	default=date.today
    )
    rent_end_date = models.DateField(
    	verbose_name="Дата окончания аренды",
    	null=True,
    	blank=True
    )

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ['full_name']

    def __str__(self):
        return self.full_name

    @property
    def is_rent_active(self):
        if self.rent_end_date and date.today() > self.rent_end_date:
            return False
        return True

    @property
    def days_remaining(self):
        if not self.rent_end_date:
            return None
        return max(0, (self.rent_end_date - date.today()).days)
