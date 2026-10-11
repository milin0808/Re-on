# RE:ON Spring Boot ↔ FastAPI 연결 가이드

목표: Core Backend(Spring Boot)가 Moment 저장 후 Memory Engine을 호출하고, `memory_id`로 기존 Memory를 upsert한다.

## 추천 연동 구조

```text
[Frontend Moment 저장]
     |
     v
[Spring Boot POST /moments -> DB 저장 완료]
     |
     v
[Spring Boot DB에서 user_id의 분석 대상 Moment 조회]
     |
     +----> [Spring Boot DB에서 같은 사용자 Memory ID + content_hash 조회]
     |
     v
[POST http://memory-engine:8000/api/v1/memories/analyze]
     |
     v
[FastAPI: 규칙 분석 → Memory + sync_action + content_hash 반환]
     |
     v
[Spring Boot: CREATE/UPDATE는 memory_id 기준 UPSERT, UNCHANGED는 SKIP]
     |
     v
[Frontend Memory 목록 조회 / RE:PLAY]
```

**개발 환경:** `http://127.0.0.1:8000`으로 호출 (Spring Boot와 API가 같은 PC에서 실행되는 경우)

**서버 분리 시:** 내부 DNS 및 서비스 전용 토큰/HTTPS를 사용. `127.0.0.1`은 호출하는 컨테이너/호스트 자신의 루프백이므로 컨테이너 간 통신에는 사용할 수 없음.

## Request 예시

자세한 실제 데이터는 `examples/request.json` 참고.

```json
{
  "moments": [
    {
      "moment_id": "123",
      "user_id": "u123",
      "artist": "IU",
      "song_title": "밤편지",
      "recorded_at": "2026-08-11T23:00:00+09:00",
      "location": null,
      "memo": "집 가는 길",
      "track_id": null
    }
  ],
  "existing_memories": [
    {"memory_id": "mem_이미저장된ID", "content_hash": null}
  ]
}
```

- `user_id`: 인증받은 사용자 ID를 Spring Boot에서 세팅 (클라이언트 임의 값 그대로 신뢰하지 않기)
- `artist`: API가 반환한 채널명을 그대로 넣기보다 정규화된 아티스트 이름 권장
- `recorded_at`: 오프셋을 포함한 ISO 8601 (예: `+09:00` 또는 `Z`)
- `location`은 동의 기반 수집이며 사용자에게 속한 데이터만 전송
- `existing_memories`: Spring Boot의 실제 기존 DB 값으로 채우기
- 전체 사용자 히스토리 또는 월별 완전한 기록 세트를 보내야 생성 임계치 통계가 유효함

## 반환 결과

`memories[]`의 `sync_action`이 `CREATE`/`UPDATE`라면 DB 저장 대상으로 보고, `UNCHANGED`는 건너뛰세요.

```text
CREATE -> memory_id가 DB에 없다. insert/upsert.
UPDATE -> 같은 memory_id가 있지만 내용 해시가 다르다. update/upsert.
UNCHANGED -> 내용 해시도 동일하다. DB 변경 불필요.
```

**중요:** FastAPI는 DB에 접근하지 않습니다. `existing_memories`를 주지 않으면 매번 `CREATE`입니다.

**DB 제약 조건:** `memory_id`는 PK 또는 UNIQUE, 추가로 사용자별 조회 인덱스(user_id, period_month)를 권장합니다. 재시도·동시 요청 시 `sync_action`만으로는 원자적 중복 방지가 되지 않으므로 `memory_id` PK/UNIQUE 및 트랜잭션 처리가 필수입니다.

## Spring RestClient 호출 예시 (스케치)

이미 Core Backend에 `spring-boot-starter-restclient` 의존성이 포함된 것으로 확인했습니다. 아래 코드는 **DTO/Repository/보안 처리 연결 전의 통신 샘플**이며 프로젝트에 그대로 붙여 넣는 완성형 서비스는 아닙니다.

```java
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;

public class MemoryEngineClient {
    private final RestClient client;

    public MemoryEngineClient(String baseUrl, String serviceToken) {
        this.client = RestClient.builder()
                .baseUrl(baseUrl)
                .defaultHeader("X-Service-Token", serviceToken)
                .build();
    }

    public JsonNode analyze(Object momentDtos, Object existingMemoryDtos) {
        return client.post()
                .uri("/api/v1/memories/analyze")
                .contentType(MediaType.APPLICATION_JSON)
                .body(Map.of("moments", momentDtos,
                             "existing_memories", existingMemoryDtos))
                .retrieve()
                .body(JsonNode.class);
    }
}
```

실제 서비스에서는 `RestClient`에 **연결/읽기 타임아웃**, 재시도 상한, 에러 로깅(개인정보 제외), 서비스 토큰 설정 관리가 추가되어야 합니다. 사용자별 DB transaction 및 unique upsert까지 연결한 후 통합 테스트하세요.

