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