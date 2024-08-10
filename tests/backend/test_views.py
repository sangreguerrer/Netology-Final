import json

from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from backend.models import User, ConfirmEmailToken, Shop, Category, Brand, Product, Parameter, ProductParameter, \
    ProductInfo, Order, OrderItem, Contact
from django.test import TestCase

from backend.views import OrdersView


class RegisterViewTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('user-register')

    def test_register_valid_data(self):
        data = {
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'johndoe',
            'password': 'Test123456!',
            'password2': 'Test123456!',
            'type': 'buyer',
        }
        response = self.client.post(path=self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='johndoe')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.last_name, 'Doe')
        self.assertEqual(user.type, 'buyer')


class ConfirmEmailTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('user-register-confirm')
        self.user = User.objects.create(email='test@example.com', is_active=False)
        self.token = ConfirmEmailToken.objects.create(user=self.user)

    def test_confirm_email_valid_token(self):
        response = self.client.post(self.url, dict(email=self.user.email, token=self.token.key))
        print(self.user.email)
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.token.user, self.user)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertFalse(ConfirmEmailToken.objects.filter(id=self.token.id).exists())


class TestBasketItems(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='testuser', is_active='True')
        self.user2 = User.objects.create(username='testuser2', email='test2@example.com')
        self.token = Token.objects.create(user=self.user)
        self.shop = Shop.objects.create(name='Test Shop', user=self.user)
        self.shop2 = Shop.objects.create(name='Test Shop 2', user=self.user2)
        shops = [self.shop, self.shop2]
        self.category = Category.objects.create(name='Test Category')
        self.category.shops.set(shops)
        self.brand = Brand.objects.create(name='Test Brand')
        self.product = Product.objects.create(name='Test Product', category=self.category)
        self.product_info = ProductInfo.objects.create(
            shop=self.shop,
            product=self.product,
            brand=self.brand,
            price=100,
            external_id=1,
            quantity=10,
            price_rrc=90
        )
        self.parameter = Parameter.objects.create(name='Test Parameter')
        self.product_parameter = ProductParameter.objects.create(
            product_info=self.product_info,
            parameter=self.parameter
        )
        self.url = reverse('basket')

    def test_add_basket_items(self):
        self.client.force_authenticate(user=self.user, token=self.token)
        items = [
                    {'product_info': self.product_info.id, 'quantity': 1},
                ]
        response = self.client.post(self.url, {'items': json.dumps(items)}, format='json')
        self.assertEqual(response.status_code, 200)
        order_item1 = OrderItem.objects.filter(order__user_id=self.user.id, product_info=self.product_info).first()
        self.assertEqual(Order.objects.filter(user_id=self.user.id, state='basket').count(), 1)
        self.assertEqual(OrderItem.objects.filter(order__user_id=self.user.id).count(), 1)
        self.assertEqual(order_item1.quantity, 1)

    def test_get_basket_items(self):
        self.client.force_authenticate(user=self.user, token=self.token)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_put_basket_items(self):
        self.order_item = OrderItem.objects.create(
            order=Order.objects.create(user_id=self.user.id, state='basket'),
            product_info=self.product_info,
            quantity=1
        )
        self.client.force_authenticate(user=self.user, token=self.token)
        items = [
                    {'id': self.product_info.id, 'quantity': 3},
                ]
        response = self.client.put(self.url, {'items': json.dumps(items)}, format='json')
        self.assertEqual(response.status_code, 200)

        self.assertEqual(OrderItem.objects.count(), 1)
        self.assertEqual(Order.objects.filter(user_id=self.user.id, state='basket').count(), 1)


class PartnerUpdateViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('partner-update')
        self.user = User.objects.create_user(username='testuser', password='testpassword', email='test@example.com')
        self.token = Token.objects.create(user=self.user)

    def test_partner_update_view_with_unauthenticated_user(self):
        response = self.client.post(
            self.url,
            {'url': 'https://raw.githubusercontent.com/netology-code/python-final-diplom/master/data/shop1.yaml'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json(), {'Status': False, 'Error': 'Log in required'})

    def test_partner_update_not_shop(self):
        """
        Test partner_update view with user type not 'shop'
        """
        self.client.force_authenticate(user=self.user, token=self.token)
        self.user.type = 'buyer'
        self.user.save()
        url = reverse('partner-update')
        response = self.client.post(url, {
            'url': 'https://raw.githubusercontent.com/netology-code/python-final-diplom/master/data/shop1.yaml'},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'Status': False, 'Error': 'You are not a partner'})

    def test_partner_update_authenticated_user(self):
        self.user.type = 'shop'
        self.user.save()
        self.client.force_authenticate(user=self.user, token=self.token)
        response = self.client.post(
            self.url,
            {'url': 'https://raw.githubusercontent.com/netology-code/python-final-diplom/master/data/shop1.yaml'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'Status': self.user.id})


class PartnerOrdersTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(
            username='testuser', email='test@example.com', password='testpassword', type='shop')
        self.token = Token.objects.create(user=self.user)
        self.shop = Shop.objects.create(user=self.user)
        self.category = Category.objects.create(name='Test Category')
        self.parameter = Parameter.objects.create(name='Test Parameter')
        self.product = Product.objects.create(name='Test Product', category=self.category)
        self.contact = Contact.objects.create(
                                                user=self.user,
                                                city='Moscow',
                                                street='Lenina',
                                                house='1',
                                                phone='81234567890'
        )
        self.product_info = ProductInfo.objects.create(
            shop=self.shop,
            product=self.product,
            price=100,
            external_id=1,
            quantity=10,
            price_rrc=90
        )
        self.product_parameter = ProductParameter.objects.create(
                                                                 product_info=self.product_info,
                                                                 parameter=self.parameter,
                                                                 value='Test Value'
        )
        self.order = Order.objects.create(user=self.user, contact=self.contact, state='new')
        self.order_item = OrderItem.objects.create(order=self.order, product_info=self.product_info, quantity=2)

    def test_partner_orders_view(self):
        self.client.login(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user, token=self.token)
        response = self.client.get(reverse('partner-orders'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        order = response.data[0]
        self.assertEqual(order['id'], self.order.id)
        self.assertEqual(order['user'], self.user.id)
        self.assertEqual(order['contact']['id'], self.contact.id)
        self.assertEqual(order['state'], 'new')
        self.assertEqual(order['total_sum'], 200)
        order_item = order['order_items'][0]
        print(order_item)
        self.assertEqual(order_item['id'], self.order_item.id)
        self.assertEqual(order_item['product_info']['model'], self.product_info.model)
        self.assertEqual(order_item['quantity'], 2)
