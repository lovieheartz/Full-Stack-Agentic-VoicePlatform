from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str
    PORT: int
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ENCRYPTION_KEY: str
    FRONTEND_URL: str = "http://localhost:5173"
    CAMPAIGN_LEADS_SERVICE_URL: str = "http://localhost:8003"

    class Config:
        env_file = ".env"


settings = Settings()
