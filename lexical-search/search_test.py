import asyncio
import re
from elasticsearch8 import AsyncElasticsearch, BadRequestError
from konlpy.tag import Mecab
from standardization import standardize_word

ES_HOST = "http://localhost:9200"
INDEX_NAME = "graduation_project_data"

"""
정규화 기반 하이브리드 검색 테스트 템플릿 예제
"""

# Mecab 전역 인스턴스
mecab = Mecab()


def build_word_data_from_eojeol(eojeol: str) -> dict:
    """
    Mecab 형태소 분석 결과를 네 정규화 함수가 기대하는 형태로 변환.
    반환 형식:
    {
      "morphs": [
        {"morph": "나는", "pos": "NOUN"},
        {"morph": "을", "pos": "PARTICLE"},
        ...
      ]
    }

    여기서는 Mecab의 태그를 그대로 pos에 넣고,
    내부에서 is_category(pos, posCategory.*) 로 분류한다고 가정.
    """
    morphs = mecab.pos(eojeol)  # 예: [("나", "NP"), ("는", "JX")]

    return {
        "morphs": [
            {"morph": morph, "pos": pos}
            for morph, pos in morphs
        ]
    }


def normalize_query(sentence: str) -> str:
    """
    1. 문장 기본 정리
    2. Mecab으로 형태소 분석
    3. 각 어절을 standardize_word 규칙에 따라 정규화
    4. 정규화된 어절들을 공백으로 이어서 하나의 문자열로 반환
    """
    s = sentence.strip()
    if not s:
        return ""

    # 연속 공백 정리
    s = re.sub(r"\s+", " ", s)

    # 어절 단위로 나누기
    eojeols = s.split()

    normalized_tokens = []

    for eojeol in eojeols:
        word_data = build_word_data_from_eojeol(eojeol)
        normalized = standardize_word(word_data)  # 네가 정의한 그 함수!
        if normalized:
            normalized_tokens.append(normalized)

    # ES에 인덱싱된 normalized_tags와 최대한 동일한 포맷으로 맞추기
    # (보통 "NOUN_X는 NOUN_X하고 NOUN_O를 VERB_O_N었다다" 이런 식)
    return " ".join(normalized_tokens)


async def hybrid_search_documents(es: AsyncElasticsearch, query_text: str, max_results: int = 5):
    """
    1. 사용자 문장 입력
    2. 형태소 기반 정규화 (normalize_query)
    3. 정규화된 문장으로 normalized_tags 필드 검색 (token_analyzer 사용)
    4. 결과 부족하면 normalized_tags.ngram으로 N-gram 기반 보정
    """

    print(f"\n=== 원본 검색 문장: '{query_text}' ===")

    # 1) 정규화
    normalized_query = normalize_query(query_text)
    print(f"  → 정규화 결과: '{normalized_query}'")

    if not normalized_query:
        print("경고: 정규화된 쿼리가 비어 있습니다. 검색을 수행할 수 없습니다.")
        return []

    found_ids = set()
    final_results = []

    # --- 1단계: token_analyzer 기반 normalized_tags match ---
    print(f"\n--- [1단계] normalized_tags match 검색 ---")

    exact_match_query = {
        "match": {
            "normalized_tags": {
                "query": normalized_query,
            }
        }
    }

    exact_search_result = await es.search(
        index=INDEX_NAME,
        query=exact_match_query,
        size=max_results,
    )

    for hit in exact_search_result["hits"]["hits"]:
        if len(final_results) < max_results:
            final_results.append(hit)
            found_ids.add(hit["_id"])

    print(f"  > 1단계에서 찾은 결과: {len(final_results)}개")

    # --- 2단계: N-gram 보정 (부족하면) ---
    needed_count = max_results - len(final_results)

    if needed_count > 0:
        print(f"\n--- [2단계] normalized_tags.ngram N-gram 보정 검색 ---")

        ngram_match_query = {
            "match": {
                "normalized_tags.ngram": {
                    "query": normalized_query,
                    "minimum_should_match": "50%",
                }
            }
        }

        ngram_search_result = await es.search(
            index=INDEX_NAME,
            query=ngram_match_query,
            size=needed_count * 3,
        )

        added_count = 0
        for hit in ngram_search_result["hits"]["hits"]:
            if added_count >= needed_count:
                break
            if hit["_id"] in found_ids:
                continue

            final_results.append(hit)
            found_ids.add(hit["_id"])
            added_count += 1

        print(f"  > 2단계에서 추가된 결과: {added_count}개")

    # --- 최종 결과 출력 ---
    print(f"\n--- 최종 검색 결과 (총 {len(final_results)}개) ---")
    for i, hit in enumerate(final_results):
        source = hit["_source"]
        print(f"  {i+1}. [Score: {hit['_score']:.2f}, ID: {hit['_id']}]")
        print(f"     original_text   : {source.get('original_text')}")
        print(f"     normalized_tags : {source.get('normalized_tags')}")
        print(f"     metadata        : {source.get('metadata')}")
        print()

    return final_results


async def main():
    print(f"Connecting to Elasticsearch at {ES_HOST}...")
    es = AsyncElasticsearch(hosts=[ES_HOST], request_timeout=30)

    try:
        # 샘플 문장
        queries = [
            "나는 친구하고 김밥를 먹었다.",
        ]

        for q in queries:
            await hybrid_search_documents(es, q, max_results=5)

    except BadRequestError as e:
        print("\n--- FATAL ERROR (BadRequest) ---")
        print(f"status: {e.status_code}")
        print(e)
    except Exception as e:
        print("\n--- FATAL ERROR (Other) ---")
        print(f"오류 상세: {e}")
        raise
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(main())
