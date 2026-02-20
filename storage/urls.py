from django.urls import path
from . import views


app_name = 'storage'

urlpatterns =  [
    path('ajax/get-boxes/', views.get_boxes_by_warehouse, name='ajax_get_boxes'),
    ]
