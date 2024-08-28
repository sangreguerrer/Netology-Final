from rest_framework.authtoken.models import Token


def save_vk_access_token(backend, user, response, *args, **kwargs):
    if backend.name == 'vk-oauth2':
        access_token = response.get('access_token')
        if access_token:
            # Создаем или получаем Django Token
            token, _ = Token.objects.get_or_create(user=user)
        else:
            raise ValueError("Access token is missing in the response from VK")

        return {'token': token.key}
