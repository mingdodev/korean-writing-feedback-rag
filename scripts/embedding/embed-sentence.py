import os
import uuid
import json
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_HOST = 'localhost'
CHROMA_PORT = 8000
COLLECTION_NAME = 'korean_sentences'

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
JSONL_FILE_PATH = os.path.join(BASE_DIR, 'data', 'processed', 'processed_corpus.jsonl')

embedder = SentenceTransformer('jhgan/ko-sroberta-multitask')

def load_jsonl(file_path):
    """JSONL 파일을 읽어 리스트 형태로 반환합니다."""
    print(f"Loading data from: {file_path}")
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"WARNING: JSON decode error in {file_path} at line {i}: {e}. Skipping line.")
                    continue
    except FileNotFoundError:
        print(f"WARNING: File not found at {file_path}. Returning empty list.")
        return []
    return data

def prepare_chroma_data(records):
    """
    로드된 JSON 데이터를 ChromaDB 형식에 맞게 변환합니다.
    - documents: original_sentence
    - metadatas: grade, words, error_words
    - ids: file_number + uuid
    """
    documents = []
    metadatas = []
    ids = []
    
    for record in records:      
        # documents
        sentence = record.get('original_sentence')
        if not sentence:
            continue

        # metadatas
        metadata = {}
        for k, v in record.items():
            if k not in ['original_sentence', 'file_number']:
                # 중첩 구조는 문자열 리스트로 변환
                if isinstance(v, (list, dict)):
                    metadata[k] = json.dumps(v, ensure_ascii=False)
                else:
                    metadata[k] = v

        # ids
        file_num_val = record.get('file_number')
        if file_num_val is None:
            continue
        file_num = str(file_num_val)
        doc_id = f"{file_num}_{uuid.uuid4().hex}"
        
        documents.append(sentence)
        metadatas.append(metadata)
        ids.append(doc_id)
        
    return documents, metadatas, ids

def embed_data_to_chromadb():
    """데이터를 로드하고 ChromaDB에 임베딩합니다."""
    
    # 데이터 로드 및 준비
    records = load_jsonl(JSONL_FILE_PATH)
    if not records:
        print("No data to process. Exiting.")
        return

    documents, metadatas, ids = prepare_chroma_data(records)
    print(f"Prepared {len(documents)} documents for embedding.")

    # ChromaDB 클라이언트 연결
    try:
        client = chromadb.HttpClient(
            host=CHROMA_HOST,
            port=CHROMA_PORT
        )
        print(f"Successfully connected to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
    except Exception as e:
        print(f"ERROR: Could not connect to ChromaDB server. Is the container running on port {CHROMA_PORT}? Error: {e}")
        return

    # 컬렉션 생성/가져오기
    try:
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"} # 코사인 유사도 공간 사용
        )
        print(f"Collection '{COLLECTION_NAME}' ready. Current count: {collection.count()}")

    except Exception as e:
        print(f"ERROR: Failed to create/get collection: {e}")
        return

    # 데이터 임베딩 및 추가 (1000개씩 배치 처리)
    try:
        batch_size = 1000
        total_documents = len(documents)
        
        for i in range(0, total_documents, batch_size):
            docs_batch = documents[i:i + batch_size]
            meta_batch = metadatas[i:i + batch_size]
            ids_batch = ids[i:i + batch_size]

            print(f"Embedding batch {i + 1} to {min(i + batch_size, total_documents)}...")
            embeddings_batch = embedder.encode(docs_batch, convert_to_numpy=True).tolist()
            
            collection.add(
                embeddings=embeddings_batch,
                documents=docs_batch,
                metadatas=meta_batch,
                ids=ids_batch
            )
            print(f"Added documents {i + 1} to {min(i + batch_size, total_documents)} / {total_documents}")

        final_count = collection.count()
        print(f"Total documents in collection '{COLLECTION_NAME}': {final_count}")

    except Exception as e:
        print(f"FATAL ERROR during data addition: {e}") 

if __name__ == "__main__":
    embed_data_to_chromadb()