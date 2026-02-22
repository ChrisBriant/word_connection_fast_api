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
    get_random_words
)
from data.shemas import (
    WordWithoutSelectionSchema,
    WordSchema,
    ClueWithSelectedWordsSchema,
    AIGuessResponseSchema,
)
from authentication.auth import get_api_key
from services.ai import  ai_guess_word
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
    ai_selection = ai_guess_word(word_data,clue_with_selection.clue,clue_with_selection.number_of_selected_words)
    #ai_selection =   [{'id': 992, 'word': 'golf', 'selected': False}, {'id': 747, 'word': 'budget', 'selected': False}, {'id': 301, 'word': 'excitement', 'selected': True}, {'id': 493, 'word': 'study', 'selected': True}, {'id': 901, 'word': 'guarantee', 'selected': False}, {'id': 1092, 'word': 'anger', 'selected': False}, {'id': 486, 'word': 'work', 'selected': True}, {'id': 1515, 'word': 'silly', 'selected': False}, {'id': 942, 'word': 'holiday', 'selected': False}]
    ai_guess_response = [ WordSchema.model_validate(guess) for guess in ai_selection]
    response = AIGuessResponseSchema(
        clue=clue_with_selection.clue,
        number_of_selected_words=clue_with_selection.number_of_selected_words,
        words=ai_guess_response,
    )
    print("AI SELECTION", response)

    return response


#     print("TRANSLATION ID ", translation_id_and_voice.translation_id)
#     async_session = sessionmaker(
#         engine, class_=AsyncSession, expire_on_commit=False
#     )

#     usages_list = []

#     async with async_session() as session:
#         usages = await get_usages_by_translation_id(session,int(translation_id_and_voice.translation_id))
#         print("USAGES", usages)
#         if len(usages) < 1:
#             raise HTTPException(status_code=404, detail=f"No usages found.")
#         for usage in usages[0:1]:
#             print("USAGE OBJECT", usage.id, usage.ja)
#             #Set usage ID to a variable
#             usage_id = usage.id


#             #This gets the audio link if it already exists so we don't waste tokens for Eleven LABS

#             existing_usage = await get_existing_audio_for_usage(session,usage.id)
#             if(existing_usage):
#                 # usages_list.append(LinkResponse.model_validate({
#                 #     "id": existing_usage.id,
#                 #     "usage_id": existing_usage.usage_id,
#                 #     "audio_id": existing_usage.audio_id,
#                 #     "storage_url": existing_usage.audio.storage_url,
#                 #     "created_at": existing_usage.created_at,
#                 # }))
#                 usages_list.append(existing_usage)
#                 continue

#             #Generate the audio file
#             BASE_DIR = Path(__file__).resolve().parent
#             audio_dir = BASE_DIR / "audio"
#             audio_dir.mkdir(exist_ok=True)
#             audio_filename = str(uuid.uuid4()) + ".mp3"
#             audio_path = audio_dir / audio_filename

#             voice_id_to_send = translation_id_and_voice.voice_id if translation_id_and_voice.voice_id else "EXAVITQu4vr4xnSDxMaL"
#             print("THE VOICE ID IS", voice_id_to_send)

#             try:
#                 audio_file_path = await get_audio_from_eleven_labs(usage.ja,audio_path,voice_id_to_send)
#             except ElevenLabsAPIError as elae:
#                 print("ELAE", elae)
#                 if elae.status_code == 404:
#                     raise HTTPException(status_code=404, detail=f"A voice with the voice id ${voice_id_to_send} was not found.")
#                 else:
#                     raise HTTPException(status_code=400, detail="An error occurred generating the audio.")
#             except Exception as e:
#                 raise HTTPException(status_code=400, detail="An error occurred generating the audio.")

#             #Upload the audio file to S3 storage
#             with open(audio_file_path, "rb") as f:
#                 #Get the file data required for transferring to S3
#                 audio_data = f.read()
#             storage_url = await upload_to_s3(audio_data,audio_filename)
#             print("UPLOADED FILE ", storage_url)

#             link = await add_usage_audio(session,usage_id,storage_url,voice_id_to_send)
#             #link_obj = LinkResponse.model_validate(link)
#             print("ADDED STORAGE LINK TO DB", link.__dict__)
#             usages_list.append(LinkResponse.model_validate({
#                 "id": link.id,
#                 "usage_id": usage_id,
#                 "storage_url": link.storage_url,
#                 "created_at": link.created_at,
#             }))
#     return usages_list

# @app.get('/gettranslation', response_model=TranslationWithAudioResponse)
# async def get_translation_by_word_or_id(
#     translation_id: int = Query(None, ge=1, description="Page number, must be >= 1"),
#     word: str = Query(None, description="Page number, must be >= 1"),
# ):
#     if(not word and not translation_id):
#         raise HTTPException(status_code=400,detail="translation_id or word must be included in the query parameters")

#     async_session = sessionmaker(
#         engine, 
#         class_=AsyncSession, expire_on_commit=False
#     )

#     translation = None
#     audio = None

#     async with async_session() as session:
#         #Try the id first
#         if(translation_id):
#             translation, audio = await get_translation_with_audio_by_id(session,translation_id)
#             #print(translation)
#             if not translation and word:
#                 #Try getting by word
#                 translation, audio = await get_translation_with_audio_by_word(session,word)

#         if not translation_id and word:
#             #Try getting by word
#             translation, audio = await get_translation_with_audio_by_word(session,word)

#     if not translation:
#         raise HTTPException(status_code=404,detail="Translation not found.")
    


#     #Create the response
#     response = TranslationWithAudioResponse(
#         translation=translation,
#         audio=audio
#     )
#     return response



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