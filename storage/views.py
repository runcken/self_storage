from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages 
from django.utils import timezone  
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .forms import OrderForm 
from .models import Box, Client, RentalAgreement, Warehouse
from datetime import timedelta
from .models import PromoCode
from datetime import date
from .utils import send_order_notification_to_client
import logging


logger = logging.getLogger(__name__)

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
        status_label = "Свободен" if box.status == 'free' else f"Занят"
        data.append({
            'id': box.id,
            'label': f"Бокс №{box.number} ({box.box_type.volume}м³) - {status_label}",
            'disabled': box.status != 'free'
        })
        
    return JsonResponse({'boxes': data})


@login_required
def order_view(request):

    if request.method == 'POST':
        form = OrderForm(request.POST)
        
        if not form.is_valid():
            context = {
                'form': form,
                'calculator_js': True
            }
            return render(request, 'order_form.html', context)

        # 1. СНАЧАЛА получаем или создаем клиента (нужен для проверки промокода)
        client, created = Client.objects.get_or_create(
            user=request.user,
            defaults={
                'full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
                'phone': request.POST.get('phone', ''),
                'email': request.user.email,
                'address': request.POST.get('address', '')
            }
        )
        
        # 2. Обработка промокода
        promo_code_input = form.cleaned_data.get('promo_code', '').strip()
        applied_promo = None
        promo_discount = 0
        
        if promo_code_input:
            try:
                promo = PromoCode.objects.get(
                    code=promo_code_input,
                    is_active=True,
                    valid_from__lte=date.today(),
                    valid_until__gte=date.today()
                )
                
                # ПРОВЕРКА: Уже использовал ли этот клиент этот промокод?
                if RentalAgreement.objects.filter(client=client, promo_code=promo).exists():
                    messages.warning(request, f'Промокод "{promo.code}" уже использован вами ранее')
                    applied_promo = None
                    promo_discount = 0
                # Проверка: Валиден ли промокод (лимит использований)?
                elif not promo.is_valid():
                    messages.warning(request, 'Лимит использований промокода исчерпан')
                    applied_promo = None
                    promo_discount = 0
                else:
                    # Промокод можно использовать
                    applied_promo = promo
                    promo_discount = promo.discount_percent
                    messages.success(request, f'Промокод "{promo.code}" применён: скидка {promo_discount}%')
                    promo.used_count += 1
                    promo.save()
                    
            except PromoCode.DoesNotExist:
                messages.warning(request, 'Промокод не найден или не действителен')
        
        # 3. Расчет цены
        price_info = form.calculate_price(promo_discount=promo_discount)
        
        if price_info['volume'] == 0:
            messages.error(request, 'Ошибка расчёта. Проверьте данные.')
            context = {
                'form': form,
                'calculator_js': True
            }
            return render(request, 'order_form.html', context)
        
        # 4. Создание договора
        start_date = form.cleaned_data['start_date']
        duration_months = form.cleaned_data['rental_duration']
        end_date = start_date + timedelta(days=int(duration_months * 30.44))
        need_delivery = form.cleaned_data.get('need_delivery', False)
        
        agreement = RentalAgreement.objects.create(
            client=client,
            warehouse=form.cleaned_data['warehouse'],
            start_date=start_date,
            end_date=end_date,
            status='active',
            promo_code=applied_promo,
            free_delivery=need_delivery
        )
        
        
        # 5. Назначение бокса
        final_box = form.cleaned_data['selected_box']
        volume_needed = float(price_info['volume'])
        
        if final_box:
            agreement.boxes.add(final_box)
            final_box.status = 'occupied'
            final_box.current_agreement = agreement
            final_box.save()
            
            mode = form.cleaned_data.get('mode', 'manual')
            if mode == 'manual':
                msg = f'Заказ оформлен! Бокс №{final_box.number} ({final_box.box_type.volume}м³)'
            else:
                msg = f'Автоподбор: назначен бокс №{final_box.number} ({final_box.box_type.volume}м³)'
            
            messages.success(request, msg)
        else:
            messages.error(request, 'Ошибка: бокс не назначен')
        
        # 6. Отправка уведомления клиенту в Telegram
        try:
            send_order_notification_to_client(
                agreement=agreement,
                price_info=price_info,
                client=client,
                final_box=final_box,  # Важно: final_box должен быть определён выше!
                applied_promo=applied_promo
            )
        except Exception as e:
            logger.error(f"Ошибка отправки Telegram: {e}")
        
        
        
        # 7. Сохранение в сессию
        request.session['order_data'] = {
            'warehouse': str(form.cleaned_data['warehouse']),
            'volume': volume_needed,
            'duration': int(price_info['duration']),
            'monthly_price': float(price_info['monthly_price']),
            'total_price': float(price_info['total_price']),
            'discount_percent': int(price_info['discount_percent']),
            'promo_code': applied_promo.code if applied_promo else None,
            'promo_discount': promo_discount,
            'start_date': start_date.strftime('%d.%m.%Y'),
            'end_date': end_date.strftime('%d.%m.%Y'),
            'agreement_id': agreement.id,
            'box_numbers': [b.number for b in agreement.boxes.all()],
            'box_assigned': final_box is not None,
            'free_delivery': need_delivery,
        }
        
        return redirect('order_confirmation')
    
    else:
        initial = {
            'start_date': (timezone.now() + timedelta(days=1)).date(),
            'rental_duration': 1,
            'need_length': 1.5,
            'need_width': 1.0,
            'need_height': 2.0,
        }
        
        preselected_box_id = request.GET.get('box_id')
        if preselected_box_id:
            try:
                box = Box.objects.get(id=preselected_box_id, status='free')
                initial['warehouse'] = box.box_type.warehouse.id
                initial['selected_box'] = box.id
                initial['mode'] = 'manual'
                messages.info(
                    request,
                    f'Выбран бокс №{box.number}. Проверьте и подтвердите заказ.'
                )
            except Box.DoesNotExist:
                messages.error(request, 'Бокс уже занят или не существует')
        
        form = OrderForm(initial=initial)
    
    context = {
        'form': form,
        'calculator_js': True
    }
    return render(request, 'order_form.html', context)


