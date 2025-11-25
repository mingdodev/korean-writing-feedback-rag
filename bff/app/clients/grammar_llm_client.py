from pydantic import BaseModel
from typing import Dict, Type, Any
from ..schemas.feedback_response import CorrectionOutput, GrammarFeedback
from ..llm.clova_client import ClovaStudioClient

SYSTEM_PROMPT_CORRECTION = """
당신은 한국어 학습자의 문장을 자연스럽고 정확하게 교정하는 전문가입니다.

## 역할
- 사용자가 작성한 문장을 읽고, 의미는 유지하면서 자연스럽고 문법적으로 올바른 문장으로 교정합니다.
- 추가로, 이 문장에서 교정된 문법 요소/형태(조사, 어미, 연결어미, 높임 표현 등)를 간단한 단어/구 단위로 나열합니다.

## 출력 형식
- corrected_sentence: 최종 교정된 문장 전체
- errors: 교정 과정에서 중심이 된 문법 요소/형태의 간단한 이름 목록
    - 예시: ["과", "이", "-어야 하다"]
"""

SYSTEM_PROMPT_GRAMMAR_FEEDBACK = """
당신은 한국어 학습자를 위한 문법 피드백을 제공하는 전문가입니다.

## 입력으로 주어지는 정보
- original_sentence: 학습자가 실제로 작성한 문장
- corrected_sentence: 자연스럽고 문법적으로 올바르게 교정된 문장
- grammar_db_info: 이 문장과 관련된 문법 요소와 설명 목록

## 역할
1. original_sentence와 corrected_sentence를 비교하여, 어떤 표현이 어떻게 교정되었는지 파악합니다.
2. grammar_db_info를 참고하여, 각 교정이 어떤 문법 요소와 관련이 있는지, 왜 그런지 학습자가 이해하기 쉽도록 설명합니다.
3. 한 문장 안에 여러 개의 교정이 있을 수 있으므로, 각 교정에 대해 별도의 항목으로 정리합니다.

## 출력 형식 (내부 모델)
- corrected_sentence: 최종 교정된 문장 전체 (입력으로 받은 corrected_sentence를 기반으로 합니다)
- feedbacks: 배열
  - 각 요소는 다음 필드를 가집니다.
    - corrects: "틀린표현 -> 맞은표현" 형식의 문자열
    - reason: 해당 교정이 필요한 이유, 관련 문법 설명

## 주의사항
- 같은 교정을 중복해서 나열하지 마세요.
- 학습자에게 직접 말하듯이, 지나치게 어려운 용어보다는 예시와 함께 쉽게 설명하세요.
- grammar_db_info가 비어 있어도, 문장 비교만으로 합리적인 설명을 작성하세요.
"""

class GrammarLLMClient:

    def __init__(self, llm: ClovaStudioClient):
        self.llm = llm

    async def get_corrected_sentence(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        original_sentence = payload["original_sentence"]
        error_examples = payload.get("error_examples", [])

        user_content = (
            "다음은 한국어 학습자가 작성한 문장과, 유사한 오류를 포함한 예문들입니다.\n\n"
            f"### 학습자 문장\n{original_sentence}\n\n"
            f"### 유사 오류 예문(error_examples)\n{error_examples}\n\n"
            "위 정보를 참고하여, 학습자 문장을 자연스럽고 문법적으로 올바른 문장으로 교정하고,\n"
            "교정 과정에서 중요한 문법 요소/형태를 errors 목록에 담아주세요."
        )

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT_CORRECTION,
            },
            {
                "role": "user",
                "content": user_content,
            },
        ]

        result: CorrectionOutput = await self.llm.chat_structred(
            messages=messages,
            response_model=CorrectionOutput,
        )

        return result.model_dump()

    async def get_grammar_feedback(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        original_sentence = payload["original_sentence"]
        corrected_sentence = payload["corrected_sentence"]
        grammar_db_info = payload.get("grammar_db_info", [])

        user_content = (
            f"### 학습자 문장 (original_sentence)\n{original_sentence}\n\n"
            f"### 교정된 문장 (corrected_sentence)\n{corrected_sentence}\n\n"
            f"### 관련 문법 정보 (grammar_db_info)\n{grammar_db_info}\n\n"
            "위 정보를 바탕으로, 한 문장 안에 존재하는 여러 교정을 각각 정리해 주세요.\n"
            "- 각 교정에 대해 '틀린표현 -> 맞은표현' 형식의 corrects와,\n"
            "  왜 그렇게 고쳐야 하는지에 대한 reason을 작성합니다.\n"
            "- 최종 출력은 내부 모델 GrammarFeedback 형식에 맞게 생성합니다."
        )

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT_GRAMMAR_FEEDBACK,
            },
            {
                "role": "user",
                "content": user_content,
            },
        ]

        result: GrammarFeedback = await self.llm.chat_structred(
            messages=messages,
            response_model=GrammarFeedback,
        )

        return result.model_dump()