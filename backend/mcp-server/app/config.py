from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str
    PORT: int
    INTEGRATIONS_SERVICE_URL: str

    class Config:
        env_file = ".env"


settings = Settings()
