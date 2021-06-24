from datetime import datetime

from rest_framework.fields import JSONField, DateTimeField
from rest_witchcraft.serializers import ModelSerializer

from vox_message.models import Message, db, ConsumerEvent


class ConsumerEventSerializer(ModelSerializer):
    class Meta:
        model = ConsumerEvent
        session = db
        fields = ['pk', 'error_message', 'consumer_name', 'is_error', 'created_at', 'message_pk']
        read_only_fields = ['is_error', 'pk', 'created_at']


class MessageSerializer(ModelSerializer):
    class Meta:
        model = Message
        session = db
        fields = ['pk', 'event', 'message', 'error_message', 'created_at', 'dispatched_at', 'schedule_date',
                  'message_source', 'consumer_events']
        read_only_fields = ['created_at', 'dispatched_at', 'consumer_events']

    message = JSONField()
    schedule_date = DateTimeField(allow_null=True, required=False)
    consumer_events = ConsumerEventSerializer(many=True, read_only=True)

    def create(self, validated_data):
        message = super().create(validated_data)
        message.created_at = datetime.now()
        message.locked = True

        if not message.schedule_date:
            message.schedule_date = datetime.now()

        return message
