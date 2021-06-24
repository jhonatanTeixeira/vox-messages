from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED
from rest_witchcraft.viewsets import ModelViewSet

from vox_message.models import Message, ConsumerEvent, db
from vox_message.serializers import MessageSerializer, ConsumerEventSerializer


class MessageView(ModelViewSet):
    queryset = Message.query
    serializer_class = MessageSerializer

    def paginate(self, queryset):
        return self.get_paginated_response(
            self.get_serializer(self.paginate_queryset(queryset), many=True).data,
        )

    @action(detail=False)
    def scheduled(self, request):
        return self.paginate(Message.scheduled)

    @action(detail=False)
    def undelivered(self, request):
        return self.paginate(Message.undelivered)

    @action(detail=False)
    def with_error(self, request):
        queryset = db.query(Message).join(ConsumerEvent).filter(ConsumerEvent.is_error == True)

        return self.paginate(queryset)

    def create_event(self, request, message_pk) -> ConsumerEventSerializer:
        data = request.data
        data['message_pk'] = message_pk
        serializer = ConsumerEventSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        serializer.instance.message = self.get_object()

        return serializer

    def save(self, serializer):
        serializer.save()

        return Response(serializer.data, HTTP_201_CREATED)

    @action(detail=True, methods=['POST'])
    @swagger_auto_schema(request_body=ConsumerEventSerializer())
    def add_error(self, request, *args, **kwargs):
        serializer = self.create_event(request, kwargs['pk'])
        serializer.instance.is_error = True

        return self.save(serializer)

    @action(detail=True, methods=['POST'])
    @swagger_auto_schema(request_body=ConsumerEventSerializer())
    def add_success(self, request, *args, **kwargs):
        serializer = self.create_event(request, kwargs['pk'])

        return self.save(serializer)
