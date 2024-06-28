from distutils.util import strtobool

import yaml
from django.contrib.auth import authenticate
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.http import JsonResponse
from requests import get
from rest_framework import status
from django.core.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import api_view
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from django.contrib.auth.password_validation import validate_password
from yaml import safe_load
from django.db.models import Q, Sum, F
from ujson import loads as load_json

from .models import User, ConfirmEmailToken, Category, Shop, ProductInfo, Product, Order, OrderItem, ProductParameter, \
    Parameter, Contact, Brand
from .serializers import UserSerializer, CategorySerializer, ShopSerializer, ProductInfoSerializer, OrderSerializer, \
    OrderItemSerializer, ContactSerializer, BrandSerializer
from .signals import new_order


class RegisterView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        required_args = {'email', 'first_name', 'last_name', 'username', 'password', 'password2', 'type'}
        """
        A view that registers users.
        """
        if not required_args.issubset(request.data.keys()):
            missing_fields = required_args - request.data.keys()
            return JsonResponse(
                {'Status': False, 'Error': f'Missing fields: {", ".join(missing_fields)}'},
                status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(request.data['password'])
        except ValidationError as password_error:
            err_array = [str(error) for error in password_error.messages]
            return JsonResponse({'Status': False, 'Error': err_array})
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(
                {'Status': True, 'Message': 'User registered successfully'},
                status=status.HTTP_201_CREATED
            )
        return JsonResponse({'Status': False, 'Errors': serializer.errors}, status='404')


@api_view(['POST'])
def confirm_acc(request: Request, *args, **kwargs):
    required_args = {'email', 'token'}
    if not required_args.issubset(request.data.keys()):
        missing_fields = required_args - request.data.keys()
        return JsonResponse(
            {'Status': False, 'Error': f'Missing fields: {", ".join(missing_fields)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    token = ConfirmEmailToken.objects.filter(user__email=request.data['email'], key=request.data['token']).first()
    if token:
        token.user.is_active = True
        token.user.save()
        token.delete()
        return JsonResponse(
            {'Status': True, 'Message': 'Account confirmed successfully'},
            status=status.HTTP_200_OK
        )
    return JsonResponse(
        {'Status': False, 'Error': 'Invalid token'},
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
def login(request, *args, **kwargs):
    required_args = {'email', 'password'}
    if not required_args.issubset(request.data.keys()):
        missing_fields = required_args - request.data.keys()
        return JsonResponse(
            {'Status': False, 'Error': f'Missing fields: {", ".join(missing_fields)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    user = authenticate(request, username=request.data['email'], password=request.data['password'])
    if user is not None:
        if user.is_active:
            token, _ = Token.objects.get_or_create(user=user)
            return JsonResponse(
                {'Status': True, 'Token': token.key},
                status=status.HTTP_200_OK
            )
    return JsonResponse({'Status': False, 'Error': 'Авторизация не пройдена'})


class AccountDetails(APIView):
    parser_classes = (MultiPartParser, FormParser)
    """
    A view that can retrieves and updates account details

    Methods:
    - get: Retrieve the details of the authenticated user.
    - post: Update the account details of the authenticated user.
    """

    #get info
    def get(self, request: Request, *args, **kwargs):
        """
          Retrieve the details of the authenticated user.

          Args:
          - request (Request): The Django request object.

          Returns:
          - Response: The response containing the details of the authenticated user.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    #update parameters
    def post(self, request, *args, **kwargs):
        """
        Update the account details of the authenticated user.

        Args:
        - request (Request): The Django request object.

        Returns:
        - JsonResponse: The response indicating the status of the operation and any errors.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        #check for password change
        if 'password' in request.data:
            errors = {}

            #password validating for safety
            try:
                validate_password(request.data['password'])
            except ValidationError as err:
                err_array = []
                for error in err.messages:
                    err_array.append(error)
                return JsonResponse(
                    {'Status': False, 'Error': 'invalid password'},
                    status=status.HTTP_403_FORBIDDEN)
        #saving changes
        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse(
                {'Status': True, 'Message': 'Account updated successfully'},
                status=status.HTTP_200_OK
            )
        else:
            return JsonResponse(
                {'Status': False, 'Errors': user_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )


class BrandView(APIView):
    """
      Класс для просмотра и добавления брэндов
      Methods:
          - get: Retrieve the list of brands.
          - post: Add a new brand.
    """

    def get(self, request, *args, **kwargs):
        queryset = Brand.objects.all()
        serializer = BrandSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        if request.user.type != 'shop':
            return JsonResponse(
                {'Status': False, 'Error': 'You are not a partner'}
            )

        serializer = BrandSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CategoryView(ListAPIView):
    """
      Класс для просмотра и добавления категорий
      Methods:
          - get: Retrieve the list of categories.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ShopView(ListAPIView):
    """
      Класс для просмотра и добавления магазинов
      Methods:
          - get: Retrieve the list of shops.
    """
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer


@api_view(['GET'])
def product_view(request, *args, **kwargs):
    """
       Retrieve the product information based on the specified filters.

       Args:
       - request (Request): The Django request object.

       Returns:
       - Response: The response containing the product information.
    """
    query = Q(shop__state=True)
    shop_id = request.query_params.get('shop_id')
    category_id = request.query_params.get('category_id')
    brand_id = request.query_params.get('brand_id')
    brand = request.query_params.get('brand')

    if shop_id:
        query = query & Q(shop_id=shop_id)

    if brand:
        query = query & Q(brand__name=brand)

    if brand_id:
        query = query & Q(brand_id=brand_id)

    if category_id:
        query = query & Q(product__category_id=category_id)

    queryset = ProductInfo.objects.filter(query).select_related(
        'shop', 'product__category', 'brand', 'image').prefetch_related('product_parameter__parameter').distinct(
    )
    serializer = ProductInfoSerializer(queryset, many=True)
    return Response(serializer.data)


class BasketView(APIView):
    """
    A class for managing the user's shopping basket.

    Methods:
    - get: Retrieve the items in the user's basket.
    - post: Add an item to the user's basket.
    - put: Update the quantity of an item in the user's basket.
    - delete: Remove an item from the user's basket.

    Attributes:
    - None
    """

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        orders = Order.objects.filter(
            user_id=request.user.id, state='basket'
        ).prefetch_related(
            'order_items__product_info__product__category',
            'order_items__product_info__brand',
            'order_items__product_info__product_parameter__parameter'
        ).annotate(total_sum=Sum(F('order_items__quantity') * F('order_items__product_info__price'))).distinct()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
               Add an items to the user's basket.

               Args:
               - request (Request): The Django request object.

               Returns:
               - JsonResponse: The response indicating the status of the operation and any errors.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        items_string = request.data.get('items')
        if items_string:
            try:
                items = load_json(items_string)
            except ValueError:
                return JsonResponse(
                    {'Status': False, 'Error': 'Invalid JSON format'},
                )
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_created = 0
                for order_items in items:
                    order_items.update({'order': basket.id})
                    serializer = OrderItemSerializer(data=order_items)
                    if serializer.is_valid():
                        try:
                            serializer.save()
                        except IntegrityError as error:
                            return JsonResponse({'Status': False, 'Errors': str(error)})
                        else:
                            objects_created += 1
                    else:
                        return JsonResponse({'Status': False, 'Errors': serializer.errors})
                return JsonResponse({'Status': True, 'Создано объектов': objects_created})

            return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    def delete(self, request, *args, **kwargs):
        """
        Remove  items from the user's basket.

        Args:
        - request (Request): The Django request object.

        Returns:
        - JsonResponse: The response indicating the status of the operation and any errors.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        items_string = request.data.get('items')
        if items_string:
            item_list = items_string.split(',')
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
            query = Q()
            objects_deleted = False
            for item in item_list:
                if item.isdigit():
                    query = query | Q(order_id=basket.id, id=item)
                    objects_deleted = True
            if objects_deleted:
                deleted = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    def put(self, request, *args, **kwargs):
        """
        Update the quantity of an item in the user's basket.

        Args:
        - request (Request): The Django request object.

        Returns:
        - JsonResponse: The response indicating the status of the operation and any errors.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        items_string = request.data.get('items')
        if items_string:
            try:
                item_dict = load_json(items_string)
            except ValueError:
                return JsonResponse(
                    {'Status': False, 'Error': 'Invalid JSON format'},
                )
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_updated = 0
                for item in item_dict:
                    if isinstance(item['id'], int) and isinstance(item['quantity'], int):
                        objects_updated += OrderItem.objects.filter(
                            order_id=basket.id, id=item['id']
                        ).update(quantity=item['quantity'])
                return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


@api_view(['POST'])
def partner_update(request, *args, **kwargs):
    """
    A class for updating shops.

    Methods:
    - post: upload validated goods data.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

    if request.user.type != 'shop':
        return JsonResponse(
            {'Status': False, 'Error': 'You are not a partner'}
        )

    url = request.data.get('url')
    if url:
        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as err:
            return JsonResponse(
                {'Status': False, 'Error': str(err)},
            )
        else:
            try:
                stream = get(url).content
                yaml_file = safe_load(stream)
            except yaml.YAMLError as exc:
                return JsonResponse({'Status': False, 'Error': f'YAML Error: {exc}'})
            shop, _ = Shop.objects.get_or_create(name=yaml_file['shop'], user_id=request.user.id)
            for category in yaml_file['categories']:
                category_obj, _ = Category.objects.get_or_create(name=category['name'])
                category_obj.shops.add(shop.id)
                category_obj.save()
            ProductInfo.objects.filter(shop_id=shop.id).delete()
            for product in yaml_file['goods']:
                brand, _ = Brand.objects.get_or_create(name=product['brand'])
                product_obj, _ = Product.objects.get_or_create(name=product['name'], category=category_obj)
                product_info, _ = ProductInfo.objects.get_or_create(
                    model=product['model'],
                    brand=brand,
                    product_id=product_obj.id,
                    shop_id=shop.id,
                    external_id=product['id'],
                    quantity=product['quantity'],
                    price=product['price'],
                    price_rrc=product['price_rrc']
                )
                for name, value in product['parameters'].items():
                    parameter_obj, _ = Parameter.objects.get_or_create(name=name)
                    ProductParameter.objects.create(
                        product_info_id=product_info.id,
                        parameter_id=parameter_obj.id,
                        value=value,
                    )
            return JsonResponse({'Status': True})
    return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerState(APIView):
    """
        Retrieve the state of the partner.

        Args:
        - request (Request): The Django request object.

        Returns:
        - Response: The response containing the state of the partner.
    """

    def get(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
        Update the state of a partner.

        Args:
        - request (Request): The Django request object.

        Returns:
        - JsonResponse: The response indicating the status of the operation and any errors.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        state = request.data.get('state')
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=strtobool(state))
                return JsonResponse({'Status': True})
            except ValueError as error:
                return JsonResponse({'Status': False, 'Errors': str(error)})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerOrders(APIView):
    def get(self, request, *args, **kwargs):
        """
        Retrieve the list of orders for a partner.

        Args:
        - request (Request): The Django request object.

        Returns:
        - Response: The response containing the list of orders.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        queryset = Order.objects.filter(
            order_items__product_info__shop__user_id=request.user.id).exclude(state='basket').prefetch_related(
            'order_items__product_info__product__category',
            'order_items__product_info__product_parameter__parameter').annotate(
            total_sum=Sum(F('order_items__quantity') * F('order_items__product_info__price'))).distinct()

        serializer = OrderSerializer(queryset, many=True)
        return Response(serializer.data)


class ContactView(APIView):
    """
       A class for managing contact information.

       Methods:
       - get: Retrieve the contact information of the authenticated user.
       - post: Create a new contact for the authenticated user.
       - put: Update the contact information of the authenticated user.
       - delete: Delete the contact of the authenticated user.

       Attributes:
       - None
       """

    def get(self, request, *args, **kwargs):
        """
        Retrieve information of authenticatded user
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        queryset = Contact.objects.filter(user_id=request.user.id)
        serializer = ContactSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
        Create a new contact for the authenticated user.
        :param request:
        :param args:
        :param kwargs:
        :return:
         """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        required_args = {"city", "street", "house", "apartment", "phone"}
        if not required_args.issubset(request.data.keys()):
            missing_fields = required_args - request.data.keys()
            return JsonResponse(
                {'Status': False, 'Error': f'Missing fields: {", ".join(missing_fields)}'},
            )
        request.data._mutable = True
        request.data.update({"user": request.user.id})
        serilizer = ContactSerializer(data=request.data)
        if serilizer.is_valid():
            serilizer.save()
            return Response(serilizer.data)
        else:
            return Response({'status': False, 'Errors': serilizer.errors})

    def delete(self, request, *args, **kwargs):
        """
        Delete the contact of the authenticated user.
        :param request:
        :param args:
        :param kwargs:
        :return:
         """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        items_string = request.data.get('items')
        if items_string:
            items = items_string.split(',')
            query = Q()
            object_deleted = False
            for item in items:
                if item.isdigit():
                    query = query | Q(user_id=request.user.id, id=item)
                    object_deleted = True
                    if object_deleted:
                        deleted = Contact.objects.filter(query).delete()[0]
                        return JsonResponse({'Status': True, 'Удалено объектов': deleted})
        return JsonResponse({'Status': False, 'Error': 'Не указаны все необходимые аргументы'})

    def put(self, request, *args, **kwargs):
        """
        Update the contact information of the authenticated user.
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if 'id' in request.data:
            if request.data['id'].isdigit():
                queryset = Contact.objects.filter(id=request.data['id'], user_id=request.user.id).first()
                serilizer = ContactSerializer(queryset, data=request.data, partial=True)
                if serilizer.is_valid():
                    serilizer.save()
                    return Response(serilizer.data)
                else:
                    return Response({'status': False, 'Errors': serilizer.errors})

        return JsonResponse({'Status': False, 'Error': 'Не указаны все необходимые аргументы'})


class OrdersView(APIView):
    """
    Класс для получения и размешения заказов пользователями
    Methods:
    - get: Retrieve the details of a specific order.
    - post: Create a new order.
    - put: Update the details of a specific order.
    - delete: Delete a specific order.

    Attributes:
    - None
    """

    def get(self, request, *args, **kwargs):
        """
        Retrieve the details of a specific order.
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        orders = Order.objects.filter(user_id=request.user.id).exclude(state='basket').prefetch_related(
            'order_items__product_info__product__category',
            'order_items__product_info__product__brand',
            'order_items__product_info__product_parameter__parameter').annotate(
            total_sum=Sum(F('order_items__quantity') * F('order_items__product_info__price'))).distinct()

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
        Create a new order.
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if {'id', 'contact'}.issubset(request.data):
            if request.data['id'].isdigit():
                try:
                    is_updated = Order.objects.filter(
                        user_id=request.user.id,
                        id=request.data['id']).update(contact_id=request.data['contact'], state='new')
                except IntegrityError as err:
                    return JsonResponse({'Status': False, 'Error': str(err)})
                else:
                    if is_updated:
                        new_order.send(sender=request.user.id, user_id=request.user.id)
                        return JsonResponse({'Status': True})
                    else:
                        return JsonResponse({'Status': False, 'Error': 'Заказ не найден'})
        return JsonResponse({'Status': False, 'Error': 'Не указаны все необходимые аргументы'})
