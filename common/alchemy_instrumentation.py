import json
# from sqlalchemy.event import listen
from typing import Optional

import sentry_sdk
from opentelemetry import trace
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor, EngineTracer
from opentelemetry.instrumentation.sqlalchemy.engine import _after_cur_exec, _handle_error
from opentelemetry.instrumentation.utils import _generate_sql_comment
from opentelemetry.sdk.resources import Attributes
from opentelemetry.trace import Span
from opentelemetry.trace import Status, StatusCode
from sqlalchemy import event
from sqlalchemy.dialects.postgresql.asyncpg import AsyncAdapt_asyncpg_cursor

from .consts import (
    METIS_DO_NOT_TRACK_COMMENT,
    METIS_STATEMENT_SPAN_ATTRIBUTE,
    METIS_PLAN_SPAN_ATTRIBUTE,
    EXPLAIN_SUPPORTED_STATEMENTS
)
from .plan_collect_type import PlanCollectType
from .utils.log import log

INSTRUMENTING_LIBRARY_VERSION = '0.30b1'


class NoPlanException(BaseException):
    pass


@log
def add_quote_to_value_of_type_string(value):
    if isinstance(value, str):
        new_value = str(value).replace("'", "''")
        return "'{}'".format(new_value)  # pylint: disable=consider-using-f-string
    return value


@log
def fix_sql_query(sql, params):
    """without the fix the query is not working because string is not quoted"""
    if isinstance(params, dict):
        fixed_params = {
            key: add_quote_to_value_of_type_string(value)
            for key, value in params.items()
        }
    elif isinstance(params, (list, tuple)):
        # This actually can't happen in sqlalchemy with postgresql
        if params and isinstance(params[0], dict):
            all_keys = {k for d in params for k in d.keys()}
            fixed_params = {
                key: tuple(add_quote_to_value_of_type_string(d[key])
                           for d in params if key in d)
                for key in all_keys
            }
        else:
            fixed_params = params
    else:
        raise TypeError(f'Params of type {type(params)} and value {params}')

    return sql % fixed_params


class MetisSQLAlchemyInstrumentor(SQLAlchemyInstrumentor):

    @log
    def __init__(self,
                 resource_tags: Optional[Attributes] = None,
                 sentry_logger: Optional[sentry_sdk.Hub] = None,
                 ) -> None:
        super().__init__()
        self.plan_collection_option = None
        self.resource_tags = resource_tags
        self.sentry_logger = sentry_logger

    @log
    def _instrument(self, **kwargs):
        self.plan_collection_option = kwargs.get(
            "plan_collection_option", PlanCollectType.ESTIMATED,
        )
        self.exporter_tracer: EngineTracer = super()._instrument(enable_commenter=True, **kwargs)

        self.tracer_provider = kwargs.get('trace_provider')

        self.exporter_tracer.tracer = trace.get_tracer(
            "metis",
            INSTRUMENTING_LIBRARY_VERSION,
            tracer_provider=self.tracer_provider,
        )

        @log
        def _generate_comment(span: Span) -> str:
            span_context = span.get_span_context()
            meta = {}
            if span_context.is_valid:
                from opentelemetry.instrumentation.utils import (
                    _generate_opentelemetry_traceparent,
                )
                meta.update(_generate_opentelemetry_traceparent(span))
                if self.resource_tags is not None:
                    meta.update(self.resource_tags)
            return _generate_sql_comment(**meta)

        self.exporter_tracer._generate_comment = staticmethod(_generate_comment)

        engine = kwargs.get("engine")

        @log
        def handle_error(context):
            span = getattr(context.execution_context, "_metis_span", None)

            if span is None:
                return

            if span.is_recording():
                # If the exception means the operation results in an
                # error state, you can also use it to update the span status.
                span.set_status(
                    Status(
                        StatusCode.ERROR,
                        str(context.original_exception),
                    ),
                )
                span.record_exception(context.original_exception)

            span.end()

        event.listen(engine, "before_cursor_execute", self.before_query_hook, retval=True)
        event.listen(engine, "handle_error", handle_error)

    @log
    def _uninstrument(self, **kwargs):
        super()._uninstrument(**kwargs)
        engine = self.exporter_tracer.engine
        event.remove(engine, "before_cursor_execute", self.exporter_tracer._before_cur_exec)
        event.remove(engine, "before_cursor_execute", self.before_query_hook)

        event.remove(engine, "after_cursor_execute", _after_cur_exec)
        event.remove(engine, "handle_error", _handle_error)

    @log
    def before_query_hook(  # pylint: disable=too-many-arguments, unused-argument
            self,
            conn,
            cursor,
            statement,
            parameters,
            context,
            executemany,
    ):
        try:
            if statement.startswith(METIS_DO_NOT_TRACK_COMMENT):
                return statement, parameters

            current_span = context._otel_span
            if current_span.is_recording():
                try:
                    interpolated_statement = fix_sql_query(statement, parameters)
                except TypeError as e:
                    interpolated_statement = statement
                    if self.sentry_logger is not None:
                        self.sentry_logger.capture_exception(e)

                if interpolated_statement is not None:
                    current_span.set_attribute(
                        METIS_STATEMENT_SPAN_ATTRIBUTE,
                        interpolated_statement,
                    )

                if self.plan_collection_option == PlanCollectType.ESTIMATED:
                    if conn.dialect.name != "postgresql":
                        raise Exception(
                            "Plan collection is only supported for PostgreSQL",
                        )
                    if any(
                            statement.upper().startswith(prefix)
                            for prefix in EXPLAIN_SUPPORTED_STATEMENTS
                    ):
                        new_cursor = context.create_cursor()
                        try:
                            if isinstance(cursor, AsyncAdapt_asyncpg_cursor):
                                new_cursor.setinputsizes(*cursor._inputsizes)
                            new_cursor.execute(
                                METIS_DO_NOT_TRACK_COMMENT
                                + "explain (verbose, costs, summary, format JSON) "
                                + statement,
                                parameters,
                            )
                            res = new_cursor.fetchall()
                        finally:
                            new_cursor.close()

                        if not res:
                            raise NoPlanException(f"Query: {interpolated_statement}")
                        current_span.set_attribute(
                            METIS_PLAN_SPAN_ATTRIBUTE,
                            json.dumps(res[0][0][0]),
                        )
        except Exception as e:
            if self.sentry_logger is not None:
                self.sentry_logger.capture_exception(e)
        finally:
            return statement, parameters
