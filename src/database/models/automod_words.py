from ..database import Base
from sqlalchemy import Column, Integer, String, DateTime
from discord import Member
from datetime import datetime

class AutomodWordsModel(Base):
    __tablename__ = 'automod_words'
    wordID = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String, unique=True, nullable=False)
    time = Column(DateTime)

    def __init__(self, word: str):
        self.word = word
        self.time = datetime.now()

