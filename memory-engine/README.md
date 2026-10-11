# 🎧 RE:ON — FastAPI Memory Engine MVP v0.2

**Moment(음악·시간·위치·메모) → 패턴 탐지 → Memory 자동 생성**을 담당하는 Python 기반 AI 백엔드 프로토타입입니다.

> 이 단계는 **학습형 AI/LLM이 아닌 규칙 기반 패턴 분석 엔진**입니다. Spring Boot의 Moment DB·로그인·YouTube 연동과는 분리되어 있으며, HTTP API로 연결할 준비가 되어 있습니다.

## 1. Windows에서 가장 쉽게 실행하기

**준비물:** Python 3.10 이상 + 첫 실행 시 인터넷(라이브러리 설치용)

1. ZIP 파일 압축을 풉니다.
2. 압축 해제한 `memory-engine` 폴더에 들어갑니다.
3. **`run_server.bat`를 더블클릭**합니다.
   - 프로젝트별 가상 환경 `.venv` 생성 후 의존성 설치
   - 주소 **http://127.0.0.1:8000** 으로 서버 시작
4. 서버 창을 닫지 않은 채 브라우저에서 **http://127.0.0.1:8000/docs** 를 엽니다.
5. Swagger UI의 `POST /api/v1/memories/analyze` → **Try it out** → `examples/request.json`의 내용을 붙여 넣어 **Execute**합니다.
6. 또는 서버를 켠 상태에서 **`try_api.bat`** 를 더블클릭하면 예제 데이터를 API에 보내고 `outputs/api_response.json`으로 결과를 저장합니다.

서버 종료: `run_server.bat` 창에서 `Ctrl+C`.

> Windows에서 `.bat`가 실행되지 않으면 `py --version`으로 Python 설치 여부를 확인하세요. **처음 실행할 때만** `pip install`을 위한 인터넷이 필요합니다.

## 2. Mac / Linux / 터미널 실행

```bash
cd memory-engine
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

API 문서: <http://127.0.0.1:8000/docs>

다른 터미널에서 `python try_api.py` 또는 `curl`로 요청을 전송할 수 있습니다.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/memories/analyze \
  -H 'Content-Type: application/json' \
  --data-binary @examples/request.json
```

오프라인 CLI 데모는 기존 그대로 동작합니다: `python main.py`. 결과: `outputs/memories.json`.

## 3. API

| Method | Endpoint | 동작 |
| --- | --- | --- |
| `GET` | `/health` | 서버 상태 / 버전 |
| `GET` | `/docs` | Swagger API 문서 |
| `POST` | `/api/v1/memories/analyze` | 한 사용자의 Moment 목록을 분석해 Memory와 변경 상태 반환 |

**요청 예:**

```json
{
  "moments": [
    {
      "moment_id": "1",
      "user_id": "demo_user_1",
      "artist": "NCT 127",
      "song_title": "Fact Check",
      "recorded_at": "2026-07-03T19:30:00+09:00",
      "location": "체조경기장",
      "memo": "집 가는 길",
      "track_id": null
    }
  ],
  "existing_memories": []
}
```

`moments`는 **필수 배열**입니다. `moment_id`, `user_id`, `artist`, `song_title`, `recorded_at` 필수; `location`, `memo`, `track_id`는 선택입니다. 날짜는 **ISO 8601과 시간대(+09:00 또는 Z) 필수**입니다. 한 API 요청에서 다른 사용자들을 섞을 수 없으며, 같은 사용자에 중복된 `moment_id`가 있으면 `422`를 반환합니다. `moments`는 최대 1000개입니다.

한 개의 Moment만으로는 패턴 임계치에 도달하지 않으므로 Memory 결과가 빈 배열인 게 정상입니다. 데모에서는 `examples/request.json`에 샘플 20개가 있습니다.

**응답 예 (축약):**

```json
{
  "meta": {
    "input_moments": 20,
    "generated_memories": 2,
    "create_count": 2,
    "update_count": 0,
    "unchanged_count": 0,
    "engine_version": "0.2.0",
    "algorithm": "rules-v1"
  },
  "memories": [
    {
      "memory_id": "mem_...",
      "user_id": "demo_user_1",
      "type": "ARTIST",
      "title": "NCT 127과 함께한 7월",
      "description": "...",
      "period": {"month": "2026-07", "start": "2026-07-03", "end": "2026-07-16"},
      "moment_ids": ["1", "2", "3"],
      "tracks": [{"track_id": null, "artist": "NCT 127", "song_title": "Fact Check"}],
      "context": {"pattern_key": "nct 127", "count": 8},
      "content_hash": "64자리 SHA-256 해시",
      "sync_action": "CREATE"
    }
  ]
}
```

위 응답은 **스키마 설명용 축약**이며 실제 반환 JSON은 `outputs/api_response.json` 또는 `examples/response.json`에 있습니다.

## 4. 중요: 중복 생성 방지 방식

이 엔진은 **상태를 저장하지 않는(stateless) 서비스**입니다. *Memory ID와 콘텐츠 해시를 안정적으로 생성하지만 DB에 저장하지는 않습니다.* **Spring Boot가 DB에 `memory_id` UNIQUE 제약을 적용하고 upsert해야** 재시도/동시 요청 상황에서도 실제 중복 저장을 방지할 수 있습니다.

