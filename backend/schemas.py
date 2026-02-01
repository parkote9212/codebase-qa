"""API 요청/응답 스키마"""

from pydantic import BaseModel, Field, model_validator
from typing import Optional, Any


# =============================================================================
# 인덱싱
# =============================================================================

class IndexRequest(BaseModel):
    """인덱싱 요청 (code_path/codePath/path, project_name/projectName/name 모두 허용)"""
    code_path: str = Field(..., description="인덱싱할 코드 경로")
    project_name: Optional[str] = Field(default=None, description="프로젝트명")
    force: bool = Field(default=False, description="강제 재인덱싱")

    @model_validator(mode="before")
    @classmethod
    def accept_path_and_name_aliases(cls, data: Any) -> Any:
        """path/codePath → code_path, name/projectName → project_name (클라이언트 변형 대응)"""
        if not isinstance(data, dict):
            return data
        d = dict(data)
        code_path = d.get("code_path") or d.get("codePath") or d.get("path")
        project_name = d.get("project_name") or d.get("projectName") or d.get("name")
        if code_path is not None:
            d["code_path"] = code_path
        if project_name is not None:
            d["project_name"] = project_name
        return d

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [
                {"code_path": "/Users/gcpark/code/BizSync", "project_name": "BizSync", "force": False}
            ]
        }
    }


class IndexResponse(BaseModel):
    """인덱싱 응답"""
    status: str = Field(description="success | skipped")
    project: str = Field(description="프로젝트 폴더명")
    indexed_files: int = Field(description="인덱싱된 파일 수")
    chunks: int = Field(description="저장된 청크 수")
    message: str = Field(description="결과 메시지")


# =============================================================================
# 질의
# =============================================================================

class QueryRequest(BaseModel):
    """질의 요청"""
    question: str = Field(..., description="질문")
    top_k: int = Field(5, description="검색할 문서 수", ge=1, le=20)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"question": "JWT 인증 로직 설명해줘", "top_k": 5}
            ]
        }
    }


class SourceInfo(BaseModel):
    """검색된 코드 청크 정보"""
    file: str = Field(description="파일 경로")
    project: str = Field(description="프로젝트명")
    chunk_type: str = Field(description="함수 | 클래스 | script 등")
    name: str = Field(description="청크 이름(함수명 등)")
    snippet: str = Field(description="코드 미리보기")
    distance: float = Field(description="유사도 거리(작을수록 유사)")


class QueryResponse(BaseModel):
    """질의 응답"""
    answer: str = Field(description="LLM 답변")
    sources: list[SourceInfo] = Field(description="참조된 코드 청크 목록")
    model: str = Field(description="사용된 Ollama 모델명")


# =============================================================================
# 상태
# =============================================================================

class ProjectStats(BaseModel):
    """프로젝트별 통계"""
    project: str = Field(description="프로젝트명")
    chunks: int = Field(description="청크 수")
    languages: dict[str, int] = Field(description="언어별 파일 수")


class StatusResponse(BaseModel):
    """상태 응답"""
    ollama_connected: bool = Field(description="Ollama 연결 여부")
    ollama_model: str = Field(description="현재 사용 모델")
    total_chunks: int = Field(description="전체 청크 수")
    projects: list[ProjectStats] = Field(description="프로젝트별 통계")


# =============================================================================
# 삭제
# =============================================================================

class DeleteResponse(BaseModel):
    """삭제 응답"""
    status: str = Field(description="success")
    project: str = Field(description="삭제된 프로젝트명")
    deleted_chunks: int = Field(description="삭제된 청크 수")
    message: str = Field(description="결과 메시지")


# =============================================================================
# 모델
# =============================================================================

class ModelInfo(BaseModel):
    """Ollama 모델 정보"""
    name: str = Field(description="모델명(예: qwen2.5:3b)")
    size: str = Field(description="용량(예: 1.9GB)")
    modified: str = Field(description="수정일(YYYY-MM-DD)")


class ModelsResponse(BaseModel):
    """모델 목록 응답"""
    models: list[ModelInfo] = Field(description="설치된 모델 목록")
    current: str = Field(description="현재 RAG에서 사용 중인 모델")


class SwitchModelRequest(BaseModel):
    """모델 변경 요청"""
    model: str = Field(..., description="변경할 모델명 (예: qwen2.5:3b)")


class SwitchModelResponse(BaseModel):
    """모델 변경 응답"""
    status: str = Field(description="success")
    previous: str = Field(description="이전 모델명")
    current: str = Field(description="변경된 모델명")


# =============================================================================
# 인덱싱 진행률
# =============================================================================

class IndexProgressResponse(BaseModel):
    """인덱싱 진행률 응답"""
    is_indexing: bool = Field(description="인덱싱 진행 중 여부")
    project: Optional[str] = Field(None, description="대상 프로젝트명")
    current: int = Field(0, description="현재 처리 수")
    total: int = Field(0, description="전체 수")
    percent: int = Field(0, description="진행률 0~100")
    stage: str = Field("", description="scanning | embedding | storing")
