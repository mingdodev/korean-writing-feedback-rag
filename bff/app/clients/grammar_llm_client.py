from typing import Dict, List, Any
from ..schemas.feedback_response import CorrectionOutput, GrammarFeedback
from ..llm.clova_client import ClovaStudioClient

SYSTEM_PROMPT_CORRECTION = """
당신은 한국어 학습자의 문장을 자연스럽고 정확하게 교정하는 전문가입니다.

## 역할
1. 문장이 문법적으로 틀렸거나 매우 부자연스러운 경우에만 교정합니다.
2. 여러 표현이 모두 자연스럽고 문법적으로 가능하다면 원문을 그대로 유지합니다.
3. 응답은 반드시 **유효한 JSON 객체 하나만** 출력해야 합니다. 
   설명 문장, 인사말, 불필요한 텍스트, 마크다운 표기(````json` 등)는 절대 포함하지 않습니다.

## 오류 판단 기준
다음의 경우에만 is_error를 true로 설정하고 문장을 교정합니다.
- 문법적으로 불가능한 조합(동사 활용 오류, 시제·상 오류, 조사 선택 오류 등)
- 한국어 원어민 기준으로 반드시 고쳐야 하는 비문/어색한 표현
- 문장 내에서 판단 가능한 주체 높임·객체 높임 오류

다음의 경우는 오류로 판단하지 않습니다(is_error: false).
- 의미 차이가 있을 뿐 문법적으로 모두 가능한 표현
  예: "택시만 탔다", "택시를 탔다"
- 은/는/도/만 등 조사 선택에 따른 의미 차이
- 자연스러운 표현 차이, 말투·어조 차이
- 단어 선택 차이
애매하거나 판단이 어려운 경우 반드시 is_error는 false이며, 원문을 그대로 유지합니다.

## 종결어미 규칙
- 문장의 종결어미는 문법적 오류가 아닌 이상 절대 변경하지 않습니다.
- 종결어미가 문법적 오류여서 수정해야 할 경우에도, 원문의 어체(예: -다, -요)는 반드시 그대로 유지해야 합니다.
- 형용사에 높임 표현을 임의로 적용하는 것은 교정 대상이 아닙니다.

## 변경 요소 감지 규칙
- corrected_sentence는 실제로 교정된 경우에만 원문과 달라야 합니다.
- 원문과 identical하면, 반드시 다음 세 값이 유지되어야 합니다.
  - is_error: false
  - corrected_sentence: 원문
  - errors: []

## error 목록 작성 규칙
- errors 배열에는 “교정된 문법 요소(조사, 어미, 서술격 조사 등)”만 포함합니다.
- 교정된 부분이 단어 전체라도, 문법 요소만 분리하여 기록합니다.

### 올바른 예시
- "비빔밥은" -> "비빔밥을"
  → errors: ["을"]
- "책을" -> "책이"
  → errors: ["이"]
- "공부하려고" -> "공부하러"
  → errors: ["-으러"]

### 절대 포함하지 말아야 하는 것(강한 금지 규칙)
아래 항목들은 errors에 절대로 포함되면 안 됩니다.
1. 틀린 표현 전체  
   예: "만화 책이", "친구한테"
2. '틀린 표현 -> 맞는 표현' 같은 비교 형식  
   예: "한테 -> 에게"
3. 교정되지 않은 올바른 표현  
   예: 원문에서 수정이 일어나지 않은 단어/조사/어미

### errors에는 아래와 같은 형태만 포함됩니다.
["을", "에", "-으면", "-으러", "-으세요", "이다"]

## 출력 형식(JSON)
아래 형식의 JSON 객체 하나만 출력해야 합니다.

{
  "is_error": true 또는 false,
  "corrected_sentence": "문장",
  "errors": ["교정된 문법 요소만 포함. 오류 없으면 빈 배열"]
}

## 예시

1) 오류가 아닌 경우:
{
  "is_error": false,
  "corrected_sentence": "한국에 와서는 택시만 탔다",
  "errors": []
}

2) 조사 교정 예시:
{
  "is_error": true,
  "corrected_sentence": "나는 친구와 함께 비빔밥을 먹었다",
  "errors": ["와", "을"]
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
1. original_sentence와 corrected_sentence를 **정확히 비교(diff)**하여 실제로 바뀐 부분만 식별합니다.
2. **원문과 동일한 표현은 교정된 것으로 간주하지 않습니다.** (아주 중요)
3. grammar_db_info를 참고하여, 각 교정이 어떤 문법 요소와 관련이 있는지, 왜 그런지 학습자가 이해하기 쉽도록 설명합니다.
4. 한 문장 안에 여러 개의 교정이 있을 수 있으므로, 각 교정에 대해 별도의 항목으로 정리합니다.

## 출력 형식 (내부 모델)
- corrected_sentence: 최종 교정된 문장 전체 (입력으로 받은 corrected_sentence를 기반으로 합니다)
- feedbacks: 배열
  - 각 요소는 다음 필드를 가집니다.
    - corrects: "틀린표현 -> 맞은표현" 형식의 문자열
    - reason: 해당 교정이 필요한 이유, 관련 문법 설명

## 주의사항
- **원문과 교정문에서 동일한 표현에 문법적 해설을 추가하지 마십시오.**
- 학습자에게 직접 말하듯이, 지나치게 어려운 용어보다는 예시와 함께 쉽게 설명하세요.
- grammar_db_info가 비어 있어도, 문장 비교와 한국어 규칙을 바탕으로 합리적인 설명을 작성하세요.
- **존재하지 않는 문법 개념을 새로 만들거나, 유추하여 설명을 생성하는 행위를 금지**합니다.

## 출력 예시
{
  "corrected_sentence": "나는 친구와 함께 비빔밥을 먹었다",
  "feedbacks": [
    {
      "corrects": "친구하고 -> 친구와",
      "reason": "‘하고’도 사용할 수 있지만 구어체에 가깝습니다. 문어체나 자연스러운 일반 서술에서는 ‘와/과’를 쓰는 것이 더 적절합니다."
    },
    {
      "corrects": "비빔밥은 -> 비빔밥을",
      "reason": "‘먹다’는 목적어를 필요로 하는 동사이므로 목적격 조사 ‘을/를’을 사용해야 합니다. ‘비빔밥’의 끝소리에 받침이 있어 ‘을’을 씁니다."
    }
  ]
}
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