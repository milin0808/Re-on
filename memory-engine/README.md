# 🎧 RE:ON — Memory Engine v0.3.0

Moment의 아티스트·시간·위치·메모를 분석하는 규칙 기반 FastAPI 서비스다.
DB 저장과 사용자 인증은 Core Backend가 담당하며, 엔진은 분석 결과만 반환한다.
현재 Core 브랜치에는 음악 조회만 구현되어 있다. 아래 Moment 전달·Memory 저장 계약은
이번 엔진 패치의 계약이며, 구현된 Core Moment CRUD API를 뜻하지 않는다.

## 실행

Windows: `run_server.bat` 실행 → <http://127.0.0.1:8000/docs>.

```bash
cd memory-engine
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn api:app --host 127.0.0.1 --port 8000
python -m unittest discover -s tests -v
```

CLI 데모는 `python main.py`, API 예제 호출은 서버 실행 후 `python try_api.py`다.

## 엔드포인트

| Method | 경로 | 입력 |
| --- | --- | --- |
| GET | `/health` | 상태·버전 |
| POST | `/api/v1/memories/analyze` | 엔진 형식: `moment_id`, `user_id`, `recorded_at` 등 |
| POST | `/api/v1/memories/analyze/core` | 현재 Core 음악 DTO 및 프론트 Moment 필드 |

예제: `examples/request.json`, `examples/core_request.json`,
`examples/frontend_request.json`, `examples/scoped_request.json`.
실제 샘플 응답: `examples/response.json`.

## 이번 패치의 기준

- 월·시간대·기간은 **Asia/Seoul(UTC+09:00)**로 계산한다. 같은 시각의 `Z`와 `+09:00`는 같은 결과다.
- 프론트 `id`, `createdAt`, `track.title`, `track.artist`, `track.albumCoverUrl`을 받는다.
  Core는 인증된 사용자 ID를 요청의 `userId` 또는 각 Moment의 `userId`로 채운다.
- Core `music`은 기존 `videoId`, `title`, `channelTitle`, `thumbnailUrl`을 그대로 받는다.
- `artist`를 별도의 별칭 사전으로 바꾸지 않는다. 전달된 표기를 유지하며, 공통 분석 단계에서
  Unicode NFKC·대소문자·공백 차이만 비교용으로 정규화한다.
  `아이유`와 `IU`, `NCT127`과 `NCT 127`은 별개의 표기다. 같은 아티스트를 묶으려면
  Core에서 일관된 artist 값을 보내야 한다. 엔진 입력 명칭을 프론트에 강요하지 않는다.
- 아티스트가 없으면 null로 처리한다. 일반 채널명(SMTOWN/1theK 등)을 artist로 사용하지 않는다.
  `이름 - Topic` 채널만 임시 fallback으로 사용한다. 미확정 곡도 시간·위치 분석과 월 전체 분모에 포함한다.
- `track_id`/`videoId`는 11자리 YouTube ID 또는 null이다. 형식 검증은 영상 존재나 재생 가능성을 보장하지 않는다.
- 반환 `tracks`에는 ID가 있는 곡만 넣고 ID로 중복을 제거한다. 원본 기록은 `moment_ids`에 모두 남는다.
  `replay_available`은 사용 가능한 ID가 하나 이상 있다는 뜻이다. 실제 곡 추가 실패는 Core가 처리한다.
- 잘못된 ID(불리언·실수), 중복 Moment, 사용자 혼합, 시간대 없는 날짜는 422다.

## 패턴 기준

| 유형 | 조건 |
| --- | --- |
| ARTIST | 같은 달 동일 아티스트 3회 이상 + 월 전체 기록의 40% 이상 |
| LOCATION | 같은 달 동일 위치 3회 이상 + 월 전체 기록의 50% 이상 |
| TIME | 같은 달 동일 시간대 4회 이상 + 월 전체 기록의 65% 이상 |

ARTIST → LOCATION → TIME 우선순위, 사용자·월별 최대 3개, 유사 후보 제외.
메모는 반복 키워드를 보조 Context로 사용한다. 학습형 AI/LLM은 아직 없다.

## 저장·수정·삭제 계약

- `memory_id`와 `content_hash`로 `CREATE` / `UPDATE` / `UNCHANGED`를 반환한다.
- Core는 memory_id UNIQUE + upsert를 사용한다. 엔진은 DB에 직접 쓰지 않는다.
- Moment 삭제나 월 이동으로 패턴이 사라질 때 `deactivated_memory_ids`를 반환할 수 있다.
  Core는 해당 Memory를 `is_active=false`로 갱신하고 조회·RE:PLAY에서 제외한다.
- 비활성화는 **명시적 scope + 완전한 월별 데이터 + 소유자/월이 있는 기존 Memory 스냅샷**에만 적용한다.
  scope를 생략하면 기존 호환 동작으로 분석·upsert 결과만 반환하고 비활성화를 지시하지 않는다.
- scope에는 `user_id`, `months`, `complete_month_history: true`, `history_revision`이 필요하다.
  기존 Memory에는 `user_id`, `period_month`, `memory_id`, `content_hash`, `is_active`를 보낸다.
- 응답의 scope/history_revision은 입력을 되돌려준다. **Core가 DB의 최신 revision을 원자적으로 비교해야**
  오래된 응답의 덮어쓰기를 막는다. 엔진 자체가 동시 요청 순서를 보장하지는 않는다.
- inactive Memory가 다시 생성되면 `is_active:false` 스냅샷에 대해 UPDATE를 반환한다.
  Core는 CREATE/UPDATE를 반영할 때 `is_active=true`로 설정한다.
- 요청 최대 1,000 Moments / 1,000 existing_memories, scope 최대 120개월.
  여러 달은 월별로 나눠 호출하되, 한 달을 페이지별로 따로 분석하면 안 된다.
  한 달 자체가 제한을 넘으면 서버 제한을 조정해야 하며 일부 기록을 complete라고 보내면 안 된다.

정확한 요청과 DB 반영 순서는 `docs/SPRING_BOOT_INTEGRATION.md`에 있다.

## 내부 인증

로컬 실행 기본 주소는 127.0.0.1이다. 서버 간 사용 시 OS 환경변수에 ASCII 서비스 토큰을 설정한다.
`.env.example`은 참고용이며 자동 로딩하지 않는다.

```powershell
$env:REON_ENGINE_TOKEN = "replace-with-a-random-ascii-service-secret"
```

Core는 `X-Service-Token` 헤더를 보낸다. 잘못된 요청 토큰은 401,
빈 문자열·비ASCII 서버 설정은 503이다. 토큰 미설정은 로컬 개발 모드이므로
외부 배포 시 반드시 토큰과 내부 네트워크 구성을 적용한다.

## 검증

기존 테스트 42개 + 회귀 테스트 18개, 총 **60개**.
시간 변환, 프론트/Core 입력, 아티스트 미확정, 토큰 예외, 잘못된 ID,
곡 ID 중복, 범위별 비활성화와 재활성화를 검사한다.

Google 로그인, Moment CRUD, DB 저장·조회, YouTube OAuth/Playlist는 Core 담당이며
실제 서비스 통합은 해당 기능 구현 후 검증해야 한다.
