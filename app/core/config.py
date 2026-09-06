"""Application settings read from the environment."""

from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Runtime configuration with safe development defaults."""

    PROJECT_NAME: str = getenv("PROJECT_NAME", "Flight Management System")
    API_V1_STR: str = getenv("API_V1_STR", "/api/v1")
    DATABASE_URL: str | None = getenv("DATABASE_URL") or getenv("NEON_DATABASE_URL")
    PINECONE_API_KEY: str | None = getenv("PINECONE_API_KEY")
    GEMINI_API_KEY: str | None = (
        getenv("GEMINI_API_KEY") or getenv("GOOGLE_API_KEY") or getenv("GEMINI_KEY")
    )
    PINECONE_INDEX_NAME: str = getenv("PINECONE_INDEX_NAME", "flight-policies")


settings = Settings()
