# api/serializers/auth.py
from rest_framework import serializers
from .models import User
from django.contrib.auth.password_validation import validate_password

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
    class Meta:
        model = User
        fields = ('id', 'email', 'name', 'forename', 'role', 'avatar', 
                 'phone', 'adresse', 'Profession', 'date_joined')
        read_only_fields = ('id', 'date_joined')

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
    
# authentication/serializers.py
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

# authentication/serializers.py - à AJOUTER

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
    
    def validate(self, data):
        # Validation spécifique pour employeur
        required_fields = ['company_name', 'Domaine_activity']
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError({
                    field: f"Ce champ est requis pour les employeurs."
                })
        return data
    
    def update(self, instance, validated_data):
        instance.onboarding_step = 4
        instance.save()
        return super().update(instance, validated_data)


class TranslatorProfileSerializer(serializers.ModelSerializer):
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
        fields = ('preference_apprentissage', 'langue_parlee')
    
    def update(self, instance, validated_data):
        instance.onboarding_step = 4
        instance.save()
        return super().update(instance, validated_data)


class EntendantProfileSerializer(serializers.ModelSerializer):
    """Pour les utilisateurs avec rôle 'entendant'"""
    class Meta:
        model = User
        fields = ('langue_parlee',)
    
    def update(self, instance, validated_data):
        instance.onboarding_step = 4
        instance.save()
        return super().update(instance, validated_data)


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
    

class UserSerializer(serializers.ModelSerializer):
    """Serializer complet pour l'utilisateur (lecture seulement)"""
    secondary_roles = serializers.SerializerMethodField()
    onboarding_completed = serializers.BooleanField(read_only=False)
    onboarding_step = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'name', 'forename', 'role', 'secondary_roles',
            'phone', 'avatar', 'adresse', 'Profession',
            'onboarding_completed', 'onboarding_step', 'date_joined',
            
            # Champs pour malentendant
            'niveau_perte_auditive', 'status_utilisez_vous_un_appareil_auditif', 'level_en_LSF',
            
            # Champs pour apprenant
            'preference_apprentissage',
            
            # Champs pour traducteur
            'certification', 'Annee_experience', 'niveau_expertise',
            'Competence', 'Jour_disponible', 'Creneau_horaire_disponible', 'Tarif_horaire',
            
            # Champs pour employeur
            'company_name', 'Domaine_activity', 'Type_company',
            'Adresse_company', 'Taille_Company', 'Site_web',
            
            # Langues parlées
            'langue_parlee'
        )
        read_only_fields = (
    'id', 'email', 'date_joined',
    # etc., tous les champs que l’utilisateur ne doit pas modifier directement
) # Tous les champs en lecture seule pour cet endpoint
    
    def get_secondary_roles(self, obj):
        """Récupérer les rôles secondaires depuis le champ JSON"""
        if hasattr(obj, 'secondary_roles'):
            return obj.secondary_roles
        return []
    
    def to_representation(self, instance):
        """Personnaliser la représentation JSON"""
        representation = super().to_representation(instance)
        
        # Gérer l'URL de l'avatar
        if instance.avatar:
            representation['avatar'] = instance.avatar.url
        else:
            representation['avatar'] = None
        
        # Formater la date
        representation['date_joined'] = instance.date_joined.isoformat()
        
        return representation


class CurrentUserSerializer(serializers.ModelSerializer):
    """Serializer spécifique pour l'utilisateur connecté"""
    secondary_roles = serializers.SerializerMethodField()
    has_completed_onboarding = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'name', 'forename', 'role', 'secondary_roles',
            'phone', 'avatar_url', 'adresse', 'Profession',
            'has_completed_onboarding', 'onboarding_step',
            'date_joined_formatted'
        )
    
    def get_secondary_roles(self, obj):
        if hasattr(obj, 'secondary_roles'):
            return obj.secondary_roles
        return []
    
    def get_has_completed_onboarding(self, obj):
        if hasattr(obj, 'onboarding_completed'):
            return obj.onboarding_completed
        return False
    
    avatar_url = serializers.SerializerMethodField()
    
    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None
    
    date_joined_formatted = serializers.SerializerMethodField()
    
    def get_date_joined_formatted(self, obj):
        return obj.date_joined.strftime("%d/%m/%Y %H:%M")