## Moment 저장 이벤트 처리 시 주의

- 첫 MVP는 **Moment가 저장된 후 비동기로 Memory 분석 작업을 큐에 넣는 방식**을 권장합니다. 사용자가 노래 기록을 저장할 때 FastAPI 응답을 기다리도록 하면 분석 서버 오류가 Moment 저장 실패로 전파될 수 있습니다.
- MVP 단순 구현이라면 Spring Boot 트랜잭션 커밋 이후 분석 호출 + 실패 시 재시도 정책으로 시작할 수 있습니다.
- **단순히 `@Async`만 붙이면 서버 재시작 중 작업이 유실될 수 있으므로**, 운영에선 작업 큐 또는 주기적 재분석 보완을 권장합니다.
- 삭제된 Moment나 변경된 Moment가 기존 Memory에 어떤 영향을 주는지 제품 정책을 별도로 정하세요. 엔진은 오래된 Memory를 삭제하라고 지시하지 않습니다.
- Spring Boot 4 / Java 21 프로젝트의 실제 Entity와 DTO가 완성되면 그 이름에 맞게 JSON 매핑만 연결하면 됩니다.


## Spring Boot의 실제 음악 조회 DTO에 맞춘 어댑터 (2026-10-11 기준)

승환님의 `choiseunghwan` 브랜치 `MusicResolveResponse`는 다음 4개 필드만 반환합니다.

```json
{
  "videoId": "영상 ID",
  "title": "YouTube 영상 제목",
  "channelTitle": "YouTube 채널 이름",
  "thumbnailUrl": "썸네일 URL 또는 null"
}
```

**구현 완료된 API는 `POST /api/v1/music/resolve`뿐입니다.** Moment CRUD, 사용자 로그인,
Memory 저장은 아직 미구현입니다. 따라서 아래 구조는 연동 전까지 테스트용 제안 형식이며,
실제 Spring Boot의 Moment API 형식으로 확정된 것이 아닙니다.

### FastAPI 어댑터 API

기존 정규화 요청은 `POST /api/v1/memories/analyze`로 계속 보낼 수 있습니다.
별도로 `POST /api/v1/memories/analyze/core`를 추가하여 Spring Boot의 음악 조회
응답을 `music` 객체로 그대로 전달할 수 있도록 했습니다.

```json
{
  "moments": [
    {
      "momentId": "123",
      "userId": "u123",
      "recordedAt": "2026-08-11T23:00:00+09:00",
      "artist": "IU",
      "songTitle": "밤편지",
      "music": {
        "videoId": "wJhWwt1OmT8",
        "title": "YouTube 영상 제목",
        "channelTitle": "YouTube 채널 이름",
        "thumbnailUrl": null
      },
      "memo": "집 가는 길",
      "location": null
    }
  ],
  "existing_memories": []
}
```

- 음악 메타데이터: `music.videoId → track_id`, `music.title → song_title`.
- `songTitle`이 별도로 있으면 영상 제목 대신 사용합니다. YouTube `title`은
  `(Official MV)` 등이 붙어 실제 곡명과 다를 수 있습니다.
- 사용자·Moment 식별자 및 시간은 아직 **Core Moment API에 없는 필드**이므로
  Moment DB 구현 후 반드시 채워야 합니다.
- `artist`는 가능하면 정확한 아티스트 이름을 별도로 넣어야 합니다.
  `channelTitle`은 일반적으로 아티스트가 아니므로 **자동으로 대체하지 않습니다**.
  `IU - Topic`처럼 ` - Topic`으로 끝나는 채널명에 한해 임시 추출을 허용합니다.
  `SMTOWN` 같은 채널명만 있으면 `422`가 반환됩니다. 임의의 아티스트 추론은 하지 않습니다.
- 아티스트 별칭(현재 예: `아이유 ↔ IU`, `NCT127 ↔ NCT 127`)은
  `core_adapter.py`의 `ARTIST_ALIASES`에서 관리하며, 확실한 매핑만 추가합니다.
- 기존 API와 마찬가지로 `X-Service-Token` 인증, 사용자 혼합 제한,
  저장용 `memory_id`/`content_hash` 처리 원칙이 동일하게 적용됩니다.
- `examples/core_request.json`은 **가상 데이터**입니다. `TESTTRACKxx`는
  예제용 임의 ID이지 실제 YouTube 영상을 뜻하지 않습니다.

### 테스트

```powershell
cd memory-engine
.\run_tests.bat
.\run_server.bat
```

서버 실행 중 `http://127.0.0.1:8000/docs`의 `analyze/core`로
`examples/core_request.json` 내용을 전송하면 됩니다. 실제 Spring Boot 연동은
Moment CRUD 및 DB가 개발된 다음 진행해야 합니다.
