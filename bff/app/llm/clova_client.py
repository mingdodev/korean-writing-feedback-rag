import json
from typing import Any, Dict, List, Literal, Type, TypeVar

import httpx
from pydantic import BaseModel

from ..core.config import settings

Role = Literal["system", "user", "assistant"]
Message = Dict[str, str]
T = TypeVar("T", bound=BaseModel)


class ClovaStudioError(Exception):
    pass


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

    # ------------------------------------------------------------------

    # 헬퍼 메소드

    def _buil_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _extract_pydantic_schema(model: Type[BaseModel]) -> Dict[str, Any]:
        if hasattr(model, "model_json_schema"):
            schema = model.model_json_schema()
        else:
            raise TypeError("response_model은 Pydantic BaseModel을 상속해야 합니다.")

        properties: Dict[str, Any] = schema.get("properties", {}) or {}
        required: List[str] = list(properties.keys())

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

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

    # Structed Output 기반 API 요청 메서드

    async def chat_structred(
        self,
        messages: List[Message],
        response_model: Type[T],
        top_p: float = 0.8,
        top_k: int = 0,
        max_completion_tokens: int = 512,
        temperature: float = 0.5,
        repetition_penalty: float = 1.1,
    ) -> T:
        
        schema = self._extract_pydantic_schema(response_model)

        payload: Dict[str, Any] = {
            "messages": messages,
            "topP": top_p,
            "topK": top_k,
            "maxCompletionTokens": max_completion_tokens,
            "temperature": temperature,
            "repetitionPenalty": repetition_penalty,
            "responseFormat": {
                "type": "json",
                "schema": schema,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.url,
                headers=self._buil_headers(),
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        
        self._check_status(body)

        content_str: str = body["result"]["message"]["content"]

        try:
            content_dict = json.loads(content_str)
        except json.JSONDecodeError as e:
            raise ClovaStudioError(f"응답 content를 JSON으로 파싱할 수 없습니다: {e}\ncontent={content_str!r}")

        if hasattr(response_model, "model_validate"):
            return response_model.model_validate(content_dict)
