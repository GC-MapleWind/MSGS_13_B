# 📋 운영팀 한마디 (Team Message) 작업 내역

운영팀 정보 및 팀원별 상세 한마디 조회를 위한 백엔드 기능 개발 내역입니다.

## 1. 개요
*   **목적**: 사이드바 및 전용 페이지에서 운영진의 정보와 상세 메시지(사진 + 텍스트)를 제공.
*   **주요 기능**: 운영팀 리스트 조회, 특정 팀원 상세 정보 조회.

## 2. 변경된 파일 및 주요 내용

### [NEW] Models
*   `models/team.py`: `TeamMember` (기본 정보) 및 `TeamMessage` (상세 메시지) 테이블 정의. 1:1 관계 설정.

### [NEW] Schemas (DTO)
*   `schemas/team_dto.py`: API 응답을 위한 `TeamMemberResponse`, `TeamMemberDetailResponse` 정의.

### [MODIFY] Controllers
*   `controller/v1/system.py`:
    *   `GET /api/v1/system/team`: 전체 운영진 리스트 조회 API 추가.
    *   `GET /api/v1/system/team/{member_id}`: 특정 팀원 상세(메시지 포함) 조회 API 추가.

### [NEW] Services & Repositories
*   `repositories/team_repo.py`: DB 접근 로직 (SQLAlchemy 비동기 쿼리).
*   `services/team_service.py`: 비즈니스 로직 및 예외 처리.

## 3. API 사용 가이드

| 기능 | Method | URL | 설명 |
| :--- | :--- | :--- | :--- |
| **팀 리스트** | `GET` | `/api/v1/system/team` | 성명, 역할, 프로필 사진 URL 목록 반환 |
| **팀원 상세** | `GET` | `/api/v1/system/team/{id}` | 멤버 기본 정보 + 상세 한마디 텍스트 + 사진 URL |

## 4. 참고 사항
*   **초기 데이터**: 사용자의 요청에 따라 자동 시드 데이터(Test Data) 생성 로직은 제거되었습니다.
*   **데이터 추가**: 새로운 운영진 정보를 표시하려면 DB(`team_members`, `team_messages` 테이블)에 직접 데이터를 삽입해야 합니다.
