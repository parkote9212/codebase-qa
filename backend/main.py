"""Codebase QA API

FastAPI 기반 코드베이스 Q&A 서버
"""

import json
from pathlib import Path
from datetime import datetime
from threading import Lock

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from schemas import (
    IndexRequest,
    IndexResponse,
    QueryRequest,
    QueryResponse,
    SourceInfo,
    StatusResponse,
    ProjectStats,
    DeleteResponse,
    ModelInfo,
    ModelsResponse,
    SwitchModelRequest,
    SwitchModelResponse,
    IndexProgressResponse,
)
from services import Embedder, Retriever, LLM, RAGChain, OllamaError
from services.llm import close_http_client
from utils.code_parser import scan_files, parse_file, CODE_BASE_PATH
from config import get_settings


# =============================================================================
# 앱 설정
# =============================================================================

# Swagger 리스트에서 보일 태그 그룹 (순서·설명)
OPENAPI_TAGS = [
    {"name": "기본", "description": "헬스체크 등 서버 기본 API"},
    {"name": "모델 관리", "description": "Ollama 모델 목록 조회·변경"},
    {"name": "인덱싱", "description": "코드베이스 스캔·벡터 DB 저장·진행률·삭제"},
    {"name": "질의", "description": "RAG 질문/답변 (일반·스트리밍)"},
    {"name": "상태", "description": "Ollama 연결·인덱스 현황 조회"},
]

app = FastAPI(
    title="Codebase QA API",
    description="코드베이스 RAG 기반 Q&A 시스템. 코드 경로를 인덱싱한 뒤 질문하면 관련 코드를 검색해 LLM이 답변합니다.",
    version="1.0.0",
    openapi_tags=OPENAPI_TAGS,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 서비스 인스턴스 (lazy loading)
_embedder = None
_retriever = None
_llm = None
_rag_chain = None

# 인덱싱 진행 상태
_index_progress = {
    "is_indexing": False,
    "project": None,
    "current": 0,
    "total": 0,
    "percent": 0,
    "stage": "",
    "cancelled": False,
}
_index_lock = Lock()

# 로그 파일 경로
LOG_FILE = Path(__file__).parent.parent / "data" / "query_logs.jsonl"


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def get_llm() -> LLM:
    global _llm
    if _llm is None:
        _llm = LLM()
    return _llm


def get_rag_chain() -> RAGChain:
    global _rag_chain
    if _rag_chain is None:
        _rag_chain = RAGChain(
            retriever=get_retriever(),
            embedder=get_embedder(),
            llm=get_llm(),
        )
    return _rag_chain


def log_query(question: str, answer: str, model: str):
    """질문/답변 로그 저장"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "answer": answer,
        "model": model,
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def update_progress(stage: str, current: int, total: int, project: str = None):
    """인덱싱 진행률 업데이트"""
    global _index_progress
    with _index_lock:
        _index_progress = {
            "is_indexing": True,
            "project": project,
            "current": current,
            "total": total,
            "percent": int((current / total * 100) if total > 0 else 0),
            "stage": stage,
        }


def clear_progress():
    """인덱싱 진행률 초기화"""
    global _index_progress
    with _index_lock:
        _index_progress = {
            "is_indexing": False,
            "project": None,
            "current": 0,
            "total": 0,
            "percent": 0,
            "stage": "",
            "cancelled": False,
        }


def is_cancelled() -> bool:
    """인덱싱 취소 여부 확인"""
    with _index_lock:
        return _index_progress.get("cancelled", False)


# =============================================================================
# 앱 이벤트
# =============================================================================

@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료시 리소스 정리"""
    close_http_client()


# =============================================================================
# 헬스체크
# =============================================================================

@app.get(
    "/api/health",
    tags=["기본"],
    summary="헬스체크",
    description="서버 동작 여부 확인. 정상이면 `status: ok` 반환.",
)
async def health():
    return {"status": "ok"}


# =============================================================================
# 디렉토리 탐색
# =============================================================================

@app.get(
    "/api/browse",
    tags=["기본"],
    summary="디렉토리 목록 조회",
    description="지정한 경로의 하위 디렉토리 목록을 반환합니다. 쿼리 파라미터: path 또는 name (동일). 허용된 경로 내에서만 탐색 가능합니다.",
)
async def browse_directory(path: str = None, name: str = None):
    """디렉토리 탐색 API (path 또는 name 쿼리 파라미터)"""
    # path / name 둘 다 받기 (일부 클라이언트가 name으로 보냄)
    path = path or name
    if path is None:
        path = settings.allowed_browse_paths_list[0] if settings.allowed_browse_paths_list else "/Users/gcpark/code"

    target_path = Path(path)

    # 경로 보안 검증
    if not settings.is_path_allowed(str(target_path)):
        raise HTTPException(
            status_code=403,
            detail=f"접근이 허용되지 않은 경로입니다. 허용된 경로: {', '.join(settings.allowed_browse_paths_list)}"
        )

    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"경로가 존재하지 않습니다: {path}")

    if not target_path.is_dir():
        raise HTTPException(status_code=400, detail=f"디렉토리가 아닙니다: {path}")

    # 하위 디렉토리 목록
    directories = []
    try:
        for item in sorted(target_path.iterdir()):
            if item.is_dir() and not item.name.startswith('.'):
                # 코드 프로젝트인지 간단히 확인
                has_code = any(
                    item.glob(f"**/*{ext}")
                    for ext in ['.py', '.java', '.vue', '.js']
                )
                directories.append({
                    "name": item.name,
                    "path": str(item),
                    "has_code": has_code if has_code else False,
                })
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"접근 권한이 없습니다: {path}")

    return {
        "current_path": str(target_path),
        "parent_path": str(target_path.parent) if target_path.parent != target_path else None,
        "directories": directories,
    }