def box_details(request, box_id):
    """AJAX: детали бокса"""
    box = get_object_or_404(Box, id=box_id)
    return JsonResponse({
        'id': box.id,
        'number': box.number,
        'length': float(box.box_type.length),
        'width': float(box.box_type.width),
        'height': float(box.box_type.height),
        'volume': float(box.box_type.volume),
        'price': float(box.box_type.price),
        'warehouse': str(box.box_type.warehouse),
    })


def order_confirmation_view(request):
    order_data = request.session.get('order_data', {})
    
    if not order_data:
        messages.error(request, 'Нет данных заказа')
        return redirect('order')
    
    return render(request, 'order_confirmation.html', {
        'order_data': order_data,
        'show_cabinet_link': True
    })
    
def check_promo_code(request):
    code = request.GET.get('code', '').strip()
    
    # Получаем клиента текущего пользователя
    try:
        client = Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        client = None
    
    try:
        promo = PromoCode.objects.get(code=code, is_active=True)
        
        # Проверка: уже использовал ли этот клиент этот промокод?
        if client and RentalAgreement.objects.filter(client=client, promo_code=promo).exists():
            return JsonResponse({
                'valid': False,
                'message': f'Промокод "{promo.code}" уже использован вами в другой аренде'
            })
        
        # Проверка: валиден ли (лимит, сроки)?
        if not promo.is_valid():
            return JsonResponse({
                'valid': False,
                'message': 'Промокод просрочен или исчерпан'
            })
        
        # Промокод можно использовать
        return JsonResponse({
            'valid': True,
            'discount': promo.discount_percent,
            'message': f'Промокод действует! Скидка {promo.discount_percent}%'
        })
        
    except PromoCode.DoesNotExist:
        return JsonResponse({
            'valid': False,
            'message': 'Промокод не найден'
        })    


@login_required
def extend_rent_view(request, pk):
    rental = get_object_or_404(RentalAgreement, id=pk, client__user=request.user)
    rental.end_date += timedelta(days=30)
    rental.save()
    messages.success(request, "Срок аренды продлен на 1 месяц!")
    return redirect('my_rent')


@login_required
def open_box_view(request, pk):
    rental = get_object_or_404(RentalAgreement, id=pk, client__user=request.user)
    box_numbers = ', '.join(str(b.number) for b in rental.boxes.all())
    messages.info(request, f"Бокс(ы) №{box_numbers} открыт(ы).")
    return redirect('my_rent')


@login_required
def request_qr_code_view(request, pk):
    """Отправляет QR-код для доступа к боксу по запросу пользователя"""
    from .notification_service import TelegramNotificationService
    from .models import RentalAgreement
    
    # Получаем договор, проверяем что он принадлежит пользователю
    agreement = get_object_or_404(RentalAgreement, id=pk, client__user=request.user)
    
    # Проверяем, привязан ли Telegram
    if not request.user.client_profile.telegram_linked or not request.user.client_profile.telegram_chat_id:
        messages.warning(request, 'Сначала привяжите Telegram в настройках профиля')
        return redirect('my_rent')
    
    # Отправляем QR-код
    success = TelegramNotificationService.send_qr_code_for_access(agreement)
    
    if success:
        messages.success(request, 'QR-код отправлен в ваш Telegram!')
    else:
        messages.error(request, 'Ошибка отправки. Проверьте, что бот привязан.')
    
    return redirect('my_rent')