from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import Profile


class UserRegistrationForm(UserCreationForm):

    email = forms.EmailField(
        required=True,
        label='Электронная почта',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@email.com'
        })
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=False,
        label='Имя',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Иван'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=False,
        label='Фамилия',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Иванов'
        })
    )
    
    phone = forms.CharField(
        max_length=15,
        required=True,
        label='Телефон',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+79991234567'
        })
    )
    
    address = forms.CharField(
        required=False,
        label='Адрес доставки',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'г. Москва, ул. Тверская, д. 1'
        })
    )
    
    avatar = forms.ImageField(
        required=False,
        label='Аватар',
        help_text='Загрузите фото профиля (необязательно)'
    )
    
    pdn_accepted = forms.BooleanField(
        required=True,
        label='Согласен на обработку персональных данных',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ivan_ivanov'
            }),
            'password1': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': '••••••••'
            }),
            'password2': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': '••••••••'
            }),
        }
        labels = {
            'username': 'Имя пользователя',
            'password1': 'Пароль',
            'password2': 'Подтверждение пароля',
        }
    
    def clean_email(self):
        #Проверка уникальности email
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует.')
        return email
    
    def save(self, commit=True):
    
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            
            # Получаем или создаём профиль
            profile = user.profile
            
            # Обновляем данные профиля
            profile.first_name = self.cleaned_data.get('first_name', '')
            profile.last_name = self.cleaned_data.get('last_name', '')
            profile.phone = self.cleaned_data.get('phone', '')
            profile.address = self.cleaned_data.get('address', '')
            profile.pdn_accepted = self.cleaned_data['pdn_accepted']
            
            # Сохраняем аватар, если он загружен
            avatar = self.cleaned_data.get('avatar')
            if avatar:
                profile.avatar = avatar
            
            profile.save()
        
        return user


class UserLoginForm(AuthenticationForm):

    username = forms.CharField(
        label='Имя пользователя или email',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ivan_ivanov или ivan@example.com'
        })
    )
    
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••'
        })
    )
    
    def clean(self):
        # Получаем введённые данные
        username_or_email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username_or_email and password:
            # Проверяем, это email или username
            if '@' in username_or_email:
                # Ищем пользователя по email
                try:
                    user = User.objects.get(email=username_or_email)
                    username = user.username
                except User.DoesNotExist:
                    raise forms.ValidationError(
                        'Пользователь с таким email не найден.',
                        code='invalid_login'
                    )
            else:
                username = username_or_email

            # Аутентифицируем по username
            self.user_cache = authenticate(
                self.request, 
                username=username, 
                password=password
            )
            
            if self.user_cache is None:
                raise forms.ValidationError(
                    'Неверные данные для входа.',
                    code='invalid_login'
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data