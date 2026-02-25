import dotenv
import os
from openai import OpenAI
import json
import ast
import re

dotenv_file = ".env"
if os.path.isfile(dotenv_file):
    dotenv.load_dotenv(dotenv_file)

API_KEY = os.environ.get("OPENAI_API_KEY")

class AIResponseNotValid(Exception):
    """Raised when the AI response does not match the expected format or schema."""

    def __init__(self, message="AI response is not valid.", response=None, errors=None):
        super().__init__(message)
        self.response = response
        self.errors = errors

    def __str__(self):
        base = super().__str__()
        details = []

        if self.errors:
            details.append(f"errors={self.errors}")

        if self.response:
            details.append(f"response={self.response}")

        if details:
            return f"{base} ({', '.join(details)})"

        return base


def ai_get_linking_word(list_of_word_objects:list) -> str:
    """
        Get a word from open AI which links the selected ones
        
        :param list_of_word_objects: Description
        :type list_of_word_objects: list
        :return: linking_word
        :rtype: str
    """
    if not API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    
    client = OpenAI(api_key=API_KEY)

    # --- PROMPT FOR AI ---
    prompt = f"""
        You are generating a clue for a word connection game.

        You are given this list of word objects in JSON format:
        {list_of_word_objects}

        Task:
        1. Identify ONLY the words where "selected" is true.
        2. Ignore all other words completely.
        3. Think of ONE English word that clearly links ALL selected words.
        4. The clue must not reasonably relate to any unselected words.

        Rules:
        - The clue must be exactly one English word.
        - The word must be completely different from any of the words in the list of word objects
        - No spaces.
        - No punctuation.
        - No explanation.
        - Output ONLY the word.
        - If no strong exclusive link exists, choose the best possible linking word anyway.
    """

    # --- API CALL ---
    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": "You are generating a clue for a word connection game."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_output_tokens=100
    )

    # --- EXTRACT TEXT OUTPUT ---
    clue = response.output_text.strip()  # Remove leading/trailing whitespace
    print("CLUE:", clue)

    return clue
    # try:
    #     reply_dict = json.loads(reply_data)
    # except json.JSONDecodeError as e:
    #     # Handle malformed JSON
    #     print("JSON parse error:", e)
    #     reply_dict = None
    # return reply_dict


def validate_ai_clue(original_words:list,ai_response:list, clue:str) -> bool:
    """
    #   1 .word ids and words must match
    #   2. clue word must be different from any of the selected words         
    """
    #Get the original ids and response IDs
    original_ids = [ word["id"]  for word in original_words]
    response_ids = [ word["id"]  for word in ai_response]
    if set(original_ids) != set(response_ids):
        print("IDs do not match")
        return False
    #Get the original words and response words
    original_words = [ word["word"]  for word in original_words]
    response_words = [ word["word"]  for word in ai_response]
    if set(original_words) != set(response_words):
        print("Words do not match")
        return False
    #Check the clue word
    if clue in original_words:
        print("Clue is in word list")
        return False
    return True

def ai_get_clue_and_selected_words(list_of_word_objects:list) -> str:
    """
        Get a clue to match a slection of words from open AI
        
        :param list_of_word_objects: Description
        :type list_of_word_objects: list
        :return: linking_word
        :rtype: str
    """
    if not API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    
    client = OpenAI(api_key=API_KEY)

    # --- PROMPT FOR AI ---
    prompt = f"""
        You are generating a clue for a word connection game.

        You are given this list of word objects in JSON format:
        {list_of_word_objects}

        Each object contains:
        - "id": integer
        - "word": string

        Your task:

        1. Generate ONE single English word as a clue.
        2. The clue must NOT exactly match any word in the list.
        3. Select the words that have a strong, clear, and guessable association with the clue.
        4. You must select at least one word.
        5. Aim to maximise the number of selected words, but NEVER at the expense of strong association.
        6. Weak or vague associations are not allowed.

        CRITICAL STRUCTURE RULES:
        - You MUST return ALL original objects.
        - You MUST preserve the original order.
        - You MUST NOT modify any "id" values.
        - You MUST NOT modify any "word" values.
        - You may ONLY add a boolean field called "selected".
        - Every object must contain: id, word, selected.

        Output Rules:
        - Return ONLY valid JSON.
        - No markdown.
        - No explanations.
        - The JSON must match this exact structure:

        {{
        "clue": "<single_word>",
        "selected_words": [
            {{ "id": <original_id>, "word": "<original_word>", "selected": true_or_false }}
        ]
        }}

        The selected_words array MUST contain the same number of objects as the input.
    """

    # --- API CALL ---
    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": "You are generating a clue for a word connection game."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_output_tokens=500
    )

    # --- EXTRACT TEXT OUTPUT ---
    # Raw model output
    raw_output = response.output_text.strip()

    # Remove any code fences ``` or ```python
    clean_output = re.sub(r"^```(?:python)?|```$", "", raw_output, flags=re.MULTILINE).strip()

    # Convert to Python object
    #selected_words_with_clue= ast.literal_eval(clean_output)
    selected_words_with_clue = json.loads(clean_output)

    #selected_words_list = ast.literal_eval(response.output_text.strip())
    print("SELECTED WORDS", selected_words_with_clue)
    #TODO:
    #Need to validate the response, 
    #   1 .word ids and words must match
    #   2. clue word must be different from any of the selected words 
    #Error handling from API method needs to return a 400 error if the AI fails
    if not validate_ai_clue(list_of_word_objects,selected_words_with_clue["selected_words"],selected_words_with_clue["clue"]):
        raise AIResponseNotValid(
            message="Mismatch between input words and clue response.",
            response=response,
            errors=["Invalid clue response from AI"]
        )
    
    return selected_words_with_clue


