from django.contrib import admin

# Register your models here.
# api/views/admin.py
# from rest_framework import viewsets, permissions
# from .models import Role, Permission
# from .serializers import RoleSerializer, PermissionSerializer

# class PermissionViewSet(viewsets.ModelViewSet):
#     queryset = Permission.objects.all()
#     serializer_class = PermissionSerializer
#     permission_classes = [permissions.IsAdminUser]

# class RoleViewSet(viewsets.ModelViewSet):
#     queryset = Role.objects.all()
#     serializer_class = RoleSerializer
#     permission_classes = [permissions.IsAdminUser]
    
#     def perform_create(self, serializer):
#         role = serializer.save()
#         # Logique pour attribuer des permissions par défaut selon le type de rôle
#         return role

# authentication/admin.py
# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from django.contrib.auth.models import Group
# from django.utils.html import format_html
# from django.urls import reverse
# from django.contrib import messages
# from django.http import HttpResponseRedirect
# from .models import User, Role, Permission

# # Désinscrire le Group standard de Django admin
# admin.site.unregister(Group)

# # 1. Admin pour les Permissions
# @admin.register(Permission)
# class PermissionAdmin(admin.ModelAdmin):
#     list_display = ('name', 'codename', 'description_short')
#     list_filter = ('codename',)
#     search_fields = ('name', 'codename', 'description')
#     ordering = ('name',)
    
#     def description_short(self, obj):
#         return obj.description[:50] + '...' if obj.description and len(obj.description) > 50 else obj.description
#     description_short.short_description = 'Description'

# # 2. Admin pour les Rôles avec gestion des permissions
# @admin.register(Role)
# class RoleAdmin(admin.ModelAdmin):
#     list_display = ('name', 'permission_count', 'user_count', 'description_short')
#     list_filter = ('name',)
#     search_fields = ('name', 'description')
#     filter_horizontal = ('permissions',)  # Interface drag-and-drop pour les permissions
#     ordering = ('name',)
    
#     fieldsets = (
#         ('Informations de base', {
#             'fields': ('name', 'description')
#         }),
#         ('Permissions', {
#             'fields': ('permissions',),
#             'description': 'Sélectionnez les permissions associées à ce rôle'
#         }),
#     )
    
#     # Actions personnalisées
#     actions = ['duplicate_role', 'set_default_permissions']
    
#     def permission_count(self, obj):
#         return obj.permissions.count()
#     permission_count.short_description = 'Permissions'
    
#     def user_count(self, obj):
#         # Compte les utilisateurs ayant ce rôle (si vous avez un champ ManyToMany)
#         # Sinon, adaptez selon votre modèle
#         return User.objects.filter(role=obj.name).count()
#     user_count.short_description = 'Utilisateurs'
    
#     def description_short(self, obj):
#         return obj.description[:100] + '...' if obj.description and len(obj.description) > 100 else obj.description
#     description_short.short_description = 'Description'
    
#     # Action: Dupliquer un rôle
#     def duplicate_role(self, request, queryset):
#         for role in queryset:
#             new_role = Role.objects.create(
#                 name=f"{role.name} (copie)",
#                 description=role.description
#             )
#             new_role.permissions.set(role.permissions.all())
#             self.message_user(
#                 request, 
#                 f'Rôle "{role.name}" dupliqué en "{new_role.name}"', 
#                 messages.SUCCESS
#             )
#     duplicate_role.short_description = "Dupliquer les rôles sélectionnés"
    
#     # Action: Appliquer des permissions par défaut selon le type de rôle
#     def set_default_permissions(self, request, queryset):
#         for role in queryset:
#             default_permissions = self.get_default_permissions_for_role(role.name)
            
#             if default_permissions:
#                 role.permissions.add(*default_permissions)
#                 self.message_user(
#                     request,
#                     f'Permissions par défaut appliquées pour "{role.name}"',
#                     messages.SUCCESS
#                 )
#     set_default_permissions.short_description = "Appliquer permissions par défaut"
    
