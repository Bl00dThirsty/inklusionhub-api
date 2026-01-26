"""
URL configuration for inklusionhub_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from authentication.views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
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
    path('user/update/', UpdateProfileView.as_view(), name='update-profile'),
    path('avatars/<str:filename>', serve_avatar, name='serve_avatar'),
    path('user/update-avatar/', UpdateAvatarView.as_view(), name='update-avatar'),

    path('user/me/secondary-roles/<str:role>/',UpdateUserSecondaryRoleProfileView.as_view(),name='update-secondary-role'),
    
    # Communication app URLs
    path('communication/', include('communication.urls')),
    
]

# Servir les fichiers média en développement
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )