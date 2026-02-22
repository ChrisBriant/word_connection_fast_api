from typing import List
from pydantic import BaseModel
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from .models import WordConnectionWord, WordConnection,Word, Clue
from .db import engine
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload, joinedload
from sqlalchemy import select, func
from pathlib import Path
from datetime import datetime
import json


async def add_words(session: AsyncSession, word_list: list[str]) -> int:
    """
    Add words from a list to the database, ignoring duplicates.
    
    Returns the number of words successfully added.
    """
    added_count = 0
    for w in word_list:
        w = w.strip()  # remove leading/trailing spaces
        if not w:
            continue  # skip empty strings
        word_obj = Word(word=w)
        session.add(word_obj)
        try:
            await session.commit()
            added_count += 1
        except IntegrityError:
            await session.rollback()  # word already exists, skip it
    return added_count

async def get_random_words(session: AsyncSession, count: int = 9) -> list[Word]:
    """
    Fetch `count` random words from the words table.
    Returns a list of Word objects.
    """
    result = await session.execute(
        select(Word)
        .order_by(func.random())  # PostgreSQL random ordering
        .limit(count)
    )
    return result.scalars().all()

async def create_word_connection(
    session: AsyncSession,
    words: list[Word],
    selected_flags: list[bool | None] | None = None
) -> WordConnection:
    if selected_flags is None:
        selected_flags = [None] * len(words)  # explicitly None
    elif len(selected_flags) != len(words):
        raise ValueError("selected_flags must be the same length as words")

    # Create the WordConnection
    connection = WordConnection()
    session.add(connection)
    await session.flush()  # assign id

    # Add WordConnectionWord rows
    for word, selected in zip(words, selected_flags):
        wcw = WordConnectionWord(
            word_id=word.id,
            connection_id=connection.id,
            selected=selected  # now can be None
        )
        session.add(wcw)

    await session.commit()
    await session.refresh(connection)
    return connection

async def get_word_connection_by_id(
    session: AsyncSession,
    connection_id: int
) -> WordConnection | None:
    """
    Fetch a WordConnection by ID, including all words and selected flags.
    
    Returns:
        WordConnection object or None if not found
    """
    result = await session.execute(
        select(WordConnection)
        .where(WordConnection.id == connection_id)
        .options(
            # eager load associated words via the secondary table
            # adjust based on your relationships
            # For full WordConnectionWord info including selected:
            selectinload(WordConnection.word_links).selectinload(WordConnectionWord.word),
            selectinload(WordConnection.clue)
        )
    )
    connection = result.scalars().first()
    return connection

def valid_clue_text(clue_text):
    clue_text = clue_text.strip()

    if not clue_text:
        return False
    # Reject if it contains any whitespace
    if any(char.isspace() for char in clue_text):
        return False
    return True

async def add_clue_to_selection(
    session: AsyncSession,
    selection_id: int,
    selection_list: list[dict],
    clue_text: str,
    clue_word_count: int,
) -> Clue:
    """
    Updates selected flags on WordConnectionWord rows,
    validates selected count,
    and creates a Clue.
    """

    #Validate the clue string
    if not valid_clue_text(clue_text):
        raise ValueError("Clue must be a single word with no spaces")

    # 1️⃣ Load selection and word links
    result = await session.execute(
        select(WordConnection)
        .where(WordConnection.id == selection_id)
        .options(selectinload(WordConnection.word_links))
    )

    word_connection = result.scalar_one_or_none()

    if not word_connection:
        raise ValueError(f"Selection {selection_id} not found")

    # Optional: prevent duplicate clue
    if word_connection.clue:
        raise ValueError("A clue already exists for this selection")

    # 2️⃣ Build lookup of links
    word_links_by_id = {
        link.word_id: link
        for link in word_connection.word_links
    }

    true_count = 0

    # 3️⃣ Update selected values
    for item in selection_list:
        word_id = item["word_id"]
        selected_value = item.get("selected")

        if word_id not in word_links_by_id:
            raise ValueError(f"Word {word_id} not part of this selection")

        word_links_by_id[word_id].selected = selected_value

        if selected_value is True:
            true_count += 1

    # 4️⃣ Validate count matches expected
    if true_count != clue_word_count:
        raise ValueError(
            f"clue_word_count ({clue_word_count}) "
            f"does not match number of selected words ({true_count})"
        )

    # 5️⃣ Create clue
    new_clue = Clue(
        clue=clue_text.strip(),
        clue_word_count=clue_word_count,
        connection_id=selection_id,
    )

    session.add(new_clue)
    await session.flush()  # assign id


    # 6️⃣ Commit atomically
    await session.commit()
    await session.refresh(new_clue)
    return new_clue

async def get_clue_by_id(
    session: AsyncSession,
    clue_id: int,
) -> Clue | None:

    result = await session.execute(
        select(Clue)
        .where(Clue.id == clue_id)
        .options(
            selectinload(Clue.connection)
                .selectinload(WordConnection.word_links)
                .selectinload(WordConnectionWord.word)
        )
    )

    return result.scalar_one_or_none()


async def main():
    BASE_DIR = Path(__file__).resolve().parent.parent
    file_path = BASE_DIR / "word_list.txt"

    with open(file_path, "r") as file:
        words = [line.strip() for line in file]
    print(words[0:2])

    # Create async session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        #TEST ADD THE WORDS
        #inserted_words = await add_words(session,words)
        #print("WORDS INSERTED", inserted_words)
        #TEST SELECT RANDOM WORDS AND CREATE SELECTION
        nine_random_words = await get_random_words(session)
        print("NINE RANDOM WORDS", nine_random_words)
        for word in nine_random_words:
            print("WORD", word.word)
        selected_list = [True,False,True,True,False,False,False,False,True]
        word_selection = await create_word_connection(session,nine_random_words,selected_flags=selected_list)
        print(word_selection.id)
        #TEST GET A WORD SELECTION
        word_connection = await get_word_connection_by_id(session,word_selection.id)
        print("WORD CONNECTION", word_connection.to_dict())
        word_connection_dict = word_connection.to_dict()
        word_connection_list = [{'word_id': word['word_id'], 'selected' : word['selected'] } for word in word_connection_dict['words']]
        print("WORD CONNECTION LIST TO SEND", word_connection_list)
        #TEST ADD WORD SELECTION TO A CLUE
        try:
            clue = await add_clue_to_selection(session,word_connection.id,word_connection_list,"rights",4)
        except Exception as e:
            print(e)
        print("CLUE ADDED", clue.id)
        #TEST GET THE CLUE OBJECT
        #TO DO test getting the clue as an object
        try:
            clue_response = await get_clue_by_id(session,clue.id)
        except Exception as e:
            print("ERROR OCCURRED", e)
        print("CLUE RESPONSE", clue_response.to_dict())


if __name__ == "__main__":
    asyncio.run(main())