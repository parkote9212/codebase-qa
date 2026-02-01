"""벡터 검색 서비스"""

import os
from pathlib import Path
from collections import Counter

import chromadb
from chromadb.config import Settings


# ChromaDB 저장 경로
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "chroma_db"


class Retriever:
    """ChromaDB 벡터 검색 클래스"""

    _instance = None

    def __new__(cls, persist_directory: str = None):
        """싱글톤 패턴"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, persist_directory: str = None):
        if hasattr(self, "_initialized"):
            return

        if persist_directory is None:
            persist_directory = str(DATA_DIR)

        # 디렉토리 생성
        os.makedirs(persist_directory, exist_ok=True)

        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name="codebase",
            metadata={"hnsw:space": "cosine"},
        )
        self._initialized = True

    def add(
        self,
        documents: list[str],
        embeddings: list[list[float]],
        ids: list[str],
        metadatas: list[dict] = None,
    ):
        """문서 추가"""
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        )

    def query(self, embedding: list[float], n_results: int = 5) -> dict:
        """유사 문서 검색"""
        return self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
        )

    def count(self) -> int:
        """전체 문서 수 반환"""
        return self.collection.count()

    def get_by_project(self, project: str) -> dict:
        """프로젝트별 문서 조회"""
        return self.collection.get(
            where={"project": project},
        )

    def count_by_project(self, project: str) -> int:
        """프로젝트별 문서 수"""
        result = self.collection.get(
            where={"project": project},
            include=[],
        )
        return len(result.get("ids", []))

    def delete_by_project(self, project: str) -> int:
        """프로젝트별 문서 삭제"""
        # 삭제 전 개수 확인
        count = self.count_by_project(project)
        if count > 0:
            self.collection.delete(where={"project": project})
        return count

    def get_project_stats(self) -> list[dict]:
        """프로젝트별 통계"""
        # 모든 메타데이터 조회
        result = self.collection.get(include=["metadatas"])
        metadatas = result.get("metadatas", [])

        if not metadatas:
            return []

        # 프로젝트별 집계
        project_data = {}
        for meta in metadatas:
            project = meta.get("project", "unknown")
            language = meta.get("language", "unknown")

            if project not in project_data:
                project_data[project] = {"chunks": 0, "languages": Counter()}

            project_data[project]["chunks"] += 1
            project_data[project]["languages"][language] += 1

        # 정렬하여 반환
        return [
            {
                "project": project,
                "chunks": data["chunks"],
                "languages": dict(data["languages"]),
            }
            for project, data in sorted(project_data.items())
        ]

    def has_project(self, project: str) -> bool:
        """프로젝트가 인덱싱되어 있는지 확인"""
        return self.count_by_project(project) > 0

    def clear_all(self):
        """모든 문서 삭제"""
        # 컬렉션 삭제 후 재생성
        self.client.delete_collection("codebase")
        self.collection = self.client.get_or_create_collection(
            name="codebase",
            metadata={"hnsw:space": "cosine"},
        )
