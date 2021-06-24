import os
import json
from datetime import datetime

from django.conf import settings
from django.utils.decorators import classproperty
from django_sorcery.db import databases

from vox_django.models import uml_model

db = databases.get("default")


@uml_model
class Message(db.Model):
    __tablename__ = 'TATL_ITGO_PRTO'

    pk = db.Column('CG_ITGO_PRTO', db.Integer(), db.Sequence('SATL_ITGO_PRTO'), primary_key=True)
    event = db.Column('DS_EVTO_RZDO', db.String(length=256))
    message_raw = db.Column('TE_INST_RZDO', db.String())
    error_message = db.Column('DS_LOG_ERRO', db.String())
    dispatched_at = db.Column('DH_INST_RZDO', db.DateTime(), nullable=True)
    created_at = db.Column('DH_CDRO_RGRO', db.DateTime(), nullable=True)
    version = db.Column('DH_VRSO', db.TIMESTAMP(), nullable=False)
    locked = db.Column('IN_BLDO', db.Boolean(), nullable=False)
    schedule_date = db.Column('DH_AGTO_EXEO', db.DateTime(), nullable=False, default=datetime.now())
    message_source = db.Column('DS_OBTO_IRGEM', db.String(), nullable=True)

    undelivered = db.queryproperty(dispatched_at=None)

    @classproperty
    def scheduled(self):
        return Message.objects.filter(Message.schedule_date >= datetime.now())

    __mapper_args__ = {
        "version_id_col": version,
        'version_id_generator': lambda version: datetime.now()
    }

    def __init__(self, **args):
        self.locked = False
        self.created_at = datetime.now()
        super(Message, self).__init__(**args)

    @property
    def message(self):
        return json.loads(self.message_raw)

    @message.setter
    def message(self, message):
        self.message_raw = json.dumps(message)

    def lock(self):
        self.locked = True
        db.commit()


@uml_model
class ConsumerEvent(db.Model):
    __tablename__ = 'TATL_EVTO_CNDR'

    pk = db.Column('CG_EVTO_CNDR', db.Integer(), db.Sequence('SATL_EVTO_CNDR'),
                   primary_key=True)
    message_pk = db.Column('CG_ITGO_PRTO', db.Integer(), db.ForeignKey('TATL_ITGO_PRTO.CG_ITGO_PRTO'))

    error_message = db.Column('DS_MNGM_ERRO', db.Text(), nullable=True)
    consumer_name = db.Column('NO_EVTO_CNDR', db.String(length=256), nullable=False)
    created_at = db.Column('DH_CDRO_RGRO', db.DateTime(), nullable=False, default=datetime.now())
    is_error = db.Column('IN_EVTO_ERRO_CNDR', db.Boolean(), nullable=False, default=False)

    message = db.relationship(Message, backref=db.backref('consumer_events', cascade="all, delete-orphan"))
