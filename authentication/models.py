#Model authentication
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
import uuid

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('L\'email est obligatoire')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin')
        
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Champs de base
    email = models.EmailField(unique=True, verbose_name='Adresse email')
    name = models.CharField(max_length=100, verbose_name='Nom')
    forename = models.CharField(max_length=100, verbose_name='Prénom')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Téléphone')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Photo de profil')
    adresse = models.TextField(blank=True, null=True, verbose_name='Adresse')
    Profession = models.CharField(max_length=100, blank=True, null=True, verbose_name='Profession')
    
    # Rôle utilisateur
    ROLE_CHOICES = [
        ('apprenant', 'Apprenant'),
        ('entendant', 'Entendant'),
        ('malentendant', 'Malentendant'),
        ('employeur', 'Employeur'),
        ('traducteur', 'Traducteur LSF'),
        ('admin', 'Administrateur'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='apprenant', verbose_name='Rôle')
    
    # Champs pour Malentendant
    niveau_perte_auditive = models.CharField(max_length=50, blank=True, null=True, verbose_name='Niveau de perte auditive')
    status_utilisez_vous_un_appareil_auditif = models.BooleanField(default=False, verbose_name='Utilise un appareil auditif')
    level_en_LSF = models.CharField(max_length=50, blank=True, null=True, verbose_name='Niveau en LSF')
    
    # Champs pour Apprenant
    preference_apprentissage = models.JSONField(default=list, blank=True, verbose_name='Préférences d\'apprentissage')
    
    # Champs pour Traducteur
    certification = models.CharField(max_length=200, blank=True, null=True, verbose_name='Certification LSF')
    Annee_experience = models.IntegerField(default=0, verbose_name='Années d\'expérience')
    niveau_expertise = models.CharField(max_length=50, blank=True, null=True, verbose_name='Niveau d\'expertise')
    Competence = models.TextField(blank=True, null=True, verbose_name='Compétences')
    Jour_disponible = models.CharField(max_length=200, blank=True, null=True, verbose_name='Jours disponibles')
    Creneau_horaire_disponible = models.CharField(max_length=200, blank=True, null=True, verbose_name='Créneaux horaires disponibles')
    Tarif_horaire = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Tarif horaire')
    
    # Champs pour Employeur
    company_name = models.CharField(max_length=200, blank=True, null=True, verbose_name='Nom de l\'entreprise')
    Domaine_activity = models.CharField(max_length=200, blank=True, null=True, verbose_name='Domaine d\'activité')
    Type_company = models.CharField(max_length=100, blank=True, null=True, verbose_name='Type d\'entreprise')
    Adresse_company = models.TextField(blank=True, null=True, verbose_name='Adresse de l\'entreprise')
    Taille_Company = models.CharField(max_length=50, blank=True, null=True, verbose_name='Taille de l\'entreprise')
    Site_web = models.URLField(blank=True, null=True, verbose_name='Site web')
    
    # Langues parlées (commun à plusieurs rôles)
    langue_parlee = models.JSONField(default=list, blank=True, verbose_name='Langues parlées')
    
    # Champs Django
    is_active = models.BooleanField(default=True, verbose_name='Compte actif')
    is_staff = models.BooleanField(default=False, verbose_name='Staff')
    is_superuser = models.BooleanField(default=False, verbose_name='Super utilisateur')
    
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="Date d'inscription")
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')
     # Nouveau champ pour les rôles secondaires
    secondary_roles = models.JSONField(default=list, blank=True, 
                                       verbose_name='Rôles secondaires') 
    # Pour suivre la progression de l'onboarding
    onboarding_completed = models.BooleanField(default=False, 
                                               verbose_name='Onboarding terminé')
    onboarding_step = models.IntegerField(default=1, 
                                          verbose_name='Étape onboarding')
    # Préférences utilisateur
    preferences = models.JSONField(default=dict, blank=True,
                                   verbose_name='Préférences utilisateur')
    
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'forename']
    
    objects = UserManager()
    
    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
    
    def __str__(self):
        return f"{self.name} {self.forename} ({self.email})"
    
    def get_full_name(self):
        return f"{self.name} {self.forename}"
    
    def get_short_name(self):
        return self.forename
    
    def get_role_display_fr(self):
        role_display = dict(self.ROLE_CHOICES)
        return role_display.get(self.role, self.role)


class Permission(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Nom de la permission')
    codename = models.CharField(max_length=100, unique=True, verbose_name='Code')
    description = models.TextField(blank=True, verbose_name='Description')
    
    class Meta:
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
    
    def __str__(self):
        return self.name


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Nom du rôle')
    permissions = models.ManyToManyField(Permission, blank=True, verbose_name='Permissions')
    description = models.TextField(blank=True, verbose_name='Description')
    
    class Meta:
        verbose_name = 'Rôle'
        verbose_name_plural = 'Rôles'
    
    def __str__(self):
        return self.name
