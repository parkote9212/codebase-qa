"""RAG 파이프라인

질문 → 벡터 검색 → LLM 답변 생성
"""

from typing import Generator, Optional
from dataclasses import dataclass

from .retriever import Retriever
from .embedder import Embedder
from .llm import LLM, LLMResponse, OllamaError


# RAG 프롬프트 템플릿
RAG_SYSTEM_PROMPT = """당신은 코드 분석 전문가입니다.
아래 코드 컨텍스트를 참고하여 질문에 답변하세요.

[코드 컨텍스트]
{context}

[질문]
{question}

답변은 한글로, 코드 예시가 필요하면 포함하세요."""


@dataclass
class RAGResult:
    """RAG 결과"""
    answer: str
    sources: list[dict]  # 검색된 소스 코드 정보
    model: str


class RAGChain:
    """RAG 파이프라인"""

    def __init__(
        self,
        retriever: Optional[Retriever] = None,
        embedder: Optional[Embedder] = None,
        llm: Optional[LLM] = None,
        top_k: int = 5,
    ):
        self.retriever = retriever or Retriever()
        self.embedder = embedder or Embedder()
        self.llm = llm or LLM()
        self.top_k = top_k

    def _parse_search_results(self, search_results: dict, include_distance: bool = True) -> list[dict]:
        """검색 결과를 문서 리스트로 파싱"""
        documents = []
        if not search_results.get("documents"):
            return documents

        docs = search_results["documents"][0]
        metadatas = search_results.get("metadatas", [[]])[0]
        distances = search_results.get("distances", [[]])[0] if include_distance else [0] * len(docs)

        for doc, meta, dist in zip(docs, metadatas, distances):
            doc_dict = {"content": doc, **meta}
            if include_distance:
                doc_dict["distance"] = dist
            documents.append(doc_dict)

        return documents

    def _format_context(self, documents: list[dict]) -> str:
        """검색된 문서를 컨텍스트 문자열로 포맷"""
        if not documents:
            return "관련 코드를 찾을 수 없습니다."

        context_parts = []
        for i, doc in enumerate(documents, 1):
            filepath = doc.get("filepath", "unknown")
            language = doc.get("language", "unknown")
            chunk_type = doc.get("chunk_type", "code")
            name = doc.get("name", "unknown")
            content = doc.get("content", "")

            context_parts.append(
                f"--- 코드 {i} ---\n"
                f"파일: {filepath}\n"
                f"언어: {language}\n"
                f"타입: {chunk_type}\n"
                f"이름: {name}\n"
                f"```{language}\n{content}\n```"
            )

        return "\n\n".join(context_parts)

    def _build_prompt(self, question: str, context: str) -> str:
        """프롬프트 생성"""
        return RAG_SYSTEM_PROMPT.format(
            context=context,
            question=question,
        )

    def query(self, question: str) -> RAGResult:
        """질문에 대한 RAG 답변 생성"""
        # 1. 질문 임베딩
        question_embedding = self.embedder.embed(question)

        # 2. 관련 코드 검색
        search_results = self.retriever.query(
            embedding=question_embedding,
            n_results=self.top_k,
        )

        # 검색 결과 파싱
        documents = self._parse_search_results(search_results, include_distance=True)

        # 3. 컨텍스트 포맷
        context = self._format_context(documents)

        # 4. 프롬프트 생성
        prompt = self._build_prompt(question, context)

        # 5. LLM 답변 생성
        try:
            response = self.llm.generate(prompt)
            answer = response.content
            model = response.model
        except OllamaError as e:
            answer = f"LLM 에러: {str(e)}"
            model = self.llm.model

        # 소스 정보 (content 제외)
        sources = [
            {
                "filepath": doc.get("filepath"),
                "language": doc.get("language"),
                "project": doc.get("project"),
                "chunk_type": doc.get("chunk_type"),
                "name": doc.get("name"),
                "distance": doc.get("distance"),
            }
            for doc in documents
        ]

        return RAGResult(
            answer=answer,
            sources=sources,
            model=model,
        )

    def query_stream(self, question: str) -> Generator[str, None, None]:
        """스트리밍 RAG 답변 생성"""
        # 1. 질문 임베딩
        question_embedding = self.embedder.embed(question)

        # 2. 관련 코드 검색
        search_results = self.retriever.query(
            embedding=question_embedding,
            n_results=self.top_k,
        )

        # 검색 결과 파싱
        documents = self._parse_search_results(search_results, include_distance=False)

        # 3. 컨텍스트 포맷
        context = self._format_context(documents)

        # 4. 프롬프트 생성
        prompt = self._build_prompt(question, context)

        # 5. 스트리밍 LLM 답변 생성
        try:
            for chunk in self.llm.generate_stream(prompt):
                yield chunk
        except OllamaError as e:
            yield f"\n\nLLM 에러: {str(e)}"

    def search_only(self, question: str) -> list[dict]:
        """검색만 수행 (LLM 호출 없이)"""
        question_embedding = self.embedder.embed(question)

        search_results = self.retriever.query(
            embedding=question_embedding,
            n_results=self.top_k,
        )

        return self._parse_search_results(search_results, include_distance=True)


# =============================================================================
# 테스트
# =============================================================================

if __name__ == "__main__":
    rag = RAGChain()

    # 테스트 질문
    test_questions = [
        "BizSync에서 JWT 인증 어떻게 구현했어?",
        "Redis 캐싱은 어디서 사용해?",
        "Vue 컴포넌트 구조 설명해줘",
    ]

    for q in test_questions:
        print(f"\n{'='*60}")
        print(f"질문: {q}")
        print('='*60)

        try:
            result = rag.query(q)
            print(f"\n답변:\n{result.answer}")
            print(f"\n소스 ({len(result.sources)}개):")
            for src in result.sources:
                print(f"  - {src['filepath']} ({src['chunk_type']}: {src['name']})")
        except Exception as e:
            print(f"에러: {e}")
