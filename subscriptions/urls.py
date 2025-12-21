from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SubscriptionPlanViewSet, UserSubscriptionViewSet,
    TransactionViewSet, PromoCodeViewSet,
    PurchaseSubscriptionView, UserBalanceView,
    RefundRequestView, RefundPolicyView,
    TestRenewSubscriptionView, UpdateEndDateView, ManualRenewalCheckView,
    SendTestEmailView, AdminSubscriptionViewSet, AdminTransactionViewSet,
)

router = DefaultRouter()
router.register(r'plans', SubscriptionPlanViewSet, basename='plan')
router.register(r'my-subscriptions', UserSubscriptionViewSet, basename='mysubscription')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'promocodes', PromoCodeViewSet, basename='promocode')
router.register(r'admin-subscriptions', AdminSubscriptionViewSet, basename='admin-subscription'),
router.register(r'admin-transactions', AdminTransactionViewSet, basename='admin-transaction'),

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
    # path('manual-renewal/', ManualRenewalCheckView.as_view(), name='manual-renewal'),
    path('run-renewal/', ManualRenewalCheckView.as_view(), name='run-renewal'),
    
    # Email уведомления
    path('send-test-email/', SendTestEmailView.as_view(), name='send-test-email'),

]