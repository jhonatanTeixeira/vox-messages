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
    __tablename__ = 'tatl_itgo_prto'

    pk = db.Column('cg_itgo_prto', db.Integer(), db.Sequence('satl_itgo_prto'), primary_key=True)
    event = db.Column('ds_evto_rzdo', db.String(length=256))
    message_raw = db.Column('te_inst_rzdo', db.String())
    error_message = db.Column('ds_log_erro', db.String())
    dispatched_at = db.Column('dh_inst_rzdo', db.DateTime(), nullable=True)
    created_at = db.Column('dh_cdro_rgro', db.DateTime(), nullable=True)
    version = db.Column('dh_vrso', db.TIMESTAMP(), nullable=False)
    locked = db.Column('in_bldo', db.Boolean(), nullable=False)
    schedule_date = db.Column('dh_agto_exeo', db.DateTime(), nullable=False, default=datetime.now())
    message_source = db.Column('ds_obto_irgem', db.String(), nullable=True)

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
    __tablename__ = 'tatl_evto_cndr'

    pk = db.Column('cg_evto_cndr', db.Integer(), db.Sequence('satl_evto_cndr'),
                   primary_key=True)
    message_pk = db.Column('cg_itgo_prto', db.Integer(), db.ForeignKey('tatl_itgo_prto.cg_itgo_prto'))

    error_message = db.Column('ds_mngm_erro', db.Text(), nullable=True)
    consumer_name = db.Column('no_evto_cndr', db.String(length=256), nullable=False)
    created_at = db.Column('dh_cdro_rgro', db.DateTime(), nullable=False, default=datetime.now())
    is_error = db.Column('in_evto_erro_cndr', db.Boolean(), nullable=False, default=False)

    message = db.relationship(Message, backref=db.backref('consumer_events', cascade="all, delete-orphan"))
