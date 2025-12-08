# 새로운 오류 데이터 수집을 위한 MQ

**collector** 서비스는 Kafka Consumer로 동작하며,  
`collect-events` 토픽에서 전송된 **userId, originalText, correctedText, feedbacks** 등을 포함한 이벤트를  
CSV 형태로 로컬 스토리지에 지속적으로 적재합니다.

사용자는 복잡한 인증이 아닌 **웹 기반 세션을 통해 간단히 구분**됩니다.

이 파이프라인을 통해 수집된 데이터는 
<strong>후속 연구(오류 유형 분석 · RAG 품질 개선)를 위한 Raw Dataset</strong>으로 활용할 수 있습니다.