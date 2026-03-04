import os


class Settings:
    app_name: str = os.getenv("APP_NAME", "Assistant Demarches Simplifiees")
    app_env: str = os.getenv("APP_ENV", "dev")
    target_country: str = os.getenv("TARGET_COUNTRY", "Togo")


settings = Settings()
