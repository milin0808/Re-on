# 포함 파일

Core 실행 기반은 choiseunghwan 9a80dbf 그대로이며, Memory 변경과 구분해 표시했다.
코드의 동작 기준은 `APPLY_README.md`와 `backend/MEMORY_IMPLEMENTATION.md`를 참고한다.

| 파일 | 구분 |
|---|---|
| `backend/.env.example` | 기존 파일 수정 |
| `backend/.gitattributes` | Core 기존 실행 기반 그대로 포함 |
| `backend/.gitignore` | Core 기존 실행 기반 그대로 포함 |
| `backend/MEMORY_IMPLEMENTATION.md` | 신규 구현 / 문서 |
| `backend/README.md` | 기존 파일 수정 |
| `backend/build.gradle` | 기존 파일 수정 |
| `backend/gradle/wrapper/gradle-wrapper.jar` | Core 기존 실행 기반 그대로 포함 |
| `backend/gradle/wrapper/gradle-wrapper.properties` | Core 기존 실행 기반 그대로 포함 |
| `backend/gradlew` | Core 기존 실행 기반 그대로 포함 |
| `backend/gradlew.bat` | Core 기존 실행 기반 그대로 포함 |
| `backend/settings.gradle` | Core 기존 실행 기반 그대로 포함 |
| `backend/src/main/java/com/reon/backend/ReonBackendApplication.java` | Core 기존 실행 기반 그대로 포함 |
| `backend/src/main/java/com/reon/backend/global/ApiException.java` | Core 기존 실행 기반 그대로 포함 |
| `backend/src/main/java/com/reon/backend/global/GlobalExceptionHandler.java` | Core 기존 실행 기반 그대로 포함 |
| `backend/src/main/java/com/reon/backend/memory/config/MemoryConfiguration.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/memory/controller/MemoryApiExceptionHandler.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/memory/controller/MemoryController.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/memory/dto/MemoryResponses.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/memory/engine/EngineContract.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/memory/engine/MemoryEngineClient.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/memory/entity/Memory.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/memory/entity/MemoryHistoryRevision.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/memory/entity/MemoryMoment.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/memory/port/MomentHistoryReader.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/memory/repository/MemoryHistoryRevisionRepository.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/memory/repository/MemoryRepository.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/memory/security/MemoryUserResolver.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/memory/service/MemoryHistoryService.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/memory/service/MemoryResultService.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/memory/service/MemoryService.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/memory/service/MemorySnapshotService.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/memory/service/MemorySyncCoordinator.java` | 신규 구현 / 문서 |
| `backend/src/main/java/com/reon/backend/music/controller/MusicController.java` | Core 기존 실행 기반 그대로 포함 |
| `backend/src/main/java/com/reon/backend/music/dto/MusicResolveRequest.java` | Core 기존 실행 기반 그대로 포함 |
| `backend/src/main/java/com/reon/backend/music/dto/MusicResolveResponse.java` | Core 기존 실행 기반 그대로 포함 |
| `backend/src/main/java/com/reon/backend/music/service/MusicService.java` | Core 기존 실행 기반 그대로 포함 |
| `backend/src/main/java/com/reon/backend/music/service/YouTubeClient.java` | Core 기존 실행 기반 그대로 포함 |
| `backend/src/main/resources/application-mysql.properties` | 기존 파일 수정 |
| `backend/src/main/resources/application.properties` | 기존 파일 수정 |
| `backend/src/main/resources/db/memory-schema.sql` | 신규 구현 / 문서 |
| `backend/src/test/java/com/reon/backend/ReonBackendApplicationTests.java` | Core 기존 실행 기반 그대로 포함 |
| `backend/src/test/java/com/reon/backend/memory/MemoryEngineClientTests.java` | 신규 구현 / 문서 |
| `backend/src/test/java/com/reon/backend/memory/MemoryPersistenceTests.java` | 신규 구현 / 문서 |
| `backend/src/test/java/com/reon/backend/memory/MemoryRealEngineTests.java` | 신규 구현 / 문서 |
| `backend/src/test/java/com/reon/backend/music/controller/MusicControllerTests.java` | Core 기존 실행 기반 그대로 포함 |
| `backend/src/test/java/com/reon/backend/music/service/MusicServiceTests.java` | Core 기존 실행 기반 그대로 포함 |
| `backend/src/test/java/com/reon/backend/music/service/YouTubeClientTests.java` | Core 기존 실행 기반 그대로 포함 |
| `backend/src/test/resources/application-memory-test.properties` | 신규 구현 / 문서 |
| `memory-engine/models.py` | 기존 파일 수정 |
| `memory-engine/core_adapter.py` | 기존 파일 수정 |
| `memory-engine/README.md` | 기존 파일 수정 |
| `memory-engine/docs/SPRING_BOOT_INTEGRATION.md` | 기존 파일 수정 |
| `memory-engine/examples/response.json` | 기존 파일 수정 |
| `memory-engine/tests/test_api_v04.py` | 신규 구현 / 문서 |
| `APPLY_README.md` | 신규 구현 / 문서 |
| `TEAM_HANDOFF.md` | 신규 구현 / 문서 |
| `VALIDATION.md` | 신규 구현 / 문서 |
| `FILE_LIST.md` | 이 목록 |
