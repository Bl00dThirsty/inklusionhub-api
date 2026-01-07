# api/serializers/auth.py
from rest_framework import serializers
from .models import User
from django.contrib.auth.password_validation import validate_password

# ============================================================
# LOGIN
# ============================================================
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            user = User.objects.get(email__iexact=data["email"])
        except User.DoesNotExist:
            raise serializers.ValidationError({
                "detail": "Email ou mot de passe incorrect."
            })

        if not user.check_password(data["password"]):
            raise serializers.ValidationError({
                "detail": "Email ou mot de passe incorrect."
            })

        if not user.is_active:
            raise serializers.ValidationError({
                "detail": "Votre compte est désactivé."
            })

        data["user"] = user
        return data

# ============================================================
# REGISTER
# ============================================================
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    
    
    class Meta:
        model = User
        fields = ('email', 'name', 'forename', 'password')
        extra_kwargs = {
            'name': {'required': True},
            'forename': {'required': True},
        }
    
    # def validate(self, attrs):
    #     if attrs['password'] != attrs['password2']:
    #         raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
    #     return attrs
    
    def create(self, validated_data):
        # validated_data.pop('password2')
        # Par défaut, on met 'malentendant' comme rôle initial
        user = User.objects.create_user(
            email=validated_data['email'],
            name=validated_data['name'],
            forename=validated_data['forename'],
            password=validated_data['password'],
            role='malentendant'  # Rôle par défaut
        )
        return user

class UserSerializer(serializers.ModelSerializer):
    langue_parlee = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    secondary_roles = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    preference_apprentissage = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    preferences = serializers.DictField(required=False)

    class Meta:
        model = User
        fields = "__all__"
        read_only_fields = ("id", "date_joined", "updated_at")
# ============================================================
# ROLE SELECTION (ONBOARDING STEP 2)
# ============================================================
class RoleSelectionSerializer(serializers.ModelSerializer):
    secondary_roles = serializers.ListField(
        child=serializers.ChoiceField(choices=User.ROLE_CHOICES),
        required=False,
        write_only=True,
        allow_empty=True
    )
    
    class Meta:
        model = User
        fields = ('role', 'secondary_roles')
    
    def validate_role(self, value):
        # S'assurer que le rôle est valide
        valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
        if value not in valid_roles:
            raise serializers.ValidationError(f"Rôle invalide. Choisissez parmi: {', '.join(valid_roles)}")
        return value
    
    def validate_secondary_roles(self, value):
        valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
        for role in value:
            if role not in valid_roles:
                raise serializers.ValidationError(f"Rôle secondaire invalide: {role}")
        
        # Éviter les doublons avec le rôle principal
        if self.initial_data.get('role') in value:
            raise serializers.ValidationError("Le rôle principal ne peut pas être aussi un rôle secondaire")
        
        return value
    
    def update(self, instance, validated_data):
        secondary_roles = validated_data.pop('secondary_roles', [])
        
        # Mettre à jour le rôle principal
        instance.role = validated_data.get('role', instance.role)
        
        # Stocker les rôles secondaires
        instance.secondary_roles = secondary_roles
        
        # Mettre à jour l'étape d'onboarding
        instance.onboarding_step = 2
        
        instance.save()
        return instance
    

# ============================================================
# BASIC PROFILE (ONBOARDING STEP 3)
# ============================================================
class BasicProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('phone', 'avatar', 'adresse', 'Profession')
        extra_kwargs = {
            'phone': {'required': True},
            'adresse': {'required': True},
            'Profession': {'required': True},
        }
    
    def validate_phone(self, value):
        import re
        if not re.match(r'^[\d\s\-\+\(\)]{8,20}$', value):
            raise serializers.ValidationError(
                "Format de téléphone invalide. Utilisez des chiffres, espaces, +, - ou ()."
            )
        return value
    
    def update(self, instance, validated_data):
        # Mettre à jour l'étape d'onboarding
        instance.onboarding_step = 3
        instance.save()
        
        return super().update(instance, validated_data)


# ============================================================
# ROLE-SPECIFIC PROFILES (ONBOARDING STEP 4)
# ============================================================
class EmployerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'company_name', 
            'Domaine_activity', 
            'Type_company',
            'Adresse_company', 
            'Taille_Company', 
            'Site_web'
        )
    
    #def validate(self, data):
        # Validation spécifique pour employeur
       # required_fields = ['company_name', 'Domaine_activity']
       # for field in required_fields:
        #    if not data.get(field):
          #      raise serializers.ValidationError({
          #          field: f"Ce champ est requis pour les employeurs."
         #       })
        #return data
    
    def update(self, instance, validated_data):
        instance.onboarding_step = 4
        instance.save()
        return super().update(instance, validated_data)


