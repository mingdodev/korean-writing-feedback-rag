# Backend for Frontend 서버

FastAPI 기반 **BFF(Backend for Frontend)** 레이어로, 내부의 도메인 모듈들을 통합해 **단일 엔드포인트로 제공**합니다.

<br>

## 실행 방법

```bash
# 필요한 의존성 설치
pip install -r requirements.txt

# 형태소 분석을 위한 Mecab 설치
bash <(curl -s https://raw.githubusercontent.com/konlpy/konlpy/master/scripts/mecab.sh)
```

<br>

## API 명세

`POST /api/feedback`

### 요청 (Request)

```json
{
    "title": "string",
    "contents": "string"
}
```

### 응답 (Response)

```json
{
   "context_feedback": {
     "feedback": "string"
   },
   "sentences": [
     {
       "sentence_id": 0,
       "original_sentence": "string",
       "is_error": false,
       "grammar_feedback": {
         "corrected_sentence": "string",
         "feedbacks": [
           {
             "corrects": "string",
             "reason": "string"
           }
         ]
       }
     }
   ]
}
```