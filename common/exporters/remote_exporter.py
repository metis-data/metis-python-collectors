import logging
from typing import Sequence, Optional

import requests
import sentry_sdk
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from common.consts import METIS_REQUEST_SPAN_ATTRIBUTE_IDENTIFIER, \
    METIS_STATEMENT_SPAN_ATTRIBUTE
from common.utils.chunk import chunk_string_list
from common.utils.log import log

logger = logging.getLogger(__name__)
NUM_RETRIES = 3


class MetisRemoteExporter(SpanExporter):
    @log
    def __init__(self, url, api_key, sentry_logger: Optional[sentry_sdk.Hub]):
        self.url = url
        self.session = requests.Session()
        self.session.headers.update(
            {"x-api-key": api_key}
        )
        self.sentry_logger = sentry_logger

    @log
    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        response = None
        try:
            data = [span.to_json(indent=None) for span in spans if
                    METIS_STATEMENT_SPAN_ATTRIBUTE in span.attributes or
                    METIS_REQUEST_SPAN_ATTRIBUTE_IDENTIFIER in span.attributes]
            result = SpanExportResult.SUCCESS
            if data:
                num_chunks = 0
                for chunk in chunk_string_list(data, 200000):
                    num_chunks += 1
                    response: Optional[requests.Response] = None
                    retries = 0
                    while self._should_retry(response) and retries < NUM_RETRIES:
                        try:
                            response = self.session.post(
                                url=self.url,
                                json=list(chunk),
                                timeout=30,
                            )
                            logger.debug(response.text)
                        except requests.ConnectTimeout:
                            pass
                        retries += 1
                    try:
                        response.raise_for_status()
                    except Exception as e:
                        self._handle_exception(e, response)
                        result = SpanExportResult.FAILURE
                if num_chunks > 1:
                    logger.info(f'Split exported data to {num_chunks} chunks')

            return result
        except Exception as e:
            self._handle_exception(e, response)
            return SpanExportResult.FAILURE

    def _handle_exception(self, exc: Exception, response: Optional[requests.Response]):
        if self.sentry_logger is not None:
            with self.sentry_logger.configure_scope() as scope:
                if response is not None:
                    scope.set_context('AWS Context',
                                      {'X Ray Trace Id': response.headers.get('x-amzn-trace-id'),
                                       'Request Id': response.headers.get('x-amzn-requestid'),
                                       'Response': response.text})
                self.sentry_logger.capture_exception(exc)

    @staticmethod
    def _should_retry(response: Optional[requests.Response]):
        return response is None or response.status_code >= 500 or response.status_code == 408
