from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import F, Q
from django.utils.safestring import mark_safe
from django import forms
from datetime import date
from .models import Warehouse, BoxType, Box, WarehouseImage, Client, RentalAgreement, PromoCode


class RentStatusFilter(admin.SimpleListFilter):
    title = 'Статус аренды'
    parameter_name = 'rent_status'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Активные'),
            ('expired', 'Просроченные'),
            ('future', 'Будущие'),
            ('indefinite', 'Бессрочные'),
        )

    def queryset(self, request, queryset):
        today = date.today()

        if self.value() == 'active':
            return queryset.filter(
                status='active'
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=today)
            )

        if self.value() == 'expired':
            return queryset.filter(
                status='active',
                end_date__lt=today
            )

        if self.value() == 'future':
            return queryset.filter(
                start_date__gt=today
            )

        if self.value() == 'indefinite':
            return queryset.filter(
                status='active',
                end_date__isnull=True
            )

        return queryset


class BoxTypeInline(admin.StackedInline):
    model = BoxType
    extra = 0
    
    fieldsets = (
        (None, {
            'fields': ('length', 'width', 'height'),
            'description': 'Введите размеры. Объем и категория рассчитаются автоматически.'
        }),
        ('Автоматические параметры', {
            'fields': ('volume', 'category'),
            'classes': ('collapse',),
        }),
        ('Экономика и наличие', {
            'fields': ('price',)
        }),
    )
    
    readonly_fields = ('volume', 'category')
    ordering = ('volume',)

    def get_dimensions(self, obj):
        if obj.pk:
            return f"{obj.length} x {obj.width} x {obj.height} м"
        return "Введите размеры"
    get_dimensions.short_description = "Размеры (ДхШхВ)"


class WarehouseImageInline(admin.TabularInline):
    model = WarehouseImage
    extra = 1
    fields = ('image', 'order', 'image_preview')
    readonly_fields = ('image_preview',)
    ordering = ('order',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; border-radius: 4px;" />', obj.image.url)
        return "Нет фото"
    image_preview.short_description = "Превью"


class BoxInline(admin.TabularInline):
    model = Box
    extra = 0
    fields = ('number', 'box_type', 'status', 'current_agreement')
    readonly_fields = ('current_agreement',)
    can_delete = True


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('town', 'address', 'get_total_boxes', 'get_occupied_boxes', 'get_free_boxes', 'get_min_price')
    list_filter = ('town', 'box_types__category')
    search_fields = ('address', 'town')
    
    inlines = [BoxTypeInline, WarehouseImageInline]
    
    fieldsets = (
        ('Локация', {'fields': ('town', 'address')}),
        ('Характеристики здания', {'fields': ('ceiling_height', 'temperature')}),
        ('Инфо для сайта', {'fields': ('description', 'directions', 'contacts'), 'classes': ('collapse',)}),
    )

    def get_total_boxes(self, obj):
        from .models import Box
        count = Box.objects.filter(box_type__warehouse_id=obj.id).count()
        return count
    get_total_boxes.short_description = "Всего боксов"
    get_total_boxes.admin_order_field = 'id'

    def get_occupied_boxes(self, obj):
        from .models import Box
        count = Box.objects.filter(box_type__warehouse_id=obj.id, status='occupied').count()
        return count
    get_occupied_boxes.short_description = "Занято"
    get_occupied_boxes.admin_order_field = 'id'       

    def get_free_boxes(self, obj):
        from .models import Box
        count = Box.objects.filter(box_type__warehouse_id=obj.id, status='free').count()
        return count
    get_free_boxes.short_description = "Свободно"
    get_free_boxes.admin_order_field = 'id'

    def get_min_price(self, obj):
        from .models import Box
        price = Box.objects.filter(box_type__warehouse_id=obj.id, status='free').select_related('box_type').order_by('box_type__price').first()
        if price:
            return f"{price.box_type.price} руб"
        return "—"
    get_min_price.short_description = "Цена от"
    get_min_price.admin_order_field = 'id'


@admin.register(BoxType)
class BoxTypeAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'get_dimensions', 'volume', 'category', 'price', 'get_total_boxes_count', 'get_free_boxes_count')
    list_filter = ('category', 'warehouse')
    search_fields = ('warehouse__address',)
    readonly_fields = ('volume', 'category')
    inlines = [BoxInline]

    def get_dimensions(self, obj):
        return f"{obj.length} x {obj.width} x {obj.height}"
    get_dimensions.short_description = "Размеры"

    def get_total_boxes_count(self, obj):
        return obj.boxes.count()
    get_total_boxes_count.short_description = "Всего боксов"

    def get_free_boxes_count(self, obj):
        return obj.boxes.filter(status='free').count()
    get_free_boxes_count.short_description = "Свободно"


