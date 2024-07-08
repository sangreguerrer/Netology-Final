from django import forms
from .models import Image, User, OrderItem
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


class OrderItemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(OrderItemForm, self).__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields["order"].queryset = OrderItemForm.objects.filter(order=self.instance.order)

    def clean(self):
        cleaned_data = super(OrderItemForm, self).clean()
        order = cleaned_data.get("order")
        order_identifier = self.cleaned_data.get("order").identifier
        if order is not None:
            prod_order_identifier = order.product_info.identifier
            if order_identifier != prod_order_identifier:
                raise forms.ValidationError("Bar identifier should match parent Bar identifier")
        return cleaned_data