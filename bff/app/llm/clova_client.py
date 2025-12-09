import json
from typing import Any, Dict, List, Literal, Type, TypeVar

import httpx
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from aiolimiter import AsyncLimiter

from ..core.config import settings

Role = Literal["system", "user", "assistant"]
Message = Dict[str, str]
T = TypeVar("T", bound=BaseModel)


class ClovaStudioError(Exception):
    pass

def is_rate_limit_error(exception: BaseException) -> bool:
    """HTTP 429 에러일 때만 재시도하기 위한 확인 함수"""
    return (
        isinstance(exception, httpx.HTTPStatusError) and
        exception.response.status_code == 429
    )

class ClovaStudioClient:

    def __init__(
        self,
        api_key: str = settings.CLOVA_API_KEY,
        url: str = settings.CLOVA_URL,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.url = url
        self.timeout = timeout
        # 분당 60회로 요청 속도 제한 (QPM 60)
        self.limiter = AsyncLimiter(60, 60)

    # ------------------------------------------------------------------

    # 헬퍼 메소드

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _extract_pydantic_schema(model: Type[BaseModel]) -> Dict[str, Any]:
        if hasattr(model, "model_json_schema"):
            return model.model_json_schema()
        else:
            raise TypeError("response_model은 Pydantic BaseModel을 상속해야 합니다.")

    @staticmethod
    def _check_status(body: Dict[str, Any]) -> None:
        status = body.get("status") or {}
        code = status.get("code")
        message = status.get("message")

        if code != "20000":
            raise ClovaStudioError(
                f"Clova Studio error: code={code}, message={message}"
            )

    # ------------------------------------------------------------------

    # 일반 API 요청 메서드

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(3),
        retry=retry_if_exception(is_rate_limit_error)
    )
    async def chat(
        self,
        messages: List[Message],
        top_p: float = 1.0,
        top_k: int = 0,
        max_completion_tokens: int = 1024,
        temperature: float = 0.1,
        repetition_penalty: float = 1.,
    ) -> str:

        payload: Dict[str, Any] = {
            "messages": messages,
            "topP": top_p,
            "topK": top_k,
            "maxCompletionTokens": max_completion_tokens,
            "temperature": temperature,
            "repetitionPenalty": repetition_penalty,
        }
        
        try:
            async with self.limiter:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        self.url,
                        headers=self._build_headers(),
                        json=payload,
                    )
                    resp.raise_for_status()
                    body = resp.json()

        except httpx.HTTPStatusError as e:
            print("\n" + "#"*50)
            print("[CLOVA API ERROR (HTTP Status Error)]")
            print(f"Status: {e.response.status_code}")
            print(f"Response Body:\n{e.response.text}")
            print("#"*50 + "\n")
            raise
        except Exception as e:
            print(f"An unexpected error occurred during Clova Studio API request: {e}")
            raise

        self._check_status(body)

        content: str = body["result"]["message"]["content"]

        return content

    # ------------------------------------------------------------------

    # Structed Output 기반 API 요청 메서드

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(3),
        retry=retry_if_exception(is_rate_limit_error)
    )
    async def chat_structred(
        self,
        messages: List[Message],
        response_model: Type[T],
        top_p: float = 1.0,
        top_k: int = 0,
        max_completion_tokens: int = 1024,
        temperature: float = 0.1,
        repetition_penalty: float = 1.,
    ) -> T:

        schema = self._extract_pydantic_schema(response_model)

        payload: Dict[str, Any] = {
            "messages": messages,
            "topP": top_p,
            "topK": top_k,
            "maxCompletionTokens": max_completion_tokens,
            "temperature": temperature,
            "repetitionPenalty": repetition_penalty,
            "thinking": {"effort": "none"},
            "responseFormat": {
                "type": "json",
                "schema": schema,
            },
        }

        try:
            async with self.limiter:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.url,
                        headers=self._build_headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    body = response.json()

        except httpx.HTTPStatusError as e:
            print("\n" + "#"*50)
            print("[CLOVA API ERROR (HTTP Status Error)]")
            print(f"Status: {e.response.status_code}")
            print(f"Response Body:\n{e.response.text}")
            print("#"*50 + "\n")
            raise
        except Exception as e:
            print(f"An unexpected error occurred during Clova Studio API request: {e}")
            raise

        self._check_status(body)

        content_str: str = body["result"]["message"]["content"]

        try:
            content_dict = json.loads(content_str)
        except json.JSONDecodeError as e:
            raise ClovaStudioError(
                f"응답 content를 JSON으로 파싱할 수 없습니다: {e}\ncontent={content_str!r}"
            )

        if hasattr(response_model, "model_validate"):
            return response_model.model_validate(content_dict)
