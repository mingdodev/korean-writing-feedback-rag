# 1. 데이터 전처리

> 전처리 작업에 대한 코드는 깃허브에 업로드되어 있지 않습니다.

- 쓰기 피드백을 제공해야 하므로, 데이터 셋 중 '문어' 정보인 파일들만 필터링합니다.

- 임베딩을 위해 필요한 데이터 형식을 정의합니다. 해당 프로젝트의 경우 다음과 같은 JSON 형식을 사용합니다.

    ```JSON
        [
            {
                "file_number": "데이터 셋 파일의 인덱스",
                "grade": "TOPIK 등급",
                "original_sentence": "원본 문장",
                "words": [
                    {"form": "어절", "morphs": [
                        {"morph": "형태소", "pos": "품사"},
                        {"morph": "형태소", "pos": "품사"},
                    ]},
                ],
                "error_words": [
                    {
                        "text": "오류 어절 -> 교정 어절",
                        "error_location": "오류 위치",
                        "error_aspect": "오류 양상",
                        "error_level": "오류 층위"
                    },
                    {
                        "text": "오류 어절 -> 교정 어절",
                        "error_location": "오류 위치",
                        "error_aspect": "오류 양상",
                        "error_level": "오류 층위"
                    },
                ]
            },
        ]
    ```

- 데이터 셋으로부터 필요한 정보만을 추출해, JSON 형태의 데이터로 재가공합니다.

<br>

---

# 2. 벡터화 및 임베딩

> sentence transformers 5.1.2, chromadb 1.1.1

도커 컨테이너를 활용하여 각각 **원문 문장, 오류 교정 정보**를 검색 키로 하는 벡터 데이터베이스 서버를 구축합니다.

<br>

- `embedding/embed-sentence`는 **원문 문장을 임베딩**하고, 오류 관련 정보(오류 교정 정보, 오류 위치, 오류 양상, 오류 층위)는 메타데이터에 포함합니다.

- `embedding/embed-error-words`는 **오류 교정 정보를 임베딩**하고, 오류 위치, 오류 양상, 오류 층위는 메타데이터에 포함합니다.

- **TOPIK 등급, 학습자 모어 정보, 문장의 형태소 분석 정보**는 공통적인 메타데이터로 저장됩니다.

<br>

---

# 3. 검색 성능 테스트

테스트 스크립트를 통해 검색 테스트를 수행합니다. 

<br>

- `testing/search-from-sentence`
- `testing/search-from-error-words`

각각의 스크립트는 요청을 보내는 서버 주소(현재는 localhost에서 테스트를 진행하여 port만 다름) 및 출력 형식에 차이가 있습니다.