# =============================================================================
# 모델 관리
# =============================================================================

@app.get(
    "/api/models",
    response_model=ModelsResponse,
    tags=["모델 관리"],
    summary="모델 목록 조회",
    description="Ollama에 설치된 LLM 모델 목록과 현재 사용 중인 모델명을 반환합니다.",
)
async def get_models():
    llm = get_llm()

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{llm.base_url}/api/tags")

            if response.status_code != 200:
                raise HTTPException(
                    status_code=503,
                    detail="Ollama 서버에 연결할 수 없습니다"
                )

            data = response.json()
            models = []

            for model in data.get("models", []):
                # 크기 포맷팅
                size_bytes = model.get("size", 0)
                if size_bytes > 1e9:
                    size_str = f"{size_bytes / 1e9:.1f}GB"
                else:
                    size_str = f"{size_bytes / 1e6:.1f}MB"

                models.append(ModelInfo(
                    name=model.get("name", "unknown"),
                    size=size_str,
                    modified=model.get("modified_at", "")[:10],
                ))

            return ModelsResponse(
                models=models,
                current=llm.model,
            )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama 연결 오류: {str(e)}"
        )


@app.post(
    "/api/models/switch",
    response_model=SwitchModelResponse,
    tags=["모델 관리"],
    summary="사용 모델 변경",
    description="RAG 답변 생성에 사용할 Ollama 모델을 지정합니다. `qwen2.5:3b` 등 모델명 필요.",
)
async def switch_model(request: SwitchModelRequest):
    global _llm, _rag_chain

    llm = get_llm()
    previous_model = llm.model

    # 모델 존재 확인
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{llm.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                model_names = [m.get("name") for m in data.get("models", [])]

                # 모델명 매칭 (태그 유무 모두 확인)
                model_exists = any(
                    request.model == m or request.model in m or m.startswith(request.model.split(":")[0])
                    for m in model_names
                )

                if not model_exists:
                    raise HTTPException(
                        status_code=404,
                        detail=f"모델을 찾을 수 없습니다: {request.model}"
                    )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama 연결 오류: {str(e)}"
        )

    # 모델 변경
    _llm = LLM(model=request.model)
    _rag_chain = RAGChain(
        retriever=get_retriever(),
        embedder=get_embedder(),
        llm=_llm,
    )

    return SwitchModelResponse(
        status="success",
        previous=previous_model,
        current=request.model,
    )


# =============================================================================
# 인덱싱
# =============================================================================

@app.get(
    "/api/index/progress",
    response_model=IndexProgressResponse,
    tags=["인덱싱"],
    summary="인덱싱 진행률 조회",
    description="현재 인덱싱 중이면 `is_indexing`, `percent`, `stage`(scanning/embedding/storing) 등 진행 상황을 반환합니다.",
)
async def get_index_progress():
    with _index_lock:
        return IndexProgressResponse(**_index_progress)


@app.post(
    "/api/index/cancel",
    tags=["인덱싱"],
    summary="인덱싱 취소",
    description="진행 중인 인덱싱을 취소합니다. 부분적으로 인덱싱된 데이터는 자동 삭제됩니다.",
)
async def cancel_indexing():
    global _index_progress
    with _index_lock:
        if not _index_progress["is_indexing"]:
            return {"status": "not_indexing", "message": "진행 중인 인덱싱이 없습니다."}

        project = _index_progress["project"]
        _index_progress["cancelled"] = True

    return {
        "status": "cancelling",
        "project": project,
        "message": f"인덱싱 취소 요청됨: {project}",
    }


