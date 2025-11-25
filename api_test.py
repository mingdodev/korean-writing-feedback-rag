
import requests
import json
import time

"""
BFF Server API Test
"""
BASE_URL = "http://localhost:8080"
ENDPOINT = "/api/feedback"
URL = f"{BASE_URL}{ENDPOINT}"

# Request Body
PAYLOAD = {
    "title": "힘들었던 하루",
    "contents": (
        "오늘 아침, 나는 늦게 일어났어서 기분이 별로였다. "
        "그래서 학교에 빨리 가려고 밥을 먹는 걸 포기했다. "
        "수업은 어려웠다 선생님이 어제 숙제를 너무 많이 줬다. "
        "점심시간에 친구를 만나고 같이 밥을 먹었다. "
        "나는 비빔밥은 먹었고, 친구는 김치찌개 먹었다. "
        "오후에, 나는 도서관에 가서 공부를 하려고 했다. "
        "하지만 머리가 아파서 집에 그냥 가기로 했다. "
        "집에서 드라마 봤는데, 재미있었다."
    )
}

def run_test():

    print(f"🚀 요청 시작: POST {URL}")
    print("─" * 50)
    print("📝 요청 데이터:")
    print(json.dumps(PAYLOAD, indent=2, ensure_ascii=False))
    print("─" * 50)

    try:
        start_time = time.time()

        response = requests.post(
            URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(PAYLOAD).encode('utf-8')
        )

        end_time = time.time()
        elapsed_time = end_time - start_time

        print(f"✅ 요청 완료 (소요 시간: {elapsed_time:.2f}초)")
        print("─" * 50)

        if response.status_code == 200:
            print(f"✔️ 성공 (상태 코드: {response.status_code})")
            print("─" * 50)
            print("📄 수신된 응답:")
            
            response_json = response.json()
            print(json.dumps(response_json, indent=2, ensure_ascii=False))

        else:
            print(f"❌ 실패 (상태 코드: {response.status_code})")
            print("─" * 50)
            print("📄 오류 내용:")
            print(response.text)

    except requests.exceptions.ConnectionError as e:
        print(f"❌ 연결 실패: {e}")
        print("─" * 50)
        print("💡 확인 사항:")
        print(f"1. FastAPI (BFF) 서버가 {BASE_URL}에서 실행 중인지 확인하세요.")
        print("2. 다른 모든 서비스(LLM, DB 등)가 정상적으로 동작하는지 확인하세요.")
    
    except Exception as e:
        print(f"❌ 알 수 없는 오류 발생: {e}")

if __name__ == "__main__":
    run_test()
