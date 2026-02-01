"""Ollama LLM 연동 서비스

Ollama REST API를 통해 로컬 LLM과 통신
스트리밍 응답 및 에러 핸들링 지원
"""

import httpx
import json
from typing import Generator, Optional
from dataclasses import dataclass

from config import get_settings


@dataclass
class LLMResponse:
    """LLM 응답 데이터"""
    content: str
    model: str
    done: bool
    total_duration: Optional[int] = None
    eval_count: Optional[int] = None


class OllamaError(Exception):
    """Ollama 관련 에러"""
    pass


# 커넥션 풀링을 위한 전역 클라이언트
_http_client: Optional[httpx.Client] = None


def get_http_client(timeout: float = 120.0) -> httpx.Client:
    """커넥션 풀링된 HTTP 클라이언트 반환"""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.Client(
            timeout=timeout,
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
                keepalive_expiry=30.0,
            ),
        )
    return _http_client


def close_http_client():
    """HTTP 클라이언트 종료 (앱 종료시 호출)"""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        _http_client.close()
        _http_client = None


class LLM:
    """Ollama LLM 클라이언트 (커넥션 풀링 지원)"""

    def __init__(
        self,
        model: str = None,
        base_url: str = None,
        timeout: float = None,
    ):
        settings = get_settings()
        model = model or settings.ollama_model
        base_url = base_url or settings.ollama_base_url
        timeout = timeout or settings.ollama_timeout
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    def _get_client(self) -> httpx.Client:
        """커넥션 풀링된 클라이언트 반환"""
        return get_http_client(self.timeout)

    def _check_connection(self) -> bool:
        """Ollama 서버 연결 확인"""
        try:
            client = self._get_client()
            response = client.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except httpx.RequestError:
            return False

    def _check_model_available(self) -> bool:
        """모델 사용 가능 여부 확인"""
        try:
            client = self._get_client()
            response = client.get(f"{self.base_url}/api/tags", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                # 모델명 매칭 (태그 포함/미포함 모두 확인)
                return any(
                    self.model in m or m.startswith(self.model.split(":")[0])
                    for m in models
                )
        except httpx.RequestError:
            pass
        return False

    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """동기식 텍스트 생성"""
        if not self._check_connection():
            raise OllamaError("Ollama 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            client = self._get_client()
            response = client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )

            if response.status_code != 200:
                raise OllamaError(f"Ollama API 에러: {response.status_code} - {response.text}")

            data = response.json()
            return LLMResponse(
                content=data.get("response", ""),
                model=data.get("model", self.model),
                done=data.get("done", True),
                total_duration=data.get("total_duration"),
                eval_count=data.get("eval_count"),
            )

        except httpx.TimeoutException:
            raise OllamaError(f"Ollama 요청 타임아웃 ({self.timeout}초)")
        except httpx.RequestError as e:
            raise OllamaError(f"Ollama 요청 실패: {str(e)}")

    def generate_stream(self, prompt: str, system_prompt: str = "") -> Generator[str, None, None]:
        """스트리밍 텍스트 생성"""
        if not self._check_connection():
            raise OllamaError("Ollama 서버에 연결할 수 없습니다.")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            # 스트리밍은 별도 클라이언트 사용 (연결 유지 문제)
            with httpx.Client(timeout=self.timeout) as stream_client:
                with stream_client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        raise OllamaError(f"Ollama API 에러: {response.status_code}")

                    for line in response.iter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue

        except httpx.TimeoutException:
            raise OllamaError(f"스트리밍 타임아웃 ({self.timeout}초)")
        except httpx.RequestError as e:
            raise OllamaError(f"스트리밍 요청 실패: {str(e)}")

    def chat(
        self,
        messages: list[dict],
        system_prompt: str = "",
        stream: bool = False,
    ) -> LLMResponse | Generator[str, None, None]:
        """채팅 형식 대화"""
        if not self._check_connection():
            raise OllamaError("Ollama 서버에 연결할 수 없습니다.")

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }

        if system_prompt:
            # 시스템 메시지를 맨 앞에 추가
            payload["messages"] = [
                {"role": "system", "content": system_prompt}
            ] + messages

        try:
            if stream:
                return self._chat_stream(payload)
            else:
                return self._chat_sync(payload)

        except httpx.TimeoutException:
            raise OllamaError(f"채팅 요청 타임아웃 ({self.timeout}초)")
        except httpx.RequestError as e:
            raise OllamaError(f"채팅 요청 실패: {str(e)}")

    def _chat_sync(self, payload: dict) -> LLMResponse:
        """동기식 채팅"""
        client = self._get_client()
        response = client.post(
            f"{self.base_url}/api/chat",
            json=payload,
        )

        if response.status_code != 200:
            raise OllamaError(f"채팅 API 에러: {response.status_code}")

        data = response.json()
        message = data.get("message", {})

        return LLMResponse(
            content=message.get("content", ""),
            model=data.get("model", self.model),
            done=data.get("done", True),
            total_duration=data.get("total_duration"),
            eval_count=data.get("eval_count"),
        )

    def _chat_stream(self, payload: dict) -> Generator[str, None, None]:
        """스트리밍 채팅 (별도 클라이언트 사용)"""
        with httpx.Client(timeout=self.timeout) as stream_client:
            with stream_client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
            ) as response:
                if response.status_code != 200:
                    raise OllamaError(f"채팅 스트리밍 에러: {response.status_code}")

                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            message = data.get("message", {})
                            if "content" in message:
                                yield message["content"]
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue


# =============================================================================
# 테스트
# =============================================================================

if __name__ == "__main__":
    llm = LLM()

    # 연결 확인
    print(f"Ollama 연결 상태: {llm._check_connection()}")
    print(f"모델 ({llm.model}) 사용 가능: {llm._check_model_available()}")

    # 간단한 테스트
    try:
        print("\n=== 동기 생성 테스트 ===")
        response = llm.generate("1 + 1 = ?")
        print(f"응답: {response.content}")

        print("\n=== 스트리밍 테스트 ===")
        print("응답: ", end="", flush=True)
        for chunk in llm.generate_stream("파이썬이란?"):
            print(chunk, end="", flush=True)
        print()

    except OllamaError as e:
        print(f"에러: {e}")
