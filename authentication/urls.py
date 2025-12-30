# api/urls.py
from django.urls import path
from .views import *

urlpatterns = [
    # Auth de base
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    
    # Onboarding flow
    path('onboarding/roles/', OnboardingRoleSelectionView.as_view(), name='onboarding-roles'),
    path('onboarding/basic-profile/', OnboardingBasicProfileView.as_view(), name='onboarding-basic'),
    path('onboarding/advanced-profile/', OnboardingAdvancedProfileView.as_view(), name='onboarding-advanced'),
    path('onboarding/preferences/', OnboardingPreferencesView.as_view(), name='onboarding-preferences'),
    path('onboarding/complete/', CompleteOnboardingView.as_view(), name='onboarding-complete'),
    path('user/me/', GetCurrentUserView.as_view(), name='get-current-user'),
    path('user/me/secondary-roles/', UpdateUserSecondaryRoleProfileView.as_view(), name='update-secondary-role'),
    # Récupérer l'état de l'onboarding
   # path('onboarding/status/', OnboardingStatusView.as_view(), name='onboarding-status'),
]