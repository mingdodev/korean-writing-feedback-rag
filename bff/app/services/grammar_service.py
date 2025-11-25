import asyncpg
import chromadb
import json
from sentence_transformers import SentenceTransformer
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional

from ..clients.grammar_llm_client import GrammarLLMClient
from ..core.config import settings
from ..schemas.feedback_response import (
    Sentence, 
    GrammarFeedback, 
    ErrorWord, 
    ErrorExample, 
    CorrectionOutput, 
    GrammarDBInfo
)

class ChromaCollectionNotFound(Exception):
    pass

class GrammarService:
    # 커넥션 풀을 저장할 클래스 변수
    _pool: Optional[asyncpg.Pool] = None

    def __init__(self, client: GrammarLLMClient):
        # LLM Client
        self.client = client

        # ChromaDB Client
        url = settings.CHROMA_HOST
        collection_name = settings.CHROMA_COLLECTION_NAME

        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port

        self.chroma_client = chromadb.HttpClient(host=host, port=port)

        try:
            self.collection = self.chroma_client.get_collection(name=collection_name)
        except Exception as e:
            raise ChromaCollectionNotFound(f"Failed to get collection '{collection_name}': {e}")
        
        # PostgreSQL Connection Settings
        self._db_connect_kwargs = {
            "host": settings.POSTGRES_HOST,
            "port": settings.POSTGRES_PORT,
            "database": settings.POSTGRES_DB,
            "user": settings.POSTGRES_USER,
            "password": settings.POSTGRES_PASSWORD,
            "min_size": 5,
            "max_size": 20,
        }
        
        # SentenceTransformer Embedder
        self.embedder = SentenceTransformer("jhgan/ko-sroberta-multitask")

    async def initialize_db_pool(self):
        """커넥션 풀을 초기화하는 비동기 메서드"""

        if GrammarService._pool is None:
            GrammarService._pool = await asyncpg.create_pool(**self._db_connect_kwargs)

    async def close_db_pool(self):
        """커넥션 풀을 닫는 비동기 메서드 (애플리케이션 종료 시 호출)"""

        if GrammarService._pool is not None:
            await GrammarService._pool.close()
            GrammarService._pool = None

    async def _search_grammar_db(self, corrected_errors: List[str]) -> List[GrammarDBInfo]:
        """
        PostgreSQL 커넥션 풀을 사용하여 문법 DB를 비동기적으로 검색합니다.
        """

        grammar_info_list: List[GrammarDBInfo] = []
        
        seen: set[str] = set()
        targets: List[str] = []
        for e in corrected_errors:
            key = e.strip()
            if not key:
                continue
            if key in seen:
                continue
            seen.add(key)
            targets.append(key)

        if not targets:
            return grammar_info_list
        
        try:
            if GrammarService._pool is None:
            # 풀이 초기화되지 않았다면 초기화 시도
                await self.initialize_db_pool()
            
        except Exception as e:
            print(f"PostgreSQL Pool initialization failed: {e}")
            return []

        # 풀에서 커넥션을 대여하여 사용
        try:
            async with GrammarService._pool.acquire() as conn:
                # 트랜잭션 블록 시작
                async with conn.transaction():
                    for elem in targets:
                        row = await conn.fetchrow(
                            """
                            SELECT headword, pos, topic, meaning, form_info, constraints
                            FROM grammar_items
                            WHERE headword % $1
                            ORDER BY similarity(headword, $2) DESC
                            LIMIT 1;
                            """,
                            elem, elem,
                        )
                        
                        if not row:
                            continue
                    
                        parts: List[str] = []

                        if row.get("meaning"):
                            parts.append(f"의미: {row['meaning']}")
                        if row.get("form_info"):
                            parts.append(f"형태 정보: {row['form_info']}")
                        if row.get("constraints"):
                            parts.append(f"제약: {row['constraints']}")
                        if row.get("pos"):
                            parts.append(f"품사: {row['pos']}")
                        if row.get("topic"):
                            parts.append(f"토픽 등급: {row['topic']}")

                        explanation = " / ".join(parts) if parts else "설명 정보가 없습니다."

                        grammar_info_list.append(
                            GrammarDBInfo(
                                grammar_element=row["headword"],
                                explanation=explanation,
                            )
                        )
        except Exception as e:
            print(f"PostgreSQL query execution failed: {e}")
            return []

        return grammar_info_list
    
    async def attach_grammar_feedback(self, sentence: Sentence) -> GrammarFeedback:

        try:
            # 1. ChromaDB 쿼리
            query_embedding = self.embedder.encode(sentence.original_sentence).tolist()
            n_results = 5

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
        except Exception as e:
            print(f"ChromaDB query failed for '{sentence.original_sentence}': {e}")
            results = {'metadatas': [[]]}

        error_examples: List[ErrorExample] = []

        documents = results.get('documents', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]

        if documents and metadatas:
            for doc, metadata_dict in zip(documents, metadatas):
                try:
                    original_sentence_from_db = doc 
                    error_words_raw = metadata_dict.get('error_words')
                    error_words_data = []

                    if isinstance(error_words_raw, str):
                        try:
                            error_words_data = json.loads(error_words_raw)
                        except json.JSONDecodeError:
                            print(f"Failed to decode error_words JSON string: {error_words_raw}")
                    elif isinstance(error_words_raw, list):
                        error_words_data = error_words_raw
                    
                    error_words: List[ErrorWord] = [ErrorWord(**ew) for ew in error_words_data if isinstance(ew, dict)]

                    example = ErrorExample(
                        original_sentence=original_sentence_from_db,
                        error_words=error_words
                    )
                    error_examples.append(example)

                except Exception as e:
                    print(f"Error processing ChromaDB result metadata for doc '{doc}': {e}")
                    continue

        # 2. 1차 LLM 호출 
        first_llm_input = {
            "original_sentence": sentence.original_sentence,
            "error_examples": [ex.model_dump() for ex in error_examples]
        }

        try:
            correction_result_data: Dict[str, Any] = await self.client.get_corrected_sentence(first_llm_input)
            correction_result = CorrectionOutput(**correction_result_data)
        except Exception as e:
            print(f"1st LLM call failed for '{sentence.original_sentence}'. Error: {e}")
            
            print("--- LLM Request Payload (1st call) ---")
            print(json.dumps(first_llm_input, indent=2, ensure_ascii=False))
            print("--------------------------------------")

            if hasattr(e, 'response'):
                print("--- LLM Error Response Body ---")
                try:
                    print(json.dumps(e.response.json(), indent=2, ensure_ascii=False))
                except (json.JSONDecodeError, AttributeError):
                    print(e.response.text)
                print("-----------------------------")
            raise

        corrected_sentence = correction_result.corrected_sentence
        corrected_errors = correction_result.errors

        # 3. 문법 정보 DB 쿼리
        grammar_db_info_list: List[GrammarDBInfo] = await self._search_grammar_db(corrected_errors)

        # 4. 2차 LLM 호출
        second_llm_input = {
            "original_sentence": sentence.original_sentence,
            "corrected_sentence": corrected_sentence,
            "grammar_db_info": [info.model_dump() for info in grammar_db_info_list]
        }

        try:
            final_feedback_data: Dict[str, Any] = await self.client.get_grammar_feedback(second_llm_input)
            final_feedback = GrammarFeedback(**final_feedback_data)
        except Exception as e:
            print(f"2nd LLM call failed for '{sentence.original_sentence}'. Error: {e}")
            
            print("--- LLM Request Payload (2nd call) ---")
            print(json.dumps(second_llm_input, indent=2, ensure_ascii=False))
            print("--------------------------------------")

            if hasattr(e, 'response'):
                print("--- LLM Error Response Body ---")
                try:
                    print(json.dumps(e.response.json(), indent=2, ensure_ascii=False))
                except (json.JSONDecodeError, AttributeError):
                    print(e.response.text)
                print("-----------------------------")
            raise

        return final_feedback