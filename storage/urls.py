from django.urls import path
from . import views


# app_name = 'storage'

urlpatterns =  [
    path('ajax/get-boxes/', views.get_boxes_by_warehouse, name='ajax_get_boxes'),
    path('order/', views.order_view, name='order'),
    path('order/confirmation/', views.order_confirmation_view, name='order_confirmation'),
    path('rent/<int:pk>/extend/', views.extend_rent_view, name='extend_rent'),
    path('rent/<int:pk>/open/', views.open_box_view, name='open_box'),
    ]
