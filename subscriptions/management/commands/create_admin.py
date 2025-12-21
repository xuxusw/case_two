from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Создает администратора с правильной ролью'
    
    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin', help='Имя пользователя')
        parser.add_argument('--email', type=str, default='admin@example.com', help='Email')
        parser.add_argument('--password', type=str, default='Admin123!', help='Пароль')
    
    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        
        # Проверяем, существует ли пользователь
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            user.role = 'admin'
            user.is_staff = True
            user.is_superuser = True
            user.save()
            
            self.stdout.write(self.style.SUCCESS(f'Пользователь {username} теперь администратор'))
        else:
            # Создаем нового администратора
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                role='admin'  # Устанавливаем роль
            )
            
            self.stdout.write(self.style.SUCCESS(f'Администратор создан:'))
            self.stdout.write(f'   Имя: {username}')
            self.stdout.write(f'   Email: {email}')
            self.stdout.write(f'   Роль: {user.role}')