@admin.register(Box)
class BoxAdmin(admin.ModelAdmin):
    list_display = ('number', 'box_type', 'warehouse', 'status', 'current_agreement')
    list_filter = ('status', 'box_type__category', 'box_type__warehouse')
    search_fields = ('number', 'box_type__warehouse__address')
    readonly_fields = ('current_agreement',)

    def warehouse(self, obj):
        return obj.box_type.warehouse
    warehouse.short_description = "Склад"


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = (
        'code', 
        'discount_percent', 
        'max_uses', 
        'is_active', 
        'valid_from', 
        'valid_until',
        'status_display'
    )
    list_filter = ('is_active', 'valid_from', 'valid_until')
    search_fields = ('code',)
    readonly_fields = ('created_at', 'usage_statistics')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('code', 'discount_percent', 'is_active')
        }),
        ('Срок действия', {
            'fields': ('valid_from', 'valid_until'),
            'description': 'Оставьте "Действует до" пустым для бессрочного действия'
        }),
        ('Ограничения', {
            'fields': ('max_uses',),
            'description': 'max_uses=0 - без ограничений'
        }),
        ('Статистика использования', {
            'fields': ('usage_statistics', 'created_at'),
            'classes': ('collapse',),
        }),
    )
    
    def status_display(self, obj):
        if obj.is_valid():
            return format_html('<span style="color:green;">✓ Активен</span>', '')
        else:
            return format_html('<span style="color:red;">✗ Не активен</span>', '')
    status_display.short_description = "Статус"
    
    def usage_statistics(self, obj):
        if not obj.pk:
            return "Сохраните промокод для просмотра статистики"
        
        agreements = obj.agreements.all()
        total_uses = agreements.count()
        
        if total_uses > 0:
            last_use = agreements.order_by('-created_at').first().created_at.strftime('%d.%m.%Y %H:%M')
        else:
            last_use = '—'
        
        return format_html(
            '<div>'
            '<p><strong>Всего применений:</strong> {}</p>'
            '<p><strong>Последнее использование:</strong> {}</p>'
            '</div>',
            total_uses,
            last_use
        )
    usage_statistics.short_description = "Статистика"
    
    actions = ['activate_promocodes', 'deactivate_promocodes']
    
    def activate_promocodes(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"Активировано {queryset.count()} промокодов")
    activate_promocodes.short_description = "Активировать выбранные промокоды"
    
    def deactivate_promocodes(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано {queryset.count()} промокодов")
    deactivate_promocodes.short_description = "Деактивировать выбранные промокоды"


class RentalAgreementForm(forms.ModelForm):
    class Meta:
        model = RentalAgreement
        fields = '__all__'
        widgets = {
            'boxes': forms.SelectMultiple(attrs={
                'class': 'selectfilter',
                'data-field-name': 'боксы', 
                'data-is-stacked': '0',
                'id': 'id_boxes_select'
            }),
            'warehouse': forms.Select(attrs={'id': 'id_warehouse_select'})
        }

    class Media:
        js = ('storage/js/dependent_boxes.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['promo_code'].required = False
        self.fields['promo_code'].label = "Выберите промокод из списка"
        self.fields['promo_code'].help_text = "Каждый промокод можно использовать только один раз для одного клиента"

    def clean(self):
        cleaned_data = super().clean()
        client = cleaned_data.get('client')
        promo_code = cleaned_data.get('promo_code')
        
        # Проверяем уникальность client + promo_code
        if client and promo_code:
            # Если это редактирование существующего договора
            if self.instance and self.instance.pk:
                # Проверяем, есть ли другой договор у этого клиента с таким же промокодом
                existing = RentalAgreement.objects.filter(
                    client=client,
                    promo_code=promo_code
                ).exclude(pk=self.instance.pk).exists()
            else:
                # Для нового договора
                existing = RentalAgreement.objects.filter(
                    client=client,
                    promo_code=promo_code
                ).exists()
            
            if existing:
                raise forms.ValidationError(
                    f"Клиент {client} уже использовал промокод {promo_code.code}. "
                    "Каждый промокод можно использовать только один раз для одного клиента."
                )
        
        return cleaned_data


@admin.register(RentalAgreement)
class RentalAgreementAdmin(admin.ModelAdmin):
    form = RentalAgreementForm
    list_display = (
        'client',
        'warehouse',
        'get_boxes_list',
        'status',
        'start_date',
        'status_display',
        'get_price_with_promo',
        'promo_code_display'
    )
    list_filter = ('status', RentStatusFilter, 'warehouse', 'boxes__status')
    search_fields = ('client__full_name', 'warehouse__address', 'promo_code__code')
    
    fieldsets = (
        ('Стороны договора', {'fields': ('client', 'warehouse')}),
        ('Предмет аренды', {'fields': ('boxes',)}),
        ('Сроки и статус', {'fields': ('start_date', 'end_date', 'status')}),
        ('Промокод', {
            'fields': ('promo_code',),
            'description': 'Выберите промокод из списка (оставьте пустым, если не применяется)'
        }),
        ('Финансы', {
            'fields': ('price_display',),
            'description': 'Стоимость'
        }),
    )

    readonly_fields = ('price_display',)

    def get_boxes_list(self, obj):
        if not obj.pk:
            return "-"
        return ", ".join([b.number for b in obj.boxes.all()[:3]])
    get_boxes_list.short_description = "Боксы"

    def status_display(self, obj):
        if not obj.pk:
            return "-"
        if obj.status != 'active':
            return obj.get_status_display()
        if obj.end_date and obj.end_date < date.today():
            return format_html('<span style="color:red;">Просрочен</span>', '')
        if obj.end_date and obj.end_date == date.today():
            return format_html('<span style="color:orange;">Заканчивается сегодня</span>', '')
        return format_html('<span style="color:green;">Активен</span>', '')
    status_display.short_description = "Статус срока"

    def get_price_with_promo(self, obj):
        if not obj.pk:
            return "-"
        try:
            return f"{obj.get_final_monthly_cost():.2f} ₽"
        except Exception:
            return "-"
    get_price_with_promo.short_description = "Стоимость/мес"

    def promo_code_display(self, obj):
        if obj.promo_code:
            return format_html(
                '{} (-{}%)',
                obj.promo_code.code,
                obj.promo_code.discount_percent
            )
        return "-"
    promo_code_display.short_description = "Промокод"

    def price_display(self, obj):
        if not obj.pk:
            return "Сохраните договор для расчета"
        try:
            return obj.get_final_monthly_cost_display()
        except Exception:
            return "Ошибка расчета"
    price_display.short_description = "Итоговая стоимость"


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'email', 'total_active_units')
    search_fields = ('full_name', 'phone', 'email')

    def total_active_units(self, obj):
        return obj.total_active_units
    total_active_units.short_description = "Активных мест"
    total_active_units.admin_order_field = 'id'


# @admin.register(AdTransition)
# """
# счетчик рекламных переходов
# """
# class AdTransitionAdmin(admin.ModelAdmin):
#     list_display = (
#         'created_at',
#         'source',
#         'medium',
#         'campaign',
#         'session_key',
#         'client'
#     )
#     list_filter = ('source', 'medium', 'created_at')
#     search_fields = ('campaign', 'session_key', 'client__full_name')
