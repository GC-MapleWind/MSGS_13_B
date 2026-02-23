# 단바 신청폼 마이그레이션 운영 가이드

## 개요
- 신입/재등록 폼은 프론트에서 분리(`/apply/new`, `/apply/renew`)되어 있고,
- 백엔드는 통합 도메인(`/api/v1/applications/*`)으로 저장합니다.

## 백엔드 환경변수
- `APPLICATION_CURRENT_TERM` : 현재 모집 학기 (예: `2025-2`)
- `APPLICATION_ALLOW_EDIT_AFTER_SUBMIT` : 이미 제출한 신청서 수정 허용 여부 (`true|false`)

## API
- `POST /api/v1/applications/new`
- `POST /api/v1/applications/renew`
- `GET /api/v1/applications/me`
- `GET /api/v1/meta/departments?query=`
- `GET /api/v1/meta/jobs`
- `GET /api/v1/meta/worlds`

## 유효성 검증
- 학번: 9자리 숫자
- 전화번호: `01` 시작 숫자 10~11자리
- 회칙 동의 필수
- 신입: 학생증 확인/개인정보 동의 필수
- 재등록: 회비 안내 확인 필수