def validate_ai_output(original_words : list, generated_words: list, number_of_words: int) -> bool:
    #Check the AI has output the same words
    ai_words_list = [ gen_word["word"] for gen_word in generated_words]
    orig_words_list = [ orig_word["word"] for orig_word in original_words]
    for word in ai_words_list:
        if word not in orig_words_list:
            print("NOT IN LIST", word)
            print("ORIGINAL WORDS", orig_words_list)
            print("AI WORDS", ai_words_list)
            return False
    #Check that the ai has selected the right number of words
    selected_words = [ gen_word["word"] for gen_word in generated_words if gen_word["selected"] ]
    if len(selected_words) != number_of_words:
        print("NOT SELECTED CORRECTLY")
        print("ORIGINAL WORDS", original_words)
        print("AI WORDS", generated_words)
        return False
    return True


def ai_guess_word(list_of_word_objects:list,clue:str,num_words_to_select:int) -> list:
    """
        Docstring for ai_guess_word
        
        :param list_of_word_objects: Description
        :type list_of_word_objects: list
        :param clue: Description
        :type clue: str
        :param noOfWords: Description
        :type noOfWords: int
        :return: Description
        :rtype: list
    """
    if not API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    
    client = OpenAI(api_key=API_KEY)

    # --- PROMPT FOR AI ---
    prompt = f"""
            You are playing a word connection game.

        You are given:
        1. A list of word objects in JSON/Python dict format:
        {list_of_word_objects}

        Each object has:

        - "seq": the sequence number
        - "word": the word string

        2. A linking word: "{clue}"  
        3. EXACT_NUMBER_OF_WORDS_TO_SELECT : {num_words_to_select}

        Task:
        - You mustIdentify exactly {num_words_to_select} words that are most clearly connected to the linking word.  
        - The number of identified words must match the value EXACT_NUMBER_OF_WORDS_TO_SELECT, even if there is no obvious connection you must select a number of words that matches this value.
        - Update ONLY the "selected" field of the original word objects:  
        - Set "selected": True for the words you choose.  
        - Set "selected": False for all other words.  
        - Keep all other fields unchanged.  
        - Keep the original order of the word objects.  

        Rules:
        - Output the **entire original list** with updated "selected" fields.  
        - Output nothing else: no explanations, no extra text, no commentary.  
        - Output must be valid Python-style list of dictionaries, exactly like the input list.

        Output:
    """
    print("PROMPT",prompt)

    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": "You are an AI that selects words for a word connection game."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_output_tokens=300
    )

    # Raw model output
    raw_output = response.output_text.strip()

    # Remove any code fences ``` or ```python
    clean_output = re.sub(r"^```(?:python)?|```$", "", raw_output, flags=re.MULTILINE).strip()

    # Convert to Python object
    selected_words_list = ast.literal_eval(clean_output)

    #selected_words_list = ast.literal_eval(response.output_text.strip())
    print("SELECTED WORDS", selected_words_list)
    #TODO:
    is_response_valid = validate_ai_output(list_of_word_objects,selected_words_list,num_words_to_select)
    if not is_response_valid:
        raise AIResponseNotValid(
            message="Mismatch between words and requested and response.",
            response=response,
            errors=["Word mismatch error"]
        )
    #Need to validate the output to check that has selected the given amount and that it hasn't invented words
    return selected_words_list

if __name__ == "__main__":
    # word_selection = [{'seq': 1, 'word': 'body', 'selected': True}, {'seq': 2, 'word': 'border', 'selected': False}, {'seq': 3, 'word': 'pen', 'selected': True}, {'seq': 4, 'word': 'shoulder', 'selected': False}, {'seq': 5, 'word': 'panic', 'selected': False}, {'seq': 6, 'word': 'mud', 'selected': False}, {'seq': 7, 'word': 'league', 'selected': False}, {'seq': 8, 'word': 'client', 'selected': True}, {'seq': 9, 'word': 'agent', 'selected': True}]
    # for word in word_selection:
    #     del word["selected"] 
    # print("WORDS", word_selection)
    #ai_get_linking_word(word_selection)
    word_selection = [{
            "id": 992,
            "word": "golf"
        },
        {
            "id": 747,
            "word": "budget"
        },
        {
            "id": 301,
            "word": "excitement"
        },
        {
            "id": 493,
            "word": "study"
        },
        {
            "id": 901,
            "word": "guarantee"
        },
        {
            "id": 1092,
            "word": "anger"
        },
        {
            "id": 486,
            "word": "work"
        },
        {
            "id": 1515,
            "word": "silly"
        },
        {
            "id": 942,
            "word": "holiday"
        }
    ]
    try:
        #ai_guess_word(word_selection,"fart",4)
        ai_clue_and_words =  ai_get_clue_and_selected_words(word_selection)
        print("AI RESPONSE", ai_clue_and_words)
    except Exception as e:
        print("ERROR ", e)