class TranslatorProfileSerializer(serializers.ModelSerializer):
    Jour_disponible = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    Creneau_horaire_disponible = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )

    class Meta:
        model = User
        fields = (
            'certification',
            'Annee_experience',
            'niveau_expertise',
            'Competence',
            'Jour_disponible',
            'Creneau_horaire_disponible',
            'Tarif_horaire'
        )
    
    def validate_Annee_experience(self, value):
        if value < 0:
            raise serializers.ValidationError("Les années d'expérience ne peuvent pas être négatives.")
        return value
    
    def validate_Tarif_horaire(self, value):
        if value < 0:
            raise serializers.ValidationError("Le tarif horaire ne peut pas être négatif.")
        return value
    
    def update(self, instance, validated_data):
        instance.onboarding_step = 4
        instance.save()
        return super().update(instance, validated_data)


class HearingImpairedProfileSerializer(serializers.ModelSerializer):
    langue_parlee = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )

    class Meta:
        model = User
        fields = (
            'niveau_perte_auditive',
            'status_utilisez_vous_un_appareil_auditif',
            'level_en_LSF',
            'langue_parlee'
        )
    
    def update(self, instance, validated_data):
        instance.onboarding_step = 4
        instance.save()
        return super().update(instance, validated_data)


class LearnerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('preference_apprentissage', 'langue_parlee', 'level_en_LSF')
    
    def update(self, instance, validated_data):
        instance.onboarding_step = 4
        instance.save()
        return super().update(instance, validated_data)


class EntendantProfileSerializer(serializers.ModelSerializer):
    """Pour les utilisateurs avec rôle 'entendant'"""
    class Meta:
        model = User
        fields = ('langue_parlee', 'Profession', 'level_en_LSF')
    
    def update(self, instance, validated_data):
        #instance.onboarding_step = 4
       # instance.save()
        return super().update(instance, validated_data)

# ============================================================
# PREFERENCES (ONBOARDING FINAL)
# ============================================================
class PreferencesSerializer(serializers.ModelSerializer):
    # Champs supplémentaires pour le frontend
    email_notifications = serializers.BooleanField(write_only=True, required=False)
    push_notifications = serializers.BooleanField(write_only=True, required=False)
    # marketing_emails = serializers.BooleanField(write_only=True, required=False)
    # auto_subtitles = serializers.BooleanField(write_only=True, required=False)
    # sign_language_videos = serializers.BooleanField(write_only=True, required=False)
    # high_contrast_mode = serializers.BooleanField(write_only=True, required=False)
    # font_size = serializers.CharField(write_only=True, required=False)
    timezone = serializers.CharField(write_only=True, required=False)
    language = serializers.CharField(write_only=True, required=False)
    profile_visibility = serializers.CharField(write_only=True, required=False)
    show_online_status = serializers.BooleanField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = (
            'langue_parlee', 
            'preferences',
            # Champs du frontend
            'email_notifications',
            'push_notifications', 
            # 'marketing_emails',
            # 'auto_subtitles',
            # 'sign_language_videos',
            # 'high_contrast_mode',
            # 'font_size',
            'timezone',
            'language',
            'profile_visibility',
            'show_online_status'
        )
    
    def update(self, instance, validated_data):
        # Extraire les préférences du frontend
        frontend_preferences = {
            'notifications': {
                'email': validated_data.pop('email_notifications', True),
                'push': validated_data.pop('push_notifications', True),
                # 'marketing': validated_data.pop('marketing_emails', False)
            },
            'accessibility': {
                # 'auto_subtitles': validated_data.pop('auto_subtitles', True),
                # 'sign_language_videos': validated_data.pop('sign_language_videos', True),
                # 'high_contrast_mode': validated_data.pop('high_contrast_mode', False),
                # 'font_size': validated_data.pop('font_size', 'medium'),
                'show_online_status': validated_data.pop('show_online_status', True)
            },
            'general': {
                'timezone': validated_data.pop('timezone', 'Europe/Paris'),
                'language': validated_data.pop('language', 'fr'),
                'profile_visibility': validated_data.pop('profile_visibility', 'public'),
                
            }
        }
        
        # Mettre à jour le champ preferences
        instance.preferences = frontend_preferences
        
        # Marquer l'onboarding comme terminé
        instance.onboarding_completed = True
        instance.onboarding_step = 5
        
        # Sauvegarder
        instance.save()
        
        return instance
    

