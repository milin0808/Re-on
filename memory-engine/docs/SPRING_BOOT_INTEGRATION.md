# Spring Boot ↔ FastAPI 계약 v0.4.0

김민정 담당 Spring Memory 모듈은 `backend/src/main/java/com/reon/backend/memory`에 구현되어 있다.
공개 Memory API, DB 저장·갱신·비활성화, revision 검증, DB 기반 재시도 작업이 포함된다.
실제 인증·Moment CRUD·Moment 조회 어댑터는 최승환 코드에 연결한다.
전체 연결 순서와 예시는 [Memory 구현 문서](../../backend/MEMORY_IMPLEMENTATION.md)에 있다.

## 내부 HTTP

- Spring `MemoryEngineClient` → `POST /api/v1/memories/analyze/core`
- Spring 환경변수 `MEMORY_ENGINE_TOKEN` → `X-Service-Token` 헤더
- FastAPI 환경변수 `REON_ENGINE_TOKEN` → 헤더 검증; 두 값은 동일한 랜덤 ASCII 값
- Spring `MEMORY_ENGINE_URL` 기본값 `http://127.0.0.1:8000`
- 연결 제한 3초 / 읽기 제한 20초. DB 트랜잭션 밖에서 HTTP를 호출한다.

공개 API의 Bearer 사용자 인증과 내부 서비스 토큰은 별개다.
엔진은 DB 또는 실제 사용자의 인증 세션을 보유하지 않는다.

## v0.4 Moment 입력

| Spring / 기존 프론트 필드 | 엔진 내부 |
|---|---|
| `id` / `momentId` | `moment_id` |
| `recordedAt` / `createdAt` | `recorded_at` (UTC offset 필수) |
| Spring 인증 정보에서 채운 `userId` | `user_id` |
| 개별 `artist` → `track.artist` → `music.artist` | 원본 표시명을 유지한 artist |
| `songTitle` → `track.title` → `music.title` | `song_title` |
| `music.videoId` → `track.videoId` | `track_id`; 미확정은 null |
| `location:{latitude,longitude}` | 소수점 셋째 자리 좌표 셀 문자열 |
| 기존 문자열 `location` | 기존 위치명 그대로 |
| `memo` | 보조 Context |

`music`은 `videoId,title,artist,channelTitle,thumbnailUrl,originalUrl`을 받는다.
artist/channelTitle/URL/videoId는 null 또는 생략 가능하지만 title은 필요하다.
일반 채널명을 artist로 사용하지 않는다. artist가 없을 때만 ` - Topic` 채널을 임시 보조 정보로 쓴다.
표시명의 별칭 사전은 사용하지 않고, NFKC·공백·대소문자 차이만 비교용으로 정규화한다.

## 분석 및 결과 반영

요청 `scope`에는 `user_id`, `months`, `complete_month_history:true`, `history_revision`을 담는다.
운영 Spring 모듈은 한 달 전체를 읽어 요청한다. 비어 있는 달도 분석해 남은 Memory를 비활성화한다.
기존 Memory에는 `memory_id,user_id,period_month,is_active,content_hash`를 담는다.

FastAPI는 안정적인 `memory_id`, `content_hash`, `sync_action`, `deactivated_memory_ids`와 요청 scope를 반환한다.
엔진은 revision을 전달할 뿐 최신 DB revision을 검증하지 않는다.
Spring `MemoryResultService`가 사용자 revision 행을 잠그고 비교와 전체 반영을 같은 트랜잭션에서 수행한다.
이때 사용자·월·Moment ID·기간·곡 ID·비활성 대상도 검증한다. 오래된 결과는 전체 폐기한다.
`sync_action` 자체에 의존하지 않고 실제 DB에서 upsert·비활성화를 결정한다.

`tracks`에는 형식상 유효한 11자리 videoId가 있는 곡만 중복 제거해 넣는다.
실제 영상 접근성·삭제 여부·Playlist 추가 실패는 최승환의 RE:PLAY 서비스가 처리한다.
공개 목록·상세 DTO에는 engine ID나 snake_case 내부 필드를 노출하지 않는다.

## 테스트

FastAPI: `python -m unittest discover -s tests -v`.
Spring: `backend`에서 `gradlew test`.
실제 HTTP 왕복 테스트 실행 방법은 `backend/MEMORY_IMPLEMENTATION.md`에 있다.
