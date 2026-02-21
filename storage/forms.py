from django import forms
from django.core.exceptions import ValidationError
from .models import Warehouse, Box


class OrderForm(forms.Form):
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all().order_by('town'),
        label='Склад',
        widget=forms.Select(attrs={
            'class': 'form-select fs_24 py-3',
            'id': 'id_warehouse'
        })
    )
    
    rental_duration = forms.IntegerField(
        min_value=1, max_value=24, initial=1,
        label='Срок аренды (месяцев)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control fs_24 py-3',
            'id': 'id_duration'
        })
    )
    
    start_date = forms.DateField(
        label='Дата начала',
        widget=forms.DateInput(attrs={
            'class': 'form-control fs_24 py-3',
            'type': 'date',
            'id': 'id_start_date'
        })
    )
    
    pdn_accepted = forms.BooleanField(
        required=True,
        label='Согласен на обработку персональных данных',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_pdn'
        })
    )
    
    mode = forms.ChoiceField(
        choices=[('manual', 'Ручной'), ('auto', 'Авто')],
        initial='manual',
        widget=forms.HiddenInput(attrs={'id': 'id_mode'})
    )
    
    selected_box = forms.ModelChoiceField(
        queryset=Box.objects.filter(status='free'),
        label='Выберите бокс',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select fs_24 py-3',
            'id': 'id_selected_box'
        })
    )
    
    need_length = forms.DecimalField(
        min_value=0.1, max_value=10, initial=1.5,
        label='Длина (м)',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control fs_24 py-3',
            'id': 'id_need_length',
            'step': '0.1'
        })
    )
    
    need_width = forms.DecimalField(
        min_value=0.1, max_value=10, initial=1.0,
        label='Ширина (м)',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control fs_24 py-3',
            'id': 'id_need_width',
            'step': '0.1'
        })
    )
    
    need_height = forms.DecimalField(
        min_value=0.1, max_value=3.5, initial=2.0,
        label='Высота (м)',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control fs_24 py-3',
            'id': 'id_need_height',
            'step': '0.1'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['selected_box'].queryset = Box.objects.filter(
            status='free'
        ).select_related('box_type', 'box_type__warehouse')
    
    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get('mode')
        warehouse = cleaned_data.get('warehouse')
        
        if mode == 'manual':
            selected_box = cleaned_data.get('selected_box')
            
            if not selected_box:
                raise ValidationError('Выберите конкретный бокс')
            
            if selected_box.box_type.warehouse != warehouse:
                raise ValidationError(
                    f'Бокс №{selected_box.number} находится на другом складе'
                )
            
            if selected_box.status != 'free':
                raise ValidationError(
                    f'Бокс №{selected_box.number} уже занят'
                )
            
            cleaned_data['box_length'] = selected_box.box_type.length
            cleaned_data['box_width'] = selected_box.box_type.width
            cleaned_data['box_height'] = selected_box.box_type.height
            cleaned_data['box_volume'] = selected_box.box_type.volume
            
        else:
            length = cleaned_data.get('need_length')
            width = cleaned_data.get('need_width')
            height = cleaned_data.get('need_height')
            
            if not all([length, width, height]):
                raise ValidationError('Укажите все три размера')
            
            volume_needed = length * width * height
            cleaned_data['volume_needed'] = volume_needed
            
            suitable_box = Box.objects.filter(
                box_type__warehouse=warehouse,
                status='free',
                box_type__volume__gte=volume_needed
            ).order_by('box_type__volume').first()
            
            if not suitable_box:
                any_free = Box.objects.filter(
                    box_type__warehouse=warehouse,
                    status='free'
                ).exists()
                
                if any_free:
                    raise ValidationError(
                        f'Нет бокса под объём {volume_needed:.2f}м³. '
                        f'Переключитесь в ручной режим или выберите другой склад.'
                    )
                else:
                    raise ValidationError(
                        f'На складе {warehouse} нет свободных боксов'
                    )
            
            cleaned_data['selected_box'] = suitable_box
            cleaned_data['box_length'] = suitable_box.box_type.length
            cleaned_data['box_width'] = suitable_box.box_type.width
            cleaned_data['box_height'] = suitable_box.box_type.height
            cleaned_data['box_volume'] = suitable_box.box_type.volume
        
        return cleaned_data
    
    def calculate_price(self):

        default_result = {
            'volume': 0,
            'monthly_price': 0,
            'total_price': 0,
            'discount_percent': 0,
            'duration': 1,
        }
        
        if not self.is_valid():
            return default_result
        
        try:
            cleaned_data = self.cleaned_data
            box = cleaned_data['selected_box']
            duration = cleaned_data['rental_duration']
            
            monthly_price = float(box.box_type.price)
            
            discount = 0
            if duration >= 12:
                discount = 0.15
            elif duration >= 6:
                discount = 0.10
            
            final_monthly = monthly_price * (1 - discount)
            total = final_monthly * duration
            
            return {
                'volume': float(box.box_type.volume),
                'monthly_price': round(final_monthly, 2),
                'total_price': round(total, 2),
                'discount_percent': int(discount * 100),
                'duration': duration,
                'box_number': box.number,
                'box_dimensions': f"{box.box_type.length}×{box.box_type.width}×{box.box_type.height}",
                'warehouse': str(box.box_type.warehouse),
            }
            
        except Exception as e:
            print(f"Error in calculate_price: {e}")
            return default_result