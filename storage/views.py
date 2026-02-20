from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .models import Box


def index(request):
    return render(request, 'index.html')


def get_boxes_by_warehouse(request):
    warehouse_id = request.GET.get('warehouse_id')
    
    if not warehouse_id:
        return JsonResponse({'boxes': []})
    
    boxes = Box.objects.filter(
        box_type__warehouse_id=warehouse_id
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
