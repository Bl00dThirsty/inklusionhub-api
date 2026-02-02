
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from rest_framework.pagination import PageNumberPagination



from .models import Conversation, Message, UserStatus
from .serializers import ConversationSerializer, FileHistorySerializer, MessageSerializer, UserSerializer, UserStatusSerializer

User = get_user_model()

#  Liste des conversations de l’utilisateur connecté
class ConversationListView(generics.ListAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Retourne uniquement les conversations où l'utilisateur courant
        est participant. Ne renvoie que les conversations existantes.
        """
        return Conversation.objects.filter(
            participants=self.request.user
        ).prefetch_related("participants", "messages").distinct()

    def get_serializer_context(self):
        return {"request": self.request}


#  Liste des utilisateurs (excluant l’utilisateur connecté)
class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.exclude(id=self.request.user.id)


#  Messages d’une conversation
class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        conversation = get_object_or_404(
            Conversation,
            id=self.kwargs["conversation_id"],
            participants=self.request.user
        )
        return Message.objects.filter(conversation=conversation)\
            .select_related("sender", "receiver")

    def get_serializer_context(self):
        return {"request": self.request}


#  Envoyer un message
class MessageCreateView(generics.CreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        conversation = serializer.validated_data["conversation"]

        if self.request.user not in conversation.participants.all():
            raise PermissionDenied("Accès interdit à cette conversation")

        serializer.save(sender=self.request.user)

    def get_serializer_context(self):
        return {"request": self.request}


#  Marquer un message comme lu
class MarkMessageReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):
        message = get_object_or_404(
            Message,
            id=message_id,
            conversation__participants=request.user
        )

        if message.sender == request.user:
            return Response(
                {"detail": "Impossible de marquer son propre message"},
                status=403
            )

        message.mark_as_read()
        return Response({"status": "read"})
    
#  Créer ou obtenir une conversation entre deux utilisateurs
class CreateOrGetConversation(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.data.get("user_id")
        other_user = get_object_or_404(User, id=user_id)

        # Chercher une conversation existante entre les deux
        conversation = Conversation.objects.filter(
            is_group=False,
            participants=request.user
        ).filter(
            participants=other_user
        ).first()

        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.set([request.user, other_user])
            conversation.save()

        serializer = ConversationSerializer(conversation, context={"request": request})
        return Response(serializer.data, status=200)

#  Combinaison liste / création messages d’une conversation
class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs.get("conversation_id")
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            participants=self.request.user
        )
        return Message.objects.filter(conversation=conversation).order_by("timestamp")

    def perform_create(self, serializer):
        conversation_id = self.kwargs.get("conversation_id")
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            participants=self.request.user
        )

        file_obj = self.request.FILES.get("file")
        image_obj = self.request.FILES.get("image")

        serializer.save(
            sender=self.request.user,
            conversation=conversation,
            image=image_obj,
            file=file_obj,
            file_name=file_obj.name if file_obj else None,
            file_size=file_obj.size if file_obj else None
        )

        print("FILES:", self.request.FILES)
        print("DATA:", self.request.data)


        
#  Liste des statuts des utilisateurs (online/offline)
class UserStatusList(APIView):
      permission_classes = [IsAuthenticated]

      def get(self, request):
        """
        Retourne le statut (online/offline) de tous les autres utilisateurs
        """
        statuses = UserStatus.objects.exclude(user=request.user)
        serializer = UserStatusSerializer(
            statuses,
            many=True,
            context={"request": request}
        )
        return Response(serializer.data)        

class ConversationFileHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        files = Message.objects.filter(
            conversation_id=conversation_id
        ).exclude(
            file__isnull=True,
            image__isnull=True
        ).order_by("-timestamp")

        serializer = FileHistorySerializer(files, many=True)
        return Response(serializer.data)
 
class UserSearchView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        q = self.request.query_params.get("q", "")
        return User.objects.filter(
    name__icontains=q
).exclude(id=self.request.user.id)
        