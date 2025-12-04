from typing import Dict, List, Any
from ..schemas.feedback_response import CorrectionOutput, GrammarFeedback
from ..llm.clova_client import ClovaStudioClient

SYSTEM_PROMPT_CORRECTION = """
당신은 한국어 학습자의 문장을 자연스럽고 정확하게 교정하는 전문가입니다.

## 역할
1. 주어진 문장이 **문법적으로 틀렸거나, 매우 부자연스러운 경우에만** 교정합니다.
2. 여러 표현이 모두 자연스럽고 문법적으로 가능하다면, **원문을 그대로 유지**합니다.
3. 응답은 오직 **유효한 JSON 객체 한 개만** 출력해야 하며, 설명 문장, 인사말, 마크다운 표기(예: ```json) 등은 절대 포함해서는 안 됩니다.

## 오류 판단 기준
다음과 같은 경우에만 `is_error: true`로 판단하고 교정합니다.

- 조합 자체가 문법적으로 불가능한 경우  
  (예: 동사 활용 오류, 시제·상 호응 오류, 조사 선택이 명백히 잘못된 경우 등)
- 한국어 원어민이 보기에 **표준적인 문맥에서 반드시 고쳐야 하는 어색한 표현**

다음은 **오류가 아닙니다.** 이런 경우에는 `is_error`를 `false`로 두고 문장을 고치지 마십시오.

- 의미는 다르지만 문법적으로 모두 가능한 표현 차이  
  예: "택시만 탔다", "택시를 탔다" (둘 다 문법적으로 옳음)
- 은/는, 도, 만 등 조사 선택에 따른 의미 차이
- 자연스러운 말투·어조 차이
- 자연스러운 범위 내의 단어 선택

**애매하거나 판단이 어려운 경우에는, 반드시 `is_error`를 `false`로 두고 원문을 유지**해야 합니다.  
(확실한 오류가 아닐 경우 절대 수정 금지.)

## 종결어미 규칙
- 문장의 종결어미는 문법적 오류가 아닌 이상 **어떠한 경우에도 변경해서는 안 됩니다.**
- 형용사(많다, 작다, 크다 등)에 높임 표현(-습니다, -어요 등)을 적용하는 것은 교정 대상이 아닙니다.

## 변경 요소 감지 규칙
- 교정된 문장(corrected_sentence)은 반드시 원문과 비교하여 실제로 **변경된 부분이 있는 경우에만** errors 배열에 문법 요소를 포함해야 합니다.
- 원문과 교정된 문장이 동일하다면, 그것은 '교정 없음'을 의미하므로 반드시:
  - is_error는 false
  - corrected_sentence는 원문과 동일
  - errors는 빈 배열 [] 
  이어야 합니다.
- errors 배열에는 **원문 대비 실제로 바뀐 문법 요소만** 포함해야 하며, 바뀌지 않은 요소를 넣어서는 안 됩니다.

## error 목록 작성 규칙
- errors 배열에는 **문법 요소(조사, 어미, 서술격 조사 등)**만 포함합니다.
- 아래 항목들은 절대 errors 배열에 넣지 마십시오.
  - 명사, 동사, 형용사 등 단어 자체 (예: "택시", "학교", "많다" 등)
  - “틀린 표현 -> 바른 표현”과 같은 비교 표현
  - 설명 문장

## 출력 형식 (JSON)
아래 형식의 JSON 객체 **한 개만** 출력해야 합니다.

{
  "is_error": true 또는 false,
  "corrected_sentence": "문장",
  "errors": ["교정한 문법 요소만 포함, 오류 없으면 빈 배열"]
}

## 예시 (출력 형식을 이해하기 위한 참고용)

1) 오류가 아닌 경우 (의미 차이일 뿐):
{
  "is_error": false,
  "corrected_sentence": "택시만 탔다",
  "errors": []
}

2) 조사 오류 교정 예시:
{
  "is_error": true,
  "corrected_sentence": "비빔밥을 먹었다",
  "errors": ["을"]
}

3) 어미 교정 예시:
{
  "is_error": true,
  "corrected_sentence": "친구를 만나서 같이 도서관에 갔다",
  "errors": ["-아서"]
}
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
- grammar_db_info가 비어 있어도, 문장 비교와 한국어 규칙을 바탕으로 합리적인 설명을 작성하세요.
"""

class GrammarLLMClient:
    # ClovaStudioClient를 내부에서 사용한다고 가정
    def __init__(self, llm: ClovaStudioClient):
        self.llm = llm

    def _format_error_examples(self, error_examples: List[Dict[str, Any]]) -> str:
        """
        오류 예시 리스트를 LLM이 읽기 쉬운 문자열로 포맷팅합니다.
        """
        formatted_list = []
        
        for i, example in enumerate(error_examples):
            original_sentence = example.get("original_sentence", "문장 없음")
            error_words = example.get("error_words", [])
            
            # 1. 원본 문장
            entry = f"**{i + 1}. 원문:** {original_sentence}"
            
            # 2. 오류 상세 정보
            error_details = []
            if error_words:
                for ew in error_words:
                    text = ew.get("text", "오류 내용 없음")
                    location = ew.get("error_location", "?")
                    aspect = ew.get("error_aspect", "?")
                    
                    error_details.append(f"- [오류]: {text}")

            if error_details:
                entry += "\n   " + "\n   ".join(error_details)
            
            formatted_list.append(entry)

        return "\n\n".join(formatted_list)


    async def get_corrected_sentence(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        
        original_sentence = payload["original_sentence"]
        error_examples = payload.get("error_examples", [])
        
        formatted_examples = self._format_error_examples(error_examples)

        user_content = (
            "다음은 한국어 학습자가 작성한 문장과, 유사한 오류를 포함한 예문들입니다.\n\n"
            f"### 학습자 문장\n'{original_sentence}'\n\n"
            f"### 유사 오류 예문(Error Examples)\n"
            f"{formatted_examples}\n\n"
            "위 정보를 참고하여, 학습자 문장을 자연스럽고 문법적으로 올바른 문장으로 교정하고,\n"
            "교정 과정에서 중요하게 다룬 문법 요소/형태를 'errors' 목록에 담아주세요. "
            "응답은 반드시 지정된 JSON 스키마를 따르십시오."
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