# models.py
from .db import Base
from pydantic import BaseModel
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    ForeignKey,
    ForeignKeyConstraint,
    TIMESTAMP,
    func,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import CITEXT


class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(CITEXT, nullable=False, unique=True)

    created_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    connections = relationship(
        "WordConnection",
        secondary="word_connection_words",
        back_populates="words",
    )

    # word_selection = relationship(
    #     "WordSelection",
    #     back_populates="word_selection",
    #     cascade="all, delete-orphan",
    # )

    connection_links = relationship("WordConnectionWord",back_populates="word")

    def to_dict(self):
        return {
            "word_id": self.word_id,
            "word": self.word.word if self.word else None,
            "selected": self.selected,
        }
    
    # def to_object(self):
    #     return Word(
    #         word_id=self.word_id,
    #         word=
    #     )



class WordConnection(Base):
    __tablename__ = "word_connections"

    id = Column(Integer, primary_key=True)

    words = relationship(
        "Word",
        secondary="word_connection_words",
        back_populates="connections",
    )

    # clue_id = Column(
    #     Integer,
    #     ForeignKey("clues.id", ondelete="CASCADE"),
    #     nullable=True,
    # )

    word_links = relationship("WordConnectionWord", back_populates="connection")
    clue = relationship("Clue", back_populates="connection")




    def to_dict(self):
        return {
            "id": self.id,
            "words": [wcw.to_dict() for wcw in self.word_links],
            "clue" : self.clue,
        }

class WordConnectionWord(Base):
    __tablename__ = "word_connection_words"

    word_id = Column(
        Integer,
        ForeignKey("words.id", ondelete="CASCADE"),
        primary_key=True,
    )

    connection_id = Column(
        Integer,
        ForeignKey("word_connections.id", ondelete="CASCADE"),
        primary_key=True,
    )

    selected = Column(Boolean, nullable=True)


    #clue = relationship("Clue", back_populates="words")

    word = relationship("Word", back_populates="connection_links")
    connection = relationship("WordConnection", back_populates="word_links")

    def to_dict(self):
        return {
            "word_id": self.word_id,
            "word": self.word.word if self.word else None,
            "selected": self.selected,
        }

class Clue(Base):
    __tablename__ = "clues"

    id = Column(
        Integer,
        primary_key=True,
    )

    clue = Column(
        CITEXT,
        nullable=False   
    )

    clue_word_count = Column(
        Integer,
        nullable=False
    )

    created_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    connection_id = Column(
        Integer,
        ForeignKey("word_connections.id", ondelete="CASCADE"),
    )

    # words = relationship(
    #     "WordConnectionWord",
    #     back_populates="clue",
    # )

    connection = relationship(
        "WordConnection",
        back_populates="clue"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "clue": self.clue,
            "clue_word_count": self.clue_word_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "connection": self.connection.to_dict() if self.connection else None,
        }