from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine('sqlite:///templates/db/city_bot.db')

Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()


class Incident(Base):
    __tablename__ = 'incidents'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String)
    text = Column(String)


Base.metadata.create_all(engine)