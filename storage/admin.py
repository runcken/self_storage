from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import F, Q
from django.utils.safestring import mark_safe
from django import forms
from datetime import date
from .models import Warehouse, BoxType, Box, WarehouseImage, Client, RentalAgreement, AdTransition


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


@admin.register(RentalAgreement)
class RentalAgreementAdmin(admin.ModelAdmin):
    form = RentalAgreementForm
    list_display = (
        'client',
        'warehouse',
        'get_boxes_list',
        'status',
        'start_date',
        'is_expired_display',
        'get_price_with_penalty'
    )
    list_filter = ('status', RentStatusFilter, 'warehouse', 'boxes__status')
    search_fields = ('client__full_name', 'warehouse__address')
    
    fieldsets = (
        ('Стороны договора', {'fields': ('client', 'warehouse')}),
        ('Предмет аренды', {'fields': ('boxes',)}),
        ('Сроки и статус', {'fields': ('start_date', 'end_date', 'status')}),
        ('Финансы', {
            'fields': ('display_current_cost',),
            'description': 'Стоимость'
            }),
    )

    readonly_fields = ('display_current_cost',)

    def get_boxes_list(self, obj):
        if not obj.pk or not hasattr(obj, '_prefetched_objects_cache'):
            return "-"
        try:
            return ", ".join([b.number for b in obj.boxes.all()])
        except Exception:
            return "-"
    get_boxes_list.short_description = "Боксы"

    def is_expired_display(self, obj):
        if not obj.pk:
            return "-"
        if obj.status != 'active':
            return "-"
        if obj.end_date and obj.end_date < date.today():
            return format_html('<span style="color:red;">{}</span>', "Просрочен")
        if obj.end_date and obj.end_date == date.today():
            return format_html('<span style="color:orange;">{}</span>', "Заканчивается сегодня")
        return format_html('<span style="color:green;">{}</span>', "OK")
    is_expired_display.short_description = "Статус срока"

    def get_price_with_penalty(self, obj):
        if not obj.pk:
            return "-"
        try:
            cost = obj.get_total_monthly_cost()
            if obj.is_overdue and not obj.is_grace_period_expired:
                return format_html('<span style="color:red; font-weight:bold;">{} ₽ ( +25%)</span>', cost)
            elif obj.is_grace_period_expired:
                return format_html('<span style="color:red; font-weight:bold;">{} ₽ (ИСТЕК СРОК)</span>', cost)
            return f"{cost} ₽"
        except Exception:
            return "-"
    get_price_with_penalty.short_description = "Стоимость/мес"

    # def is_overdue_warning(self, obj):
    #     if not obj.pk or not obj.end_date:
    #         return "-"
    #     try:
    #         if obj.is_grace_period_expired:
    #             return format_html('<span style="color:red; font-weight:bold;">ОСВОБОДИТЬ СРОЧНО</span>')
    #         if obj.is_overdue:
    #             days_overdue = (date.today() - obj.end_date).days
    #             return format_html('<span style="color:orange;">Просрочен на {} дн.</span>', days_overdue)
    #         return "-"
    #     except Exception:
    #         return "-"
    # is_overdue_warning.short_description = "Статус срока"

    def display_current_cost(self, obj):
        if not obj.pk:
            return "Сохраните договор, чтобы увидеть расчет стоимости"
        try:
            base = sum(b.box_type.price for b in obj.boxes.all())
            mult = obj.get_current_price_multiplier()
            total = base * mult
        
            text = f"Базовая цена: {base} руб.\n"
            if mult > 1:
                text += f"Коэффициент просрочки: x{mult}\n"
            text += f"Итого к оплате: {total} руб."
            return text
        except Exception:
            return "Ошибка расчета"
    display_current_cost.short_description = "Детали расчета"   

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)


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
