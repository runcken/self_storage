from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User


class UserRegistrationForm(UserCreationForm):
    """
    Форма регистрации нового пользователя
    """
    email = forms.EmailField(
        required=True,
        label='Электронная почта',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@email.com'
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
    
    pdn_accepted = forms.BooleanField(
        required=True,
        label='Согласен на обработку персональных данных',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
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
        """Проверка уникальности email"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует.')
        return email


class UserLoginForm(AuthenticationForm):
    """
    Форма входа пользователя
    """
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