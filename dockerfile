FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# 기본 패키지 + tini(정상적인 signal 처리/종료)
RUN apt-get update && apt-get install -y \
    ca-certificates curl gnupg tini \
    && rm -rf /var/lib/apt/lists/*

# Node.js 설치 (NodeSource)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get update && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# n8n 취약 버전
RUN npm i -g n8n@1.120.4

# non-root 유저로 실행
RUN useradd -m -u 1000 n8n
USER n8n
WORKDIR /home/n8n

# n8n 데이터 저장 경로(설정/DB/인증정보 등)
#VOLUME ["/home/n8n/.n8n"]

EXPOSE 5678

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["n8n"]
