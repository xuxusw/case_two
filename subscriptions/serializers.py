from rest_framework import serializers
from .models import SubscriptionPlan, UserSubscription, Transaction, PromoCode
from django.utils import timezone

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'

class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlan.objects.filter(is_active=True),
        write_only=True,
        source='plan'
    )
    days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSubscription
        fields = ['id', 'plan', 'plan_id', 'status', 'start_date', 
                 'end_date', 'auto_renew', 'created_at', 'days_remaining']
        read_only_fields = ['status', 'start_date', 'end_date', 'created_at']
    
    def get_days_remaining(self, obj):
        return obj.days_remaining()

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['user', 'status', 'payment_data', 'created_at']

class PromoCodeSerializer(serializers.ModelSerializer):
    is_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = PromoCode
        fields = '__all__'
    
    def get_is_valid(self, obj):
        return obj.is_valid()

class SubscriptionPurchaseSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    promo_code = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        try:
            plan = SubscriptionPlan.objects.get(id=data['plan_id'], is_active=True)
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("План подписки не найден или неактивен")
        
        data['plan'] = plan
        
        if data.get('promo_code'):
            try:
                promo = PromoCode.objects.get(code=data['promo_code'])
                if not promo.is_valid():
                    raise serializers.ValidationError("Промокод недействителен")
                data['promo'] = promo
            except PromoCode.DoesNotExist:
                raise serializers.ValidationError("Промокод не найден")
        
        return data