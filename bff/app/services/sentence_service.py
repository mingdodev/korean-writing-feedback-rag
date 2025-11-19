import enum
from typing import List
from ..schemas.feedback_response import Sentence
from konlpy.tag import Mecab
import kss

class SentenceService:

    def __init__(self, error_threshold: float = 6.0):
        self.mecab = Mecab()
        self.ERROR_THRESHOLD = error_threshold

    def _calculate_error_score(self, sentence: str) -> float:
        score = 0.0

        # 1. 분석 실패 시 최고 가중치 10.0 부여 및 계산 중단
        try:
            tokens = self.mecab.pos(sentence)
        except Exception:
            return self.ERROR_THRESHOLD + 10.0
        
        # 2. 필수 성분 누락 의심 (주어/서술어 호응) 시 가중치 +4.0
        # 문장에 '주어 후보(NP, NNG+JKS/JX)'와 '서술어 후보(VV, VA)'가 모두 부족할 때
        subject_cands = [t for t, tag in tokens if tag in ['NP', 'NNG'] and ('JKS' in [t for t, tag in tokens] or 'JX' in [t for t, tag in tokens])]
        verb_cands = [t for t, tag in tokens if tag in ['VV', 'VA']] # 동사, 형용사
        
        # 필수 성분(주어 또는 서술어)이 문장 길이에 비해 현저히 부족할 때 점수 부여
        if (len(subject_cands) == 0 and len(verb_cands) > 0) or \
           (len(verb_cands) == 0 and len(tokens) > 5): # 서술어 없이 5단어 이상일 때
            score += 4.0

        # 3. 잘못된 문장 구조 의심 시 가중치 +3.0
        # 보조사(JX)나 조사(J)가 비정상적으로 반복되거나, 어미(E)가 잘못 붙은 경우
        j_count = sum(1 for t, tag in tokens if tag.startswith('J')) # 조사 카운트
        e_count = sum(1 for t, tag in tokens if tag.startswith('E')) # 어미 카운트
        
        # 문장 길이 대비 조사가 과도하게 많거나, 어미 활용이 비정상적일 때
        if j_count > 3 or e_count > 3:
            score += 3.0
            
        # 4. 미등록 단어 (KoNLPy의 'Unknown' 태그 또는 특정 문맥) 가중치 +2.0
        unknown_tags = ['SL', 'SW'] # 외국어(SL), 기타 기호(SW)도 비표준으로 간주 가능
        if any(tag in unknown_tags for t, tag in tokens):
            score += 2.0
            
        # 5. 문장 길이 (보정)
        if len(sentence) > 80: # 너무 긴 문장은 구조적 오류 가능성이 높음
            score += 1.0
        elif len(sentence) < 3: # 너무 짧은 문장은 오류가 아닐 가능성 높음
            score -= 1.0

        return max(0.0, score)


    def split_into_sentences(self, contents: str) -> list[Sentence]:
        # 형태소 분석기 기반 문장 분리
        sentence_list = kss.split_sentences(contents)

        sentences = []
        for idx, sent_text in enumerate(sentence_list):
            sentences.append(
                Sentence(
                    sentence_id=idx,
                    original_sentence=sent_text.strip()
                )
            )

        return sentences
    
    def tag_error_sentences_by_konlpy(self, sentences: list[Sentence]) -> list[Sentence]:
        # 순회하며 오류 의심이 되면 contains_error를 true로 만들기

        for sent in sentences:
            score = self._calculate_error_score(sent.original_sentence)
            
            if score >= self.ERROR_THRESHOLD:
                sent.is_error_candidate = True
         
        return sentences
