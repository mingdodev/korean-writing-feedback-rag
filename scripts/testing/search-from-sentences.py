import json
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_HOST = 'localhost'
CHROMA_PORT = 8000
COLLECTION_NAME = 'korean_sentences'

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
n_results = 5

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

# 7. 결과 출력
def _safe_load_field(v):
    if v is None:
        return None
    if isinstance(v, (list, dict)):
        return v
    if isinstance(v, str):
        s = v.strip()
        if s == '':
            return None
        if s[0] in ('{', '[', '"'):
            try:
                return json.loads(s)
            except Exception:
                return s
        return s
    return v

def _format_errors(meta):
    errs = _safe_load_field(meta.get('error_words'))
    if not errs:
        return None
    # errs는 리스트여야 함. 아니면 그냥 스트링으로 출력
    if not isinstance(errs, list):
        return str(errs)
    lines = []
    for e in errs:
        text = e.get('text') or ''
        parts = []
        if e.get('error_location'):
            parts.append(f"location={e.get('error_location')}")
        if e.get('error_aspect'):
            parts.append(f"aspect={e.get('error_aspect')}")
        if e.get('error_level'):
            parts.append(f"level={e.get('error_level')}")
        if parts:
            lines.append(f"    - {text} ({', '.join(parts)})")
        else:
            lines.append(f"    - {text}")
    return "\n".join(lines)

print("\n--- Search Results ---")
for i, (doc, meta, dist) in enumerate(zip(results['documents'][0], results['metadatas'][0], results['distances'][0])):
    print(f"{i+1} (Distance: {dist:.4f})")
    print(f"  Sentence: {doc}")
    print(f"  Grade: {meta.get('grade')}")
    print(f"  Mother Language: {meta.get('mother_language')}")
    errors_pretty = _format_errors(meta)
    if errors_pretty:
        print("  Errors:")
        print(errors_pretty)
    print("-" * 20)