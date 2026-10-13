# Re:on Backend

Java 21 / Spring Boot 4.1.1 / Gradle Wrapper

구현: `POST /api/v1/music/resolve` 및 Memory 목록·상세·읽음 API, Memory DB 처리와 FastAPI 분석 연동.
Memory 모듈은 mysql 프로필에서 활성화됩니다. 구현·연결 방법은 [MEMORY_IMPLEMENTATION.md](MEMORY_IMPLEMENTATION.md)를 참고하세요.
Auth/User, 실제 Moment CRUD, OAuth, Playlist는 아직 구현하지 않았습니다.

## 실행

JDK 21을 설치하고 JAVA_HOME을 실제 JDK 설치 경로로 지정하세요.

```bash
cd backend
export JAVA_HOME=/path/to/jdk21
export YOUTUBE_API_KEY='발급받은 키'
./gradlew bootRun
```

YouTube Data API v3가 활성화된 Google Cloud 프로젝트의 API 키가 필요합니다. `.env.example`은 참고용이며 `.env`는 자동 로딩되지 않습니다. 키 없이 서버를 시작할 수 있지만 정상 링크 조회에는 503이 반환됩니다.

```bash
curl -i -X POST http://localhost:8080/api/v1/music/resolve \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://music.youtube.com/watch?v=wJhWwt1OmT8&si=share"}'
```

응답: `videoId`, `title`, `channelTitle`, `thumbnailUrl`. 채널명을 아티스트로 정규화하지 않습니다. 썸네일이 없으면 null입니다. 시작 가이드 기준으로 기존 API 명세 v0.4의 `artist`와 `originalUrl`은 포함하지 않습니다.

HTTPS `music.youtube.com/watch`와 11자리 ID를 검증합니다. 공유 파라미터는 허용하고 중복 v, 외부 호스트, 잘못된 ID는 거부합니다. 고정된 Google videos.list 엔드포인트만 호출하며 연결 제한 3초, 읽기 제한 5초를 적용합니다.

| HTTP | code | 상황 |
| --- | --- | --- |
| 400 | INVALID_REQUEST | 빈 URL, 2048자 초과, 잘못된 JSON |
| 400 | INVALID_YOUTUBE_MUSIC_URL | 잘못된 URL 또는 ID |
| 404 | MUSIC_NOT_FOUND | 조회 가능한 영상 없음 |
| 503 | YOUTUBE_API_NOT_CONFIGURED | 키 누락 |
| 502 | YOUTUBE_API_ERROR | Google 오류, 연결 실패, 잘못된 외부 응답 |

오류는 `{ "code": "...", "message": "..." }` 형식입니다. 키 오류와 할당량 초과도 현재 502로 처리합니다.

## 테스트 / 빌드

```bash
./gradlew test
./gradlew bootJar
```

24개 테스트로 URL 검증, DTO 응답, 외부 오류 및 요청 검증을 확인합니다. Google 호출은 모킹하며 실제 키를 사용하는 조회는 별도 확인이 필요합니다.

## MySQL 프로필

기본 음악 조회는 DB 없이 실행됩니다. JPA / MySQL 의존성은 포함되어 있습니다.

```bash
export DB_URL='jdbc:mysql://localhost:3306/reon'
export DB_USERNAME='reon'
export DB_PASSWORD='로컬 DB 비밀번호'
./gradlew bootRun --args='--spring.profiles.active=mysql'
```

mysql 프로필은 Memory 테이블을 최초 생성하고 `ddl-auto=validate`로 검증합니다.
User/Moment 엔티티와 스키마는 아직 없으므로 실제 Moment 조회 어댑터 및 인증 연결이 필요합니다.

## 구조

- `music/controller`: HTTP 요청과 응답
- `music/dto`: 요청·응답 DTO
- `music/service/MusicService`: URL 검증 / videoId 추출
- `music/service/YouTubeClient`: Google API 호출 / 메타데이터 변환
- `global`: 공통 예외 처리

## Git에 올리기

`src`, `build.gradle`, `settings.gradle`, `gradlew`, `gradlew.bat`, `gradle/wrapper`, `.env.example`과 README를 올립니다. `build`, `.gradle`, `.idea`, `.env`, 키 파일은 올리지 않습니다. Wrapper JAR는 커밋에 필요합니다.

복원 당시 잘못 들어온 backend의 Expo 복제 파일과 빌드 캐시를 백업 폴더로 옮겼습니다. Git에서 보이는 해당 파일 삭제는 의도된 변경입니다. 루트의 프론트엔드 파일은 유지했습니다.
