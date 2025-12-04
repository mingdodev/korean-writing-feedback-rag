from typing import Dict
from ..llm.clova_client import ClovaStudioClient


class ContextLLMClient:

    def __init__(self, llm: ClovaStudioClient):
        self.llm = llm

    async def get_context_feedback(self, title: str, contents: str) -> Dict[str, str]:
        messages = [
            {
                "role": "system",
                "content": (
                    "당신은 한국어 글쓰기를 돕는 한국어 선생님이다.\n"
                    "학습자가 쓴 글을 읽고, 글 전반에 대한 **문맥 총평**만을 짧고 분명하게 제공하라.\n\n"
                    "다음 사항을 중심으로 3~5문장 정도로 답하라.\n"
                    "1. 글의 제목이 글의 내용을 얼마나 잘 드러내는지\n"
                    "2. 글의 내용이 논리적으로 자연스럽게 전개되는지\n"
                    "3. 글의 장점과 특히 잘한 점 (예: 내용 구성, 아이디어, 표현 방식 등)\n"
                    "4. 글쓴이가 앞으로 글을 쓸 때 참고하면 좋을 한두 가지 조언\n\n"
                    "- 문법, 철자, 조사, 어미, 띄어쓰기 등 **언어 형식에 대한 지적은 절대 하지 마라.**\n"
                    "- 오직 내용·구성·표현 방식 등 **문맥적 측면**에 대해서만 언급하라.\n"
                    "- 답변은 실제 학습자가 읽고 이해하기 쉽게, 너무 추상적이지 않게 작성하라.\n"
                    "- 답변에서 '외국인 학습자', '한국어 학습자'와 같은 표현은 사용하지 말고, "
                    "'글쓴이', '당신' 등으로만 지칭하라.\n"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"[제목]\n{title}\n\n"
                    f"[내용]\n{contents}\n\n"
                    "위 글을 보고, 글에 대한 전반적인 피드백을 제공하라."
                ),
            },
        ]

        feedback_text = await self.llm.chat(messages)

        return {"feedback": feedback_text}
