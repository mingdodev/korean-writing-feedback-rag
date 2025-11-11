from morpheme_constants import (
    posCategory, is_category
)

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