def _sanitize_project_name(name: str) -> str:
    """프로젝트명 검증 및 정제 (path traversal 방지)"""
    import re
    sanitized = re.sub(r'[^a-zA-Z0-9\-_가-힣]', '', name)
    if not sanitized:
        raise HTTPException(status_code=400, detail="유효하지 않은 프로젝트명입니다.")
    return sanitized[:50]


@app.post(
    "/api/index",
    response_model=IndexResponse,
    tags=["인덱싱"],
    summary="코드베이스 인덱싱",
    description="지정한 `code_path` 디렉토리를 스캔해 파싱·임베딩 후 ChromaDB에 저장합니다. `force=true`면 기존 인덱스를 덮어씁니다.",
)
async def index_codebase(request: IndexRequest):
    code_path = Path(request.code_path)

    # 경로 보안 검증
    if not settings.is_path_allowed(str(code_path)):
        raise HTTPException(
            status_code=403,
            detail=f"인덱싱이 허용되지 않은 경로입니다."
        )

    # 경로 검증
    if not code_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"경로가 존재하지 않습니다: {code_path}"
        )

    if not code_path.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"디렉토리가 아닙니다: {code_path}"
        )

    # 프로젝트명 (지정된 경우 사용, 아니면 폴더명) + 검증
    raw_name = request.project_name.strip() if request.project_name else code_path.name
    project_name = _sanitize_project_name(raw_name)

    # 이미 인덱싱 되어 있는지 확인
    retriever = get_retriever()
    if retriever.has_project(project_name) and not request.force:
        existing_count = retriever.count_by_project(project_name)
        return IndexResponse(
            status="skipped",
            project=project_name,
            indexed_files=0,
            chunks=existing_count,
            message=f"이미 인덱싱되어 있습니다 ({existing_count}개 청크). force=true로 재인덱싱하세요.",
        )

    # 기존 인덱스 삭제 (force=true인 경우)
    if request.force:
        retriever.delete_by_project(project_name)

    # 파일 스캔
    update_progress("scanning", 0, 1, project_name)
    files = scan_files(str(code_path))

    if not files:
        clear_progress()
        raise HTTPException(
            status_code=400,
            detail=f"지원하는 파일이 없습니다: {code_path}"
        )

    # 청킹
    all_chunks = []
    total_files = len(files)
    for i, filepath in enumerate(files):
        # 취소 체크
        if is_cancelled():
            retriever.delete_by_project(project_name)
            clear_progress()
            raise HTTPException(
                status_code=499,
                detail=f"인덱싱이 취소되었습니다: {project_name}"
            )

        update_progress("scanning", i + 1, total_files, project_name)
        chunks = parse_file(filepath)
        # 프로젝트명 override (사용자가 지정한 이름 사용)
        for chunk in chunks:
            chunk.project = project_name
        all_chunks.extend(chunks)

    if not all_chunks:
        clear_progress()
        raise HTTPException(
            status_code=400,
            detail="파싱된 청크가 없습니다."
        )

    # 임베딩
    update_progress("embedding", 0, len(all_chunks), project_name)
    embedder = get_embedder()
    contents = [chunk.content for chunk in all_chunks]

    # 배치 임베딩 (진행률 업데이트를 위해 작은 배치로 분할)
    embeddings = []
    embed_batch_size = 32
    for i in range(0, len(contents), embed_batch_size):
        # 취소 체크
        if is_cancelled():
            retriever.delete_by_project(project_name)
            clear_progress()
            raise HTTPException(
                status_code=499,
                detail=f"인덱싱이 취소되었습니다: {project_name}"
            )

        batch = contents[i:i + embed_batch_size]
        batch_embeddings = embedder.embed_batch(batch)
        embeddings.extend(batch_embeddings)
        update_progress("embedding", min(i + embed_batch_size, len(contents)), len(contents), project_name)

    # 벡터 DB에 저장
    update_progress("storing", 0, len(all_chunks), project_name)
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        # 취소 체크
        if is_cancelled():
            retriever.delete_by_project(project_name)
            clear_progress()
            raise HTTPException(
                status_code=499,
                detail=f"인덱싱이 취소되었습니다: {project_name}"
            )

        batch_chunks = all_chunks[i:i + batch_size]
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
        update_progress("storing", min(i + batch_size, len(all_chunks)), len(all_chunks), project_name)

    clear_progress()

    return IndexResponse(
        status="success",
        project=project_name,
        indexed_files=len(files),
        chunks=len(all_chunks),
        message=f"인덱싱 완료: {len(files)}개 파일, {len(all_chunks)}개 청크",
    )


