from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages 
from django.utils import timezone  
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from .forms import OrderForm 
from .models import Box, Client, RentalAgreement, Warehouse
from datetime import timedelta
from decimal import Decimal


def index(request):
    return render(request, 'index.html')


def get_boxes_by_warehouse(request):
    warehouse_id = request.GET.get('warehouse_id')
    
    if not warehouse_id:
        return JsonResponse({'boxes': []})
    
    boxes = Box.objects.filter(
        box_type__warehouse_id=warehouse_id,
    ).select_related('box_type').order_by('number')
    
    data = []
    for box in boxes:
        status_label = "Свободен" if box.status == 'free' else f"Занят ({box.current_agreement})"
        data.append({
            'id': box.id,
            'label': f"Бокс №{box.number} ({box.box_type.volume}м³) - {status_label}",
            'disabled': box.status != 'free'
        })
        
    return JsonResponse({'boxes': data})

@login_required
def order_view(request):
    """
    Вьюха создания заказа на аренду бокса
    """
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # 1. Расчет стоимости
            price_info = form.calculate_price()
            
            # 2. Получаем или создаем клиента
            client, created = Client.objects.get_or_create(
                user=request.user,
                defaults={
                    'full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
                    'phone': request.POST.get('phone', ''),
                    'email': request.user.email,
                    'address': request.POST.get('address', '')
                }
            )
            
            # 3. Рассчитываем даты
            start_date = form.cleaned_data['start_date']
            duration_months = form.cleaned_data['rental_duration']
            end_date = start_date + timedelta(days=int(duration_months * 30.44))
            
            # 4. Создаем договор аренды
            agreement = RentalAgreement.objects.create(
                client=client,
                warehouse=form.cleaned_data['warehouse'],
                start_date=start_date,
                end_date=end_date,
                status='active'
            )
            
            # 5. Подбираем бокс
            volume_needed = float(price_info['volume'])
            
            suitable_box = Box.objects.filter(
                box_type__warehouse=form.cleaned_data['warehouse'],
                status='free',
                box_type__volume__gte=volume_needed * 0.8,
                box_type__volume__lte=volume_needed * 1.5
            ).select_related('box_type').first()
            
            if suitable_box:
                agreement.boxes.add(suitable_box)
                suitable_box.status = 'occupied'
                suitable_box.current_agreement = agreement
                suitable_box.save()
            
            # 6. Сохраняем данные заказа в сессию
            request.session['order_data'] = {
                'warehouse': str(form.cleaned_data['warehouse']),
                'volume': float(price_info['volume']),
                'duration': int(price_info['duration']),
                'monthly_price': float(price_info['monthly_price']),
                'total_price': float(price_info['total_price']),
                'discount_percent': int(price_info['discount_percent']),
                'start_date': start_date.strftime('%d.%m.%Y'),
                'end_date': end_date.strftime('%d.%m.%Y'),
                'agreement_id': agreement.id,
                'box_numbers': [b.number for b in agreement.boxes.all()]
            }
            
            messages.success(
                request, 
                'Заказ успешно оформлен! В ближайшее время с вами свяжется менеджер.'
            )
            return redirect('order_confirmation')
    else:
        # GET запрос - показываем пустую форму
        initial_data = {
            'start_date': (timezone.now() + timedelta(days=1)).date(),
            'rental_duration': 1,
            'item_length': 1.5,
            'item_width': 1.0,
            'item_height': 2.0,
        }
        form = OrderForm(initial=initial_data)
    
    context = {
        'form': form,
        'calculator_js': True
    }
    
    
    return render(request, 'order_form.html', context)

def order_confirmation_view(request):
    """
    Страница подтверждения заказа
    """
    order_data = request.session.get('order_data', {})
    
    if not order_data:
        messages.error(request, 'Нет данных заказа. Пожалуйста, оформите заказ заново.')
        return redirect('order')
    
    context = {
        'order_data': order_data,
        'show_cabinet_link': True
    }
    return render(request, 'order_confirmation.html', context)

@login_required
def extend_rent_view(request, pk):
    rental = get_object_or_404(RentalAgreement, id=pk, client__user=request.user)
    # Увеличиваем дату окончания аренды на 1 месяц
    rental.end_date += timedelta(days=30)
    rental.save()
    messages.success(request, "Срок аренды успешно продлен на 1 месяц!")
    return redirect('my_rent')

@login_required
def open_box_view(request, pk):
    rental = get_object_or_404(RentalAgreement, id=pk, client__user=request.user)
    # Для примера просто сообщение
    box_numbers = ', '.join(str(b.number) for b in rental.boxes.all())
    messages.info(request, f"Бокс(ы) №{box_numbers} открыт(ы).")
    return redirect('my_rent')
