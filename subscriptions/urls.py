from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SubscriptionPlanViewSet, UserSubscriptionViewSet,
    TransactionViewSet, PromoCodeViewSet,
    PurchaseSubscriptionView, UserBalanceView
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
]