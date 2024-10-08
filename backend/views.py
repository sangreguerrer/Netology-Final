from distutils.util import strtobool

import sentry_sdk
from django.shortcuts import render
from drf_spectacular.utils import extend_schema
from rest_framework.throttling import AnonRateThrottle
from yaml.representer import RepresenterError

from djangoProjectFinalWork.tasks import do_import, generate_thumbnails, notify_low_stock
from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
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
from django.db.models import Q, Sum, F
from ujson import loads as load_json

from .forms import ImageForm
from .models import ConfirmEmailToken, Category, Shop, ProductInfo, Order, OrderItem, Contact, Brand
from .serializers import UserSerializer, CategorySerializer, ShopSerializer, ProductInfoSerializer, OrderSerializer, \
    OrderItemSerializer, ContactSerializer, BrandSerializer, UserDetailsSerializer, ConfirmAccountSerializer, \
    UserAuthSerializer, ErrorResponseSerializer, SuccessResponseSerializer
from .signals import new_order


def login_page(request):
    return render(request, 'login.html')


class RegisterView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    throttle_classes = [AnonRateThrottle]

    @extend_schema(
        request=UserSerializer,
        responses={
            201: {'description': 'User registered successfully.'},
            400: {'description': 'Bad request, including missing fields and validation errors.'}
        },
        description="Register a new user by providing necessary information. All fields except 'image' are required."
    )
    def post(self, request, *args, **kwargs):
        """
        Register a new user
        Args:
            - request (Request): The Django request object includes in body(
            'email', 'first_name', 'last_name', 'username', 'password', 'password2', 'type', 'image'(optional)
            ).
        """
        required_args = {'email', 'first_name', 'last_name', 'username', 'password', 'password2', 'type'}
        missing_fields = required_args - request.data.keys()
        if missing_fields:
            return Response(
                {'Status': False, 'Error': f'Missing fields: {", ".join(missing_fields)}'},
                status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(request.data['password'])
        except ValidationError as password_error:
            err_array = [str(error) for error in password_error.messages]
            return Response({'Status': False, 'Error': err_array})
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'Status': True, 'Message': 'User registered successfully'},
                status=status.HTTP_201_CREATED
            )
        return Response({'Status': False, 'Errors': serializer.errors}, status='404')


