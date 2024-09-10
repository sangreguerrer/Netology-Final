# Sho - o -perz
## Приложение для автоматизации закупок
## Краткое описание:
Проект по автоматизации закупок, созданный на архитектуре REST API. 
Написан при использовании DJango - REST Framework и СУБД PostgreSQL.
Включает асинхронные процессы(Отправка эл.писем, импорт списка товаров одним файлом, создание миниатюр изображений)
## Эндпоинты:
### POST register user
 https://mysite.com/register  body: (
            'email', 'first_name', 'last_name', 'username', 'password', 'password2', 'type', 'image'(optional)
            ).
### POST confirm email
 https://mysite.com/register/confirm  body: (
    'email', 'token'
)
### POST login user
 https://mysite.com/login  body: (
            'username', 'password'
)
### POST reset password
 https://mysite.com/reset_password  body: (
            'email'
)
### POST reset password confirm
 https://mysite.com/reset_password/confirm  body: (
            'email', 'token', 'password')
 )
### POST create 
 