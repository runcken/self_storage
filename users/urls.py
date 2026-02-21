from django.urls import path
from . import views

# app_name = 'users'

urlpatterns = [
    # Основные страницы
    path('', views.home_view, name='home'),
    path('boxes/', views.boxes_view, name='boxes'),
    path('faq/', views.faq_view, name='faq'),
    
    # Аутентификация
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Личный кабинет
    path('cabinet/', views.cabinet_view, name='cabinet'),
    path('cabinet/edit/', views.edit_profile_view, name='edit_profile'),
    path('my-rent/', views.my_rent_view, name='my_rent'),
]