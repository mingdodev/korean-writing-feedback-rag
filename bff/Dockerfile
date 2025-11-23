FROM python:3.12-slim

# 표준 출력 버퍼링 끄기, 파이썬 캐시 파일 생성 방지
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    git \
    build-essential \
    autoconf \
    automake \
    openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    cd /tmp; \
    curl -LO https://bitbucket.org/eunjeon/mecab-ko/downloads/mecab-0.996-ko-0.9.2.tar.gz; \
    tar zxf mecab-0.996-ko-0.9.2.tar.gz; \
    cd mecab-0.996-ko-0.9.2; \
    ./configure; \
    make; \
    make check; \
    make install

RUN set -eux; \
    cd /tmp; \
    curl -LO https://bitbucket.org/eunjeon/mecab-ko-dic/downloads/mecab-ko-dic-2.1.1-20180720.tar.gz; \
    tar zxf mecab-ko-dic-2.1.1-20180720.tar.gz; \
    cd mecab-ko-dic-2.1.1-20180720; \
    ./autogen.sh; \
    ./configure; \
    mecab-config --libs-only-L > /etc/ld.so.conf.d/mecab.conf; \
    ldconfig; \
    make; \
    echo "dicdir=/usr/local/lib/mecab/dic/mecab-ko-dic" > /usr/local/etc/mecabrc; \
    make install

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]