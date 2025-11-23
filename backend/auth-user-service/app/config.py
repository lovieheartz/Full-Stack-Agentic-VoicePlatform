from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # All required - must be in .env
    PROJECT_NAME: str
    PORT: int
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    SMTP_FROM_NAME: str
    OTP_EXPIRE_MINUTES: int
    OTP_LENGTH: int
    ALLOWED_ORIGINS: str
    ADMIN_EMAIL: str  # Email to receive organization onboarding notifications
    FRONTEND_URL: str  # Frontend URL for generating action links
    # Optional: Public base URL of this auth service for direct links from emails
    # Example: https://auth.api.alsatalk.com or http://localhost:8001
    API_PUBLIC_URL: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
