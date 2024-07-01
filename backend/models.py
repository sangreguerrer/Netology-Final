from datetime import datetime

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.tokens import get_token_generator
from django.utils.text import slugify


STATE_CHOICES = (
    ('basket', 'Статус корзины'),
    ('new', 'Новый'),
    ('confirmed', 'Подтвержден'),
    ('assembled', 'Собран'),
    ('sent', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('canceled', 'Отменен'),
)

USER_TYPE_CHOICES = (
    ('shop', 'Магазин'),
    ('buyer', 'Покупатель'),
)

# class CustomManager(UserManager):
#     pass


class UserManager(BaseUserManager):
    """
    Миксин для управления пользователями
    """
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class Image(models.Model):
    title = models.CharField(max_length=200, default=datetime.now())
    image = models.ImageField(upload_to='images/')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Изображение'
        verbose_name_plural = 'Изображения'


class User(AbstractUser):
    """
    Модель пользователей
    """
    REQUIRED_FIELDS = []
    objects = UserManager()
    USERNAME_FIELD = 'email'
    email = models.EmailField(_('email address'), unique=True, max_length=100)
    username_validator = UnicodeUsernameValidator()
    username = models.CharField(
        _('username'),
        max_length=150,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[username_validator],
        error_messages={'unique': _('A user with that username already exists.')}
    )
    is_active = models.BooleanField(
        _('active'),
        default=False,
        help_text=_('Designates whether this user should be treated as active. '
                    'Unselect this instead of deleting accounts.'
                    ),
    )
    type = models.CharField(verbose_name='Тип пользователя', choices=USER_TYPE_CHOICES, max_length=5, default='buyer')
    image = models.OneToOneField(Image, on_delete=models.CASCADE, blank=True, verbose_name='Кул ава', null=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Список пользователей'
        ordering = ('-email',)


class Brand(models.Model):
    name = models.CharField(max_length=200, unique=True)
    country = models.CharField(max_length=200, blank=True, null=True)
    email = models.EmailField(max_length=200, unique=True, blank=True, null=True)
    url = models.URLField(max_length=300, unique=True, blank=True, null=True)
    image = models.OneToOneField(Image, on_delete=models.CASCADE,verbose_name='Изображение', null=True, blank=True)
    slug = models.SlugField(max_length=150, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренды'
        ordering = ('-name',)

    def __str__(self):
        return self.name


class Shop(models.Model):
    name = models.CharField(max_length=200)
    user = models.OneToOneField(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE
    )
    address = models.CharField(max_length=150, blank=True)
    slug = models.SlugField(max_length=150)
    image = models.OneToOneField(Image, related_name='shop', on_delete=models.CASCADE, null=True, blank=True)
    state = models.BooleanField(verbose_name='статус получения заказов', default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Магазины'
        ordering = ('-name',)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=200)
    shops = models.ManyToManyField(Shop, verbose_name='Магазины', related_name='categories')
    slug = models.SlugField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ('-name',)

    @property
    def get_products(self):
        return Product.objects.filter(category=self)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=150)
    category = models.ForeignKey(
        Category,
        verbose_name='Категория',
        related_name='products',
        on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'
        ordering = ('-name',)

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    model = models.CharField(max_length=80, verbose_name='Модель', blank=True)
    product = models.ForeignKey(
        Product,
        verbose_name='Продукт',
        related_name='product_infos',
        on_delete=models.CASCADE)
    brand = models.ForeignKey(
        Brand,
        verbose_name='Брэнд',
        related_name='product_infos',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    shop = models.ForeignKey(
        Shop,
        verbose_name='Магазин',
        related_name='product_infos',
        on_delete=models.CASCADE)
    external_id = models.PositiveIntegerField(verbose_name='Артикул')
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        verbose_name='Цена',
        validators=[MinValueValidator(0)]
    )
    price_rrc = models.DecimalField(
        verbose_name='Рекомендуемая розничная цена',
        max_digits=18,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.OneToOneField(
        Image,
        blank=True, null=True,
        verbose_name='Изображение',
        on_delete=models.SET_NULL)

    class Meta:
        verbose_name = 'Информация о продукте'
        verbose_name_plural = "Информация о каждом продукте"
        constraints = [
            models.UniqueConstraint(fields=['product', 'shop', 'brand', 'external_id'], name='unique_product_info'),
        ]


class Parameter(models.Model):
    name = models.CharField(max_length=50, verbose_name='Название параметра')

    class Meta:
        verbose_name = 'Имя параметра'
        verbose_name_plural = 'Список параметров'
        ordering = ('-name',)

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    product_info = models.ForeignKey(
        ProductInfo,
        verbose_name='Информация о продукте',
        related_name='product_parameter',
        on_delete=models.CASCADE
    )
    parameter = models.ForeignKey(
        Parameter,
        verbose_name='Параметр',
        related_name='product_parameter',
        on_delete=models.CASCADE
    )
    value = models.CharField(verbose_name='Значение', max_length=300)

    class Meta:
        verbose_name = 'Параметр продукта'
        verbose_name_plural = 'Параметры продуктов'
        constraints = [models.UniqueConstraint(fields=['product_info', 'parameter'], name='unique_product_parameter')]


class Contact(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        related_name='contacts',
        on_delete=models.CASCADE
    )
    city = models.CharField(max_length=50, verbose_name='Город')
    street = models.CharField(max_length=150, verbose_name='Улица')
    house = models.CharField(max_length=15, verbose_name='Дом')
    structure = models.CharField(max_length=15, verbose_name='Корпус', blank=True)
    building = models.CharField(max_length=15, verbose_name='Строение', blank=True)
    apartment = models.CharField(max_length=10, verbose_name='Квартира')
    phone = models.CharField(max_length=11, verbose_name='Телефон')

    class Meta:
        verbose_name = 'Контакты пользователя'
        verbose_name_plural = "Список контактов пользователя"
        constraints = [
            models.UniqueConstraint(fields=['user', 'city', 'street', 'house', 'structure', 'building', 'apartment'],
                                    name='unique_user_contact')
        ]

    def __str__(self):
        return f'{self.city} {self.street} {self.house}'


class Order(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        related_name='orders',
        on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    state = models.CharField(verbose_name='статус', choices=STATE_CHOICES, max_length=15)
    contact = models.ForeignKey(Contact, verbose_name='Контакты', blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Список заказов'
        ordering = ('-created',)

    def __str__(self):
        return f'{self.created}'


class OrderItem(models.Model):
    objects = models.manager.Manager()
    order = models.ForeignKey(
        Order,
        verbose_name='Заказ',
        related_name='order_items',
        on_delete=models.CASCADE)

    product_info = models.ForeignKey(
        ProductInfo,
        verbose_name='Информация о продукте',
        related_name='order_items',
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(verbose_name='Количество')

    class Meta:
        verbose_name = 'Заказанная позиция'
        verbose_name_plural = 'Список заказанных позиций'
        constraints = [models.UniqueConstraint(fields=['order', 'product_info'], name='unique_order_item')]


class ConfirmEmailToken(models.Model):
    class Meta:
        verbose_name = 'Токен подтверждения email'
        verbose_name_plural = 'Токены подтверждения email'

    @staticmethod
    def generate_key():
        return get_token_generator().generate_token()

    user = models.ForeignKey(
        User,
        related_name='confirm_email_tokens',
        on_delete=models.CASCADE,
        verbose_name=_('The User which is associated to this password reset token')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='When was this token generated')
    key = models.CharField(_("Key"), max_length=64, db_index=True, unique=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    def __str__(self):
        return "Password reset token for user {user}".format(user=self.user)
