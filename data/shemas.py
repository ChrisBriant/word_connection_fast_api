from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from typing import List


class WordSchema(BaseModel):
    id: int
    word: str
    selected: bool | None

    model_config = ConfigDict(from_attributes=True)

class WordWithoutSelectionSchema(BaseModel):
    id: int
    word: str

    model_config = ConfigDict(from_attributes=True)

# class ListOfWordsSchema(BaseModel):
#     List[WordWithoutSelectionSchema]

class ClueWithSelectedWordsSchema(BaseModel):
    clue : str
    number_of_selected_words : int
    words : List[WordWithoutSelectionSchema]

class AIClueWithSelectedWordsSchema(BaseModel):
    clue_id : int
    clue : str
    number_of_selected_words : int
    created_at : datetime
    words : List[WordSchema]

class AIGuessResponseSchema(BaseModel):
    clue : str
    number_of_selected_words : int
    words : List[WordSchema]

class WordConnectionWordSchema(BaseModel):
    word: WordSchema
    selected: Optional[bool]

    model_config = ConfigDict(from_attributes=True)

class WordConnectionSchema(BaseModel):
    id: int
    word_links: List[WordConnectionWordSchema]

    model_config = ConfigDict(from_attributes=True)



class ClueSchema(BaseModel):
    id: int
    clue: str
    clue_word_count: int
    created_at: datetime
    connection: WordConnectionSchema

    model_config = ConfigDict(from_attributes=True)