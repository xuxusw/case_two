from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SubscriptionPlanViewSet, UserSubscriptionViewSet,
    TransactionViewSet, PromoCodeViewSet,
    PurchaseSubscriptionView, UserBalanceView,
    RefundRequestView, RefundPolicyView,
    TestRenewSubscriptionView, UpdateEndDateView, ManualRenewalCheckView,
)

router = DefaultRouter()
router.register(r'plans', SubscriptionPlanViewSet, basename='plan')
router.register(r'my-subscriptions', UserSubscriptionViewSet, basename='mysubscription')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'promocodes', PromoCodeViewSet, basename='promocode')

urlpatterns = [
    path('', include(router.urls)),
    path('purchase/', PurchaseSubscriptionView.as_view(), name='purchase-subscription'),
    path('balance/', UserBalanceView.as_view(), name='user-balance'),

    # Возвраты
    path('refund-request/', RefundRequestView.as_view(), name='refund-request'),
    path('refund-policy/', RefundPolicyView.as_view(), name='refund-policy'),
    
    # Тестовые эндпоинты
    path('test-renew/<int:subscription_id>/', TestRenewSubscriptionView.as_view(), name='test-renew'),
    path('test/update-end-date/<int:subscription_id>/', UpdateEndDateView.as_view(), name='update-end-date'),
    path('manual-renewal/', ManualRenewalCheckView.as_view(), name='manual-renewal'),
]