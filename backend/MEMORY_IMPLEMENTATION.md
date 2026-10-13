# Memory 구현 및 연결 방법

기준: API 명세 v0.4, `minjoung` f544ecd, `choiseunghwan` 9a80dbf.
김민정 담당은 FastAPI 엔진과 이 문서의 Spring Memory 모듈 전체다.

## 구현한 API

| Method | Endpoint | 응답 / 동작 |
|---|---|---|
| GET | `/api/v1/memories` | `{content:[...]}`; 본인의 활성 Memory만, endDate·id 내림차순 |
| GET | `/api/v1/memories/{memoryId}` | 명세의 title/description/기간/count/contexts/moments |
| PATCH | `/api/v1/memories/{memoryId}/read` | `{id,isNew:false}`; 본문 없음, 반복 호출 가능 |

외부에 Memory 생성·분석 호출 API는 추가하지 않았다. 엔진 URL은 프론트가 호출하지 않는다.
인증된 `Principal.getName()`은 **DB userId의 숫자 문자열**이어야 한다. 검증되지 않은 Bearer
문자열이나 클라이언트 userId를 직접 파싱해 로그인으로 인정하지 않는다.
인증 필터가 아직 없으므로 현재 HTTP 요청은 정상 Bearer라도 Principal이 없으면 401이다.
다른 사용자·비활성·없는 Memory는 모두 `MEMORY_NOT_FOUND` 404다.

## 확정한 동작

- 공개 Memory ID는 DB `Long`; 내부 `mem_...`는 별도 UNIQUE 컬럼에 보관한다.
- 상세 GET 자체는 읽음을 바꾸지 않는다. FE가 상세 조회 성공 후 PATCH를 호출한다.
- `readAt`을 저장한다. 내용 갱신·재활성화는 ID와 읽음 상태를 유지한다.
- 날짜·분석 월·시간대는 Asia/Seoul. DB 시각은 UTC로 정규화해 저장한다.
- Context는 `TIME(label,value)`와 반복 위치가 있는 경우 `PLACE(label)`이다.
- 좌표 위치는 소수점 셋째 자리 반올림 셀이다. 역지오코딩 및 '몇 m 이내' 판정은 하지 않는다.
- Moment 변경 트랜잭션에서 영향을 받는 월의 Memory를 즉시 비활성화하고 메모·곡 스냅샷을 지운다.
  재분석 전에는 목록·상세·RE:PLAY에서 잠시 제외된다. 개인정보 수정·삭제의 이전 값이 노출되지 않는다.
- 분석 기준: 월별 Artist 3개/40%, Location 3개/50%, Time 4개/65%; 월 최대 3 Memory.
- 한 Moment가 여러 패턴에 포함될 수 있다. 유사한 후보는 기존 엔진의 중복 억제 규칙을 따른다.

## 데이터와 트랜잭션

`reon_memory`, `reon_memory_moment`, `memory_history_revision`은 Memory 모듈 전용 테이블이다.
Moment Entity를 임의로 중복 정의하지 않고 상세용 스냅샷을 보관한다. User/Moment DB가 아직 없으므로
현재는 해당 테이블과의 외래키를 추가하지 않았다. 사용자 삭제는 아래 삭제 훅을 같은 트랜잭션에서 호출한다.

1. Moment 쓰기 전, 같은 트랜잭션에서 `MemoryHistoryService.recordChange`를 호출한다.
2. 사용자 revision 증가, 기존 Memory 비활성화, 대기 월 기록이 Moment 변경과 함께 커밋된다.
3. 5초 간격 작업자가 사용자 revision 행을 잠그고 한 달의 전체 Moment/기존 Memory를 읽는다.
4. DB 트랜잭션을 종료한 후 FastAPI HTTP 호출을 한다. DB 잠금 중 HTTP를 기다리지 않는다.
5. 결과 적용 트랜잭션이 같은 revision 행을 잠근다. 요청 revision이 최신 값과 다르면 결과 전체를 버린다.
6. 사용자·월·Moment ID·기간·곡 ID·비활성 대상 검증 후 전체 저장/갱신/비활성화를 원자적으로 반영한다.
7. 성공한 월만 대기 목록에서 제거한다. 오류·충돌·재시작 후에는 DB에 남은 작업을 재시도한다.

