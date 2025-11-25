import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
import chromadb
from sentence_transformers import SentenceTransformer
from urllib.parse import urlparse
from typing import List, Dict, Any

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
        
        # PostgreSQL Client
        self._db_dsn = (
            f"host={settings.POSTGRES_HOST} "
            f"port={settings.POSTGRES_PORT} "
            f"dbname={settings.POSTGRES_DB} "
            f"user={settings.POSTGRES_USER} "
            f"password={settings.POSTGRES_PASSWORD}"
        )
        
        # SentenceTransformer Embedder
        self.embedder = SentenceTransformer("jhgan/ko-sroberta-multitask")

    def _search_grammar_db_sync(self, corrected_errors: List[str]) -> List[GrammarDBInfo]:
        grammar_info_list: List[GrammarDBInfo] = []

        # 빈 문자열 제거 + 중복 제거
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

        with psycopg2.connect(self._db_dsn) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for elem in targets:
                    # pg_trgm 이용: headword와 유사한 항목 1개 가져오기
                    # headword % %s : trigram 유사도 연산자
                    cur.execute(
                        """
                        SELECT headword, pos, topic, meaning, form_info, constraints
                        FROM grammar_items
                        WHERE headword % %s
                        ORDER BY similarity(headword, %s) DESC
                        LIMIT 1;
                        """,
                        (elem, elem),
                    )
                    row = cur.fetchone()
                    if not row:
                        continue

                    # explanation 문자열 구성
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

        return grammar_info_list

    async def _search_grammar_db(self, corrected_errors: List[str]) -> List[GrammarDBInfo]:
        # 동기 DB 연결이 이벤트 루프를 막지 않도록, 새로운 스레드 생성

        loop = asyncio.get_running_loop()

        return await asyncio.to_thread(self._search_grammar_db_sync, corrected_errors)

    async def attach_grammar_feedback(self, sentence: Sentence) -> GrammarFeedback:

        query_embedding = self.embedder.encode(sentence.original_sentence).tolist()
        n_results = 5

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            # metadata 필터링: 필요하다면 where={'grade': 'TOPIK 3'} 등을 추가
            include=['documents', 'metadatas', 'distances']
        )

        error_examples: List[ErrorExample] = []

        if results.get('metadatas') and results.get('metadatas')[0]:
            for metadata_dict in results['metadatas'][0]:
                try:
                    original_sentence_from_db = metadata_dict.get('original_sentence')
                    error_words_data = metadata_dict.get('error_words', [])
                    
                    error_words: List[ErrorWord] = [ErrorWord(**ew) for ew in error_words_data]

                    example = ErrorExample(
                        original_sentence=original_sentence_from_db,
                        error_words=error_words
                    )
                    error_examples.append(example)

                except Exception as e:
                    print(f"Error processing ChromaDB result metadata: {e}")
                    continue

        # 원본 문장, 오류가 있는 문장 5개를 LLM에게 보내 교정 문장, 교정한 문법 요소/형태 받기
        first_llm_input = {
            "original_sentence": sentence.original_sentence,
            "error_examples": [ex.model_dump() for ex in error_examples]
        }

        correction_result_data: Dict[str, Any] = await self.client.get_corrected_sentence(first_llm_input)

        correction_result = CorrectionOutput(**correction_result_data)

        corrected_sentence = correction_result.corrected_sentence
        corrected_errors = correction_result.errors

        # 교정한 문법 요소/형태를 문법 DB에서 검색 -> postgres container 5432 포트로 접속해서
        # postgres trgm으로 저장된 document 검색
        grammar_db_info_list: List[GrammarDBInfo] = await self._search_grammar_db(corrected_errors)

        # 원본 문장, 교정 문장, 문법 DB 정보를 LLM에게 보내 최종 피드백 생성
        second_llm_input = {
            "original_sentence": sentence.original_sentence,
            "corrected_sentence": corrected_sentence,
            "grammar_db_info": [info.model_dump() for info in grammar_db_info_list]
        }

        final_feedback_data: Dict[str, Any] = await self.client.get_grammar_feedback(second_llm_input)
        
        # 최종 결과를 GrammarFeedback 스키마로 파싱하여 반환합니다.
        final_feedback = GrammarFeedback(**final_feedback_data)
        
        return final_feedback