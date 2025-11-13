import json
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_HOST = 'localhost'
CHROMA_PORT = 8001
COLLECTION_NAME = 'korean_error_words'

# 1. ChromaDB 클라이언트 연결
client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

# 2. 검색어 벡터화를 위한 임베딩 모델 로드
embedder = SentenceTransformer('jhgan/ko-sroberta-multitask')

# 3. 컬렉션 가져오기
try:
    collection = client.get_collection(name=COLLECTION_NAME)
    print(f"Collection '{COLLECTION_NAME}' loaded. Total count: {collection.count()}")
    
except Exception as e:
    print(f"ERROR: Failed to get collection: {e}")
    exit()

# 4. 검색어 정의
query_text = "학교가 끝난 후에 동생하고 약속 있어요."
n_results = 10

# 5. 검색어 벡터화
query_embedding = embedder.encode([query_text], convert_to_numpy=True).tolist()
print(f"Searching for query: '{query_text}'")

# 6. 유사도 검색 실행
results = collection.query(
    query_embeddings=query_embedding,
    n_results=n_results,
    # metadata 필터링: 필요하다면 where={'grade': 'TOPIK 3'} 등을 추가
    include=['documents', 'metadatas', 'distances']
)

def _safe_load_field(v):
    if v is None:
        return None
    if isinstance(v, (list, dict)):
        return v
    if isinstance(v, str):
        s = v.strip()
        if s == '':
            return None
        # 문자열이 JSON 형태로 보이면 파싱 시도
        if s[0] in ('{','[','"'):
            try:
                return json.loads(s)
            except Exception:
                return s
        return s
    return v

# 7. 결과 출력
print("\n--- Search Results ---")
for i, (doc, meta, dist) in enumerate(zip(results['documents'][0], results['metadatas'][0], results['distances'][0])):
    print(f"{i+1} (Distance: {dist:.4f})")
    print(f"  Errors: {doc}")

    orig = _safe_load_field(meta.get('original_sentence'))
    if orig is not None:
        print(f"  Sentence: {orig}")

    if meta.get('grade') is not None:
        print(f"  Grade: {meta.get('grade')}")
    if meta.get('mother_language') is not None:
        print(f"  Mother Language: {meta.get('mother_language')}")

    loc = _safe_load_field(meta.get('error_location'))
    asp = _safe_load_field(meta.get('error_aspect'))
    lvl = _safe_load_field(meta.get('error_level'))

    parts = []
    if loc not in (None, ''):
        parts.append(f"Error Location: {loc}")
    if asp not in (None, ''):
        parts.append(f"Error Aspect: {asp}")
    if lvl not in (None, ''):
        parts.append(f"Error Level: {lvl}")

    if parts:
        for p in parts:
            print(f"  {p}")
    print("-" * 20)