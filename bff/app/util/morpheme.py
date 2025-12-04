from konlpy.tag import Mecab
from typing import List, Dict

# Mecab 인스턴스를 모듈 레벨에서 한 번만 생성하여 재사용
mecab = Mecab()

def analyze_sentence_to_words(sentence: str) -> List[Dict]:
    """
    주어진 문장 문자열을 형태소 분석하여,
    'words' 구조 (어절별 형태소 딕셔너리 리스트)를 생성합니다.
    es_indexing.py에서 사용하는 데이터 구조와 동일합니다.

    Args:
        sentence (str): 분석할 문장 문자열

    Returns:
        List[Dict]: 어절 리스트. 각 어절은 'morphs' 키를 가지며,
                    형태소 정보 딕셔너리의 리스트를 값으로 가집니다.
    """
    words_list = []
    # 문장을 공백 기준으로 어절로 분리
    eojeols = sentence.split()

    for eojeol in eojeols:
        if not eojeol.strip():
            continue
        
        # Mecab으로 어절 단위 형태소 분석
        morphs_pos = mecab.pos(eojeol)
        
        morphs_data = [
            {"morph": morph, "pos": pos}
            for morph, pos in morphs_pos
        ]
        
        words_list.append({"morphs": morphs_data})
        
    return words_list