# =============================================================================
# 질의
# =============================================================================

@app.post(
    "/api/query",
    response_model=QueryResponse,
    tags=["질의"],
    summary="RAG 질의 (일반)",
    description="질문과 유사한 코드 청크를 벡터 검색한 뒤, LLM이 맥락을 참고해 답변합니다. `top_k`로 검색 개수(1~20) 조절.",
)
async def query(request: QueryRequest):
    rag_chain = get_rag_chain()
    rag_chain.top_k = request.top_k

    try:
        result = rag_chain.query(request.question)
    except OllamaError as e:
        raise HTTPException(
            status_code=503,
            detail=f"LLM 서비스 오류: {str(e)}"
        )

    # 로그 저장
    log_query(request.question, result.answer, result.model)

    # 소스 정보 변환
    sources = []
    for src in result.sources:
        # 스니펫 생성 (처음 200자)
        snippet = ""
        if "content" in src:
            snippet = src["content"][:200] + "..." if len(src.get("content", "")) > 200 else src.get("content", "")

        sources.append(SourceInfo(
            file=src.get("filepath", "unknown"),
            project=src.get("project", "unknown"),
            chunk_type=src.get("chunk_type", "unknown"),
            name=src.get("name", "unknown"),
            snippet=snippet,
            distance=src.get("distance", 0.0),
        ))

    return QueryResponse(
        answer=result.answer,
        sources=sources,
        model=result.model,
    )


@app.post(
    "/api/query/stream",
    tags=["질의"],
    summary="RAG 질의 (스트리밍)",
    description="답변을 SSE로 토큰 단위 스트리밍. 이벤트: `message`(텍스트), `done`, `error`.",
)
async def query_stream(request: QueryRequest):
    rag_chain = get_rag_chain()
    rag_chain.top_k = request.top_k

    async def generate():
        full_answer = []
        try:
            for chunk in rag_chain.query_stream(request.question):
                full_answer.append(chunk)
                yield {
                    "event": "message",
                    "data": chunk,
                }
            yield {
                "event": "done",
                "data": "[DONE]",
            }

            # 스트리밍 완료 후 로그 저장
            log_query(request.question, "".join(full_answer), get_llm().model)

        except OllamaError as e:
            yield {
                "event": "error",
                "data": str(e),
            }

    return EventSourceResponse(generate())


# =============================================================================
# 상태
# =============================================================================

@app.get(
    "/api/status",
    response_model=StatusResponse,
    tags=["상태"],
    summary="시스템 상태 조회",
    description="Ollama 연결 여부, 현재 모델명, 인덱싱된 프로젝트별 청크 수·언어 통계를 반환합니다.",
)
async def status():
    llm = get_llm()
    retriever = get_retriever()

    # Ollama 연결 확인
    ollama_connected = llm._check_connection()

    # 프로젝트별 통계
    project_stats = retriever.get_project_stats()
    total_chunks = sum(p["chunks"] for p in project_stats)

    projects = [
        ProjectStats(
            project=p["project"],
            chunks=p["chunks"],
            languages=p["languages"],
        )
        for p in project_stats
    ]

    return StatusResponse(
        ollama_connected=ollama_connected,
        ollama_model=llm.model,
        total_chunks=total_chunks,
        projects=projects,
    )


# =============================================================================
# 삭제
# =============================================================================

@app.delete(
    "/api/index/{project_name}",
    response_model=DeleteResponse,
    tags=["인덱싱"],
    summary="프로젝트 인덱스 삭제",
    description="지정한 프로젝트명의 벡터 인덱스를 삭제합니다. 경로가 아닌 프로젝트 폴더명(예: BizSync)을 넣으세요.",
)
async def delete_index(project_name: str):
    retriever = get_retriever()

    # 존재 확인
    if not retriever.has_project(project_name):
        raise HTTPException(
            status_code=404,
            detail=f"프로젝트를 찾을 수 없습니다: {project_name}"
        )

    deleted_count = retriever.delete_by_project(project_name)

    return DeleteResponse(
        status="success",
        project=project_name,
        deleted_chunks=deleted_count,
        message=f"삭제 완료: {deleted_count}개 청크",
    )


# =============================================================================
# 개발 서버 실행
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
