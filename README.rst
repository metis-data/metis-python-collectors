How to use::

   from flask import Flask
   from flask_sqlalchemy import SQLAlchemy

   # import the function
   from sqlalchemycollector import instrument_sqlalchemy

   app = Flask()
   db = SQLAlchemy(app)

   # add the following line to instrument SQLAlchemy
   instrument_sqlalchemy(app, db.get_engine())