#     def get_default_permissions_for_role(self, role_name):
#         """Retourne les permissions par défaut selon le rôle"""
#         # Mapping des permissions par rôle
#         permissions_map = {
#             'admin': [
#                 'add_user', 'change_user', 'delete_user', 'view_user',
#                 'add_role', 'change_role', 'delete_role', 'view_role',
#                 'add_permission', 'change_permission', 'delete_permission', 'view_permission',
#             ],
#             'employeur': [
#                 'view_user', 'add_job', 'change_job', 'delete_job', 'view_job',
#                 'view_application', 'change_application',
#             ],
#             'traducteur': [
#                 'view_user', 'add_translation', 'change_translation', 'view_translation',
#                 'manage_availability', 'view_requests',
#             ],
#             'malentendant': [
#                 'view_user', 'request_translation', 'view_translation',
#                 'access_community', 'create_event',
#             ],
#             'apprenant': [
#                 'view_user', 'access_courses', 'take_quiz', 'view_progress',
#                 'access_community',
#             ],
#             'entendant': [
#                 'view_user', 'access_community', 'create_event',
#                 'volunteer_translation',
#             ],
#         }
        
#         # Convertir les noms de permissions en objets Permission
#         permission_codenames = permissions_map.get(role_name.lower(), [])
#         return Permission.objects.filter(codename__in=permission_codenames)

# # 3. Admin personnalisé pour User
# @admin.register(User)
# class UserAdmin(BaseUserAdmin):
#     # Configuration de l'affichage liste
#     list_display = ('email', 'forename', 'name', 'role', 'is_active', 
#                    'date_joined', 'onboarding_completed')
#     list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 
#                   'onboarding_completed', 'date_joined')
#     search_fields = ('email', 'name', 'forename', 'phone')
#     ordering = ('-date_joined',)
    
#     # Configuration des onglets de modification
#     fieldsets = (
#         ('Informations personnelles', {
#             'fields': ('email', 'password', 'name', 'forename', 
#                       'avatar_preview', 'avatar')
#         }),
#         ('Contact', {
#             'fields': ('phone', 'adresse', 'Profession')
#         }),
#         ('Rôle et permissions', {
#             'fields': ('role', 'secondary_roles', 'is_active', 
#                       'is_staff', 'is_superuser', 'groups', 'user_permissions')
#         }),
#         ('Onboarding', {
#             'fields': ('onboarding_completed', 'onboarding_step')
#         }),
#         ('Rôle spécifique: Malentendant', {
#             'fields': ('niveau_perte_auditive', 
#                       'status_utilisez_vous_un_appareil_auditif',
#                       'level_en_LSF'),
#             'classes': ('collapse',)
#         }),
#         ('Rôle spécifique: Traducteur', {
#             'fields': ('certification', 'Annee_experience', 'niveau_expertise',
#                       'Competence', 'Jour_disponible', 
#                       'Creneau_horaire_disponible', 'Tarif_horaire'),
#             'classes': ('collapse',)
#         }),
#         ('Rôle spécifique: Employeur', {
#             'fields': ('company_name', 'Domaine_activity', 'Type_company',
#                       'Adresse_company', 'Taille_Company', 'Site_web'),
#             'classes': ('collapse',)
#         }),
#         ('Préférences', {
#             'fields': ('langue_parlee', 'preferences')
#         }),
#         ('Dates importantes', {
#             'fields': ('last_login', 'date_joined', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )
    
#     readonly_fields = ('avatar_preview', 'date_joined', 'last_login', 
#                       'updated_at', 'api_key')
    
#     # Configuration de l'ajout d'utilisateur
#     add_fieldsets = (
#         ('Créer un nouvel utilisateur', {
#             'classes': ('wide',),
#             'fields': ('email', 'name', 'forename', 'password1', 
#                       'password2', 'role', 'is_active', 'is_staff'),
#         }),
#     )
    
#     # Actions personnalisées
#     actions = ['activate_users', 'deactivate_users', 'send_welcome_email',
#                'reset_onboarding']
    
#     def avatar_preview(self, obj):
#         if obj.avatar:
#             return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', 
#                              obj.avatar.url)
#         return "Pas de photo"
#     avatar_preview.short_description = 'Photo actuelle'
    
