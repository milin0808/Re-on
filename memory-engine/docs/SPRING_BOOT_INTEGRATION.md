# Core Backend → Memory Engine 연결 계약 v0.3.0

현재 `choiseunghwan` 브랜치에서 실제 구현된 API는 `POST /api/v1/music/resolve`이며
응답은 `videoId`, `title`, `channelTitle`, `thumbnailUrl`이다.
Core의 Moment CRUD·Memory 저장·조회 API는 아직 없다. 이 문서는 엔진 측 계약이다.
외부 공개 API의 경로와 Entity/DTO는 Core가 확정하고, 엔진 어댑터는 그 DTO에 맞춘다.

## 요청

권장 내부 엔드포인트: `POST /api/v1/memories/analyze/core`.
기존 `/api/v1/memories/analyze`도 계속 지원한다.

| 현재 프론트 / Core | 엔진 내부 |
| --- | --- |
| `id` 또는 `momentId` | `moment_id` |
| `createdAt` 또는 `recordedAt` | `recorded_at` |
| Core가 채운 요청 `userId` / 개별 `userId` / `scope.user_id` | `user_id` |
| 개별 `artist`, 없으면 `track.artist` | `artist` |
| `songTitle`, 없으면 `track.title`, 없으면 `music.title` | `song_title` |
| `music.videoId`, 없으면 `track.videoId` | `track_id` |
| `location`, `memo` | 그대로 |

`music`과 `track` 중 하나는 필수다. 둘 다 보내면 `music.videoId`를 사용하며,
`track.videoId`도 있으면 두 ID가 같아야 한다. 프론트에는 없는 사용자 ID를
Core가 로그인 인증 정보에서 채운다. 클라이언트의 임의 사용자 ID를 신뢰하지 않는다.
썸네일/원본 메모 등 상세 화면 정보는 Core가 `moment_ids`로 원본 데이터를 결합한다.

아티스트 표기는 프론트/Core 값을 유지한다. 엔진에는 임의 별칭 매핑이 없다.
같은 아티스트의 서로 다른 언어 표기를 묶으려면 Core가 일관된 값을 확보해서 보낸다.
아티스트가 없으면 null을 보낼 수 있다. 일반 channelTitle은 artist로 사용하지 않는다.
` - Topic` fallback은 임시 처리이고, 별도 artist 값이 있으면 그것을 우선한다.

`Z`와 `+09:00` 입력 모두 가능하다. 분석 월·시간대는 Asia/Seoul로 변환한다.
프론트의 `createdAt`는 현재 기록 시각으로 연결한다. 추후 Core가 작성 시각과 기록 대상 시각을
분리한다면 사용자가 수정하는 기록 대상 시각을 recordedAt로 매핑한다.

## 사용자·월 범위 및 수정/삭제 반영

운영 호출은 해당 사용자의 **완전한 월별 기록**과 명시적인 scope를 보낸다.

```json
{
  "userId": "u123",
  "scope": {
    "user_id": "u123",
    "months": ["2026-07"],
    "complete_month_history": true,
    "history_revision": 17
  },
  "moments": [],
  "existing_memories": [
    {
      "memory_id": "mem_실제저장된ID",
      "user_id": "u123",
      "period_month": "2026-07",
      "content_hash": null,
      "is_active": true
    }
  ]
}
```

빈 moments는 이 사용자의 해당 월 기록이 전부 삭제된 경우에도 유효하다.
동일한 사용자의 스냅샷만 보내며, scope 사용 시 user_id/period_month 없는 기존 Memory는 422다.
다른 월의 스냅샷이 포함되어도 비활성화는 scope.months에 한정한다.
월 이동 수정은 **기존 월과 변경된 월**을 재분석한다. 생성/수정/삭제의 DB 커밋 이후 호출한다.

기존 scope 없는 호출은 분석과 변경 상태 비교만 수행한다. 누락된 Memory를 비활성화하지 않는다.
완전한 기록을 보장하지 못한 페이지나 최근 N개만 보내고 complete_month_history를 true로 표시하면 안 된다.
요청당 1,000 Moments가 상한이다. 월별로 나눌 수 있지만 한 달의 기록이 1,000개를 넘으면
제한을 조정하거나 별도 집계 경로를 구현해야 한다. 한 달을 여러 페이지로 분석하면 통계가 왜곡된다.

