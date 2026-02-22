import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.mistral_api_key: str = os.getenv("MISTRAL_API_KEY", "")
        self.user: str = os.getenv("USER", "")
