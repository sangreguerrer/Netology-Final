1.docker-compose build          
2.docker-compose up             
3.docker exec -it django_app python manage.py shell -c "from backend.models import User;
User.objects.create_superuser('admin@example.com', 'mypassword')" #