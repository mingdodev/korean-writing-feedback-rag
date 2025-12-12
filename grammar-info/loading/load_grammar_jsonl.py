import json
import psycopg2
from psycopg2.extras import execute_batch
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
JSONL_PATH = BASE_DIR / "data" / "grammar_items.jsonl"

DB_CONFIG = {
    "host": "localhost",
    "port": 5431,
    "dbname": "grammar",
    "user": "grammar",
    "password": "grammarpassword",
}

def load_jsonl(path: Path):
    items = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def main():
    print(f"JSONL 파일 위치: {JSONL_PATH}")

    items = load_jsonl(JSONL_PATH)
    print(f"{len(items)}개 문법 항목 로딩 완료")

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            sql = """
            INSERT INTO grammar_items (
                id, headword, pos, topik,
                meaning, form_info, constraints
            ) VALUES (
                %(id)s, %(headword)s, %(pos)s, %(topik)s,
                %(meaning)s, %(form_info)s, %(constraints)s
            )
            ON CONFLICT (id) DO UPDATE SET
                headword    = EXCLUDED.headword,
                pos         = EXCLUDED.pos,
                topik       = EXCLUDED.topik,
                meaning     = EXCLUDED.meaning,
                form_info   = EXCLUDED.form_info,
                constraints = EXCLUDED.constraints;
            """

            execute_batch(cur, sql, items, page_size=100)

        conn.commit()
        print("✓ DB insert/update 완료")

    except Exception as e:
        conn.rollback()
        print("에러 발생, 롤백:", e)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
