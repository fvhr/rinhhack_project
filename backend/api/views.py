from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
)
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from . import models, serializers


class UserViewSet(ModelViewSet):
    queryset = models.User.objects.all()
    serializer_class = serializers.UserSerializer

    @swagger_auto_schema(
        'GET',
        responses={
            200: serializers.ChatSerializer(many=True),
        },
    )
    @action(['GET'], True, 'admin-chats', 'user-admin-chats')
    def admin_chats(self, request: Request, pk: int):
        try:
            pk = int(pk)
        except ValueError:
            return Response({'detail': 'user does not exists'}, 404)

        chats = models.UsersChats.objects.filter(
            user_id=pk, is_admin=True
        ).values_list('chat', flat=True)
        chats = models.Chat.objects.filter(id__in=chats)
        chats = serializers.ChatSerializer(instance=chats, many=True).data
        return Response(chats, 200)

    @action(['GET'], True, 'member-chats', 'user-member-chats')
    def member_chats(self, request: Request, pk: int):
        try:
            pk = int(pk)
        except ValueError:
            return Response({'detail': 'user does not exists'}, 404)

        chats = models.UsersChats.objects.filter(
            user_id=pk, is_admin=False
        ).values_list('chat', flat=True)
        chats = models.Chat.objects.filter(id__in=chats, bot_is_admin=True)
        chats = serializers.ChatSerializer(instance=chats, many=True).data
        return Response(chats, 200)

    @swagger_auto_schema(
        'POST',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'chat_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY, items=openapi.TYPE_INTEGER
                )
            },
        ),
    )
    @action(['POST'], True, 'bulk-delete', 'user-bulk-delete')
    def bulk_delete(self, request: Request, pk):
        chats_ids = request.data.get('chat_ids', [])
        user = self.get_object()
        models.UsersChats.objects.filter(
            user=user, chat__in=chats_ids
        ).delete()
        return Response(status=204)


class ChatViewSet(ModelViewSet):
    queryset = models.Chat.objects.all()
    serializer_class = serializers.ChatSerializer

    @swagger_auto_schema(
        'GET',
        responses={200: serializers.UsersChatsWithUserSerializer(many=True)},
    )
    @action(['GET'], True, 'users', 'chat-users')
    def users(self, request: Request, pk: int):
        users = models.UsersChats.objects.filter(chat_id=pk).select_related(
            'user'
        )
        users = serializers.UsersChatsWithUserSerializer(
            instance=users, many=True
        ).data
        return Response(users, 200)

    @swagger_auto_schema(
        'GET',
        manual_parameters=[
            openapi.Parameter(
                'q', openapi.IN_QUERY, required=True, type=openapi.TYPE_STRING
            )
        ],
        responses={200: serializers.UsersChatsWithUserSerializer(many=True)},
    )
    @action(['GET'], True, 'users/search', 'users-search')
    def users_search(self, request: Request, pk):
        query = request.query_params.get('q', None)
        if not query:
            data = serializers.UsersChatsWithUserSerializer(
                models.UsersChats.objects.filter(chat_id=pk), many=True
            ).data
            return Response(data, 200)

        vector = (
            SearchVector('first_name', weight='A')
            + SearchVector('last_name', weight='A')
            + SearchVector('username', weight='A')
        )

        query = SearchQuery(query)
        rank = SearchRank(vector, query)

        users = (
            models.User.objects.annotate(search=vector, rank=rank)
            .filter(chats__chat_id=pk, search=query)
            .order_by('-rank')
        )
        data = serializers.UsersChatsWithUserSerializer(
            models.UsersChats.objects.filter(user_id__in=users, chat_id=pk),
            many=True,
        ).data
        return Response(data, 200)

    @swagger_auto_schema(
        'GET',
        manual_parameters=[
            openapi.Parameter(
                'q', openapi.IN_QUERY, required=True, type=openapi.TYPE_STRING
            )
        ],
    )
    @action(['GET'], False, 'search', 'search')
    def search(self, request: Request):
        query = request.query_params.get('q', None)
        if not query:
            data = serializers.ChatSerializer(
                models.Chat.objects.all(), many=True
            ).data
            return Response(data, 200)

        vector = SearchVector('title', weight='A') + SearchVector(
            'description', weight='B'
        )
        query = SearchQuery(query)
        rank = SearchRank(vector, query)

        chats = (
            models.Chat.objects.annotate(search=vector, rank=rank)
            .filter(search=query)
            .order_by('-rank')
        )
        data = serializers.ChatSerializer(chats, many=True).data
        return Response(data, 200)

    @swagger_auto_schema(
        'POST', request_body=serializers.UserSerializer(), responses={204: ''}
    )
    @action(['POST'], True, 'check-user', 'check-user-in-chat')
    def check_user_in_chat(self, request: Request, pk):
        if not models.User.objects.filter(id=request.data.get('id')):
            serializer = serializers.UserSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        models.UsersChats.objects.get_or_create(
            user_id=request.data.get('id'), chat_id=pk
        )
        return Response(status=204)

    @swagger_auto_schema(
        'PATCH',
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_QUERY,
                required=True,
                type=openapi.TYPE_INTEGER,
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={'is_admin': openapi.Schema(type=openapi.TYPE_BOOLEAN)},
        ),
        responses={200: serializers.UserSerializer()},
    )
    @action(['PATCH'], True, 'update-is-admin')
    def update_is_admin(self, request: Request, pk):
        is_admin = request.data.get('is_admin', False)
        user_id = request.query_params.get('user_id', None)
        if user_id is None:
            return Response({'detail': 'user does not exists'})

        instance = models.UsersChats.objects.filter(
            user_id=user_id, chat_id=pk
        )
        if not instance:
            serializer = serializers.UsersChatsSerializer(
                data={'user': user_id, 'chat': pk, 'is_admin': is_admin},
            )
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, 201)

        serializer = serializers.UsersChatsSerializer(
            instance.get(), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, 200)

    @swagger_auto_schema(
        'DELETE',
        manual_parameters=[
            openapi.Parameter(
                'user_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER
            )
        ],
        responses={204: ''},
    )
    @action(['DELETE'], True, 'delete-user', 'delete-user')
    def delete_user_from_chat(self, request: Request, pk):
        models.UsersChats.objects.filter(
            user_id=request.query_params.get('user_id'), chat_id=pk
        ).delete()
        return Response(status=204)

    @swagger_auto_schema(
        'POST',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'user_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY, items=openapi.TYPE_INTEGER
                )
            },
        ),
        responses={
            200: openapi.Response(
                'success', serializers.UsersChatsSerializer(many=True)
            )
        },
    )
    @action(['POST'], True, 'bulk-add', 'users-chats-bulk-add')
    def bulk_create(self, request: Request, pk: int):
        user_ids = request.data.get('user_ids', [])
        chat = self.get_object()
        users_chats = models.UsersChats.objects.bulk_create(
            [
                models.UsersChats(user_id=user_id, chat=chat)
                for user_id in user_ids
            ]
        )
        data = serializers.UsersChatsSerializer(
            instance=users_chats, many=True
        ).data
        return Response(data, 200)


class UsersChatsViewSet(ModelViewSet):
    queryset = models.UsersChats.objects.all()
    serializer_class = serializers.UsersChatsSerializer
