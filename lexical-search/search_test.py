import asyncio
import re
from elasticsearch8 import AsyncElasticsearch, BadRequestError

ES_HOST = "http://localhost:9200"
INDEX_NAME = "graduation_project_data"

"""
정규화 기반 하이브리드 검색 테스트 템플릿 예제
(현재 사용하고 있지 않음)
"""


def normalize_query(sentence: str) -> str:
    """
    1. 기본적인 정규화 로직 (예시)
       - 양 끝 공백 제거
       - 여러 공백을 하나로 통일
       - 소문자 변환 (필요 없으면 빼도 됨)
    2. 인덱싱 때 normalized_tags를 만들 때 쓴 규칙이 있다면,
       여기랑 최대한 동일하게 맞춰주는 게 좋음.
    """
    # 필요에 따라 로직 더 추가해도 됨
    s = sentence.strip()
    # 연속 공백 -> 하나
    s = re.sub(r"\s+", " ", s)
    # 소문자화 (영어 섞일수도 있으면)
    s = s.lower()
    return s


async def hybrid_search_documents(es: AsyncElasticsearch, query_text: str, max_results: int = 5):
    """
    1. 사용자 문장 입력
    2. 정규화 (normalize_query)
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
                # analyzer는 인덱스에 설정된 token_analyzer가 자동 적용됨
                # 필요하면 여기 operator, minimum_should_match 등을 추가 가능
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
                    # 여기서도 normalized_query를 쓰는 게 일관됨
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
            "나는 어제 밥을 먹었다",
            "오늘 점심에 밥을 먹었어요",
            "예쁜 꽃이 있었다",
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
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(main())
