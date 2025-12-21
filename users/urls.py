from django.urls import path
from .views import (
    RegisterView, LoginView, UserProfileView, 
    get_user_balance, deposit_funds, get_user_profile_full,
    get_user_balance_admin, adjust_balance_admin,
    AdminUserViewSet, AdminUpdateUserView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    
    # Эндпоинты для баланса 
    path('balance/', get_user_balance, name='get_balance'),
    path('deposit/', deposit_funds, name='deposit_funds'),
    path('profile/full/', get_user_profile_full, name='profile_full'),
    
    # Админские эндпоинты
    path('admin/users/', AdminUserViewSet.as_view({'get': 'list'}), name='admin_users'),
    path('admin/users/<int:user_id>/update/', AdminUpdateUserView.as_view(), name='admin_update_user'),
    path('admin/users/<int:user_id>/balance/', get_user_balance_admin, name='admin_user_balance'),
    path('admin/users/<int:user_id>/adjust-balance/', adjust_balance_admin, name='adjust_balance_admin'),
]