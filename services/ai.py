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
        3. A number of words that are connected: {num_words_to_select}

        Task:
        - Identify exactly {num_words_to_select} words that are most clearly connected to the linking word.  
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
    word_selection = [{'seq': 1, 'word': 'body', 'selected': True}, {'seq': 2, 'word': 'border', 'selected': False}, {'seq': 3, 'word': 'pen', 'selected': True}, {'seq': 4, 'word': 'shoulder', 'selected': False}, {'seq': 5, 'word': 'panic', 'selected': False}, {'seq': 6, 'word': 'mud', 'selected': False}, {'seq': 7, 'word': 'league', 'selected': False}, {'seq': 8, 'word': 'client', 'selected': True}, {'seq': 9, 'word': 'agent', 'selected': True}]
    for word in word_selection:
        del word["selected"] 
    print("WORDS", word_selection)
    #ai_get_linking_word(word_selection)
    try:
        ai_guess_word(word_selection,"fart",4)
    except Exception as e:
        print("ERROR ", e)




