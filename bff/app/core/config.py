from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    CLOVA_API_KEY: str
    CLOVA_URL: str = (
        "https://clovastudio.stream.ntruss.com/v3/chat-completions/HCX-007"
    )

    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC: str

    CHROMA_HOST: str
    CHROMA_COLLECTION_NAME: str
    ELASTICSEARCH_HOST: str

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5431
    POSTGRES_DB: str = "grammar"
    POSTGRES_USER: str = "grammar"
    POSTGRES_PASSWORD: str = "grammarpassword"

    class Config:
        env_file = ".env"

settings = Settings()