DB가 engine ID별 upsert를 보장하고, `sync_action` 문자열을 그대로 믿고 쓰지 않는다.
사용자 revision 잠금으로 서로 다른 분석 결과 적용과 Moment 쓰기를 직렬화한다.
읽음 동시 변경에는 Memory `@Version`과 행 잠금을 사용한다. 충돌한 분석은 롤백 후 다시 시도한다.
한 요청은 **한 달 전체**이며 최대 1000 Moment다. 초과하면 작업을 완료 처리하지 않고 남긴다.
월 1000개 이상을 지원하려면 FastAPI와 Spring 제한을 함께 확장한다. 페이지 일부를 complete로 보내지 않는다.
대기 월은 사용자당 최대 120개월이다. 초과 시 쓰기 트랜잭션을 실패시켜 분석 누락을 방지한다.
작업자는 사용자 ID 커서를 순환해 앞선 사용자의 오류 때문에 뒤의 사용자가 계속 밀리지 않게 한다.

## 승환 코드에 연결할 지점

### 1. 인증

Google 로그인/JWT 검증이 끝난 요청에 DB userId를 `Principal.getName()`으로 제공한다.
Memory API는 별도 사용자 ID 요청 필드를 받지 않는다. 기존 인증 객체의 name이 이메일이면
인증 필터의 verified userId와 MemoryUserResolver 사이에 어댑터를 추가한다.

### 2. Moment 읽기 어댑터

`MomentHistoryReader` 구현을 `@Component` 빈으로 등록한다. 실제 Moment Repository가 아직 없어
가짜 운영 어댑터는 넣지 않았다. 빈이 없으면 자동 분석은 기다리며 대기 작업을 유지한다.
테스트에서만 별도 fixture 어댑터를 사용한다.

구현 메서드: `readCompleteMonth(long userId, YearMonth month)`.
반드시 해당 사용자의 한 달 **전체** 기록을 반환한다. 메모·위치 변경과 삭제 후 상태도 반영한다.
조회 범위는 `month.atDay(1).atStartOfDay().atOffset(+09:00)` 이상,
다음 달 1일 같은 시각 미만이다. DB가 UTC면 두 경계를 같은 instant의 UTC로 변환해 조회한다.
반환 타입은 `MomentHistoryReader.Record(id,userId,recordedAt,music,memo,location)`이다.
music은 `EngineContract.Music(videoId,title,artist,channelTitle,thumbnailUrl,originalUrl)`;
location은 `EngineContract.Location(latitude,longitude)` 또는 null이다.
일반 YouTube 채널명으로 artist를 만들지 말고, 미확정 artist/videoId는 null로 보낸다.
모든 조회는 쓰기와 같은 DataSource 및 transaction manager를 사용한다.

### 3. Moment 생성·수정·삭제 훅

실제 Core CRUD의 `@Transactional` 메서드에서 **Moment INSERT/UPDATE/DELETE 전에** 호출한다.
Memory revision → Moment 행 순서로 잠그기 위한 순서다. 메모만 바뀌어도 호출한다.
조회 어댑터나 다른 쓰기 경로에서 이 순서를 거꾸로 잠그면 DB 교착 상태가 생길 수 있다.

```java
// 생성: 사용자 ID는 인증 정보에서 얻은 값
memoryHistoryService.recordChange(userId, null, newRecordedAt);
// 이후 실제 MomentRepository.save(...)

// 수정: 기존 recordedAt과 변경 후 recordedAt (메모만 수정하면 동일한 시각 두 개)
memoryHistoryService.recordChange(userId, oldRecordedAt, newRecordedAt);
// 이후 실제 Moment 수정/저장

// 삭제
memoryHistoryService.recordChange(userId, oldRecordedAt, null);
// 이후 실제 MomentRepository.delete(...)

// 회원 탈퇴: revision을 잠근 다음 Memory와 대기 작업 삭제; 실제 User 삭제 전에 호출
memoryHistoryService.deleteUserMemories(userId);
```

