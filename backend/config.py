"""설정 관리

환경변수 또는 .env 파일에서 설정값 로드
"""

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # Ollama 설정
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout: float = 120.0

    # 임베딩 설정
    embedding_model: str = "all-MiniLM-L6-v2"

    # 코드베이스 경로
    code_base_path: str = "/Volumes/DEV_DATA/code"

    # 허용된 브라우저 경로 (쉼표 구분)
    allowed_browse_paths: str = "/Users/gcpark/code,/Volumes/DEV_DATA/code"

    # CORS 설정
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS origins를 리스트로 반환"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def allowed_browse_paths_list(self) -> list[str]:
        """허용된 브라우저 경로 리스트"""
        return [p.strip() for p in self.allowed_browse_paths.split(",") if p.strip()]

    def is_path_allowed(self, path: str) -> bool:
        """경로가 허용된 범위 내인지 확인"""
        target = Path(path).resolve()
        for allowed in self.allowed_browse_paths_list:
            allowed_path = Path(allowed).resolve()
            try:
                target.relative_to(allowed_path)
                return True
            except ValueError:
                continue
        return False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """설정 싱글톤 (캐시됨)"""
    return Settings()
