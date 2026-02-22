
from pathlib import Path
import random

def get_nine_random_words_and_select(noOfWords : int) -> list:
    BASE_DIR = Path(__file__).resolve().parent.parent
    file_path = BASE_DIR / "word_list.txt"

    with open(file_path, "r") as file:
        words = [line.strip() for line in file]

    nine_random_words = random.sample(words,9)
    selected_words = random.sample(nine_random_words,noOfWords)
    list_of_word_selections = []
    count = 1
    for word in nine_random_words:
        list_of_word_selections.append({
            "seq" : count,
            "word" : word,
            "selected" : True if word in selected_words else False
        })
        count += 1
    return list_of_word_selections



if __name__ == "__main__":
    word_selection = get_nine_random_words_and_select(4)
    selected = [word for word in word_selection if word["selected"]]
    unselected = [word for word in word_selection if not word["selected"]]
    print("WORD SELECTION", word_selection)
    #print("WORDS UNSELECTED", unselected)