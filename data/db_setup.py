#Entities - word, guess, clue

#Tables

#words

#word selection - Links 9 words

#Guess - word selection with guess word

#Clue - word selection with clue word

import asyncio
from .db import engine, Base
from .models import WordConnectionWord, WordConnection,Word, Clue
from sqlalchemy import text


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        )

        
if __name__ == "__main__":
    asyncio.run(main())