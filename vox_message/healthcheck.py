from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import HealthCheckException

from vox_message.jobs import topic_starter


class LegacyMessageDispatcherHealthCheck(BaseHealthCheckBackend):
    critical_service = True

    def check_status(self):
        if not topic_starter.is_alive():
            try:
                topic_starter.join()
                raise HealthCheckException('topic started is dead by unknown reasons')
            except Exception as e:
                raise HealthCheckException(str(e))

        if not topic_starter.is_healthy:
            raise HealthCheckException(', '.join(topic_starter.get_jobs_status()))

    def identifier(self):
        return 'Legacy Message Dispatcher'
