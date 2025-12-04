import asyncpg
import chromadb
import json
from sentence_transformers import SentenceTransformer
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional
from elasticsearch8 import AsyncElasticsearch

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
from ..util.standardization import standardize_word
from ..util.morpheme import analyze_sentence_to_words
from ..util.logger import logger

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

        self.es_client = AsyncElasticsearch(
            hosts=[settings.ELASTICSEARCH_HOST],
            request_timeout=5
        )
        self.es_index = "graduation_project_data"

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
    
    async def _search_pattern_es(self, sentence: Sentence, max_results: int = 5) -> List[ErrorExample]:
        """
        Elasticsearch에서 문법 패턴(normalized_tags) 유사도가 높은 문장을 검색해
        ErrorExample 리스트로 반환한다.
        sentence.words는 코퍼스의 words와 동일 구조라고 가정.
        """
        words = getattr(sentence, "words", None)
        if not words:
            # 형태소 분석 결과가 아직 없다면, 여기서 형태소 분석을 호출하도록 확장할 수 있음
            logger.warning(f"Sentence에 words 정보가 없어 ES 패턴 검색을 건너뜁니다. sentence={sentence.original_sentence}")
            return []

        # 1) 검색용 정규화 쿼리 생성 (인덱싱 때와 동일한 규칙)
        standardized_parts = [standardize_word(w) for w in words]
        normalized_query = " ".join(p for p in standardized_parts if p)

        if not normalized_query:
            logger.warning(f"정규화 쿼리가 비어 있어 ES 패턴 검색을 건너뜁니다. sentence={sentence.original_sentence}")
            return []

        # 2) 1단계: normalized_tags match
        query = {
            "match": {
                "normalized_tags": {
                    "query": normalized_query
                }
            }
        }

        try:
            resp = await self.es.search(
                index=self.es_index,
                query=query,
                size=max_results,
            )
        except Exception as e:
            logger.error(f"ES 패턴 검색 실패: {e}")
            return []

        hits = resp.get("hits", {}).get("hits", [])
        if not hits:
            return []

        error_examples: List[ErrorExample] = []

        for hit in hits:
            src = hit.get("_source", {})
            original_text = src.get("original_text")
            metadata = src.get("metadata", {}) or {}

            error_words_raw = metadata.get("error_words")
            error_words_data = []

            if isinstance(error_words_raw, str):
                try:
                    error_words_data = json.loads(error_words_raw)
                except json.JSONDecodeError:
                    logger.warning(f"ES error_words JSON 파싱 실패: {error_words_raw}")
            elif isinstance(error_words_raw, list):
                error_words_data = error_words_raw

            error_words: List[ErrorWord] = [
                ErrorWord(**ew) for ew in error_words_data if isinstance(ew, dict)
            ]

            if not original_text:
                continue

            error_examples.append(
                ErrorExample(
                    original_sentence=original_text,
                    error_words=error_words,
                )
            )

        return error_examples

    async def attach_grammar_feedback(self, sentence: Sentence) -> GrammarFeedback:
        logger.info(f"\n\n===== 피드백 생성 시작: '{sentence.original_sentence}' =====")
        # ------------------------------
        # 1. ChromaDB 쿼리
        # ------------------------------
        try:
            query_embedding = self.embedder.encode(sentence.original_sentence).tolist()
            n_results = 5

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
        except Exception as e:
            logger.error(f"ChromaDB query failed for '{sentence.original_sentence}': {e}")
            results = {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        chroma_examples: List[ErrorExample] = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        best_similarity = None
        if distances:
            best_similarity = 1.0 - distances[0]

        if documents and metadatas:
            for doc, metadata_dict in zip(documents, metadatas):
                try:
                    error_words_raw = metadata_dict.get("error_words")
                    error_words_data = json.loads(error_words_raw) if isinstance(error_words_raw, str) else (error_words_raw or [])
                    
                    chroma_examples.append(
                        ErrorExample(
                            original_sentence=doc,
                            error_words=[ErrorWord(**ew) for ew in error_words_data if isinstance(ew, dict)]
                        )
                    )
                except Exception as e:
                    logger.error(f"Error processing ChromaDB result metadata for doc '{doc}': {e}")

        log_msg = [f"--- 1. ChromaDB 검색 결과 (Best Sim: {best_similarity:.4f}) ---"]
        if chroma_examples:
            for ex in chroma_examples:
                log_msg.append(f"  - {ex.original_sentence}")
        else:
            log_msg.append("  - 결과 없음")
        logger.info("\n".join(log_msg))

        error_examples = chroma_examples

        # --------------------------
        # 1-2. 유사도가 낮으면 ES 문법 패턴 검색 결과 추가
        # --------------------------
        CHROMA_SIM_THRESHOLD = 0.60
        need_es_examples = not error_examples or (best_similarity is not None and best_similarity < CHROMA_SIM_THRESHOLD)

        if need_es_examples:
            logger.info(f"Chroma similarity가 낮거나 결과가 부족하여 ES 패턴 검색을 추가로 수행합니다.")
            try:
                sentence.words = analyze_sentence_to_words(sentence.original_sentence)
                es_examples = await self._search_pattern_es(sentence, max_results=5)
                
                log_msg = [f"--- 2. ES 패턴 검색 결과 ---"]
                if es_examples:
                    for ex in es_examples:
                        log_msg.append(f"  - {ex.original_sentence}")
                else:
                    log_msg.append("  - 결과 없음")
                logger.info("\n".join(log_msg))

                existing_sentences = {ex.original_sentence for ex in error_examples}
                for es_ex in es_examples:
                    if es_ex.original_sentence not in existing_sentences:
                        error_examples.append(es_ex)
                        existing_sentences.add(es_ex.original_sentence)
            except Exception as e:
                logger.error(f"ES 패턴 검색 중 오류: {e}")

        # 2. 1차 LLM 호출 
        first_llm_input = {
            "original_sentence": sentence.original_sentence,
            "error_examples": [ex.model_dump() for ex in error_examples]
        }

        try:
            correction_result_data: Dict[str, Any] = await self.client.get_corrected_sentence(first_llm_input)
            correction_result = CorrectionOutput(**correction_result_data)
        except Exception as e:
            logger.error(f"1st LLM call failed for '{sentence.original_sentence}'. Error: {e}", exc_info=True)
            raise

        log_msg = [f"--- 3. 1차 LLM 교정 결과 ---"]
        log_msg.append(f"  - is_error: {correction_result.is_error}")
        log_msg.append(f"  - Corrected: '{correction_result.corrected_sentence}'")
        log_msg.append(f"  - Errors: {correction_result.errors}")
        logger.info("\n".join(log_msg))

        if not correction_result.is_error:
            logger.info("오류 없음으로 판단, 피드백 생성 절차를 중단합니다.")
            return GrammarFeedback(corrected_sentence=sentence.original_sentence, feedbacks=[])

        corrected_sentence = correction_result.corrected_sentence
        corrected_errors = correction_result.errors

        # 3. 문법 정보 DB 쿼리
        logger.info(f"--- 4. 문법 DB 검색 ---\n  - 검색 요소: {corrected_errors}")
        grammar_db_info_list: List[GrammarDBInfo] = await self._search_grammar_db(corrected_errors)
        
        log_msg = [f"--- 5. 문법 DB 검색 결과 ---"]
        if grammar_db_info_list:
            for info in grammar_db_info_list:
                log_msg.append(f"  - Element: {info.grammar_element}, Explanation: {info.explanation[:50]}...")
        else:
            log_msg.append("  - 결과 없음")
        logger.info("\n".join(log_msg))

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
            logger.error(f"2nd LLM call failed for '{sentence.original_sentence}'. Error: {e}", exc_info=True)
            raise
        
        logger.info(f"===== 피드백 생성 종료: '{sentence.original_sentence}' =====\n")
        return final_feedback