from rest_framework import serializers
from .models import SubscriptionPlan, UserSubscription, Transaction, PromoCode
from users.models import User

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'

class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_price = serializers.DecimalField(source='plan.price', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = UserSubscription
        fields = ['id', 'plan', 'plan_name', 'plan_price', 'status', 
                 'start_date', 'end_date', 'auto_renew', 'created_at']
        read_only_fields = ['id', 'plan', 'plan_name', 'plan_price', 'status',
                           'start_date', 'end_date', 'created_at']

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = '__all__'
        read_only_fields = ['created_at']

class SubscriptionPurchaseSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField(required=True)
    promo_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def validate(self, data):
        from .models import SubscriptionPlan, PromoCode
        
        try:
            plan = SubscriptionPlan.objects.get(id=data['plan_id'], is_active=True)
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError({"plan_id": "Тарифный план не найден или неактивен"})
        
        promo_code = data.get('promo_code')
        promo = None
        
        if promo_code:
            try:
                promo = PromoCode.objects.get(code=promo_code, is_active=True)
                if not promo.is_valid():
                    raise serializers.ValidationError({"promo_code": "Промокод недействителен или истек срок действия"})
            except PromoCode.DoesNotExist:
                raise serializers.ValidationError({"promo_code": "Промокод не найден"})
        
        data['plan'] = plan
        data['promo'] = promo
        
        return data