1. Spring Boot가 해당 사용자의 Moment들을 조회합니다.
2. 같은 사용자의 DB에 존재하는 Memory 각각에서 `memory_id`와 `content_hash`를 읽어 `existing_memories`에 첨부합니다.
3. FastAPI가 각 Memory에 아래 상태를 표시합니다.
   - `CREATE`: DB 스냅샷에 해당 ID가 없을 때
   - `UPDATE`: ID는 있지만 내용이 바뀌었거나 해시가 제공되지 않았을 때
   - `UNCHANGED`: ID와 해시가 모두 같을 때
4. Spring Boot는 `CREATE` / `UPDATE`를 **memory_id 기준 upsert** 하고, `UNCHANGED`는 건너뜁니다.

**예시: 동일한 Memory가 이미 DB에 존재하는 경우의 다음 요청**

```json
{
  "moments": ["(기존과 동일한 실제 Moment 객체들)"],
  "existing_memories": [
    {"memory_id": "mem_실제반환ID", "content_hash": "실제반환된64자리해시"}
  ]
}
```

> 위의 `moments` 문자열은 설명용 표현이며 유효한 API 입력은 아닙니다. 실제 요청에는 Moment 객체 배열을 보내세요.
>
> `existing_memories`를 생략하면 **매 요청이 CREATE로 표시됩니다**. 이 API 단독으로는 DB 중복 저장을 막지 못합니다. 권장 호출·DB 정책은 `docs/SPRING_BOOT_INTEGRATION.md` 참고.

**중요한 처리 정책:** 패턴이 사라진 Memory를 엔진이 자동 삭제하지는 않습니다. 사용자 삭제/비노출/갱신 주기는 별도의 백엔드 정책입니다. API 호출 시 **대상 기간에 필요한 전체 Moment**를 전송해야 통계가 왜곡되지 않습니다.

## 5. 패턴 탐지 기준 (초기 실험값)

| 유형 | 기본 조건 |
| --- | --- |
| 아티스트 `ARTIST` | 같은 달 동일 아티스트 3회 이상 + 해당 월 40% 이상 |
| 장소 `LOCATION` | 같은 달 동일 위치 3회 이상 + 해당 월 50% 이상 |
| 시간대 `TIME` | 같은 달 동일 시간대 4회 이상 + 해당 월 65% 이상 |

기본 우선순위: `ARTIST → LOCATION → TIME` / 사용자·월별 최대 3개 / Moment 중복도가 큰 후보 제외. 설명은 데이터에서 확인한 사실만 사용합니다. 상세 규칙은 `pattern_detector.py`.

## 6. 테스트

Windows: **`run_tests.bat`** 더블클릭

Mac/Linux/PowerShell:

```bash
python -m unittest discover -s tests -v
```

- 기존 엔진 테스트 16개 + FastAPI 테스트 15개 = **31개**
- 데이터 검증, 시간대 누락, 사용자 혼합 거부, 안정적 ID, 중복 비교, 변경 시 업데이트, API 토큰 인증, Swagger 스키마를 테스트합니다.

## 7. 주요 파일

```text
memory-engine/
  api.py                   # GET /health, POST /api/v1/memories/analyze
  api_models.py            # Pydantic 입출력 스키마
  sync.py                  # SHA-256 내용 해시 및 CREATE/UPDATE/UNCHANGED
  models.py                # Moment 입력 검증
  context_analyzer.py      # Context 분석
  pattern_detector.py      # 규칙 기반 패턴 탐지
  memory_generator.py      # Memory 생성
  main.py                  # 기존 CLI 프로토타입
  requirements.txt         # FastAPI/Uvicorn/Pydantic/httpx
  data/sample_moments.json
  examples/request.json    # Swagger/HTTP 실험용 샘플
  examples/response.json   # 실제 샘플 응답
  tests/test_memory.py
  tests/test_api.py
  run_server.bat
  try_api.bat / try_api.py
  run_tests.bat
  docs/SPRING_BOOT_INTEGRATION.md
```

## 8. 보안 및 배포

로컬 실험용 실행은 `127.0.0.1`에만 바인딩합니다. **공용 인터넷에 토큰 없이 절대 노출하지 마세요.** 운영 환경에서는 개인 네트워크로 연결하고, `REON_ENGINE_TOKEN` 환경 변수를 설정해 내부 서비스 토큰을 검증하며 HTTPS/프록시 인증 및 사용자별 권한 검사를 Spring Boot에서 처리하세요. 샘플은 가상 데이터이며 실제 사용자의 위치·메모·토큰을 Git에 넣지 마세요.

PowerShell(서버 실행 전에 설정):

```powershell
$env:REON_ENGINE_TOKEN = "로컬테스트용-임의의-긴-비밀문자열"
```

이 경우 `X-Service-Token` 헤더를 보내야 분석 API 접근이 허용됩니다. `GET /health`는 상태 점검용으로 인증되지 않습니다.

## 9. 현 단계의 한계

- 실제 DB 저장, Google OAuth 및 YouTube 재생목록 생성 **미구현** (Core Backend 담당)
- 메모 감정·주제 이해, LLM 제목 생성 **미구현** (현재는 키워드+템플릿)
- Memory 삭제/재생성, 아티스트 식별자 정규화, 시간대 변경 정책, 사용자 데이터 보안은 통합 과정에서 별도 처리 필요
- **GitHub 저장소로 자동 업로드하지 않았습니다.** ZIP에 담긴 `memory-engine` 폴더를 프로젝트 개인 브랜치에 추가해 PR을 생성하세요.
