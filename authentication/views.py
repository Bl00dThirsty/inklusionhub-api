from django.shortcuts import render

# api/views/auth.py
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import authenticate
from django.db import transaction
from .serializers import *
from .models import *
from rest_framework import status
import os
from django.http import FileResponse, Http404
from django.conf import settings
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated

# class RegisterView(generics.CreateAPIView):
#     """
#     Écran 1 - Inscription rapide
#     Crée un user minimal avec rôle par défaut (malentendant)
#     """
#     serializer_class = RegisterSerializer
#     permission_classes = [permissions.AllowAny]
    
#     def perform_create(self, serializer):
#         user = serializer.save()
#         # Vous pouvez ajouter ici l'envoi d'email de confirmation
#         return user
# authentication/views.py
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            print(f"Erreurs de validation: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = serializer.save()
            
            # Générer les tokens JWT
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'success': True,
                'message': 'Inscription réussie',
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'name': user.name,
                    'forename': user.forename,
                    'role': user.role
                },
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# class LoginView(APIView):
#     """
#     Login standard (géré par laura)
#     """
#     permission_classes = [permissions.AllowAny]
    
#     def post(self, request):
#         email = request.data.get('email')
#         password = request.data.get('password')
        
#         user = authenticate(email=email, password=password)
        
