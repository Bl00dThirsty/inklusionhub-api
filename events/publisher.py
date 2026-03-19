# inklusionhub_api/events/publisher.py
import pika
import json
import uuid
from datetime import datetime
from django.conf import settings
import logging
from django.db.models.fields.files import ImageFieldFile

logger = logging.getLogger(__name__)

class AuthEventPublisher:
    def publish_user_event(self, event_type: str, user_data: dict):
        """Publier un événement utilisateur"""
        event = {
            'event_id': str(uuid.uuid4()),
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'producer': settings.SERVICE_NAME,
            'data': user_data
        }
        
        try:
            connection = pika.BlockingConnection(
                pika.URLParameters(settings.RABBITMQ_URL)
            )
            channel = connection.channel()
            
            # Déclarer l'exchange (idempotent)
            channel.exchange_declare(
                exchange=settings.RABBITMQ_EXCHANGE,
                exchange_type='topic',
                durable=True
            )
            
            # Routing key basée sur le type d'événement
            routing_key = f"user.{event_type.lower().replace('_', '.')}"
            
            channel.basic_publish(
                exchange=settings.RABBITMQ_EXCHANGE,
                routing_key=routing_key,
                body=json.dumps(event),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type='application/json'
                )
            )
            
            channel.close()
            connection.close()
            
            logger.info(f"📤 Événement {event_type} publié pour user: {user_data.get('user_id')}")
            
        except Exception as e:
            logger.error(f"❌ Erreur publication événement: {e}")

# Singleton global - Instance globale à importer pour publier facilement
auth_publisher = AuthEventPublisher()

def get_user_data_for_event(user):
    """Préparer les données utilisateur pour un événement"""
    # Convertir les champs spéciaux en types JSON-serializables
    avatar_url = None
    if user.avatar:
        if hasattr(user.avatar, 'url'):
            avatar_url = user.avatar.url
        elif isinstance(user.avatar, str):
            avatar_url = user.avatar
        elif isinstance(user.avatar, ImageFieldFile):
            avatar_url = user.avatar.name
    
    return {
        'user_id': str(user.id),
        'email': user.email,
        'name': user.name,
        'forename': user.forename,
        'full_name': f"{user.name} {user.forename}".strip(),
        'phone': user.phone,
        'avatar_url': avatar_url,
        'adresse': user.adresse,
        'profession': user.Profession,
        'role': user.role,
        'secondary_roles': user.secondary_roles or [],
        'is_active': user.is_active,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'date_joined': user.date_joined.isoformat() if user.date_joined else None,
        'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        
        # Champs spécifiques aux rôles
        'niveau_perte_auditive': user.niveau_perte_auditive,
        'status_utilisez_vous_un_appareil_auditif': user.status_utilisez_vous_un_appareil_auditif,
        'level_en_LSF': user.level_en_LSF,
        'preference_apprentissage': user.preference_apprentissage or [],
        'certification': user.certification,
        'annee_experience': user.Annee_experience,
        'niveau_expertise': user.niveau_expertise,
        'competence': user.Competence or [],
        'jour_disponible': user.Jour_disponible or [],
        'creneau_horaire_disponible': user.Creneau_horaire_disponible or {},
        'tarif_horaire': str(user.Tarif_horaire) if user.Tarif_horaire else "0",
        'company_name': user.company_name,
        'domaine_activity': user.Domaine_activity,
        'type_company': user.Type_company,
        'adresse_company': user.Adresse_company,
        'taille_company': user.Taille_Company,
        'site_web': user.Site_web,
        'langue_parlee': user.langue_parlee or [],
        
        # Onboarding et préférences
        'onboarding_completed': user.onboarding_completed,
        'onboarding_step': user.onboarding_step,
        'preferences': user.preferences or {},
    }

def publish_user_created(user):
    """Publier quand un utilisateur est créé"""
    user_data = get_user_data_for_event(user)
    user_data['event'] = 'created'
    
    auth_publisher.publish_user_event('USER_CREATED', user_data)

def publish_user_updated(user, changed_fields=None):
    """Publier quand un utilisateur est mis à jour"""
    user_data = get_user_data_for_event(user)
    user_data['event'] = 'updated'
    user_data['changed_fields'] = changed_fields or []
    
    # Inclure seulement les champs qui ont changé
    if changed_fields:
        filtered_data = {'user_id': user_data['user_id'], 'changed_fields': changed_fields}
        for field in changed_fields:
            if field in user_data:
                filtered_data[field] = user_data[field]
        
        auth_publisher.publish_user_event('USER_UPDATED', filtered_data)
    else:
        auth_publisher.publish_user_event('USER_UPDATED', user_data)

def publish_user_deleted(user_id):
    """Publier quand un utilisateur est supprimé"""
    user_data = {
        'user_id': str(user_id),
        'deleted_at': datetime.utcnow().isoformat(),
        'event': 'deleted'
    }
    auth_publisher.publish_user_event('USER_DELETED', user_data)

def publish_user_role_changed(user, old_role, new_role):
    """Publier quand le rôle principal d'un utilisateur change"""
    user_data = get_user_data_for_event(user)
    user_data['event'] = 'role_changed'
    user_data['old_role'] = old_role
    user_data['new_role'] = new_role
    
    auth_publisher.publish_user_event('USER_ROLE_CHANGED', user_data)

def publish_user_secondary_roles_updated(user, added_roles=None, removed_roles=None):
    """Publier quand les rôles secondaires sont modifiés"""
    user_data = get_user_data_for_event(user)
    user_data['event'] = 'secondary_roles_updated'
    user_data['added_roles'] = added_roles or []
    user_data['removed_roles'] = removed_roles or []
    
    auth_publisher.publish_user_event('USER_SECONDARY_ROLES_UPDATED', user_data)