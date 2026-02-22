## Run app server

uvicorn main:app --reload


## Run app dev

uvicorn main:app --host 0.0.0.0 --port 8000 --reload

## Test data


{
  "clue": "emotion",
  "number_of_selected_words": 2,
  "words":   [{
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
}