#         if user:
#             refresh = RefreshToken.for_user(user)
#             return Response({
#                 'refresh': str(refresh),
#                 'access': str(refresh.access_token),
#                 'user': UserSerializer(user).data
#             })
#         return Response({'error': 'Identifiants invalides'}, 
#                        status=status.HTTP_401_UNAUTHORIZED)
    
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data["user"]
            
            # Générer les tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "forename": user.forename,
                    "role": user.role,
                    "avatar": user.avatar.url if user.avatar else None,
                }
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OnboardingRoleSelectionView(APIView):
    """
    Écran 2 - Sélection des rôles
    """
    authentication_classes = [JWTAuthentication]  # ← AJOUTEZ CEUX-CI
    permission_classes = [permissions.IsAuthenticated]
    
    # def put(self, request):
    #     print(f"Utilisateur authentifié: {request.user}")
    #     print(f"Email: {request.user.email}")
    #     print(f"Is authenticated: {request.user.is_authenticated}")

    #     user = request.user
    #     serializer = RoleSelectionSerializer(user, data=request.data)
        
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response({
    #             'message': 'Rôles mis à jour avec succès',
    #             'user': UserSerializer(user).data
    #         })
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def put(self, request):
        # Debug
        print(f"=== DEBUG OnboardingRoleSelectionView ===")
        print(f"User: {request.user}")
        print(f"User ID: {request.user.id}")
        print(f"User authenticated: {request.user.is_authenticated}")
        print(f"Auth header: {request.META.get('HTTP_AUTHORIZATION')}")
        print(f"Request data: {request.data}")
        print("=========================================")
        
        # Si l'utilisateur n'est pas authentifié
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = request.user
        serializer = RoleSelectionSerializer(user, data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Rôles mis à jour avec succès',
                'user': UserSerializer(user).data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class OnboardingBasicProfileView(APIView):
    """
    Écran 3 - Profil de base (UNIQUEMENT les champs de base)
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def put(self, request):
        print(f"=== DEBUG BasicProfile ===")
        print(f"User: {request.user.email}")
        print(f"Data keys: {request.data.keys()}")
        print("==========================")
        
        user = request.user
        serializer = BasicProfileSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            user = serializer.save()
            
            return Response({
                'success': True,
                'message': 'Profil de base mis à jour',
                'user': UserSerializer(user).data,
                'next_step': self.get_next_step(user)
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def get_next_step(self, user):
        """Déterminer la prochaine étape selon le rôle"""
        # Vérifie si l'utilisateur a besoin d'un profil avancé
        if user.role in ['employeur', 'traducteur']:
            return 'advanced-profiles'
        else:
            return 'preferences'

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    
class OnboardingAdvancedProfileView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def put(self, request):
        print(f"=== DEBUG ADVANCED PROFILE ===")
        print(f"User: {request.user.email}")
        print(f"User role: {request.user.role}")
        print(f"Request data: {request.data}")
        print("==============================")
        
        user = request.user
        
        # Sélection du serializer selon le rôle principal
        if user.role == 'employeur':
            serializer = EmployerProfileSerializer(user, data=request.data, partial=True)
            print(f"Using EmployerProfileSerializer")
        elif user.role == 'traducteur':
            serializer = TranslatorProfileSerializer(user, data=request.data, partial=True)
            print(f"Using TranslatorProfileSerializer")
        elif user.role == 'malentendant':
            serializer = HearingImpairedProfileSerializer(user, data=request.data, partial=True)
            print(f"Using HearingImpairedProfileSerializer")
        elif user.role == 'apprenant':
            serializer = LearnerProfileSerializer(user, data=request.data, partial=True)
            print(f"Using LearnerProfileSerializer")
        elif user.role == 'entendant':
            # Créez un serializer pour entendant ou réutilisez un autre
            serializer = BasicProfileSerializer(user, data=request.data, partial=True)
            print(f"Using BasicProfileSerializer for entendant")
        else:
            return Response({
                'success': False,
                'message': 'Rôle non supporté'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validation détaillée
        if serializer.is_valid():
            print(f"Serializer is VALID")
            user = serializer.save()
            return Response({
                'success': True,
                'message': 'Profil avancé mis à jour',
                'user': UserSerializer(user).data,
                'next_step': 'preferences'
            }, status=status.HTTP_200_OK)
        else:
            print(f"Serializer ERRORS: {serializer.errors}")  # ← CE LOG EST CRUCIAL
            return Response({
                'success': False,
                'errors': serializer.errors,
                'message': 'Erreur de validation'
            }, status=status.HTTP_400_BAD_REQUEST)

class OnboardingPreferencesView(APIView):
    """
    Écran 5 - Préférences & Notifications
    """
    authentication_classes = [JWTAuthentication] 
    permission_classes = [permissions.IsAuthenticated]
    
    def put(self, request):
        user = request.user
        
        print(f"=== DEBUG Preferences ===")
        print(f"User: {user.email}")
        print(f"Request data: {request.data}")
        print("=========================")
        
        serializer = PreferencesSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            user = serializer.save()
            
            return Response({
                'success': True,
                'message': 'Préférences enregistrées et onboarding terminé',
                'user': UserSerializer(user).data,
                'redirect': '/dashboard'
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class CompleteOnboardingView(APIView):
    """
    Marquer l'onboarding comme terminé
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        user.onboarding_completed = True  # Ajouter ce champ dans le modèle User
        user.save()
        return Response({
            'message': 'Onboarding terminé',
            'redirect': '/dashboard'
        })
    
class GetCurrentUserView(APIView):
    """
    Récupérer les informations de l'utilisateur connecté
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Serializer avec tous les champs nécessaires pour le frontend
        serializer = UserSerializer(user)
        
        return Response({
            'success': True,
            'message': 'Utilisateur récupéré avec succès',
            'user': serializer.data
        }, status=status.HTTP_200_OK)



#####UPDATE PROFILE VIEW #####
class UpdateProfileView(APIView):
    """
    Mise à jour du profil de base
    """
class UpdateUserSecondaryRoleProfileView(APIView):
    ##Mise à jour des informations d’un rôle secondaire (édition depuis la modal)

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def patch(self, request):
        user = request.user
        role = request.data.get("role")
        data = request.data.get("data", {})

        if not role:
            return Response(
                {"success": False, "message": "Rôle manquant"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔐 Vérifier que l'utilisateur possède bien ce rôle
        user_roles = [user.role] + (user.secondary_roles or [])

        if role not in user_roles:
            return Response(
                {"success": False, "message": "Rôle non autorisé"},
                status=status.HTTP_403_FORBIDDEN
            )

        # 🎯 Sélection du serializer selon le rôle
        if role == "apprenant":
            serializer_class = LearnerProfileSerializer
        elif role == "traducteur":
            serializer_class = TranslatorProfileSerializer
        elif role == "employeur":
            serializer_class = EmployerProfileSerializer
        elif role == "malentendant":
            serializer_class = HearingImpairedProfileSerializer
        elif role == "entendant":
            serializer_class = BasicProfileSerializer
        else:
            return Response(
                {"success": False, "message": "Rôle non supporté"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = serializer_class(
            user,
            data=data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Profil du rôle mis à jour",
                "role": role,
                "user": UserSerializer(user).data
            }, status=status.HTTP_200_OK)

        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
