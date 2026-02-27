# communication/tasks.py
from celery import shared_task
from .models import Message
# Si tu n'as pas encore installé fcm-django, commente les lignes FCM
# from fcm_django.models import FCMDevice 

@shared_task
def async_send_push_notifications(message_id):
    try:
        # Logique de notification (à remplir plus tard)
        print(f"Envoi de notification pour le message {message_id}")
    except Exception as e:
        print(f"Erreur notification: {e}")

