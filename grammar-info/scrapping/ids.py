import re
import json
import random
import time
from typing import List, Set

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

"""
이 스크립트는 학사 졸업 연구 목적의 수집용으로 작성되었으며,
대상 사이트의 robots 정책을 준수하는 범위에서 저속 트래픽으로 동작합니다.
실제 서비스에서는 사용하지 않습니다.
"""

BASE_URL = "https://kcenter.korean.go.kr"
LIST_URL = BASE_URL + "/kcenter/search/dgrammar.do"

CHOSUNG_LIST = ["ㄱ","ㄴ","ㄷ","ㄹ","ㅁ","ㅂ","ㅅ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]


def polite_sleep(base: float = 1.0):
    time.sleep(base + random.uniform(0, 0.5))


def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    return driver


def fetch_list_html_for_chosung(driver: webdriver.Chrome, chosung: str) -> str:
    url = (
        f"{LIST_URL}"
        f"?mode=&id=&srchChosung={chosung}"
        f"&searchCategory=&searchGrade=&searchTabMenu=&searchChineseYn="
        f"&curPage=1&srchKey=headword&srchKeyword="
    )
    print(f"  → GET {url}")
    driver.get(url)
    polite_sleep(1.0)
    return driver.page_source


def extract_ids_from_list_html(html: str) -> List[int]:
    soup = BeautifulSoup(html, "html.parser")

    ids: List[int] = []
    seen: Set[int] = set()

    for tag in soup.find_all(onclick=True):
        onclick = tag.get("onclick", "")
        m = re.search(r"f_form\(['\"]?(\d+)['\"]?\)", onclick)
        if m:
            gid = int(m.group(1))
            if gid not in seen:  # 중복 방지
                ids.append(gid)
                seen.add(gid)

    return ids


def collect_all_ids_in_order(driver: webdriver.Chrome) -> List[int]:
    all_ids: List[int] = []
    seen: Set[int] = set()

    for ch in CHOSUNG_LIST:
        print(f"[chosung={ch}] 목록 요청 중...")
        html = fetch_list_html_for_chosung(driver, ch)
        ids = extract_ids_from_list_html(html)
        print(f"  → {len(ids)}개 id 발견: {ids[:5]} ...")

        for gid in ids:
            if gid not in seen:
                all_ids.append(gid)
                seen.add(gid)

        polite_sleep(0.5)

    print(f"\n총 수집 id 개수: {len(all_ids)}")
    return all_ids


def save_all_ids(path: str = "grammar_ids.json"):
    driver = create_driver()
    try:
        ids = collect_all_ids_in_order(driver)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ids, f, ensure_ascii=False, indent=2)
        print(f"\n✓ id 목록 저장 완료 → {path}")
    finally:
        driver.quit()


if __name__ == "__main__":
    save_all_ids()
