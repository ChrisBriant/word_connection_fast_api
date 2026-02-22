import os
from fastapi import HTTPException, Header
from typing import Optional


AUTH_KEY_CHECK = os.environ.get("AUTH_KEY")

#Authorizes the user based on an API key sent in the header
def get_api_key(x_api_key: Optional[str] = Header(None)):
    if not x_api_key or x_api_key != AUTH_KEY_CHECK:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    return x_api_key