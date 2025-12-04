from enum import Enum
from typing import Dict, Set

class posCategory(str, Enum):
    NOUN = "noun" # 명사
    DEPENDENT_NOUN = "dependent_noun" # 의존 명사
    VERB = "verb" # 동사
    AUXILIARY = "auxiliary" # 보조 용언
    ADJECTIVE = "adjective" # 형용사
    DETERMINER = "determiner" # 관형사
    ADVERB = "adverb" # 부사
    INTERJECTION = "interjection" # 감탄사
    PARTICLE = "particle" # 조사
    ENDING = "ending" # 어미
    AFFIX = "affix" # 접사
    RADIX = "radix" # 어근
    NUMERAL = "numeral" # 수사
    PUNCTUATION = "punctuation" # 구두점
    SYMBOL = "symbol" # 기호
    UNKNOWN = "unknown" # 불능 범주

CATEGORY_SETS: Dict[posCategory, Set[str]] = {
    posCategory.NOUN: {"NNG", "NNP", "NR", "NP"},
    posCategory.DEPENDENT_NOUN: {"NNB"},
    posCategory.VERB: {"VV", "VCP", "VCN"},
    posCategory.AUXILIARY: {"VX"},
    posCategory.ADJECTIVE: {"VA"},
    posCategory.DETERMINER: {"MM"},
    posCategory.ADVERB: {"MAG", "MAJ"},
    posCategory.INTERJECTION: {"IC"},
    posCategory.PARTICLE: {"JKS", "JKC", "JKG", "JKO", "JKB", "JKV", "JKQ", "JX", "JC"},
    posCategory.ENDING: {"EP", "EF", "EC", "ETN", "ETM"},
    posCategory.AFFIX: {"XSN", "XSV", "XSA"},
    posCategory.RADIX: {"XR"},
    posCategory.NUMERAL: {"SN"},
    posCategory.PUNCTUATION: {"SF", "SP", "SS", "SE", "SO", "SW"},
    posCategory.SYMBOL: {"SL", "SH", "SW"},
    posCategory.UNKNOWN: {"NF", "NA", "NV"},
}

def is_category(pos_tag: str, category: posCategory) -> bool:
    """
    입력된 형태소 태그(pos_tag)가 지정된 품사 범주(category)에 속하는지 확인합니다.
    """
    # 1. CATEGORY_SETS에서 해당 범주의 상세 태그 집합을 가져옵니다.
    #    (태그 집합이 정의되지 않았을 경우 빈 집합을 사용합니다.)
    target_tags: Set[str] = CATEGORY_SETS.get(category, set())
    
    # 2. 입력된 pos_tag가 해당 집합 안에 있는지 확인합니다.
    return pos_tag in target_tags

def has_final_consonant(morph: str) -> bool:
    """morph 마지막 글자의 받침 유무를 판별합니다."""
    if not morph:
        return False
    # 한글 유니코드 범위: AC00~D7A3
    last_char = morph[-1]
    if not ('가' <= last_char <= '힣'):
        return False
    # 받침: (code - 0xAC00) % 28 != 0
    code = ord(last_char)
    return (code - 0xAC00) % 28 != 0

def has_positive_vowel(morph: str) -> bool:
    """morph 마지막 글자의 모음이 'ㅏ, ㅗ'인지 판별합니다."""
    if not morph:
        return False
    last_char = morph[-1]
    if not ('가' <= last_char <= '힣'):
        return False
    # 초성 (code - 0xAC00) // 588
    # 중성 ((code - 0xAC00) // 28) % 21
    # 종성 (code - 0xAC00) % 28
    code = ord(last_char)
    vowel_idx = ((code - 0xAC00) // 28) % 21
    # 모음 조화에 관여하는 모음 인덱스: 아(0), 오(4)
    positive_vowels = {0, 4}
    return vowel_idx in positive_vowels

def standardize_word(word_data: dict) -> str:
    """
    어절 단위 데이터를 받아서 표준화된 형태로 변환합니다.
    """
    morphs = word_data.get('morphs', [])
    if not morphs:
        return ''
    
    standardized_parts = []
    
    for morph_data in morphs:
        morph_text = morph_data.get('morph', '')
        pos_tag = morph_data.get('pos')
        
        if not morph_text:
            continue
        
        # 1. PARTICLE, ENDING, DEPENDENT_NOUN, AUXILIARY 중 하나에 해당하면 morph 그대로 사용
        if (is_category(pos_tag, posCategory.PARTICLE) or
            is_category(pos_tag, posCategory.ENDING) or
            is_category(pos_tag, posCategory.DEPENDENT_NOUN) or
            is_category(pos_tag, posCategory.AUXILIARY)):
            standardized_parts.append(morph_text)
            continue
        
        # 2. NOUN, VERB, ADJECTIVE에 해당하면 받침 유무 확인 후 _O/_X 추가
        if (is_category(pos_tag, posCategory.NOUN) or
            is_category(pos_tag, posCategory.VERB) or
            is_category(pos_tag, posCategory.ADJECTIVE)):
            tag_with_consonant = pos_tag + ('_O' if has_final_consonant(morph_text) else '_X')
            
            # 3. VERB, ADJECTIVE에 해당하면 모음 양성/음성 확인 후 _P/_N 추가
            if (is_category(pos_tag, posCategory.VERB) or
                is_category(pos_tag, posCategory.ADJECTIVE)):
                vowel_suffix = '_P' if has_positive_vowel(morph_text) else '_N'
                tag_with_consonant += vowel_suffix
                
            standardized_parts.append(tag_with_consonant)
            continue
        
        # 4. 그 외 태그 (DETERMINER, ADVERB 등)는 태그만 표기
        standardized_parts.append(pos_tag)
    
    return ''.join(standardized_parts) 