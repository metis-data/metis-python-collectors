import logging
from os import getenv
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from flask_package.sqlalchemycollector import setup
from tests.objects import Book, Base, create_flask_app

API_KEY = getenv('API_KEY')
CONNECTION_STRING = getenv('CONNECTION_STRING')
DSN = 'https://0671u5v0uk.execute-api.eu-central-1.amazonaws.com/test/'


def test_large_number_of_spans():
    logging.basicConfig(level=logging.INFO)
    engine = create_engine(CONNECTION_STRING, future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all((Book(title=uuid4().hex) for _ in range(1)))
        session.commit()
    app = create_flask_app(engine, 512)
    instrumentation = setup('lots-of-spans', resource_tags={"env": "staging"}, dsn=DSN, api_key=API_KEY)
    instrumentation.instrument_app(app, engine)
    with app.test_client() as client:
        client.get('/')
    instrumentation.uninstrument_app()
    Book.__table__.drop(engine)


if __name__ == '__main__':
    test_large_number_of_spans()
