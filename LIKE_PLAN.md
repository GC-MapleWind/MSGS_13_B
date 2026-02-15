# 결산 좋아요 기능 구현 계획

형! 이모지 대신 좀 더 심플한 **좋아요(Like)** 기능으로 변경할게. 사용자가 각 결산 게시물에 좋아요를 누르거나 취소할 수 있는 기능이야.

## Proposed Changes

### Database Models

#### [NEW] [like.py](file:///c:/Users/Seo/%EC%83%88%20%ED%8F%B4%EB%8D%94/MSGS_13_B/models/like.py)
- `SettlementLike` 모델 추가: 어떤 유저(`user_id`)가 어떤 결산(`settlement_id`)을 좋아하는지 저장하는 테이블.

### Schemas (Pydantic)

#### [NEW] [like.py](file:///c:/Users/Seo/%EC%83%88%20%ED%8F%B4%EB%8D%94/MSGS_13_B/schemas/like.py)
- 좋아요 정보(개수, 내 좋아요 여부)를 담기 위한 DTO 정의.

### Controllers (API)

#### [MODIFY] [settlements.py](file:///c:/Users/Seo/%EC%83%88%20%ED%8F%B4%EB%8D%94/MSGS_13_B/controller/v1/settlements.py)
- `POST /api/v1/settlements/{id}/like`: 좋아요 토글 (누르면 추가, 다시 누르면 삭제)
- `GET /api/v1/settlements/{id}`: 해당 결산의 좋아요 총 개수와 현재 로그인한 유저의 좋아요 여부를 함께 반환하도록 수정.

## Verification Plan

### Automated Tests
- `curl` 또는 `httpx`를 통해 좋아요 추가/삭제가 정상적으로 작동하는지 확인.
- 동일한 유저가 중복해서 좋아요를 누를 수 없는지(DB 유니크 제약 조건 등) 검증.

### Manual Verification
- `maplewind.db`에서 `settlement_likes` 테이블 데이터를 직접 확인.
