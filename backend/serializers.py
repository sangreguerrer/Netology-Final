from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, Category, Shop, ProductInfo, Product, Brand, ProductParameter, Image, OrderItem, Contact, \
    Order


# Serializers define the API representation.
class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ('image',)


class UserAuthSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'password',)


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'user', 'phone',)
        read_only_fields = ('id',)
        extra_kwargs = {
            'user': {'write_only': True}
        }


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)
    image = serializers.ImageField(write_only=True, required=False)
    contacts = ContactSerializer(many=True, read_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'username', 'password', 'password2', 'is_active', 'type', 'image',
            'contacts'
        ]
        read_only_fields = ('id',)

    def create(self, validated_data):
        # Извлечение и удаление паролей из данных
        password = validated_data.pop('password')
        validated_data.pop('password2')
        # Извлечение данных изображения, если они есть
        image_data = validated_data.pop('image', None)
        # Создание пользователя
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        if image_data:
            image_instance = Image.objects.create(image=image_data)  # Создание объекта Image
            user.image = image_instance  # Связываем с пользователем
            user.save()
        return user

    def update(self, instance, validated_data):
        image_data = validated_data.pop('image', None)
        if image_data:
            image = Image.objects.create(image=image_data, title=f"{instance.username}'s image")
            instance.image = image
        return super().update(instance, validated_data)

    def validate(self, attrs):
        password = attrs.get('password')
        password2 = attrs.get('password2')
        if password != password2:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        try:
            validate_password(password)
        except ValidationError as e:
            raise serializers.ValidationError({"password": e.messages})
        return attrs


class UserDetailsSerializer(UserSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password], required=False)
    password2 = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'username', 'password', 'password2', 'is_active', 'type', 'image',
                  )
        read_only_fields = ('id',)

    def validate(self, attrs):
        if 'password' and 'password2' in attrs:
            return super().validate(attrs)
        return attrs


class BrandSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)

    class Meta:
        model = Brand
        fields = ('id', 'name', 'country', 'email', 'url', 'image')
        read_only_fields = ('id',)


class BrandRelatedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ('name',)

    def create(self, validated_data):
        # Извлечение данных изображения, если они есть
        image_data = validated_data.pop('image')
        # Создание пользователя
        brand = Brand.objects.create(**validated_data)
        brand.save()
        if image_data:
            image_instance = Image.objects.create(image=image_data)  # Создание объекта Image
            brand.image = image_instance  # Связываем с пользователем
            brand.save()
        return brand

    def update(self, instance, validated_data):
        image_data = validated_data.pop('image', None)
        if image_data:
            image = Image.objects.create(image=image_data, title=f"{instance.username}'s image")
            instance.image = image
        return super().update(instance, validated_data)


class ShopSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)

    class Meta:
        model = Shop
        fields = ('id', 'address', 'image', 'name', 'state',)
        read_only_fields = ('id',)


class CategorySerializer(serializers.ModelSerializer):
    shops = ShopSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'name', 'shops')
        read_only_fields = ('id',)


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = ('name', 'category')


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value',)


class ProductInfoSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)
    product = ProductSerializer(read_only=True)
    brand = BrandRelatedSerializer(read_only=True)
    parameters = ProductParameterSerializer(many=True, read_only=True)

    class Meta:
        model = ProductInfo
        fields = (
            'product', 'model', 'brand', 'shop', 'external_id', 'quantity', 'price', 'price_rrc', 'image', 'parameters'
        )
        read_only_fields = ('id',)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ('id', 'product_info', 'quantity', 'order',)
        read_only_fields = ('id',)
        extra_kwargs = {
            'order': {'write_only': True}
        }


class OrderItemCreateSerializer(OrderItemSerializer):
    product_info = ProductInfoSerializer(read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemCreateSerializer(read_only=True, many=True)

    total_sum = serializers.IntegerField()
    contact = ContactSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'order_items', 'state', 'created', 'total_sum', 'contact',)
        read_only_fields = ('id',)
