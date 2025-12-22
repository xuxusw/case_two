from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

def send_email_notification(user_email, subject, template_name, context):
    try:
        # в разработке выводим в консоль
        if settings.DEBUG:
            logger.info(f"Email для {user_email}: {subject}")
            logger.info(f"Контекст: {context}")
            return True
        
        # пробуем отправить реальный email
        html_message = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <div style="background-color: #4CAF50; color: white; padding: 15px; border-radius: 10px 10px 0 0; text-align: center;">
                    <h1>Subscription System</h1>
                </div>
                <div style="padding: 20px;">
                    <h2>{subject}</h2>
                    <div style="margin: 20px 0;">
                        {context.get('message', '')}
                    </div>
                    <div style="margin-top: 30px; padding: 15px; background-color: #f9f9f9; border-radius: 5px;">
                        <h3>Детали:</h3>
                        <ul>
        """
        
        for key, value in context.items():
            if key != 'message':
                html_message += f"<li><strong>{key}:</strong> {value}</li>"
        
        html_message += """
                        </ul>
                    </div>
                    <div style="margin-top: 30px; text-align: center; color: #666; font-size: 12px;">
                        <p>Это автоматическое сообщение. Пожалуйста, не отвечайте на него.</p>
                        <p>Subscription System © 2025</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Email отправлен: {user_email} - {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки email: {e}")
        return False

def send_test_email(user_email):
    context = {
        'message': 'Это тестовое сообщение от системы подписок.',
        'system': 'Subscription System',
        'status': 'Работает нормально',
        'timestamp': 'Текущее время'
    }
    
    return send_email_notification(
        user_email=user_email,
        subject='Тестовое уведомление от системы подписок',
        template_name='test_email',
        context=context
    )

def send_subscription_renewed_email(user_email, subscription_name, new_end_date, amount):
    """Уведомление о продлении подписки"""
    context = {
        'message': f'Ваша подписка "{subscription_name}" была успешно продлена.',
        'subscription': subscription_name,
        'new_end_date': new_end_date,
        'amount': f'{amount} RUB',
        'next_renewal': 'Автоматически через 30 дней'
    }
    
    return send_email_notification(
        user_email=user_email,
        subject=f'Подписка {subscription_name} продлена',
        template_name='subscription_renewed',
        context=context
    )

def send_payment_failed_email(user_email, subscription_name, error_message):
    """Уведомление об ошибке платежа"""
    context = {
        'message': f'Не удалось продлить подписку "{subscription_name}".',
        'subscription': subscription_name,
        'error': error_message,
        'action': 'Пожалуйста, проверьте данные платежной карты'
    }
    
    return send_email_notification(
        user_email=user_email,
        subject=f'Ошибка продления подписки {subscription_name}',
        template_name='payment_failed',
        context=context
    )

def send_subscription_expiring_email(user_email, subscription_name, days_left, end_date):
    """Уведомление о скором истечении подписки"""
    context = {
        'message': f'Ваша подписка "{subscription_name}" скоро истечет.',
        'subscription': subscription_name,
        'days_left': f'{days_left} дней',
        'end_date': end_date,
        'action': 'Убедитесь, что на счете достаточно средств для автопродления'
    }
    
    return send_email_notification(
        user_email=user_email,
        subject=f'Подписка {subscription_name} истекает через {days_left} дней',
        template_name='subscription_expiring',
        context=context
    )