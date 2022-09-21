from os import getenv
from unittest import TestCase, main

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from common.alchemy_instrumentation import fix_sql_query
from tests.objects import Book, Base

CONNECTION_STRING = getenv('CONNECTION_STRING')


class AlchemyInstrumentationTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.engine = create_engine(CONNECTION_STRING, future=True)
        Base.metadata.create_all(self.engine)
        event.listen(self.engine, "before_cursor_execute", self.before_query_hook)
        self.statement = None
        self.parameters = None

    def tearDown(self) -> None:
        super().tearDown()
        Book.__table__.drop(self.engine)

    def test_fix_sql_query_no_values(self):
        with Session(self.engine) as session:
            session.query(Book).all()
        fix_sql_query(self.statement, self.parameters)
        self.assertFalse(self.parameters)

    def test_fix_sql_query_single_value(self):
        value = '123'
        with Session(self.engine) as session:
            session.query(Book).get(value)
        self.assertIn(value, fix_sql_query(self.statement, self.parameters))

    def test_fix_sql_query_multiple_values(self):
        values = ('123', 'abcde')
        with Session(self.engine) as session:
            session.query(Book).filter(Book.author.in_(values)).all()
        for v in values:
            self.assertIn(v, fix_sql_query(self.statement, self.parameters))

    def before_query_hook(self, conn, cursor, statement, parameters, context, executemany):
        self.statement = statement
        self.parameters = parameters


if __name__ == '__main__':
    main()
