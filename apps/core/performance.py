"""Small, privacy-safe request query metrics.

The previous module mixed runtime helpers with an unconfigured Celery task
framework and logged rendered SQL (which can contain user data).  Runtime code
only needs this context manager, so it records counts and duration without SQL,
parameters, cache values, or request identifiers.
"""

import logging
import time

from django.db import connection


logger = logging.getLogger(__name__)


class QueryProfiler:
    """Measure query count and wall time without exposing query contents."""

    max_queries_warning = 20

    def __enter__(self):
        self._started_at = time.monotonic()
        self._initial_count = len(connection.queries)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        duration_ms = round((time.monotonic() - self._started_at) * 1000, 2)
        query_count = max(0, len(connection.queries) - self._initial_count)
        logger.info(
            "database_query_profile duration_ms=%s query_count=%s",
            duration_ms,
            query_count,
        )
        if query_count > self.max_queries_warning:
            logger.warning(
                "database_query_count_high query_count=%s threshold=%s",
                query_count,
                self.max_queries_warning,
            )
        return False

    @staticmethod
    def get_query_count():
        return len(connection.queries)
