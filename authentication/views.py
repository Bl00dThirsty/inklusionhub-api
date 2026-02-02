import datetime
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
from rest_framework.permissions import IsAuthenticated, AllowAny
from events.publisher import (
    publish_user_created, publish_user_updated, 
    publish_user_deleted, publish_user_role_changed,
    publish_user_secondary_roles_updated,  auth_publisher
)

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
            
            # Publier l'événement USER_CREATED
            try:
                publish_user_created(user)
                print(f"✅ Événement USER_CREATED publié pour {user.email}")
            except Exception as e:
                print(f"⚠️ Événement non publié: {e}")

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
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data["user"]
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




def serve_avatar(request, filename):
    # Chemin vers votre dossier avatars
    avatar_path = os.path.join(settings.BASE_DIR, 'avatars', filename)
    
    if os.path.exists(avatar_path):
        return FileResponse(open(avatar_path, 'rb'), content_type='image/jpeg')
    raise Http404("Avatar not found")

#####UPDATE PROFILE VIEW #####
class UpdateProfileView(APIView):
    """
    Mise à jour du profil de base
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def put(self, request):
        print(f"=== DEBUG Update Profile ===")
        print(f"User: {request.user.email}")
        print(f"Content-Type: {request.content_type}")
        print(f"Données brutes: {request.data}")
        
        # Gérer différentes structures de données
        user_data = request.data
        
        if isinstance(user_data, dict) and 'data' in user_data:
            print("⚠️ Structure détectée: données dans 'data'")
            user_data = user_data['data']
        
        print(f"Données à traiter: {user_data}")
        
        # Log spécifique pour les rôles
        if 'role' in user_data:
            print(f"   Rôle reçu: {user_data.get('role')}")
        if 'secondary_roles' in user_data:
            print(f"   Rôles secondaires reçus: {user_data.get('secondary_roles')}")
        
        print("==========================")
        
        user = request.user

        # Sauvegarder l'état avant modification
        old_role = user.role
        old_secondary_roles = user.secondary_roles or []
        
        serializer = UpdateProfileSerializer(user, data=user_data, partial=True)
        
        if serializer.is_valid():
            try:
                 # Récupérer les champs qui vont changer
                changed_fields = []
                for field, value in serializer.validated_data.items():
                    if getattr(user, field) != value:
                        changed_fields.append(field) 

                # Sauvegarder
                user = serializer.save()

                # Publier les événements si nécessaire
                try:
                    if changed_fields:
                        publish_user_updated(user, changed_fields)
                        print(f"✅ Événement USER_UPDATED publié avec champs: {changed_fields}")
                    
                    # Événement spécifique pour changement de rôle principal
                    if 'role' in changed_fields:
                        publish_user_role_changed(user, old_role, user.role)
                        print(f"✅ Événement USER_ROLE_CHANGED publié: {old_role} → {user.role}")
                    
                    # Événement pour rôles secondaires
                    if 'secondary_roles' in changed_fields:
                        new_secondary = user.secondary_roles or []
                        added = [r for r in new_secondary if r not in old_secondary_roles]
                        removed = [r for r in old_secondary_roles if r not in new_secondary]
                        
                        if added or removed:
                            publish_user_secondary_roles_updated(user, added, removed)
                            print(f"✅ Événement SECONDARY_ROLES_UPDATED publié")
                
                except Exception as e:
                    print(f"⚠️ Événements non publiés: {e}")
                
                return Response({
                    'success': True,
                    'message': 'Profil mis à jour avec succès',
                    'user': UserSerializer(user).data,
                }, status=status.HTTP_200_OK)
                
                # Log de confirmation
                print(f"   Profil mis à jour: {user.email}")
                print(f"   Nom: {user.name}")
                print(f"   Prénom: {user.forename}")
                print(f"   Rôle: {user.role}")
                print(f"   Rôles secondaires: {user.secondary_roles}")
                
                return Response({
                    'success': True,
                    'message': 'Profil mis à jour avec succès',
                    'user': UserSerializer(user).data,
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                print(f" Erreur lors de la sauvegarde: {str(e)}")
                import traceback
                traceback.print_exc()
                return Response({
                    'success': False,
                    'error': f'Erreur serveur: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            print(f" Erreurs de validation: {serializer.errors}")
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        

class UpdateAvatarView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]
    
    def put(self, request):
        user = request.user
        
        if 'avatar' not in request.FILES:
            return Response({
                'success': False,
                'error': 'Aucun fichier avatar fourni'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        avatar_file = request.FILES['avatar']
        user.avatar = avatar_file
        user.save()
        
        return Response({
            'success': True,
            'message': 'Avatar mis à jour',
            'avatar_url': user.avatar.url if user.avatar else None
        }, status=status.HTTP_200_OK)
    
class UpdateUserSecondaryRoleProfileView(APIView):
    """Mise à jour d'un rôle secondaire avec rôle dans l'URL"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def patch(self, request, role):
        user = request.user
        
        print(f"=== DEBUG UpdateSecondaryRoleProfileView ===")
        print(f"Rôle depuis URL: {role}")
        print(f"User: {user.email}")
        print(f"Request data: {request.data}")
        print("==============================================")
        
        # Vérifier que le rôle est valide
        valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
        if role not in valid_roles:
            return Response(
                {"success": False, "message": f"Rôle '{role}' non valide"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier que l'utilisateur possède bien ce rôle
        user_roles = [user.role] + (user.secondary_roles or [])
        
        if role not in user_roles:
            print(f"Rôle {role} non trouvé dans les rôles de l'utilisateur: {user_roles}")
            # Ajouter le rôle aux rôles secondaires si ce n'est pas le rôle principal
            if role != user.role:
                if user.secondary_roles is None:
                    user.secondary_roles = []
                if role not in user.secondary_roles:
                    user.secondary_roles.append(role)
                    user.save()
                    print(f"Ajout du rôle {role} aux rôles secondaires")
        
        # Sélection du serializer
        serializer_map = {
            "apprenant": LearnerProfileSerializer,
            "traducteur": TranslatorProfileSerializer,
            "employeur": EmployerProfileSerializer,
            "malentendant": HearingImpairedProfileSerializer,
            "entendant": EntendantProfileSerializer,
        }
        
        if role not in serializer_map:
            return Response(
                {"success": False, "message": f"Rôle '{role}' non supporté"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer_class = serializer_map[role]
        
        print(f"Using serializer: {serializer_class.__name__}")
        print(f"Fields: {serializer_class.Meta.fields}")
        
        # Utiliser directement les données de la requête
        serializer = serializer_class(
            user,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            try:
                serializer.save()
                user.refresh_from_db()
                
                return Response({
                    "success": True,
                    "message": f"Profil {role} mis à jour",
                    "role": role,
                    "user": UserSerializer(user).data
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                print(f"Save error: {str(e)}")
                import traceback
                traceback.print_exc()
                return Response({
                    "success": False,
                    "message": f"Erreur serveur: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        print(f"Validation errors: {serializer.errors}")
        return Response({
            "success": False,
            "errors": serializer.errors,
            "message": "Erreur de validation"
        }, status=status.HTTP_400_BAD_REQUEST)
    

class DeleteUserView(APIView):
    """Supprimer un utilisateur (admin seulement)"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            
            # Publier l'événement avant suppression
            try:
                publish_user_deleted(user_id)
                print(f"✅ Événement USER_DELETED publié pour {user.email}")
            except Exception as e:
                print(f"⚠️ Événement non publié: {e}")
            
            # Supprimer l'utilisateur
            user.delete()
            
            return Response({
                'success': True,
                'message': f'Utilisateur {user.email} supprimé avec succès'
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Utilisateur non trouvé'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListUsersView(generics.ListAPIView):
    """Lister tous les utilisateurs (admin seulement)"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    queryset = User.objects.all()
    # filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['role', 'is_active']
    search_fields = ['email', 'name', 'forename']
    
    def list(self, request, *args, **kwargs):
        # Publier un événement d'audit (optionnel)
        try:
            auth_publisher.publish_user_event(
                'USER_LIST_REQUESTED',
                {
                    'requested_by': str(request.user.id),
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            print(f"⚠️ Événement audit non publié: {e}")
        
        return super().list(request, *args, **kwargs)