#     # Action: Activer les utilisateurs
#     def activate_users(self, request, queryset):
#         updated = queryset.update(is_active=True)
#         self.message_user(
#             request, 
#             f'{updated} utilisateur(s) activé(s)', 
#             messages.SUCCESS
#         )
#     activate_users.short_description = "Activer les utilisateurs sélectionnés"
    
#     # Action: Désactiver les utilisateurs
#     def deactivate_users(self, request, queryset):
#         # Empêcher la désactivation de soi-même
#         if request.user in queryset:
#             self.message_user(
#                 request,
#                 'Vous ne pouvez pas vous désactiver vous-même',
#                 messages.ERROR
#             )
#             return
        
#         updated = queryset.update(is_active=False)
#         self.message_user(
#             request, 
#             f'{updated} utilisateur(s) désactivé(s)', 
#             messages.SUCCESS
#         )
#     deactivate_users.short_description = "Désactiver les utilisateurs sélectionnés"
    
#     # Action: Réinitialiser l'onboarding
#     def reset_onboarding(self, request, queryset):
#         queryset.update(
#             onboarding_completed=False,
#             onboarding_step=1
#         )
#         self.message_user(
#             request,
#             f'Onboarding réinitialisé pour {queryset.count()} utilisateur(s)',
#             messages.SUCCESS
#         )
#     reset_onboarding.short_description = "Réinitialiser l'onboarding"
    
#     # Action: Envoyer email de bienvenue
#     def send_welcome_email(self, request, queryset):
#         # Implémentez l'envoi d'email ici
#         self.message_user(
#             request,
#             f'Email de bienvenue envoyé à {queryset.count()} utilisateur(s)',
#             messages.SUCCESS
#         )
#     send_welcome_email.short_description = "Envoyer email de bienvenue"

# # 4. Page d'accueil personnalisée de l'admin
# class CustomAdminSite(admin.AdminSite):
#     site_header = "Administration InklusionHub"
#     site_title = "Portail Administrateur"
#     index_title = "Tableau de bord"
    
#     def get_app_list(self, request):
#         """
#         Organise les applications dans l'ordre souhaité
#         """
#         app_list = super().get_app_list(request)
        
#         # Réorganiser l'ordre des apps
#         ordered_apps = []
        
#         # Authentification en premier
#         auth_app = next((app for app in app_list if app['app_label'] == 'authentication'), None)
#         if auth_app:
#             ordered_apps.append(auth_app)
        
#         # Shared ensuite
#         shared_app = next((app for app in app_list if app['app_label'] == 'shared'), None)
#         if shared_app:
#             ordered_apps.append(shared_app)
        
#         # Autres apps
#         for app in app_list:
#             if app['app_label'] not in ['authentication', 'shared']:
#                 ordered_apps.append(app)
        
#         return ordered_apps

# # 5. Vue personnalisée pour attribuer des rôles en masse
# from django.shortcuts import render, redirect
# from django.contrib.admin.views.decorators import staff_member_required

# @staff_member_required
# def bulk_assign_roles(request):
#     """
#     Vue admin pour attribuer des rôles à plusieurs utilisateurs
#     """
#     if request.method == 'POST':
#         user_ids = request.POST.getlist('users')
#         role_id = request.POST.get('role')
        
#         if user_ids and role_id:
#             try:
#                 role = Role.objects.get(id=role_id)
#                 users = User.objects.filter(id__in=user_ids)
                
#                 for user in users:
#                     user.role = role.name
#                     user.save()
                
#                 messages.success(
#                     request, 
#                     f'Rôle "{role.name}" attribué à {len(users)} utilisateur(s)'
#                 )
#                 return redirect('admin:shared_user_changelist')
                
#             except Role.DoesNotExist:
#                 messages.error(request, "Rôle non trouvé")
    
#     # Récupérer tous les utilisateurs et rôles
#     users = User.objects.all().order_by('name')
#     roles = Role.objects.all().order_by('name')
    
#     context = {
#         'title': 'Attribuer des rôles en masse',
#         'users': users,
#         'roles': roles,
#         'opts': User._meta,
#     }
    
#     return render(request, 'admin/bulk_assign_roles.html', context)

# # 6. Ajouter une URL personnalisée à l'admin
# from django.urls import path

