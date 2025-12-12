import json
import random
import time
from typing import List

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlencode

"""
이 스크립트는 학사 졸업 연구 목적의 수집용으로 작성되었으며,
대상 사이트의 robots 정책을 준수하는 범위에서 저속 트래픽으로 동작합니다.
실제 서비스에서는 사용하지 않습니다.
"""

BASE_URL = "https://kcenter.korean.go.kr"
VIEW_URL = BASE_URL + "/kcenter/search/dgrammar/view.do"
IDS_PATH = "grammar_ids.json"

def polite_sleep_short():
    time.sleep(random.uniform(1.0, 2.0))

def polite_sleep_long():
    time.sleep(random.uniform(4.0, 7.0))

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

def load_all_ids(path: str = IDS_PATH) -> List[int]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def fetch_view_html(driver: webdriver.Chrome, grammar_id: int) -> str:
    params = {
        "mode": "view",
        "id": str(grammar_id),
    }
    query = urlencode(params, encoding="utf-8", doseq=True)
    url = f"{VIEW_URL}?{query}"
    print(f"  → GET {url}")
    driver.get(url)
    polite_sleep_short()
    return driver.page_source

def parse_view_html(html: str, grammar_id: int) -> dict:
    """
    view.do HTML에서:
      - 표제어(문법/표현, 품사, 토픽 등급, 토픽, 국제표준모형 등급)
      - 의미와 용법
      - 형태 정보
      - 제약 정보
    을 추출해서 dict로 반환
    """
    soup = BeautifulSoup(html, "html.parser")

    # ------------------------
    # 1. 표제어 블록
    # ------------------------
    headword = None
    pos = None
    topik_level = None
    topik = None
    intl_level = None

    title_div = soup.find("div", class_="con_tit", string=lambda t: t and "표제어" in t)
    if title_div:
        view_div = title_div.find_next("div", class_="con_view2")
        table = view_div.find("table") if view_div else None
        if table:
            for tr in table.find_all("tr"):
                th_texts = [th.get_text(strip=True) for th in tr.find_all("th")]
                td_texts = [td.get_text(" ", strip=True) for td in tr.find_all("td")]

                if not th_texts or not td_texts:
                    continue

                if "문법/표현" in th_texts[0]:
                    headword = td_texts[0]

                elif "품사" in th_texts[0]:
                    pos = td_texts[0]
                    if len(th_texts) > 1 and "토픽 등급" in th_texts[1] and len(td_texts) > 1:
                        topik_level = td_texts[1]

                elif "토픽" in th_texts[0]:
                    topik = td_texts[0]
                    if len(th_texts) > 1 and "국제표준모형 등급" in th_texts[1] and len(td_texts) > 1:
                        intl_level = td_texts[1]

    # ------------------------
    # 2. 의미와 용법
    # ------------------------
    meaning = None
    meaning_title = soup.find("div", class_="con_searchall_tit", string=lambda t: t and "의미와 용법" in t)
    if meaning_title:
        block = meaning_title.find_next("div", class_="con_searchall_c1")
        if block:
            ul = block.select_one("ul.info_set")
            if ul:
                dd_texts = [dd.get_text(" ", strip=True) for dd in ul.find_all("dd")]
                if dd_texts:
                    meaning = "\n".join(dd_texts)

    # ------------------------
    # 3. 형태 정보
    # ------------------------
    form_info_list: List[str] = []
    form_title = soup.find("div", class_="con_searchall_tit", string=lambda t: t and "형태 정보" in t)
    if form_title:
        block = form_title.find_next("div", class_="con_searchall_c1")
        if block:
            tables = block.select("table.tbll_box")
            for tbl in tables:
                first_bgtd = tbl.select_one("td.bgtd")
                if first_bgtd:
                    text = first_bgtd.get_text(" ", strip=True)
                    if text:
                        form_info_list.append(text)

    form_info = "\n".join(form_info_list) if form_info_list else None

    # ------------------------
    # 4. 제약 정보
    # ------------------------
    constraints_list: List[str] = []
    cons_title = soup.find("div", class_="con_searchall_tit", string=lambda t: t and "제약 정보" in t)
    if cons_title:
        block = cons_title.find_next("div", class_="con_searchall_c1")
        if block:
            tables = block.select("table.tbll_box")
            for tbl in tables:
                first_bgtd = tbl.select_one("td.bgtd")
                if first_bgtd:
                    text = first_bgtd.get_text(" ", strip=True)
                    if text:
                        constraints_list.append(text)

    constraints = "\n".join(constraints_list) if constraints_list else None

    return {
        "id": grammar_id,
        "headword": headword,
        "pos": pos,
        "topik_level": topik_level,
        "topik": topik,
        "intl_level": intl_level,
        "meaning": meaning,
        # 리스트와 합친 문자열 둘 다 제공
        "form_info_list": form_info_list or None,
        "form_info": form_info,
        "constraints_list": constraints_list or None,
        "constraints": constraints,
    }


def main():
    ids = load_all_ids(IDS_PATH)
    print(f"총 {len(ids)}개 id 파싱 시작")

    driver = create_driver()
    parsed_items = []

    try:
        for i, gid in enumerate(ids, start=1):
            print(f"[{i}/{len(ids)}] id={gid} 페이지 요청 및 파싱 중...")
            html = fetch_view_html(driver, gid)
            item = parse_view_html(html, gid)
            parsed_items.append(item)

            polite_sleep_short()

            if i % 50 == 0:
                polite_sleep_long()

    finally:
        driver.quit()

    with open("grammar_items.jsonl", "w", encoding="utf-8") as f:
        for item in parsed_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print("\n✓ 문법 항목 파싱 및 저장 완료 → grammar_items.jsonl")


if __name__ == "__main__":
    main()
