"""코드 임베딩 서비스

sentence-transformers를 사용한 텍스트 임베딩
"""

from sentence_transformers import SentenceTransformer
from typing import Optional

from config import get_settings


class Embedder:
    """텍스트 임베딩 클래스"""

    _instance: Optional["Embedder"] = None
    _model: Optional[SentenceTransformer] = None

    def __new__(cls, model_name: str = None):
        """싱글톤 패턴 - 모델 로딩 비용 절약"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_name: str = None):
        if self._model is None:
            settings = get_settings()
            model_name = model_name or settings.embedding_model
            print(f"임베딩 모델 로딩: {model_name}")
            self._model = SentenceTransformer(model_name)
            self.model_name = model_name
            self.embedding_dim = self._model.get_sentence_embedding_dimension()
            print(f"모델 로딩 완료 (차원: {self.embedding_dim})")

    def embed(self, text: str) -> list[float]:
        """단일 텍스트 임베딩"""
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """배치 텍스트 임베딩"""
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=True,
        )
        return embeddings.tolist()

    def get_dimension(self) -> int:
        """임베딩 차원 반환"""
        return self.embedding_dim


# =============================================================================
# 테스트
# =============================================================================

if __name__ == "__main__":
    embedder = Embedder()

    # 테스트 텍스트
    test_texts = [
        "def calculate_sum(a, b): return a + b",
        "public class UserService { }",
        "const handleClick = () => { }",
    ]

    print("\n=== 단일 임베딩 테스트 ===")
    for text in test_texts:
        embedding = embedder.embed(text)
        print(f"텍스트: {text[:50]}...")
        print(f"임베딩 차원: {len(embedding)}")
        print(f"임베딩 샘플: {embedding[:5]}...")
        print()

    print("=== 배치 임베딩 테스트 ===")
    embeddings = embedder.embed_batch(test_texts)
    print(f"배치 크기: {len(embeddings)}")
    print(f"각 임베딩 차원: {len(embeddings[0])}")
