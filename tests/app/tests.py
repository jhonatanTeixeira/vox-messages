from datetime import datetime, timedelta
from json import JSONDecodeError
from unittest.mock import patch, call, MagicMock, PropertyMock, ANY

# from django.conf import settings
from django.test import TestCase
from health_check.exceptions import HealthCheckException
from rest_framework.status import HTTP_201_CREATED


# settings.configure(
#     DEBUG=True,
#     USE_FORWARDER=True,
#     ROOT_URLCONF='app.urls',
#     KAFKA={
#         'bootstrap_servers': 'kafka',
#         'consumers': {
#             'foo': {
#                 'group_id': 'some-group',
#                 'max_poll_records': 1,
#                 'create_topic': False,
#             },
#             'bar': {
#                 'group_id': 'other-group',
#                 'max_poll_records': 10,
#                 'create_topic': False,
#             },
#         }
#     },
#     INSTALLED_APPS=[
#         'django.contrib.admin',
#         'django.contrib.auth',
#         'django.contrib.contenttypes',
#         'django.contrib.sessions',
#         'django.contrib.messages',
#         'django.contrib.staticfiles',
#         'django_sorcery',
#         'rest_framework',
#         'drf_yasg',
#         'corsheaders',
#         'rchlo_base',
#         'message',
#         'hse',
#         'forwarder',
#     ],
#     DATABASES={
#         'default': {
#             'ENGINE': 'django.db.backends.sqlite3',
#             'NAME': ':memory:',
#             'ALCHEMY_OPTIONS': {
#                 'engine_options': {
#                     'connect_args': {'timeout': 10000}
#                 }
#             }
#         }
#     },
#     LOGGING={
#         'version': 1,
#         'disable_existing_loggers': False,
#         'handlers': {
#             'console': {
#                 'class': 'logging.StreamHandler',
#             },
#         },
#         'loggers': {
#             'sqlalchemy': {
#                 'handlers': ['console'],
#                 'level': 'INFO',
#             },
#             'kafka': {
#                 'handlers': ['console'],
#                 'level': 'INFO',
#             },
#         },
#     },
#     STATIC_URL='static/',
#     STATIC_ROOT='static/',
# )


from rest_framework.test import APITestCase
from sqlalchemy import event
from sqlalchemy.orm.exc import StaleDataError


class TestSendMessages(TestCase):
    @patch('vox_message.messages.send_kafka_message')
    def test_should_send_next_message(self, send_kafka_message):
        from vox_message.models import db, Message
        from vox_message.messages import send_message_after_insert
        from vox_message.jobs import JobRunner

        runner = JobRunner('some-topic', True)

        event.remove(Message, 'after_insert', send_message_after_insert)

        message = Message(event='some-topic', message={}, created_at=datetime.now(), locked=False)
        scheduled_message = Message(event='some-topic', message={}, created_at=datetime.now(), locked=False,
                                    schedule_date=datetime.now() + timedelta(days=1))
        db.add(message)
        db.add(scheduled_message)
        db.commit()
        id = message.pk

        event.listen(Message, 'after_insert', send_message_after_insert)

        runner.run()
        runner.run()

        send_kafka_message.assert_called_once_with(topic='some-topic', payload={'message_id': id}, partition=None,
                                                   create_topic=True, num_partitions=2, replication_factor=2)

    @patch('vox_message.messages.db')
    def test_message_errors(self, db):
        import vox_message.messages

        message_mock = MagicMock()
        db.query().filter().limit().one.return_value = message_mock
        message_mock.lock.side_effect = StaleDataError()

        with self.assertRaises(StaleDataError):
            vox_message.messages.send_next_message('foo')

        message_mock = MagicMock()
        db.query().filter().limit().one.return_value = message_mock
        type(message_mock).message = PropertyMock(side_effect=JSONDecodeError('a', 'b', 0))

        with self.assertRaises(JSONDecodeError):
            vox_message.messages.send_next_message('foo')

        self.assertIsNotNone(message_mock.error_message)
        self.assertIsNotNone(message_mock.dispatched_at)
        db.commit.assert_called()

    @patch('vox_message.messages.send_kafka_message_async')
    def test_api_send_message(self, send_kafka_message_async):
        from vox_message.serializers import MessageSerializer

        serializer = MessageSerializer(data={'message': {'pk': 1}, 'event': 'foo', 'message_source': 'bar-system'})
        serializer.is_valid(True)
        serializer.save()

        send_kafka_message_async.assert_called()


class HealthCheckTest(TestCase):
    @patch('vox_message.jobs.topic_starter')
    def test_should_check_topic_starter(self, topic_starter):
        topic_starter.is_helthy.return_value = False
        topic_starter.is_alive.return_value = False

        from vox_message.healthcheck import LegacyMessageDispatcherHealthCheck

        with self.assertRaises(HealthCheckException):
            checker = LegacyMessageDispatcherHealthCheck()
            checker.check_status()


class JobTopicStater(TestCase):
    @patch('vox_message.jobs.get_topics')
    @patch('vox_message.jobs.JobRunner')
    def test_should_init_jobs_and_check_health(self, JobRunner, get_topics):
        from vox_message.jobs import TopicStarter

        get_topics.return_value = ['foo', 'bar', 'baz']
        JobRunner().is_alive.return_value = False
        topic_starter = TopicStarter(True)
        topic_starter.run()

        JobRunner.assert_has_calls([
            call('foo'),
            call().is_alive(),
            call().start(),
            call('bar'),
            call().is_alive(),
            call().start(),
            call('baz'),
            call().is_alive(),
            call().start(),
        ])

        self.assertFalse(topic_starter.is_healthy)

        JobRunner().is_alive.return_value = True

        self.assertTrue(topic_starter.is_healthy)


class TestViews(APITestCase):
    @patch('vox_message.messages.send_kafka_message_async')
    def test_send_message(self, send_kafka_message_async):
        response = self.client.post('/messages/',
                                    {'event': 'some-event', 'message': {'foo': 'bar'}},
                                    format='json')

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        # self.assertIsNotNone(response.data['dispatched_at'])

        send_kafka_message_async.assert_called()

    @patch('vox_message.messages.send_kafka_message_async')
    def test_add_error(self, send_kafka_message_async):
        response = self.client.post('/messages/1/add_error/',
                                    {'error_message': 'some error', 'consumer_name': 'some_consumer'},
                                    format='json')

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(1, response.data['message_pk'])
        self.assertEqual(True, response.data['is_error'])

        send_kafka_message_async.assert_not_called()

    @patch('vox_message.messages.send_kafka_message_async')
    def test_add_success(self, send_kafka_message_async):
        response = self.client.post('/messages/1/add_success/',
                                    {'consumer_name': 'some_consumer'},
                                    format='json')

        self.assertEqual(HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, response.data['message_pk'])
        self.assertEqual(False, response.data['is_error'])

        send_kafka_message_async.assert_not_called()
