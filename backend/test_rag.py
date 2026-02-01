"""RAG 파이프라인 테스트 스크립트

사용법:
    python test_rag.py
    python test_rag.py --index  # 인덱싱 먼저 실행
"""

import argparse
import sys
from pathlib import Path

# 상위 디렉토리를 path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from services.embedder import Embedder
from services.retriever import Retriever
from services.llm import LLM, OllamaError
from services.rag_chain import RAGChain
from utils.code_parser import parse_codebase, CODE_BASE_PATH


def index_codebase():
    """코드베이스 인덱싱"""
    print("=" * 60)
    print("코드베이스 인덱싱 시작")
    print("=" * 60)

    # 코드 파싱
    print(f"\n대상 경로: {CODE_BASE_PATH}")
    chunks = parse_codebase()

    if not chunks:
        print("청크가 없습니다. 경로를 확인하세요.")
        return False

    # 임베딩
    print("\n임베딩 생성 중...")
    embedder = Embedder()
    contents = [chunk.content for chunk in chunks]
    embeddings = embedder.embed_batch(contents)

    # 벡터 DB에 저장
    print("\n벡터 DB에 저장 중...")
    retriever = Retriever()

    # 기존 데이터 삭제
    try:
        retriever.collection.delete(where={})
        print("기존 데이터 삭제 완료")
    except Exception:
        pass

    # 배치로 추가
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i + batch_size]
        batch_embeddings = embeddings[i:i + batch_size]

        ids = [chunk.id for chunk in batch_chunks]
        documents = [chunk.content for chunk in batch_chunks]
        metadatas = [chunk.to_dict() for chunk in batch_chunks]
        # content는 document로 저장되므로 metadata에서 제외
        for meta in metadatas:
            meta.pop("content", None)

        retriever.add(
            documents=documents,
            embeddings=batch_embeddings,
            ids=ids,
            metadatas=metadatas,
        )
        print(f"  {i + len(batch_chunks)}/{len(chunks)} 저장됨")

    print(f"\n인덱싱 완료! 총 {len(chunks)}개 청크")
    return True


def test_search():
    """검색 테스트 (LLM 없이)"""
    print("\n" + "=" * 60)
    print("검색 테스트")
    print("=" * 60)

    rag = RAGChain()

    test_queries = [
        "JWT 인증",
        "Redis 캐싱",
        "WebSocket",
    ]

    for query in test_queries:
        print(f"\n질문: {query}")
        print("-" * 40)

        results = rag.search_only(query)
        print(f"검색 결과: {len(results)}개")

        for i, doc in enumerate(results[:3], 1):
            print(f"\n  [{i}] {doc.get('filepath', 'unknown')}")
            print(f"      프로젝트: {doc.get('project')}")
            print(f"      타입: {doc.get('chunk_type')} - {doc.get('name')}")
            print(f"      거리: {doc.get('distance', 0):.4f}")


def test_rag():
    """RAG 전체 테스트"""
    print("\n" + "=" * 60)
    print("RAG 테스트")
    print("=" * 60)

    # LLM 연결 확인
    llm = LLM()
    if not llm._check_connection():
        print("Ollama 서버가 실행 중이지 않습니다.")
        print("ollama serve 명령으로 서버를 시작하세요.")
        return

    rag = RAGChain()

    test_questions = [
        "BizSync에서 JWT 인증 어떻게 구현했어?",
        "Redis는 어디서 사용하고 있어?",
        "Vue 컴포넌트 구조 설명해줘",
    ]

    for question in test_questions:
        print(f"\n{'='*60}")
        print(f"질문: {question}")
        print("=" * 60)

        try:
            result = rag.query(question)

            print(f"\n[답변]\n{result.answer}")

            print(f"\n[소스 ({len(result.sources)}개)]")
            for src in result.sources:
                print(f"  - {src['filepath']}")
                print(f"    ({src['project']}/{src['chunk_type']}: {src['name']})")

        except Exception as e:
            print(f"에러: {e}")

        print()


def test_streaming():
    """스트리밍 테스트"""
    print("\n" + "=" * 60)
    print("스트리밍 테스트")
    print("=" * 60)

    llm = LLM()
    if not llm._check_connection():
        print("Ollama 서버가 실행 중이지 않습니다.")
        return

    rag = RAGChain()
    question = "BizSync 프로젝트 구조 설명해줘"

    print(f"\n질문: {question}")
    print("-" * 40)
    print("답변: ", end="", flush=True)

    try:
        for chunk in rag.query_stream(question):
            print(chunk, end="", flush=True)
        print()
    except OllamaError as e:
        print(f"\n에러: {e}")


def main():
    parser = argparse.ArgumentParser(description="RAG 테스트")
    parser.add_argument("--index", action="store_true", help="코드베이스 인덱싱 실행")
    parser.add_argument("--search", action="store_true", help="검색만 테스트")
    parser.add_argument("--stream", action="store_true", help="스트리밍 테스트")
    args = parser.parse_args()

    if args.index:
        if not index_codebase():
            return

    if args.search:
        test_search()
    elif args.stream:
        test_streaming()
    else:
        test_rag()


if __name__ == "__main__":
    main()
