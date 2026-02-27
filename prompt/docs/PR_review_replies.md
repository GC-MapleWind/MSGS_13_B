# PR 리뷰 코멘트별 답글 (붙여넣기용)

GitHub 리뷰 코멘트는 "제출된 리뷰"의 답글 API가 제한적이라, 아래 문구를 각 discussion 스레드에 직접 붙여넣어 답글할 수 있습니다.

---

## PR #11 (fix/deployment-config)

### 1. Host Header Injection (server_name _)
**Discussion:** https://github.com/GC-MapleWind/MSGS_13_B/pull/11#discussion_r2808377394

```
Thanks for the security note. We'll replace `server_name _` with the actual domain (or set `proxy_set_header Host` to a trusted value) once the production domain is fixed. For now the catch-all is intentional for multi-IP/internal deployment.
```

### 2. /redoc proxy headers
**Discussion:** https://github.com/GC-MapleWind/MSGS_13_B/pull/11#discussion_r2808377398

```
Agreed. We'll add X-Forwarded-For and X-Forwarded-Proto to the /redoc block for consistency with other API paths.
```

### 3. /openapi.json proxy headers
**Discussion:** https://github.com/GC-MapleWind/MSGS_13_B/pull/11#discussion_r2808377402

```
Will add the same proxy header set (X-Real-IP, X-Forwarded-For, X-Forwarded-Proto) to the /openapi.json location for consistency.
```

### 4. HTTPS/TLS
**Discussion:** https://github.com/GC-MapleWind/MSGS_13_B/pull/11#discussion_r2808379069

```
Noted. HTTPS (listen 443 ssl, certs, HTTP-to-HTTPS redirect, HSTS) will be added when we have SSL certs (e.g. Let's Encrypt) in place. Keeping this PR focused on HTTP and Nginx routing for now.
```

---

## PR #12 (feat/dev-deployment)

### 1. nginx -t after overwrite (Line 183-190)
**Discussion:** https://github.com/GC-MapleWind/MSGS_13_B/pull/12#discussion_r2810185246

```
Will add backup of existing config before copy, and restore .bak if `nginx -t` fails so the previous config is not lost.
```

### 2. First deploy - no .bak
**Discussion:** https://github.com/GC-MapleWind/MSGS_13_B/pull/12#discussion_r2810185247

```
Will add a sentinel (e.g. .has_prev_deploy) or check for .bak existence in rollback; when no previous deploy exists, perform clean state rollback (stop/remove containers) instead of restoring .bak.
```

### 3. Dev inline rollback - remove docker compose down
**Discussion:** https://github.com/GC-MapleWind/MSGS_13_B/pull/12#discussion_r2810185249

```
Agreed. Will remove `docker compose down --remove-orphans` from the inline failure handler so the separate rollback step can restore .bak and restart without premature teardown.
```

### 4. nginx-dev.conf comment mismatch (Line 1-6)
**Discussion:** https://github.com/GC-MapleWind/MSGS_13_B/pull/12#discussion_r2810185251

```
Will fix the top comment to reflect that common snippet is not used due to upstream name conflict (location blocks are inlined in this file).
```
