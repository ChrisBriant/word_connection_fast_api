#from typing import Union, List
from fastapi import FastAPI, Depends, HTTPException, Header, Query, status
from pydantic import BaseModel, HttpUrl
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import Optional, List
#from data.actions import get_or_add_user
import os, dotenv, base64, json
from uvicorn import Config, Server
from data.db import engine
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from data.db_actions import (
    get_random_words,
    add_clue_to_selection,
    create_word_connection,
    get_word_connection_by_id,
    get_clue_by_id,
)
from data.shemas import (
    WordWithoutSelectionSchema,
    WordSchema,
    ClueWithSelectedWordsSchema,
    AIGuessResponseSchema,
    AIClueWithSelectedWordsSchema,
    AIClueWithUnselectedWordsSchema,
)
from authentication.auth import get_api_key
from services.ai import  ai_guess_word, ai_get_clue_and_selected_words
from pathlib import Path
#import bleach


app = FastAPI()
#basedir = os.path.abspath(os.path.dirname(__file__))



origins=['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# del os.environ["GL_CLIENT_REDIRECT_URI"]
# del os.environ["FB_CLIENT_REDIRECT_URI"]
# del os.environ["X_REDIRECT_URI"]

# #LOAD ENVIRONMENT
dotenv_file = ".env"
if os.path.isfile(dotenv_file):
    dotenv.load_dotenv(dotenv_file)


# CLIENT_ID = os.environ.get("CLIENT_ID")
# CLIENT_SECRET = os.environ.get("CLIENT_SECRET")

# REDIRECT_URI="https://welcome-capital-jaybird.ngrok-free.app"

#RESPONSE MODELS

# class TranslationWithAudioResponse(BaseModel):
#     translation: TranslationResponse
#     audio: TranslationAudioResponse


#INPUT MODELS

class InputWord(BaseModel):
    word : str
    context : str
    voice_id : Optional[str] = None

class InputTranslationIdToVoice(BaseModel):
    translation_id : int
    voice_id : Optional[str] = None




@app.get('/getwordselection', response_model=List[WordWithoutSelectionSchema])
async def translate_word_eng_jap(api_key: str = Depends(get_api_key)):
    # Create async session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        nine_random_words = await get_random_words(session)
        print("NINE RANDOM WORDS", nine_random_words)
        response_test = WordWithoutSelectionSchema.model_validate(nine_random_words[0])
        response_list = [WordWithoutSelectionSchema.model_validate(word) for word in nine_random_words ]
        #response = ListOfWordsSchema.model_validate(nine_random_words)
        print("RESPONSE", response_list)
    return response_list

@app.post('/guessselection', response_model=AIGuessResponseSchema)
async def api_guess_selection(clue_with_selection : ClueWithSelectedWordsSchema, api_key: str = Depends(get_api_key)):
    print("INPUT DATA", clue_with_selection.words)
    word_data = [word.__dict__ for word in clue_with_selection.words]
    print("WORD DATA", word_data)
        
    #Get AI to make the word selection
    try:
        ai_selection = ai_guess_word(word_data,clue_with_selection.clue,clue_with_selection.number_of_selected_words)
    except Exception as e:
        print("AI ERROR")
        raise HTTPException(status_code=400, detail=f"Invalid AI response.")    
    #ai_selection =   [{'id': 992, 'word': 'golf', 'selected': False}, {'id': 747, 'word': 'budget', 'selected': False}, {'id': 301, 'word': 'excitement', 'selected': True}, {'id': 493, 'word': 'study', 'selected': True}, {'id': 901, 'word': 'guarantee', 'selected': False}, {'id': 1092, 'word': 'anger', 'selected': False}, {'id': 486, 'word': 'work', 'selected': True}, {'id': 1515, 'word': 'silly', 'selected': False}, {'id': 942, 'word': 'holiday', 'selected': False}]
    ai_guess_response = [ WordSchema.model_validate(guess) for guess in ai_selection]
    response = AIGuessResponseSchema(
        clue=clue_with_selection.clue,
        number_of_selected_words=clue_with_selection.number_of_selected_words,
        words=ai_guess_response,
    )
    print("AI SELECTION", response)
    #NOT SURE IF THE RESPONSE IS RIGHT AS IT MIGHT BE MUSSING THE SELECTIONS
    
    return response

@app.post('/generatewordsandcluefromselection', response_model=AIClueWithSelectedWordsSchema)
async def api_generate_clue(word_selection: List[WordWithoutSelectionSchema] , api_key: str = Depends(get_api_key)):
    """
        Human sends a selection of words and the AI generates a clue
    """
    print("INPUT DATA", word_selection)
    word_objects = [{"id": word.id, "word" : word.word} for word in word_selection]
    print("INPUT DATA WORD OBJECTS", word_objects)
    try:
        ai_clue_response = ai_get_clue_and_selected_words(word_objects)
    except Exception as e:
        print("AI ERROR", e)
        raise HTTPException(status_code=400, detail=f"Invalid AI response.")
    print("API AI RESPONSE", ai_clue_response)
    #ai_clue_response = {'clue': 'leisure', 'selected_words': [{'id': 992, 'word': 'golf', 'selected': True}, {'id': 747, 'word': 'budget', 'selected': False}, {'id': 301, 'word': 'excitement', 'selected': False}, {'id': 493, 'word': 'study', 'selected': False}, {'id': 901, 'word': 'guarantee', 'selected': False}, {'id': 1092, 'word': 'anger', 'selected': False}, {'id': 486, 'word': 'work', 'selected': False}, {'id': 1515, 'word': 'silly', 'selected': False}, {'id': 942, 'word': 'holiday', 'selected': True}]}
    #Put the selection and the clue into the database
    selected_flags = [word["selected"] for word in ai_clue_response["selected_words"]]
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    clue = None

    async with async_session() as session:
        #1. Create the word selection
        word_selection = await create_word_connection(session,word_selection,selected_flags=selected_flags)
        print("WORD SELECTION ID",word_selection.id)
        #2. Create the clue
        word_connection = await get_word_connection_by_id(session,word_selection.id)
        word_connection_dict = word_selection.to_dict()
        word_connection_list = [{'word_id': word['word_id'], 'selected' : word['selected'] } for word in word_connection_dict['words']]
        selected_length = len([ word for word in word_connection_dict['words'] if word["selected"] ])
        print("WORD connection LIST", word_connection_list)
        print("AI CLUE RESPONSE", ai_clue_response["clue"])
        print("SELECTED LENGTH", selected_length)
        try:
            clue = await add_clue_to_selection(session,word_selection.id,word_connection_list,ai_clue_response["clue"],selected_length)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to add the clue.")
        print("CLUE ID", clue.connection.word_links)
        word_selections = [ WordSchema(id=word_link.word_id, word=word_link.word.word, selected=word_link.selected) for word_link in clue.connection.word_links ]
        print("WORD SELECTIONS", word_selections)
        print("API CLUE RESPONSE", clue.to_dict())
        #THIS FAILS WHEN TRYING TO ASSIGN THE DATE
        response = AIClueWithSelectedWordsSchema(
            clue_id = clue.id,
            clue = clue.clue,
            number_of_selected_words = clue.clue_word_count,
            created_at = clue.created_at,
            words=word_selections
        )
        print("API RESPONSE OBJECT", response)


    return response



@app.post('/generatewordsandclue', response_model=AIClueWithUnselectedWordsSchema)
async def api_generate_words_and_clie( api_key: str = Depends(get_api_key)):
    """
        Words selection is generated and AI creates the clue
    """
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    clue = None

    async with async_session() as session:
        #1. Create the word selection
        
        word_connection = await get_random_words(session)
        word_objects = [{"id": word.id, "word" : word.word} for word in word_connection]
        print("INPUT DATA WORD OBJECTS", word_objects)
        #2. Get the clue from AI
        # try:
        #     ai_clue_response = ai_get_clue_and_selected_words(word_objects)
        # except Exception as e:
        #     print("AI ERROR", e)
        #     raise HTTPException(status_code=400, detail=f"Invalid AI response.")
        ai_clue_response = {'clue': 'light', 'selected_words': [{'id': 1327, 'word': 'deep', 'selected': False}, {'id': 1064, 'word': 'candle', 'selected': True}, {'id': 3, 'word': 'way', 'selected': False}, {'id': 1334, 'word': 'cancel', 'selected': False}, {'id': 1078, 'word': 'pension', 'selected': False}, {'id': 941, 'word': 'grade', 'selected': False}, {'id': 536, 'word': 'fat', 'selected': False}, {'id': 870, 'word': 'interview', 'selected': False}, {'id': 1514, 'word': 'rub', 'selected': False}]}
        print("API AI RESPONSE", ai_clue_response)
        selected_flags = [word["selected"] for word in ai_clue_response["selected_words"]]
        word_selection = await create_word_connection(session,word_connection,selected_flags=selected_flags)
        print("WORD SELECTION ID",word_selection.id)
        #2. Create the clue
        inserted_word_selection = await get_word_connection_by_id(session,word_selection.id)
        word_connection_dict = inserted_word_selection.to_dict()
        word_connection_list = [{'word_id': word['word_id'], 'selected' : word['selected'] } for word in word_connection_dict['words']]
        selected_length = len([ word for word in word_connection_dict['words'] if word["selected"] ])
        print("WORD connection LIST", word_connection_list)
        print("AI CLUE RESPONSE", ai_clue_response["clue"])
        print("SELECTED LENGTH", selected_length)
        try:
            clue = await add_clue_to_selection(session,word_selection.id,word_connection_list,ai_clue_response["clue"],selected_length)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to add the clue.")
        print("CLUE ID", clue.connection.word_links)
        word_selections = [ WordSchema(id=word_link.word_id, word=word_link.word.word, selected=word_link.selected) for word_link in clue.connection.word_links ]
        print("WORD SELECTIONS", word_selections)
        print("API CLUE RESPONSE", clue.to_dict())
        #THIS FAILS WHEN TRYING TO ASSIGN THE DATE
        response = AIClueWithUnselectedWordsSchema(
            clue_id = clue.id,
            clue = clue.clue,
            number_of_selected_words = clue.clue_word_count,
            created_at = clue.created_at,
            words=word_selections
        )
        print("API RESPONSE OBJECT", response)


    return response


@app.get('/getclueresponsefromid', response_model=AIClueWithSelectedWordsSchema)
async def api_get_clue_response_from_id(clue_id: int = Query(0, title="Clue ID"),api_key: str = Depends(get_api_key)):
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    clue = None

    async with async_session() as session:
        try:
            clue = await get_clue_by_id(session,clue_id)
        except Exception as e:
            print("ERROR OCCURRED", e)
            raise HTTPException(status_code=400, detail=f"An error occurred fetching the clue.")
    if not clue:
        raise HTTPException(status_code=404, detail=f"Clue not found.")
    word_selections = [ WordSchema(id=word_link.word_id, word=word_link.word.word, selected=word_link.selected) for word_link in clue.connection.word_links ]
    response = AIClueWithSelectedWordsSchema(
        clue_id = clue.id,
        clue = clue.clue,
        number_of_selected_words = clue.clue_word_count,
        created_at = clue.created_at,
        words=word_selections
    )
    return response

async def start_fastapi():
    config = Config(app=app, host="0.0.0.0", port=8000, loop="asyncio", reload=True)
    server = Server(config)
    await server.serve()

async def start_all():
    await asyncio.gather(
        start_fastapi()
    )

if __name__ == "__main__":
    asyncio.run(start_all())