@extend_schema(
    request=ConfirmAccountSerializer,
    responses={
        200: {'description': 'Account confirmed successfully.'},
        401: {'description': 'Unauthorized.'},
    },
    description="This endpoint allows users to confirm their account by providing an email and a confirmation token."
)
@api_view(['POST'])
def confirm_acc(request: Request, *args, **kwargs):
    """
    Confirm email
    The created token must be passed in the request body
    and the user get "is_active" state
    Args:
        - request (Request): The Django request object, includes in body('email', 'token').
    Returns:
        - Response: The response indicating the status of the operation and any errors.
    """
    required_args = {'email', 'token'}

    missing_fields = required_args - request.data.keys()
    if missing_fields:
        return Response(
            {'Status': False, 'Error': f'Missing fields: {", ".join(missing_fields)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    token = ConfirmEmailToken.objects.filter(user__email=request.data['email'], key=request.data['token']).first()
    if token:
        token.user.is_active = True
        token.user.save()
        token.delete()
        return Response(
            {'Status': True, 'Message': 'Account confirmed successfully'},
            status=status.HTTP_200_OK
        )
    return Response(
        {'Status': False, 'Error': 'Invalid token'},
        status=status.HTTP_400_BAD_REQUEST
    )


@extend_schema(
    request=UserAuthSerializer,
    responses={
        200: {'description': 'User logged in successfully.'},
        401: {'description': 'Login failed.'},
    },
    description="Authenticate a user by providing their email and password."
)
@api_view(['POST'])
def login(request, *args, **kwargs):
    """
    An authorization endpoint
    Args:
        - request (Request): The Django request object, includes in body('email', 'password').
    Returns:
        - Response: The key of the user's token.
    """
    required_args = {'email', 'password'}
    if not required_args.issubset(request.data.keys()):
        missing_fields = required_args - request.data.keys()
        return Response(
            {'Status': False, 'Error': f'Missing fields: {", ".join(missing_fields)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    user = authenticate(request, username=request.data['email'], password=request.data['password'])
    if user is not None:
        if user.is_active:
            token, _ = Token.objects.get_or_create(user=user)
            return Response(
                {'Status': True, 'Token': token.key},
                status=status.HTTP_200_OK
            )
    return Response({'Status': False, 'Error': 'Авторизация не пройдена'})


class AccountDetails(APIView):
    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(
        responses={
            200: UserSerializer,
            403: {'description': 'Log in required.'},
        },
        description="Retrieve the details of the authenticated user."
    )
    def get(self, request: Request, *args, **kwargs):
        """
          Retrieve the details of the authenticated user.

          Args:
          - request (Request): The Django request object including in Authorization header(
          'Authorization',Token 'token').

          Returns:
          - Response: The response containing the details of the authenticated user.
        """
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)

        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        request=UserDetailsSerializer,
        responses={
            200: {'description': 'Account updated successfully.'},
            400: {'description': 'Bad request, including missing fields and validation errors.'},
            403: {'description': 'Log in required.'},
        },
        description="Update the account details of the authenticated user."
    )
    def post(self, request, *args, **kwargs):
        """
        Update the account details of the authenticated user.

        Args:
        - request (Request): The Django request object including in Authorization header('Authorization',Token 'token')

        Returns:
        - Response: The response indicating the status of the operation and any errors.
        """
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)

        if 'password' in request.data:
            try:
                validate_password(request.data['password'])
            except ValidationError as err:
                err_array = []
                for error in err.messages:
                    err_array.append(error)
                return Response(
                    {'Status': False, 'Error': err_array},
                    status=status.HTTP_403_FORBIDDEN)
        user_serializer = UserDetailsSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return Response(                # pass this view to celery
                {'Status': True, 'Message': 'Account updated successfully'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'Status': False, 'Errors': user_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )


class BrandView(APIView):
    """
      The class for add new brand
      Methods:
          - get: Retrieve the list of brands.
          - post: Add a new brand(shops only).
    """
    @extend_schema(
        responses={
            200: BrandSerializer(many=True),
            404: {'description': 'Brand not found.'},
        },
        description="Retrieve the list of brands."
    )
    def get(self, request, *args, **kwargs):
        queryset = Brand.objects.all()
        serializer = BrandSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=BrandSerializer,
        responses={
            201: BrandSerializer,
            400: {'description': 'Bad request, including missing fields and validation errors.'},
            403: {'description': 'Log in required.'},
        },
        description="Add a new brand(shops only)."
    )
    def post(self, request, *args, **kwargs):
        """
        Add a new brand(shops only).
        Request must contain 'name' in body and header('Authorization',Token 'token')
        """
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)
        if request.user.type != 'shop':
            return Response(
                {'Status': False, 'Error': 'You are not a partner'}
            )

        serializer = BrandSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=BrandSerializer,
        responses={
            200: BrandSerializer,
            400: {'description': 'Bad request, including missing fields and validation errors.'},
            403: ErrorResponseSerializer,
        },
        description="Update brand infos."
    )
    def put(self, request, *args, **kwargs):
        """Update brand infos. Request must contain 'id' and fields, that You want to update in body and
        header('Authorization',Token 'token')"""
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)
        if request.user.type != 'shop':
            return Response(
                {'Status': False, 'Error': 'You are not a partner'}
            )
        brand_id = request.data.get('id')
        brand = Brand.objects.filter(id=brand_id).first()
        if brand:
            serializer = BrandSerializer(brand, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({'Status': False, 'Error': 'Brand was not found'})


@extend_schema(
    request=CategorySerializer,
    responses={
        200: CategorySerializer(many=True),
    },
    description="Retrieve the list of categories."
)
class CategoryView(ListAPIView):
    """
      The class for actions with categories
      Methods:
          - get: Retrieve the list of categories.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


@extend_schema(
    request=ShopSerializer,
    responses={
        200: SuccessResponseSerializer(many=True),
        404: {'description': 'Shop not found.'},
    },
    description="Retrieve the list of shops."
)
class ShopView(ListAPIView):
    """
      The class for view and additions of shops
      Methods:
          - get: Retrieve the list of shops.
    """
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer


@extend_schema(
    request=ProductInfoSerializer,
    responses={
        200: SuccessResponseSerializer(many=True),
        400: {'description': 'Bad request, including missing fields and validation errors.'},
        404: {'description': 'Product not found.'},
    },
    description="Retrieve the product information based on the specified filters."
)
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
        'shop', 'product__category', 'brand', 'image').prefetch_related('product',
                                                                        'product_parameter__parameter').distinct(
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

    @extend_schema(
        request=OrderSerializer,
        responses={
            200: OrderSerializer,
            400: {'description': 'Bad request.'},
            403: {'description': 'Log in required.'},
            404: {'description': 'Item not found in the basket.'},
        },
        description="Retrieve the items in the user's basket."
    )
    def get(self, request, *args, **kwargs):
        """
        Retrieve the items in the user's basket.

        Args:
        - request (Request): The Django request object including in Authorization header('Authorization',Token 'token'),

        Returns:
        - Response: The response containing the items in the user's basket.
        """
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)
        orders = Order.objects.filter(
            user_id=request.user.id, state='basket'
        ).prefetch_related(
            'order_items__product_info__product__category',
            'order_items__product_info__brand',
            'order_items__product_info__product_parameter__parameter'
        ).annotate(total_sum=Sum(F('order_items__quantity') * F('order_items__product_info__price'))).distinct()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=OrderItemSerializer(many=True),
        responses={200: OrderSerializer,
                   400: {'description': 'Bad request.'},
                   403: {'description': 'Log in required.'},
                   },
        description="Add items to the user's basket."
    )

    def post(self, request, *args, **kwargs):
        """
        Add items to the user's basket if they are in stock.

        Args:
        - request (Request): The Django request object including in Authorization header('Authorization',Token 'token'),
          and in the request body('items': [{product_info: int, quantity: int}]).

        Returns:
        - Response: The response indicating the status of the operation and any errors.
        """
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=status.HTTP_403_FORBIDDEN)

        items_string = request.data.get('items')

        if items_string:
            try:
                items = load_json(items_string)
            except ValueError:
                return Response({'Status': False, 'Error': 'Invalid JSON format'}, status=400)

        errors = []
        objects_created = 0

        with transaction.atomic():
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')

            for order_item in items:
                if not isinstance(order_item, dict):
                    errors.append("Each item should be a dictionary.")
                    continue

                product_info_id = order_item.get('product_info')
                quantity = order_item.get('quantity')

                if not isinstance(product_info_id, int) or not isinstance(quantity, int):
                    errors.append("Each item must have 'product_info' and 'quantity' as integers.")
                    continue

                try:
                    product_info = ProductInfo.objects.get(id=product_info_id)

                    if quantity > product_info.quantity:
                        errors.append(f"Недостаточное количество для товара с ID {product_info_id}")
                        continue
                    if OrderItem.objects.filter(order=basket, product_info=product_info).exists():
                        errors.append(f"Item with product ID {product_info_id} already exists in the basket")
                        continue

                    order_item_data = {
                        'order': basket.id,
                        'product_info': product_info_id,
                        'quantity': quantity
                    }

                    serializer = OrderItemSerializer(data=order_item_data)

                    if serializer.is_valid():
                        try:
                            serializer.save()
                            objects_created += 1
                        except RepresenterError as e:
                            errors.append(f"RepresenterError: {str(e)}")
                    else:
                        errors.append(serializer.errors)

                except ProductInfo.DoesNotExist:
                    errors.append(f"Товар с ID {product_info_id} не найден")
                except ValidationError as e:
                    errors.append(f"ValidationError: {str(e)}")
                except Exception as e:
                    errors.append(str(e))

        if errors:
            return Response({'Status': False, 'Errors': errors, 'Objects Created': objects_created},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response({'Status': True, 'Objects Created': objects_created}, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=OrderItemSerializer(many=True),
        responses={'200': OrderSerializer,
                   400: {'description': 'Bad request.'},
                   403: {'description': 'Log in required.'},
                   404: {'description': 'Item not found in the basket.'},
                   },
        description="Remove items from the user's basket."
    )
    def delete(self, request, *args, **kwargs):
        """
        Remove  items from the user's basket.

        Args:
        - request (Request): The Django request object including in Authorization header('Authorization',Token 'token')
        and in the request body('items': int, int).

        Returns:
        - Response: The response indicating the status of the operation and any errors.
        """
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)
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
                return Response({'Status': True, 'Удалено объектов': deleted})
        return Response({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    @extend_schema(
        request=OrderItemSerializer(many=True),
        responses={200: OrderSerializer,
                   400: {'description': 'Bad request.'},
                   403: {'description': 'Log in required.'},
                   },
        description="Update the quantity of items in the user's basket."
    )
    def put(self, request, *args, **kwargs):
        """
        Update the quantity of an item in the user's basket.

        Args:
        - request (Request): The Django request object including in Authorization header('Authorization',Token 'token')
        and in the request body Order objects(id) and quantity of them('items': [{id: int, quantity: int}]).

        Returns:
        - Response: The response indicating the status of the operation and any errors.
        """
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)

        items_string = request.data.get('items')
        if items_string:
            try:
                item_dict = load_json(items_string)
            except ValueError:
                return Response({'Status': False, 'Error': 'Invalid JSON format'}, status=400)
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_updated = 0
                errors = []

                for item in item_dict:
                    item_id = item.get('id')
                    item_quantity = item.get('quantity')

                    if isinstance(item_id, int) and isinstance(item_quantity, int):
                        try:
                            order_item = OrderItem.objects.get(order_id=basket.id, product_info_id=item_id)

                            product_info = ProductInfo.objects.get(id=item_id)
                            if item_quantity > product_info.quantity:
                                errors.append(f"Недостаточное количество для товара с ID {item_id}")
                                continue

                            order_item.quantity = item_quantity
                            order_item.save()
                            objects_updated += 1

                        except OrderItem.DoesNotExist:
                            errors.append(f"Товар с ID {item_id} отсутствует в вашей корзине")

                        except ProductInfo.DoesNotExist:
                            errors.append(f"Товар с ID {item_id} не найден в базе данных")

                    else:
                        errors.append(f"Неверный формат данных для товара с ID {item_id or 'не указан'}")

                response_data = {'Status': True, 'Обновлено объектов': objects_updated}
                if errors:
                    response_data['Errors'] = errors
                return Response(response_data, status=200)

        return Response({'Status': False, 'Error': 'Не указаны все необходимые аргументы'}, status=400)


@extend_schema(
    request=UserSerializer,
    responses={
        200: SuccessResponseSerializer,
        403: {'description': 'Log in required'},
        404: {'description': 'Not found'}
    }
)
@api_view(['POST'])
def partner_update(request, *args, **kwargs):
    """
    A view for updating and addition shops.
    Methods:

    - post: upload validated goods data.The authorization token is required. The data must be passed in yaml format via
    raw link  the request body.
    for example: url: https://raw.githubusercontent.com/netology-code/python-final-diplom/master/data/shop1.yaml
    """
    if not request.user.is_authenticated:
        return Response({'Status': False, 'Error': 'Log in required'}, status=403)

    if request.user.type != 'shop':
        return Response(
            {'Status': False, 'Error': 'You are not a partner'}
        )

    try:
        user_id = request.user.id
        if user_id:
            url = request.data.get('url')
            if url:
                do_import.delay(user_id, url)
                return Response({'Status': user_id})
            else:
                return Response({'Status': False, 'Error': 'No URL'})
        else:
            return Response({'Status': False, 'Error': 'No user'})
    except ValidationError as e:
        return Response({'Status': False, 'Error': {e}})


class PartnerState(APIView):
    """
    Retrieve the state of the partner.

    Args:
    - request (Request): The Django request object including in Authorization header('Authorization',Token 'token')

    Returns:
    - Response: The response containing the state of the partner.
    """

    @extend_schema(responses={
        '200': ShopSerializer,
        '403': ErrorResponseSerializer,
        '404': {'description': 'Not found'}

    })
    def get(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return Response({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    @extend_schema(
        request=ShopSerializer,
        responses={'200': ShopSerializer,
                   '400': {'description': 'Wrong type'},
                   '403': ErrorResponseSerializer,
                   },
        description="Update the state of a partner."
    )
    def post(self, request, *args, **kwargs):
        """
        Update the state of a partner.

        Args:
        - request (Request): The Django request object including in Authorization header('Authorization',Token 'token')
        and in the request body('state': bool). Shops only

        Returns:
        - Response: The response indicating the status of the operation and any errors.
        """
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return Response({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        state = request.data.get('state')
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=strtobool(state))
                return Response({'Status': True})
            except ValueError as error:
                return Response({'Status': False, 'Errors': str(error)})
        return Response({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerOrders(APIView):
    @extend_schema(
        responses={
            status.HTTP_200_OK: OrderSerializer(many=True),
            status.HTTP_403_FORBIDDEN: ErrorResponseSerializer,
        },
        description="Retrieve the items in the user's basket."
    )
    def get(self, request, *args, **kwargs):
        """
        Retrieve the list of orders for a partner.

        Args:
        - request (Request): The Django request object including in Authorization header('Authorization',Token 'token')

        Returns:
        - Response: The response containing the list of orders.
        """
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return Response({'Status': False, 'Error': 'Только для магазинов'}, status=403)
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

    @extend_schema(responses={
        '200': ContactSerializer(many=True),
        '400': ErrorResponseSerializer,
        '403': ErrorResponseSerializer,
    },
        description="Retrieve the contact information of the authenticated user."
    )
    def get(self, request, *args, **kwargs):
        """
        Retrieve information of authenticated user
        """
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)

        queryset = Contact.objects.filter(user_id=request.user.id)
        serializer = ContactSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=ContactSerializer,
        responses={'200': ContactSerializer,
                   '400': ErrorResponseSerializer,
                   '403': ErrorResponseSerializer,
                   },
        description="Create a new contact for the authenticated user."
    )
    def post(self, request, *args, **kwargs):
        """
        Create a new contact for the authenticated user.
        The request body must contain the following fields:
        city, street, house, apartment, phone and header must contain 'Authorization' and 'Token'
        """
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)

        required_args = {"city", "street", "house", "apartment", "phone"}
        missing_fields = required_args - request.data.keys()
        if missing_fields:
            return Response(
                {'Status': False, 'Error': f'Missing fields: {", ".join(missing_fields)}'},
            )
        request.data._mutable = True
        request.data.update({"user": request.user.id})
        serializer = ContactSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response({'status': False, 'Errors': serializer.errors})

    @extend_schema(
        responses={
            '200': ContactSerializer(many=True),
            '400': ErrorResponseSerializer,
            '403': ErrorResponseSerializer,
        },
        description="Delete the contact of the authenticated user."
    )
    def delete(self, request, *args, **kwargs):
        """
        Delete the contact of the authenticated user.
        """
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)
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
                        return Response({'Status': True, 'Удалено объектов': deleted})
        return Response({'Status': False, 'Error': 'Не указаны все необходимые аргументы'})

    @extend_schema(
        request=ContactSerializer,
        responses={'200': ContactSerializer,
                   '400': ErrorResponseSerializer,
                   '403': ErrorResponseSerializer,
                   },
        description="Update the contact information of the authenticated user."
    )
    def put(self, request, *args, **kwargs):
        """
        Update the contact information of the authenticated user.
        """
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)

        if 'id' in request.data:
            if request.data['id'].isdigit():
                queryset = Contact.objects.filter(id=request.data['id'], user_id=request.user.id).first()
                serializer = ContactSerializer(queryset, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)
                else:
                    return Response({'status': False, 'Errors': serializer.errors})

        return Response({'Status': False, 'Error': 'Не указаны все необходимые аргументы'})


class OrdersView(APIView):
    """
    The class for managing orders.
    Methods:
    - get: Retrieve the details of a specific order.
    - post: Create a new order.
    - put: Update the details of a specific order.
    - delete: Delete a specific order.

    Attributes:
    - None
    """

    @extend_schema(
        request=OrderSerializer,
        responses={'200': OrderSerializer,
                   '400': ErrorResponseSerializer,
                   '403': ErrorResponseSerializer,
                   },
        description="Get an order."
    )
    def get(self, request, *args, **kwargs):
        """
        Retrieve the details of a specific order.The request header must contain the 'Authorization' and 'Token' and
        body must contain 'id'
        """
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)

        orders = Order.objects.filter(user_id=request.user.id).exclude(state='basket').prefetch_related(
            'order_items__product_info__product__category',
            'order_items__product_info__brand',
            'order_items__product_info__product_parameter__parameter').annotate(
            total_sum=Sum(F('order_items__quantity') * F('order_items__product_info__price'))).distinct()

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=OrderSerializer,
        responses={'200': OrderSerializer,
                   '400': ErrorResponseSerializer,
                   '403': ErrorResponseSerializer,
                   '404': ErrorResponseSerializer,
                   },
        description="Create a new order."
    )
    def post(self, request, *args, **kwargs):
        """
        Create a new order.
        The request header must contain the 'Authorization' and 'Token' and body must contain 'id' and 'contact'
        """
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)

        if {'id', 'contact'}.issubset(request.data):
            order_id = request.data['id']
            contact_id = request.data['contact']
            order = Order.objects.filter(id=order_id, user_id=request.user.id).first()
            if order:
                if order_id.isdigit():
                    order_id = int(order_id)

                    try:
                        with transaction.atomic():
                            is_updated = Order.objects.filter(
                                user_id=request.user.id,
                                id=order_id
                            ).update(contact_id=contact_id, state='new')

                            if not is_updated:
                                return Response({'Status': False, 'Error': 'Order not found'}, status=404)

                            order_items = OrderItem.objects.filter(order_id=order_id)

                            product_quantities = order_items.values('product_info_id').annotate(
                                total_quantity=Sum('quantity'))

                            for pq in product_quantities:
                                product_info = ProductInfo.objects.get(id=pq['product_info_id'])
                                product_info.quantity -= pq['total_quantity']
                                if product_info.quantity < 0:
                                    raise ValueError(f"Insufficient stock for product {product_info.id}")
                                product_info.save()
                                notify_low_stock.delay(product_info.id)

                            new_order.send(sender=request.user.id, user_id=request.user.id)
                            return Response({'Status': True}, status=200)

                    except IntegrityError as err:
                        return Response({'Status': False, 'Error': str(err)}, status=400)
                    except ValueError as err:
                        return Response({'Status': False, 'Error': str(err)}, status=400)
            return Response({'Status': False, 'Error': 'Order not found'}, status=404)
        return Response({'Status': False, 'Error': 'Missing required arguments'}, status=400)


def image_upload_view(request):
    """Process images uploaded by users"""
    if request.method == 'POST':
        form = ImageForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            generate_thumbnails.delay(form.instance.image.path)
            img_obj = form.instance
            return render(request, 'images/image.html', {'form': form, 'img_obj': img_obj})
    else:
        form = ImageForm()
    return render(request, 'images/image.html', {'form': form})


class ErrorTriggerView(APIView):
    """
    APIView для тестирования Sentry.
    Этот view вызывает исключение, которое будет отправлено в Sentry.
    """
    def get(self, request):
        try:
            # Намеренное исключение
            division_by_zero = 1 / 0
        except ZeroDivisionError as exc:
            # Вы можете захватить ошибку и передать ее в Sentry, если необходимо
            sentry_sdk.capture_exception(exc)
            # Либо Sentry автоматически зафиксирует это исключение
            raise
        return Response({"message": "This should never be seen!"}, status=status.HTTP_200_OK)
