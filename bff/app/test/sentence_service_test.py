import time
from ..services.sentence_service import SentenceService


TEST_CONTENT = """

"""

# 예상 결과 정의 (Sequence)
EXPECTED_RESULTS = []


def _print_split_sentences(sentences: list):
    print("\n--- 분리된 문장 목록 ---")
    for sent in sentences:
        print(f"[{sent.sentence_id:02}] {sent.original_sentence}")
    print("-" * 70)


def _evaluate_sentences(service: SentenceService, sentences: list):
    start = time.perf_counter()

    evaluation = []
    for sent in sentences:
        score = service._calculate_error_score(sent.original_sentence)
        sent.is_error_candidate = score >= service.ERROR_THRESHOLD
        evaluation.append((sent, score))

    duration = time.perf_counter() - start
    return evaluation, duration


def run_test():
    # 임계값 6.0으로 서비스 초기화
    try:
        service = SentenceService(error_threshold=6.0)
    except Exception as e:
        print(f"\n[❌ MeCab 초기화 오류]: {e}")
        print("MeCab 코어 및 사전이 설치되지 않았습니다. 테스트를 중단합니다.")
        return

    print("\n" + "="*70)
    print(f"| SentenceService 오류 판별 테스트 시작 (임계값: {service.ERROR_THRESHOLD:.1f}) |")
    print("="*70)

    # 1. 문장 분리 및 출력
    test_sentences = service.split_into_sentences(TEST_CONTENT)
    _print_split_sentences(test_sentences)

    # 2. 오류 후보 판별 및 점수 계산
    evaluation, elapsed = _evaluate_sentences(service, test_sentences)

    # 결과 출력
    print("\n--- 결과 분석 ---")
    print(f"처리된 총 문장 수: {len(evaluation)}")
    print(f"총 처리 시간: {elapsed:.4f}초 (KoNLPy 연산 시간)")
    print("-" * 70)

    print("| ID | 문장 (원문) | 계산 점수 | ERROR 태그 | 예상 결과 | 일치 여부 |")
    print("-" * 70)

    error_candidates_count = 0

    for idx, (sent, score) in enumerate(evaluation):
        expected_error = EXPECTED_RESULTS[idx] if idx < len(EXPECTED_RESULTS) else False
        is_candidate = sent.is_error_candidate

        if is_candidate:
            error_candidates_count += 1

        status = "✅" if is_candidate == expected_error else "❌"
        print(f"| {sent.sentence_id: <2} | {sent.original_sentence[:30]: <30} | {score: <9.2f} | {is_candidate!s: <10} | {expected_error!s: <8} | {status} |")

    print("-" * 70)
    print(f"최종 오류 후보 문장 수: {error_candidates_count}개")
    print("==============================================================\n")


if __name__ == "__main__":
    run_test()