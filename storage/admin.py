from django.contrib import admin
from django.utils.html import format_html
from datetime import date
from .models import Warehouse, WarehouseImage, Client, RentalAgreement


class WarehouseImageInline(admin.TabularInline):
    model = WarehouseImage
    extra = 1
    fields = ('image', 'order')
    ordering = ('order',)


class AgreementInline(admin.TabularInline):
    model = RentalAgreement
    extra = 1
    fields = ('warehouse', 'units_count', 'start_date', 'end_date', 'status')
    show_change_link = True


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = (
        'town',
        'warehouse_image_preview', 
        'address', 
        'unit_size_category', 
        'temperature', 
        'get_free_units_display', 
        'cost_per_unit'
    )
    
    list_filter = ('unit_size_category', 'temperature', 'address')
    search_fields = ('address', )
    list_editable = ('cost_per_unit', 'temperature')
    inlines = [WarehouseImageInline]

    readonly_fields = ('list_tenants',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('town', 'address', 'unit_size_category', 'temperature'),
            'description': 'Базовые параметры склада.'
        }),
        ('Экономика и Вместимость', {
            'fields': ('cost_per_unit', 'ceiling_height', 'total_units', 'occupied_units'),
            'description': 'Финансовые показатели и количество мест.'
        }),
        ('Контент для сайта', {
            'fields': ('description', 'directions', 'contacts'),
            'classes': ('collapse',),
            'description': 'Тексты для всплывающих окон.'
        }),
    )
    
    def get_free_units_display(self, obj):
        return f"{obj.free_units} / {obj.total_units}"
    get_free_units_display.short_description = "Свободно / Всего"

    def warehouse_image_preview(self, obj):
        first_image = obj.images.first() 
        if first_image and first_image.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 80px; border-radius: 4px; object-fit: cover;" />',
                first_image.image.url
            )
        else:
            return format_html(
                '<div style="width: 80px; height: 50px; background: #ddd; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: #777; font-size: 10px;">Нет фото</div>'
            )
    warehouse_image_preview.short_description = "Фото"

    def list_tenants(self, obj):
        agreements = obj.agreements.filter(status='active')
        if not agreements:
            return "Нет активных арендаторов"
        lines = [f"{ag.client.full_name} ({ag.units_count} мес.)" for ag in agreements]
        return format_html("<br>".join(lines))
    list_tenants.short_description = "Кто арендует"


@admin.register(WarehouseImage)
class WarehouseImageAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'order', 'image_preview')

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; border-radius: 4px;" />', obj.image.url)
        return "Нет фото"
    
    image_preview.short_description = "Превью"


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'email', 'get_total_units', 'rent_status_summary')
    search_fields = ('full_name', 'phone', 'email')
    inlines =[AgreementInline]

    def get_total_units(self, obj):
        return obj.total_active_units
    get_total_units.short_description = "Всего мест"  
    
    def rent_status_summary(self, obj):
        count = obj.agreements.filter(status='active').count()
        return f"Активных договоров: {count}"
    rent_status_summary.short_description = "Статус"


@admin.register(RentalAgreement)
class RentalAgreementAdmin(admin.ModelAdmin):
    list_display = ('client', 'warehouse', 'units_count', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'warehouse', 'start_date')
    search_fields = ('client__full_name', 'warehouse__address')
