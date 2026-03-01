지금 상태에서 `/api/docs`(FastAPI의 Swagger UI)가 안 되는 건 **대부분 “서브경로(prefix) 프록시”에서 FastAPI가 생성하는 링크(/openapi.json 등)가 루트(`/`) 기준으로 나가서** 깨지기 때문이에요.
즉, 브라우저는 `/msgs13_dev/api/docs`로 들어갔는데, docs 페이지 내부에서 `/openapi.json`을 **그냥 `/openapi.json`으로 요청**해버리면 404/다른 서비스로 가버립니다.

아래처럼 잡으면 `/msgs13_dev/api/*` 아래에서 **health + docs + openapi.json + redoc 전부** 같이 살아납니다.

---

## 1) Nginx 프록시를 “prefix 통째로” 잡는 정석 (추천)

핵심은 이 3개예요:

1. `location /msgs13_dev/api/ { proxy_pass http://backend_dev/; }` 처럼 **둘 다 trailing slash** 맞추기
2. `/msgs13_dev/api` → `/msgs13_dev/api/`로 **redirect**
3. FastAPI가 prefix를 알 수 있게 **X-Forwarded-Prefix / root_path** 처리

### Nginx 예시

```nginx
# /msgs13_dev/api -> /msgs13_dev/api/ 로 정규화
location = /msgs13_dev/api {
    return 301 /msgs13_dev/api/;
}

# API 전체를 서브경로로 프록시
location /msgs13_dev/api/ {
    proxy_pass http://backend_dev/;   # ★ trailing slash 중요
    proxy_http_version 1.1;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # ★ FastAPI가 "내가 /msgs13_dev/api 아래에 있다"는 걸 알게 해줌
    proxy_set_header X-Forwarded-Prefix /msgs13_dev/api;

    # (웹소켓 쓰면)
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
}
```

> `proxy_pass http://backend_dev/;` 처럼 **슬래시를 붙여야**
> `/msgs13_dev/api/docs` → `http://backend_dev/docs`로 깔끔하게 매핑됩니다.

---

## 2) 근데도 `/docs`가 깨지면: FastAPI 쪽 root_path 처리 필요 (매우 흔함)

Nginx가 prefix로 잘 넘겨도, FastAPI가 스웨거 내부 경로를 루트(`/openapi.json`)로 찍어버리면 여전히 깨져요.
이때는 FastAPI 앱에 **root_path**를 주는 게 제일 확실합니다.

### (A) 코드로 고정 (가장 확실)

```python
app = FastAPI(root_path="/msgs13_dev/api")
```

### (B) 실행 옵션으로 (코드 건드리기 싫을 때)

uvicorn이면:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --root-path /msgs13_dev/api
```

### (C) “X-Forwarded-Prefix”를 root_path로 반영하도록 미들웨어/설정

FastAPI/Starlette는 환경에 따라 자동 반영이 안 되는 경우가 많아서,
현장에선 보통 (A)나 (B)로 끝내는 편이 가장 빠릅니다.

---

## 3) health만 따로 매핑(A안) vs 백엔드 라우트 추가(B안) 관점에서, docs까지 고려하면?

* **health만** 해결이면 A안(nginx에 /health만 따로 location)도 OK
* 하지만 지금은 `/api/docs`까지 포함해서 **서브경로 전체가 요구사항**이니까
  → **“/msgs13_dev/api/ 전체 프록시 + root_path” 패턴이 정답**입니다.

---

## 4) 빠른 자가진단 체크리스트

1. 백엔드 자체는 살아있나?

```bash
curl -i http://backend_dev/health
curl -i http://backend_dev/docs
curl -i http://backend_dev/openapi.json
```

2. 프록시 뒤에서 매핑이 되는가?

```bash
curl -i http://<nginx>/msgs13_dev/api/health
curl -i http://<nginx>/msgs13_dev/api/docs
curl -i http://<nginx>/msgs13_dev/api/openapi.json
```

* `/docs`는 뜨는데, `/openapi.json`이 404면 → **root_path 문제** 확률 90%

---

원하면, 지금 Nginx 설정 일부(해당 server 블록에서 `/msgs13_dev` 관련 location들)랑 백엔드가 FastAPI인지(또는 다른 프레임워크인지), uvicorn 실행 방식(docker compose 커맨드/엔트리포인트)만 붙여주면 **딱 맞는 최종 설정으로 정리해서 그대로 붙여넣을 수 있게** 만들어줄게요.
