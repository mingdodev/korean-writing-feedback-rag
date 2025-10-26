# 1. 데이터 전처리

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
                        ...
                    ]},
                    ...
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
                    ...
                ]
            },
            ...
        ]
    ```

- 데이터 셋으로부터 필요한 정보만을 추출해, JSON 형태의 데이터로 재가공합니다.