# ============================================================
# CURRENT USER (LIGHT)
# ============================================================
class CurrentUserSerializer(serializers.ModelSerializer):
    secondary_roles = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    has_completed_onboarding = serializers.SerializerMethodField()
    date_joined_formatted = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'name', 'forename', 'role',
            'secondary_roles',
            'phone', 'avatar_url', 'adresse', 'Profession',
            'has_completed_onboarding', 'onboarding_step',
            'date_joined_formatted'
        )

    def get_secondary_roles(self, obj):
        return obj.secondary_roles or []

    def get_has_completed_onboarding(self, obj):
        return obj.onboarding_completed

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None

    def get_date_joined_formatted(self, obj):
        return obj.date_joined.strftime("%d/%m/%Y %H:%M")
    
#============================================================
# UPDATE PROFILE
#============================================================
class UpdateProfileSerializer(serializers.ModelSerializer):
    # Ajoutez ces champs
    role = serializers.ChoiceField(
        choices=User.ROLE_CHOICES,
        required=False,
        allow_blank=False
    )
    
    # Pour secondary_roles, utilisez ListField si c'est une liste de strings
    secondary_roles = serializers.ListField(
        child=serializers.ChoiceField(choices=User.ROLE_CHOICES),
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = User
        fields = ('email', 'name', 'forename', 'phone', 'adresse', 'Profession', 'role', 'secondary_roles')
        extra_kwargs = {
            'email': {'required': True},
            'name': {'required': True},
            'forename': {'required': True},
            'phone': {'required': True},
            'adresse': {'required': True},
            'Profession': {'required': True},
        }
    
    def validate_phone(self, value):
        import re
        if not re.match(r'^[\d\s\-\+\(\)]{8,20}$', value):
            raise serializers.ValidationError(
                "Format de téléphone invalide. Utilisez des chiffres, espaces, +, - ou ()."
            )
        return value
    
    def validate(self, data):
        # Validation personnalisée
        role = data.get('role')
        secondary_roles = data.get('secondary_roles', [])
        
        # Vérifier que le rôle principal n'est pas dans les rôles secondaires
        if role and role in secondary_roles:
            raise serializers.ValidationError({
                'secondary_roles': 'Le rôle principal ne peut pas être aussi un rôle secondaire.'
            })
        
        # Vérifier qu'il n'y a pas de doublons dans les rôles secondaires
        if secondary_roles and len(secondary_roles) != len(set(secondary_roles)):
            raise serializers.ValidationError({
                'secondary_roles': 'Les rôles secondaires ne doivent pas contenir de doublons.'
            })
        
        return data
    
    def update(self, instance, validated_data):
        # Extraire les rôles
        role = validated_data.pop('role', None)
        secondary_roles = validated_data.pop('secondary_roles', None)
        
        # Mettre à jour les autres champs
        instance = super().update(instance, validated_data)
        
        # Mettre à jour le rôle principal si fourni
        if role is not None:
            instance.role = role
        
        # Mettre à jour les rôles secondaires si fournis
        if secondary_roles is not None:
            instance.secondary_roles = secondary_roles
        
        instance.save()
        return instance
        
# ============================================================
# USER PROFILE BY ROLE (POUR TON DIALOG FRONTEND)
# ============================================================
class UserProfileByRoleSerializer(serializers.ModelSerializer):
    secondary_roles = serializers.SerializerMethodField()
    role_profiles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "name",
            "forename",
            "role",
            "secondary_roles",
            "role_profiles",
        )

    def get_secondary_roles(self, obj):
        return obj.secondary_roles or []

    def get_role_profiles(self, obj):
        roles = set([obj.role] + (obj.secondary_roles or []))
        profiles = {}

        if "traducteur" in roles:
            profiles["traducteur"] = TranslatorProfileSerializer(obj).data

        if "malentendant" in roles:
            profiles["malentendant"] = HearingImpairedProfileSerializer(obj).data

        if "apprenant" in roles:
            profiles["apprenant"] = LearnerProfileSerializer(obj).data

        if "employeur" in roles:
            profiles["employeur"] = EmployerProfileSerializer(obj).data

        if "entendant" in roles:
            profiles["entendant"] = EntendantProfileSerializer(obj).data

        return profiles