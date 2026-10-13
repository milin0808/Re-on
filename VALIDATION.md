# 검증 기록

검증일: 2026-10-11. 기준 브랜치: minjoung f544ecd + choiseunghwan 9a80dbf.

| 항목 | 결과 |
|---|---|
| FastAPI 단위·회귀 테스트 | 67개 통과 |
| Spring 전체 테스트 | 48개 통과, 실패·오류·skip 0 |
| 기존 Core 테스트 | 24개 통과 |
| Memory DB/API 테스트 | 20개 통과 |
| MemoryEngineClient 테스트 | 3개 통과 |
| 실제 FastAPI ↔ Spring ↔ H2 저장 통합 | 1개 통과 |
| Spring bootJar | 성공 |
| git diff --check | 통과 |

Java 21.0.12.1, Gradle 9.7.1, Spring Boot 4.1.1, Python 3.12를 사용했다.
Spring은 H2 MySQL 모드에서 배포용 schema SQL을 실행한 뒤 Hibernate validate로 검사했다.
Mockito 자체 attach가 제한된 검증 환경이어서 기존 Core 테스트에는 명시적 Mockito javaagent를 사용했다.
이 환경용 경로·인증서·프록시 설정은 코드 패키지에 포함하지 않았다.

실제 FastAPI 통합은 모킹하지 않고 localhost HTTP로 호출했다. 테스트 fixture Moment를 읽어서
실제 엔진 결과로 Memory 생성·저장·상세 조회·읽음·메모 수정·재활성화·빈 달 비활성화를 확인했다.
실제 Google OAuth, 실제 Moment Entity/Repository, 실제 MySQL 서버, 실제 YouTube Playlist API는 사용하지 않았다.

프론트 lint/typecheck도 확인했다. 아래 기존 오류가 남아 있으며 이번 패키지는 프론트 소스를 수정하지 않는다.

- `src/components/animated-icon.web.tsx`: CSS module 타입 선언을 찾지 못함.
- `src/constants/theme.ts`: global.css side-effect import 타입 선언을 찾지 못함.
- `src/hooks/use-color-scheme.web.ts`: effect 내부 동기 setState lint 오류.

기본 `gradlew test`는 실제 엔진 통합 1개를 skip한다. 해당 테스트를 포함하려면
`backend/MEMORY_IMPLEMENTATION.md`의 `REON_MEMORY_ENGINE_INTEGRATION=true` 실행 방법을 사용한다.