## 응답과 Core의 DB 처리

| 응답 | Core 처리 |
| --- | --- |
| `CREATE` / `UPDATE` | memory_id UNIQUE 기준 upsert, content_hash 저장, is_active=true |
| `UNCHANGED` | 내용 갱신 생략 |
| `deactivated_memory_ids` | **동일 사용자·scope 월을 다시 확인**하고 is_active=false |
| `scope.history_revision` | 최신 Moment 데이터 revision과 비교; 오래된 응답은 폐기 |
| `replay_available=false` | 곡 ID 확보 전 RE:PLAY 불가로 처리 |

비활성화된 Memory는 목록/상세/RE:PLAY 대상에서 제외한다. 다시 패턴 조건을 충족하면
같은 ID를 활성화한다. inactive 스냅샷은 is_active=false를 포함해야 하며,
엔진은 같은 content_hash여도 UPDATE를 반환하여 재활성화할 수 있게 한다.

권장 revision 규칙은 사용자별 Moment 생성·수정·삭제 때 단조 증가하는 정수다.
Core는 분석 입력과 revision을 일관된 DB 스냅샷으로 읽고, 결과 적용 시
사용자 행 lock 또는 조건부 갱신으로 revision 비교와 Memory 반영을 같은 트랜잭션에서 처리한다.
revision이 다르면 결과를 반영하지 않고 최신 데이터로 재분석한다.
엔진은 revision을 그대로 반환할 뿐, DB 상태나 작업 순서를 직접 검증하지 않는다.

반환 tracks는 11자리 ID를 가진 항목만 포함하며 ID로 중복 제거한다.
이 검증은 실제 영상 존재/권한/삭제 여부 검증이 아니다. Playlist 생성 시 Core가 실패한 곡을 처리한다.
Moment는 곡 ID가 없어도 기록·분석할 수 있고, 모든 포함 기록은 moment_ids에 남는다.

## Spring Boot 4.1 통신 예시

현재 프로젝트는 Jackson 3을 기본 사용하므로 `tools.jackson.databind.JsonNode`를 사용한다.
다음은 내부 HTTP 통신 예시이며 DTO/Repository/작업 큐 구현은 포함하지 않는다.

```java
import java.time.Duration;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;
import tools.jackson.databind.JsonNode;

public class MemoryEngineClient {
    private final RestClient client;

    public MemoryEngineClient(String baseUrl, String serviceToken) {
        var factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(3));
        factory.setReadTimeout(Duration.ofSeconds(10));
        this.client = RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(factory)
                .defaultHeader("X-Service-Token", serviceToken)
                .build();
    }

    public JsonNode analyze(Object requestDto) {
        return client.post()
                .uri("/api/v1/memories/analyze/core")
                .contentType(MediaType.APPLICATION_JSON)
                .body(requestDto)
                .retrieve()
                .body(JsonNode.class);
    }
}
```

같은 PC에서 개발할 때 baseUrl은 `http://127.0.0.1:8000`이다.
컨테이너 간에는 서비스 DNS를 사용한다. 엔진을 다른 컨테이너에서 접근하려면
내부 네트워크에서 0.0.0.0으로 바인딩하고 서비스 토큰을 설정한다.
Moment 저장 성공과 분석 실패를 분리하고, 커밋 후 작업 처리·제한된 재시도를 Core에서 구현한다.
서비스 토큰은 ASCII 임의 문자열을 OS 환경변수로 설정하며 `.env`는 자동 로딩되지 않는다.

## 테스트 예제

- `examples/core_request.json`: 기존 Core music 객체 + 제안된 Moment envelope.
- `examples/frontend_request.json`: 현재 프론트 필드 + Core가 채운 userId/music.
- `examples/scoped_request.json`: 완전한 월 범위 및 revision을 포함한 호출.
- `examples/response.json`: 실제 기본 API 샘플 응답.

TESTTRACKxx ID는 형식 검사와 데모용 임의 값이며 실제 YouTube 영상을 뜻하지 않는다.
사용자 로그인·DB·YouTube를 사용하는 통합 테스트는 Core 구현 후 수행한다.
