from django import forms
from django.core.validators import MinValueValidator
from .models import RentalAgreement, Warehouse


class OrderForm(forms.ModelForm):
    """Форма заказа с калькуляцией стоимости"""
    
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all().order_by('town'),
        label='Склад',
        widget=forms.Select(attrs={'class': 'form-select fs_24 py-3'})
    )
    
    item_length = forms.DecimalField(
        min_value=0.1,
        max_value=10,
        initial=1.5,
        label='Длина вещей (м)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control fs_24 py-3',
            'step': '0.1',
            'placeholder': 'Например: 1.5'
        })
    )
    
    item_width = forms.DecimalField(
        min_value=0.1,
        max_value=10,
        initial=1.0,
        label='Ширина вещей (м)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control fs_24 py-3',
            'step': '0.1',
            'placeholder': 'Например: 1.0'
        })
    )
    
    item_height = forms.DecimalField(
        min_value=0.1,
        max_value=3.5,
        initial=2.0,
        label='Высота вещей (м)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control fs_24 py-3',
            'step': '0.1',
            'placeholder': 'Например: 2.0'
        })
    )
    
    rental_duration = forms.IntegerField(
        min_value=1,
        max_value=24,
        initial=1,
        label='Срок аренды (месяцев)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control fs_24 py-3',
            'min': 1,
            'max': 24
        })
    )
    
    start_date = forms.DateField(
        label='Дата начала аренды',
        widget=forms.DateInput(attrs={
            'class': 'form-control fs_24 py-3',
            'type': 'date'
        })
    )
    
    pdn_accepted = forms.BooleanField(
        required=True,
        label='Согласен на обработку персональных данных',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = RentalAgreement
        fields = ['warehouse', 'start_date']
    
    def calculate_price(self):
        """
        Расчет стоимости аренды на основе габаритов и срока
        """
        if not self.is_valid():
            return {
                'volume': 0,
                'monthly_price': 0,
                'total_price': 0,
                'discount_percent': 0,
                'duration': 1
            }
        
        # Расчет объема вещей
        length = self.cleaned_data['item_length']
        width = self.cleaned_data['item_width']
        height = self.cleaned_data['item_height']
        volume = length * width * height
        
        # Определение базовой цены за м³ по категориям
        if volume <= 3:
            base_price_per_m3 = 470   # До 3м³
        elif volume <= 10:
            base_price_per_m3 = 215   # До 10м³
        else:
            base_price_per_m3 = 226   # Свыше 10м³
        
        # Базовая стоимость за месяц
        base_monthly = volume * base_price_per_m3
        
        # Применение скидки за долгосрочную аренду
        duration = self.cleaned_data['rental_duration']
        discount = 0
        if duration >= 12:
            discount = 0.15  # 15% скидка за год
        elif duration >= 6:
            discount = 0.10  # 10% скидка за полгода
        
        # Итоговая цена
        monthly_price = base_monthly * (1 - discount)
        total_price = monthly_price * duration
        
        return {
            'volume': round(volume, 2),
            'monthly_price': round(monthly_price, 2),
            'total_price': round(total_price, 2),
            'discount_percent': int(discount * 100),
            'duration': duration,
            'base_price_per_m3': base_price_per_m3
        }