이 훅은 `Propagation.MANDATORY`라 별도 트랜잭션 없이 호출하면 실패한다.
Core 트랜잭션이 롤백되면 revision, 비활성화, 대기 작업도 함께 롤백된다.
Core CRUD 안에서 `synchronizeNext()`를 호출하지 않는다. 커밋 이후 자동 작업자가 처리한다.
기존 Moment 일괄 반영도 사용자·월마다 같은 트랜잭션에서 훅을 호출해 초기 분석을 요청한다.

### 4. RE:PLAY

최승환의 RE:PLAY 서비스에서 `memoryService.replayVideoIds(userId,memoryId)`를 사용한다.
본인 활성 Memory의 중복 제거된 videoId 목록만 반환한다. 빈 목록이면 Playlist를 만들지 않는다.
OAuth/실제 영상 접근성/Playlist 생성 오류는 RE:PLAY 서비스가 처리한다.

## 실행

JDK 21 및 Python 3.10 이상이 필요하다. MySQL DB는 먼저 생성한다.
`mysql` 프로필에서 Memory 테이블 초기 생성 SQL을 실행하고 Hibernate `validate`로 검증한다.
이 SQL은 현재 테이블 최초 설치용이다. 이미 설치한 테이블의 컬럼 변경은 자동 처리하지 않는다.

PowerShell 터미널 1:

```powershell
cd C:\Users\milan\reon\Re-on\memory-engine
$env:REON_ENGINE_TOKEN = "replace-with-a-random-ascii-token"
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

PowerShell 터미널 2:

```powershell
cd C:\Users\milan\reon\Re-on\backend
$env:DB_URL = "jdbc:mysql://localhost:3306/reon"
$env:DB_USERNAME = "reon"
$env:DB_PASSWORD = "DB 비밀번호"
$env:MEMORY_ENGINE_URL = "http://127.0.0.1:8000"
$env:MEMORY_ENGINE_TOKEN = "replace-with-a-random-ascii-token"
.\gradlew.bat bootRun --args="--spring.profiles.active=mysql"
```

두 터미널의 토큰 값을 같은 랜덤 ASCII 값으로 바꾼다.
기본 프로필은 승환의 DB 없는 음악 조회 동작을 유지한다. Memory API는 mysql 프로필에서 활성화한다.
배포 DB 계정에 DDL 권한을 주지 않는 경우 관리자가 `db/memory-schema.sql`을 먼저 실행한 다음
`spring.sql.init.mode=never`로 시작한다. 외부 데이터 전송은 내부 서비스 토큰으로 보호한다.

## 검증

```powershell
cd backend
.\gradlew.bat test
.\gradlew.bat bootJar
cd ..\memory-engine
python -m unittest discover -s tests -v
```

Spring 기본 테스트는 H2 MySQL 모드에서 **실제 설치 SQL + Hibernate validate**를 사용한다.
실제 Python 엔진 HTTP 왕복 검증은 같은 test 토큰으로 FastAPI를 시작한 뒤 실행한다.

```powershell
# 터미널 1 (memory-engine)
$env:REON_ENGINE_TOKEN = "reon-local-integration-token"
python -m uvicorn api:app --host 127.0.0.1 --port 8000
# 터미널 2 (backend)
$env:REON_MEMORY_ENGINE_INTEGRATION = "true"
.\gradlew.bat test --tests "*MemoryRealEngineTests" --rerun-tasks
```

테스트 토큰은 실제 서비스에서 쓰지 않는다. 테스트 결과와 남은 검증 범위는 패키지 `APPLY_README.md`에 적었다.
