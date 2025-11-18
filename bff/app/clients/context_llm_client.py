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
                    "당신은 한국어를 학습하는 외국인 학습자가 작성한 글에 대해 **전반적인 문맥 총평을** 제공하는 도우미이다.\n\n"
                    "한국어를 공부하는 외국인 학습자가 작성한 다음 글을 보고, 글에 대한 전반적인 피드백을 제공하라.\n\n"
                    "- 글의 제목이 글의 내용을 잘 드러내는가?\n"
                    "- 글의 내용이 문맥적으로 잘 구성되었는가?\n"
                    "- 한국어 외국인 학습자로서 특별히 칭찬할 부분이 있는가? 긍정적인 피드백을 녹여 서술하라.\n"
                    "- 글의 전체적인 인상만을 서술하라.\n"
                    "- 문법, 오타와 같은 오류는 일절 언급해서는 안 된다.\n"
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
