import logging
from datetime import datetime
from json.decoder import JSONDecodeError

from django.conf import settings
from django.core.exceptions import EmptyResultSet
from vox_kafka.kafka_client import send_kafka_message_async, send_kafka_message
from sqlalchemy import event
from sqlalchemy.orm import Mapper
from sqlalchemy.orm.exc import StaleDataError

from vox_message.models import Message, db

log = logging.getLogger('messages')


def message_success(message, should_flush=False):
    log.debug('Message sent to kafka %r', message.__dict__)
    message.error_message = None
    message.dispatched_at = datetime.now()
    message.locked = False

    if should_flush:  # pragma: no cover
        log.debug('Flushing vox_message to database %r', message.__dict__)
        db.flush()


def prepare_message_data(message):
    data = message.message
    data['message_id'] = message.pk

    return data


def send_message(message, should_flush=False):
    data = prepare_message_data(message)

    kafka_message = send_kafka_message(
        topic=message.event,
        payload=data,
        partition=None,
        create_topic=True,
        num_partitions=settings.KAFKA_DEFAULT_PARTITIONS,
        replication_factor=settings.KAFKA_DEFAULT_REPLICATION,
    )

    message_success(message, should_flush)

    return kafka_message


def send_message_async(message, success_callback=None, err_callback=None):
    data = prepare_message_data(message)

    kafka_message = send_kafka_message_async(
        topic=message.event,
        payload=data,
        partition=None,
        create_topic=True,
        num_partitions=settings.KAFKA_DEFAULT_PARTITIONS,
        replication_factor=settings.KAFKA_DEFAULT_REPLICATION,
        callback=success_callback,
        err_callback=err_callback,
    )

    return kafka_message


def set_error_message(message, error_message):
    message.error_message = error_message
    message.dispatched_at = datetime.now()
    db.commit()
    db.expunge(message)


def send_next_message(topic=None):
    filters = [Message.dispatched_at == None, Message.locked == False, Message.schedule_date <= datetime.now()]

    if topic is not None:
        filters.append(Message.event == topic)

    message = db.query(Message).filter(*filters).limit(1).one()

    if message:
        try:
            message.lock()
            send_message(message)
            # vox_message.locked = False
            db.commit()
            db.expunge(message)
        except StaleDataError as e:
            db.expunge(message)
            raise e
        except JSONDecodeError as e:
            log.error(str(e), stack_info=True, exc_info=True)
            set_error_message(message, f'json error: {str(e)}')
            raise e
        except Exception as e:
            log.error(str(e), stack_info=True, exc_info=True)
            set_error_message(message, str(e))
            raise e
    else:
        raise EmptyResultSet

    return message


def send_message_after_insert(mapper: Mapper, connection, message):
    def update_message(payload, metadata, error=None):
        message = db.query(Message).filter(Message.pk == payload['message_id']).one()
        message_success(message, True)
        db.commit()

    def update_message_error(payload, error, metadata):
        update_message(payload, metadata, error)

    if message.schedule_date <= datetime.now():
        send_message_async(message, success_callback=update_message, err_callback=update_message_error)
    else:
        expr = mapper.mapped_table.update().values({mapper.c.locked: False})
        connection.execute(expr)


def get_topics():
    events = db.query(Message.event)\
        .filter(Message.dispatched_at == None)\
        .group_by(Message.event)\
        .all()

    return [event[0] for event in events]


def install_events():
    event.listen(Message, 'after_insert', send_message_after_insert)


def uninstall_events():
    event.remove(Message, 'after_insert', send_message_after_insert)


install_events()
