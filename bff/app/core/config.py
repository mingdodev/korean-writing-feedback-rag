from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    CLOVA_API_KEY: str
    CLOVA_URL: str = (
        "https://clovastudio.stream.ntruss.com/v3/chat-completions/HCX-007"
    )

    class Config:
        env_file = ".env"

settings = Settings()