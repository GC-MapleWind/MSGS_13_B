# 백엔드 Dockerfile
FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /app

# uv 설치
RUN pip install uv

# 의존성 파일 복사
COPY pyproject.toml uv.lock ./

# 의존성 설치 (프로덕션 전용, dev 의존성 제외)
RUN uv sync --frozen --no-dev

# non-root 유저 생성 (홈 디렉토리 포함)
RUN groupadd -r appuser && \
    useradd -r -g appuser -m appuser && \
    mkdir -p /home/appuser/.cache && \
    chown -R appuser:appuser /home/appuser

# 애플리케이션 코드 복사
COPY . .

# 애플리케이션 디렉토리 소유권 변경
RUN chown -R appuser:appuser /app

# non-root 유저로 전환
USER appuser

# 포트 노출
EXPOSE 8000

# 헬스체크 (dedicated health endpoint 사용)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 애플리케이션 실행
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
