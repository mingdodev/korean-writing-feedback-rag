import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import List, Iterable

from elasticsearch8 import AsyncElasticsearch
from elasticsearch8.helpers import async_bulk
from standardization import standardize_word

ES_HOST = "http://localhost:9200"
INDEX_NAME = "graduation_project_data"
MIN_N_GRAM = 2
MAX_N_GRAM = 3


def create_es_settings():
    """
    Elasticsearch 인덱스 설정 및 매핑 정의
    """
    return {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "filter": {
                    "ngram_filter": {
                        "type": "ngram",
                        "min_gram": MIN_N_GRAM,
                        "max_gram": MAX_N_GRAM,
                    }
                },
                "analyzer": {
                    "token_analyzer": {
                        "type": "custom",
                        "tokenizer": "whitespace",
                        "filter": ["lowercase"],
                    },
                    "ngram_analyzer": {
                        "tokenizer": "keyword",
                        "filter": ["lowercase", "ngram_filter"],
                    },
                },
            },
        },
        "mappings": {
            "properties": {
                "sentence_id": {"type": "keyword"},
                "original_text": {"type": "text", "analyzer": "standard"},
                "normalized_tags": {
                    "type": "text",
                    "analyzer": "token_analyzer",
                    "fields": {
                        "ngram": {
                            "type": "text",
                            "analyzer": "ngram_analyzer",
                            "search_analyzer": "ngram_analyzer",
                        },
                        "keyword": {"type": "keyword"},
                    },
                },
                "metadata": {"type": "object"},
            }
        },
    }


def load_corpus_from_jsonl(filepath: Path) -> List[dict]:
    """
    데이터셋 로드
    """
    if not filepath.exists() or os.stat(filepath).st_size == 0:
        raise FileNotFoundError(f"코퍼스 파일을 찾을 수 없거나 비어 있습니다: {filepath}")

    data: List[dict] = []
    with filepath.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data.append(json.loads(line))
    return data


def generate_actions(data_list: List[dict]) -> Iterable[dict]:
    """
    ES 벌크 인덱싱용 도큐먼트 생성
    """
    for doc in data_list:
        original_text = doc["original_sentence"]
        words = doc.get("words", [])

        # standardize_word를 words에 그대로 적용
        standardized_result_parts = [
            standardize_word(word_data) for word_data in words
        ]
        normalized_tags = " ".join(standardized_result_parts)

        metadata = {
            "file_number": doc.get("file_number"),
            "grade": doc.get("grade"),
            "mother_language": doc.get("mother_language"),
            "error_words": doc.get("error_words", []),
        }

        doc_id = doc.get("file_number") or str(uuid.uuid4())

        yield {
            "_index": INDEX_NAME,
            "_id": doc_id,
            "sentence_id": doc_id,
            "original_text": original_text,
            "normalized_tags": normalized_tags,
            "metadata": metadata,
        }


async def setup_index(es: AsyncElasticsearch):
    """
    인덱스 초기화
    """
    if await es.indices.exists(index=INDEX_NAME):
        print(f"Index '{INDEX_NAME}' already exists. Deleting and recreating...")
        await es.indices.delete(index=INDEX_NAME)

    config = create_es_settings()
    await es.indices.create(
        index=INDEX_NAME,
        settings=config["settings"],
        mappings=config["mappings"],
    )
    print(f"Index '{INDEX_NAME}' created successfully.")


async def main():
    print(f"Connecting to Elasticsearch at {ES_HOST}...")
    es = AsyncElasticsearch(hosts=[ES_HOST], request_timeout=30)

    try:
        # 1) 인덱스 초기화
        await setup_index(es)

        # 2) 실제 데이터셋 로드
        base_dir = Path.cwd()
        corpus_filepath = base_dir / "data" / "processed" / "processed_corpus.jsonl"
        data_list = load_corpus_from_jsonl(corpus_filepath)
        print(f"Loaded corpus size: {len(data_list)}")

        # 3) 인덱싱
        actions = generate_actions(data_list)
        successes, errors = await async_bulk(es, actions, raise_on_error=False)
        print(f"Indexed docs: {successes}, errors: {len(errors)}")

    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(main())
