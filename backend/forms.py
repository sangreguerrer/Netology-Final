from django import forms
from .models import Image, User
from django.contrib.auth.forms import UserCreationForm


class ImageForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ('title', 'image')


class UserForm(UserCreationForm):
    image = forms.ImageField(required=False)

    class Meta:
        model = User
        fields = ('email', 'username', 'image', 'password1', 'password2')
