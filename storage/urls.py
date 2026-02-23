from django.urls import path
from . import views


urlpatterns =  [
    path('ajax/get-boxes/', views.get_boxes_by_warehouse, name='ajax_get_boxes'),
    path('ajax/box-details/<int:box_id>/', views.box_details, name='box_details'),
    path('ajax/check-promo/', views.check_promo_code, name='check_promo'),
    path('order/', views.order_view, name='order'),
    path('order/confirmation/', views.order_confirmation_view, name='order_confirmation'),
    path('rent/<int:pk>/extend/', views.extend_rent_view, name='extend_rent'),
    path('rent/<int:pk>/open/', views.open_box_view, name='open_box'),
    ]
