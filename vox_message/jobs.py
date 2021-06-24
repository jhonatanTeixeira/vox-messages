import logging
import time
from threading import Thread
from time import sleep

from django.conf import settings
from django.core.exceptions import EmptyResultSet
from sqlalchemy.orm.exc import NoResultFound

from vox_message.messages import send_next_message, get_topics
from vox_message.models import db

log = logging.getLogger('jobs')


class JobRunner(Thread):
    def __init__(self, topic, once=False):
        super().__init__()
        self.topic = topic
        self.once = once

    def run(self):
        log.info('job for topic %s started' % self.topic)

        while True:
            start = time.time()

            try:
                log.debug(f'looking for next message for topic {self.topic}')
                message = send_next_message(self.topic)
                log.debug(f'message sent for topic {self.topic}: {str(message)}')
                db.close()
            except (EmptyResultSet, NoResultFound):  # pragma: no cover
                log.debug(f'no messages found for topic {self.topic}')
                time.sleep(1)
            except Exception as e:  # pragma: no cover
                log.error(e)
                db.rollback()

            finish = time.time()
            took = finish - start

            if settings.DEBUG: # pragma: no cover
                log.debug('took: %s seconds, speed: %s per second' % (str(took), str(round(1000/(took*1000)))))

            if self.once:
                return


class TopicStarter(Thread):
    def __init__(self, run_once=False):
        super().__init__()
        self.jobs = {}
        self.run_once = run_once

    def get_job(self, topic):
        if topic not in self.jobs:
            self.jobs[topic] = JobRunner(topic)

        return self.jobs[topic]

    def run(self):
        while True:
            for topic in get_topics():
                job = self.get_job(topic)

                if not job.is_alive():
                    job.start()

            if self.run_once:
                return

            sleep(1)  # pragma: no cover

    @property
    def is_healthy(self):
        for topic in self.jobs:
            if not self.jobs[topic].is_alive():
                return False

        return True

    def get_jobs_status(self):
        return ['job for topic %s is %s' % (self.jobs[job].topic, 'alive' if self.jobs[job].is_alive() else 'dead')
                for job in self.jobs]


topic_starter = TopicStarter()
topic_starter.daemon = True
