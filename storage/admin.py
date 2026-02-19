from django.contrib import admin
from django.utils.html import format_html
from django.db.models import F
from django import forms
from .models import Warehouse, BoxType, Box, WarehouseImage, Client, RentalAgreement


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
        print(f"ADMIN DEBUG TOTAL: ID={obj.id}, Count={count}")
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
        print(f"DEBUG ADMIN FREE: ID={obj.id}, ID={obj.id}. Free={count}")
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
            'boxes': forms.SelectMultiple(attrs={'class': 'selectfilter', 'data-field-name': 'боксы', 'data-is-stacked': '0'}),
        }

    def clean_boxes(self):
        boxes = self.cleaned_data.get('boxes')
        warehouse = self.cleaned_data.get('warehouse')
        if warehouse and boxes:
            valid_boxes_ids = boxes.filter(box_type__warehouse=warehouse).values_list('id', flat=True)
            selected_ids = [b.id for b in boxes]
            invalid_ids = set(selected_ids) - set(valid_boxes_ids)
            if invalid_ids:
                raise forms.ValidationError("Выбраны боксы, не принадлежащие указанному складу")

        return boxes

@admin.register(RentalAgreement)
class RentalAgreementAdmin(admin.ModelAdmin):
    form = RentalAgreementForm
    list_display = ('client', 'warehouse', 'get_boxes_list', 'status', 'start_date')
    list_filter = ('status', 'warehouse', 'boxes__status')
    search_fields = ('client__full_name', 'warehouse__address')
    
    fieldsets = (
        ('Стороны договора', {'fields': ('client', 'warehouse')}),
        ('Предмет аренды', {'fields': ('boxes',)}),
        ('Сроки и статус', {'fields': ('start_date', 'end_date', 'status')}),
    )

    def get_boxes_list(self, obj):
        return ", ".join([b.number for b in obj.boxes.all()])
    get_boxes_list.short_description = "Боксы"


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'email', 'total_active_units')
    search_fields = ('full_name', 'phone', 'email')

    def total_active_units(self, obj):
        return obj.total_active_units
    total_active_units.short_description = "Активных мест"
    total_active_units.admin_order_field = 'id'
