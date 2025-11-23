from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    CLOVA_API_KEY: str
    CLOVA_URL: str = (
        "https://clovastudio.stream.ntruss.com/v3/chat-completions/HCX-007"
    )

    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC: str
    
    ELASTICSEARCH_HOST: str
    CHROMA_SENTENCE_HOST: str

    class Config:
        env_file = ".env"

settings = Settings()