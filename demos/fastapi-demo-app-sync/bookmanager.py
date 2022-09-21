import os
import uvicorn

from fastapi import Request, HTTPException
from pydantic import BaseModel

from fastapi.templating import Jinja2Templates
from fastapi import FastAPI
from sqlalchemy import create_engine
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi_sqlalchemy import DBSessionMiddleware
from starlette import status
from starlette.middleware.cors import CORSMiddleware

from fastapialchemycollector.instruments import setup, MetisInstrumentor

templates = Jinja2Templates(directory="/Users/liorz/Documents/projects/metis/sqlalchemy_collector/demos/fastapi-demo-app-sync/templates")

from dotenv import load_dotenv

load_dotenv(override=True)  # take environment variables from .env.

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# to avoid csrftokenError
db_url = os.environ['DATABASE_URI']

assert db_url is not None

app.add_middleware(DBSessionMiddleware, db_url=db_url)

project_dir = os.path.dirname(os.path.abspath(__file__))

engine = create_engine(db_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

from sqlalchemy import Column, String


class Book(Base):
    __tablename__ = 'booking'
    title = Column(String(80), unique=True, nullable=False, primary_key=True)

    def __repr__(self):
        return "<Title: {}>".format(self.title)


from sqlalchemy.orm import Session
from fastapi import Depends


def get_db():
    db = None
    try:
        db = SessionLocal()
        yield db
    finally:
        if db:
            db.close()


def books_template(request: Request, db: Session = Depends(get_db)):
    books = db.query(Book).all()
    return templates.TemplateResponse("home.html", {"request": request, "books": books})

@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    return books_template(request, db)


class BookUpdatePayload(BaseModel):
    newtitle: str
    oldtitle: str


class BookCreatePayload(BaseModel):
    title: str


@app.post('/')
async def create(request: Request, db: Session = Depends(get_db)):
    try:
        form = await request.form()
        title = form.get('title')
        db_item = Book(title=title)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return books_template(request, db)
    except Exception as e:
        print("Couldn't create book title")
        print(e)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete(req: Request, db: Session = Depends(get_db)):
    book = await req.form()
    title = book.get('title')
    book = db.get(Book, title)
    if not book:
        raise HTTPException(status_code=404, detail=f'Book: "{title}" not found')
    db.delete(book)
    db.commit()
    return books_template(req, db)


@app.delete("/{title}", status_code=status.HTTP_200_OK)
async def delete(title: str, db: Session = Depends(get_db)):
    book = db.get(Book, title)
    if not book:
        raise HTTPException(status_code=404, detail=f'Book: "{title}" not found')
    db.delete(book)
    db.commit()
    return book


instrumentation = setup('books-api', api_key="<API_KEY>",
                        resource_tags={"PR": "Lior"})

import threading


def set_interval(func, sec):
    def func_wrapper():
        # set_interval(func, sec)
        func()

    t = threading.Timer(sec, func_wrapper)
    t.start()
    return t


def instrument():
    instrumentation.instrument_app(app, engine)


def uninstrument():
    instrumentation.uninstrument_app()


# set_interval(instrument, 1)
# set_interval(uninstrument, 10)
# set_interval(instrument, 34)
# set_interval(uninstrument, 120)

if __name__ == "__main__":
    instrument()
    uvicorn.run(app, host="0.0.0.0", debug=True, port=5012)
