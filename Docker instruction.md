1.DB_HOST должен называться именем контейнера db.
2.docker-compose build          
3.docker-compose up             
4.docker exec -it django_app python manage.py shell -c "from backend.models import User;
User.objects.create_superuser('admin@example.com', 'mypassword')" #