# class UserAdminWithActions(UserAdmin):
#     def get_urls(self):
#         urls = super().get_urls()
#         custom_urls = [
#             path('bulk-assign-roles/', 
#                  self.admin_site.admin_view(bulk_assign_roles),
#                  name='bulk_assign_roles'),
#         ]
#         return custom_urls + urls

# # 7. Template HTML pour l'action en masse (optionnel)
# """
# Créez un fichier: templates/admin/bulk_assign_roles.html

# {% extends "admin/base_site.html" %}
# {% block content %}
# <div class="module">
#     <h2>Attribuer des rôles en masse</h2>
#     <form method="post">
#         {% csrf_token %}
        
#         <div class="form-row">
#             <label for="users">Sélectionnez les utilisateurs:</label>
#             <select name="users" id="users" multiple style="width: 100%; height: 200px;">
#                 {% for user in users %}
#                 <option value="{{ user.id }}">{{ user.get_full_name }} ({{ user.email }}) - {{ user.role }}</option>
#                 {% endfor %}
#             </select>
#         </div>
        
#         <div class="form-row">
#             <label for="role">Sélectionnez le nouveau rôle:</label>
#             <select name="role" id="role" required>
#                 <option value="">-- Sélectionnez un rôle --</option>
#                 {% for role in roles %}
#                 <option value="{{ role.id }}">{{ role.name }}</option>
#                 {% endfor %}
#             </select>
#         </div>
        
#         <div class="submit-row">
#             <input type="submit" value="Attribuer le rôle" class="default">
#             <a href="{% url 'admin:shared_user_changelist' %}" class="button">Annuler</a>
#         </div>
#     </form>
# </div>
# {% endblock %}
# """

# # 8. Fichier d'initialisation pour créer des permissions par défaut
# # Créez un fichier: authentication/management/commands/seed_permissions.py
# """
# from django.core.management.base import BaseCommand
# from django.contrib.auth.management import create_permissions
# from django.apps import apps
# from shared.models import Permission

# class Command(BaseCommand):
#     help = 'Crée les permissions de base pour InklusionHub'
    
#     def handle(self, *args, **kwargs):
#         # Recréer les permissions pour toutes les apps
#         for app_config in apps.get_app_configs():
#             app_config.models_module = True
#             create_permissions(app_config, verbosity=0)
#             app_config.models_module = None
        
#         self.stdout.write(self.style.SUCCESS('Permissions Django créées'))
        
#         # Créer des permissions personnalisées
#         custom_permissions = [
#             ('Gérer les traductions', 'manage_translations', 'Peut gérer les demandes de traduction'),
#             ('Accéder au forum', 'access_forum', 'Peut participer aux discussions du forum'),
#             ('Créer des événements', 'create_events', 'Peut organiser des événements'),
#             ('Poster des offres d\'emploi', 'post_jobs', 'Peut publier des offres d\'emploi'),
#             ('Accéder aux cours premium', 'access_premium_courses', 'Accès aux cours payants'),
#             ('Modérer la communauté', 'moderate_community', 'Peut modérer les contenus utilisateurs'),
#             ('Gérer les paiements', 'manage_payments', 'Peut gérer les transactions financières'),
#             ('Voir les statistiques', 'view_statistics', 'Accès aux données analytiques'),
#         ]
        
#         for name, codename, description in custom_permissions:
#             Permission.objects.get_or_create(
#                 codename=codename,
#                 defaults={
#                     'name': name,
#                     'description': description
#                 }
#             )
        
#         self.stdout.write(self.style.SUCCESS('Permissions personnalisées créées'))
        
#         # Afficher les statistiques
#         total = Permission.objects.count()
#         self.stdout.write(f'Total permissions: {total}')
# """

# # 9. Configuration finale
# # Pour utiliser l'admin personnalisé, remplacez dans votre urls.py principal:
# """
# from django.contrib import admin
# from authentication.admin import CustomAdminSite

# admin.site = CustomAdminSite()
# admin.site.register(User, UserAdminWithActions)
# admin.site.register(Role, RoleAdmin)
# admin.site.register(Permission, PermissionAdmin)
# """