"""Paramètres de l'application, lus dans les variables d'environnement (ou le fichier backend/.env).

Aucun secret n'est écrit dans le code : voir `.env.example`.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CIAT VISION"
    environment: str = "development"  # development | production | test

    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/ciat_vision"

    jwt_secret: str = "CHANGER-CE-SECRET-EN-PRODUCTION"
    jwt_algorithm: str = "HS256"

    # Origines autorisées à appeler l'API (frontend), séparées par des virgules
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    anthropic_api_key: str | None = None
    ai_model: str = "claude-opus-5-5"

    # Comptes de démonstration créés au premier démarrage (désactivable en production)
    create_demo_accounts: bool = True
    # Peuplement automatique avec les données SIMULÉES si la base est vide
    seed_simulated_data: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        """Render fournit des URL « postgres:// » : on force le pilote psycopg 3."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
