from flask import Flask
from sqlalchemy import Column, String
from sqlalchemy.orm import declarative_base, Session

Base = declarative_base()


class Book(Base):
    __tablename__ = 'book'

    title = Column(String(80), unique=True, nullable=False, primary_key=True)
    author = Column(String())


def create_flask_app(engine, num_requests=1):
    app = Flask(__name__)

    @app.route('/')
    def app_index():
        with Session(engine) as session:
            for _ in range(num_requests):
                session.query(Book).all()
        return ''

    return app
