# 전달할 내용

아래 문구는 전달용 초안이다. 실제 메시지는 보내지 않았다.

## 승환에게

API 명세 v0.4 기준으로 Memory 목록·상세·읽음 API 3개, Memory Entity/Repository/Service,
DB 저장·갱신·비활성화와 revision 검증까지 내 담당으로 구현했다.
Memory 관련 코드는 `backend/src/main/java/com/reon/backend/memory`에 있고,
연결 방법은 `backend/MEMORY_IMPLEMENTATION.md`에 적었다.

네 Auth/Moment 코드에 아래 부분을 연결해줘.

1. 인증 완료 요청에서 검증된 DB userId를 전달해줘. 지금 Memory는 `Principal.getName()`의 숫자 userId를 사용한다.
   네 인증 구조에서 Principal name이 이메일 등 다른 값이어야 한다면, 인증 완료 후 DB userId를 꺼내는 방식을
   네가 정해서 알려줘. 그 부분은 내 MemoryUserResolver를 네 구조에 맞추겠다.
2. 네 Moment Repository로 `MomentHistoryReader.readCompleteMonth(userId,month)`를 구현해 빈으로 등록해줘.
   본인 기록의 한국 시간 기준 한 달 전체여야 하고, 페이지 일부를 넘기면 안 된다.
   Moment 필드 형식은 명세의 `music`, `recordedAt`, `memo`, 좌표형 `location`에 맞췄다.
3. Moment 생성·수정·삭제의 같은 `@Transactional` 메서드에서 **실제 쓰기 전에**
   `MemoryHistoryService.recordChange(userId,oldRecordedAt,newRecordedAt)`를 호출해줘.
   메모만 수정할 때도 필요하고, 날짜가 다른 달로 옮겨지면 기존 월·새 월 모두 처리한다.
   네 CRUD가 실패하면 revision 변경과 Memory 비활성화도 함께 롤백된다.
4. 회원 탈퇴 트랜잭션에서 실제 사용자 삭제 전에 `deleteUserMemories(userId)`를 호출해줘.
5. RE:PLAY는 `MemoryService.replayVideoIds(userId,memoryId)`로 곡 ID를 받아줘.
   본인 활성 Memory만 허용하고 videoId를 중복 제거한다. 빈 목록이면 Playlist를 만들지 말아줘.
   OAuth·Playlist 생성·실제 영상 추가 실패 처리는 네 RE:PLAY 쪽에서 처리해줘.

Memory 분석은 커밋 이후 DB에 쌓인 대기 작업을 자동 처리한다. Core CRUD에서 분석 HTTP를 직접 호출할 필요는 없다.
외부 Memory API ID는 숫자 DB ID이고, 내부 엔진 ID `mem_...`는 별도 저장한다.
상세 GET은 읽음을 바꾸지 않고, 읽음 PATCH가 `readAt`을 저장한다. 갱신·재활성화에도 읽음은 유지한다.
Moment가 바뀌면 그 월의 이전 Memory를 잠시 숨겨 수정·삭제 전 메모가 노출되지 않게 했다.

아티스트는 네가 전달하는 원본 artist를 유지하고, 미확정이면 null로 받는다.
기존 `channelTitle`도 받을 수 있지만 일반 YouTube 채널명을 artist로 만들지 않는다.
artist 표기를 통일하는 방식은 네 음악 메타데이터 처리 방식으로 정해서 보내줘. 엔진 입력은 그 결과에 맞추겠다.
좌표 위치는 일단 소수점 셋째 자리 반올림 셀로 분석한다. 실제 장소명을 임의로 만들지 않는다.

Spring의 `MEMORY_ENGINE_TOKEN`과 FastAPI의 `REON_ENGINE_TOKEN`은 동일한 랜덤 ASCII 값으로 설정해줘.
Memory DB 모듈은 `mysql` 프로필에서 활성화된다.

## 유진 / Memory 프론트 담당에게

명세 v0.4의 Memory API 3개를 그대로 구현했다.

- `GET /api/v1/memories`: `{content:[...]}`. 목록에 `id,title,description,momentCount,startDate,endDate,isNew`가 온다.
- `GET /api/v1/memories/{memoryId}`: `contexts`와 포함 `moments`까지 반환한다.
- `PATCH /api/v1/memories/{memoryId}/read`: 요청 본문 없이 호출하고 `{id,isNew:false}`를 받는다.

상세 GET이 성공해서 화면을 보여준 다음 읽음 PATCH를 호출해줘. 목록에 진입하는 것만으로 읽음 처리하지 않는다.
PATCH가 성공하면 목록 캐시의 해당 항목 `isNew`를 false로 바꾸거나 목록을 다시 조회하면 된다.
읽음 PATCH는 재시도해도 동일하게 처리된다. 내용 갱신·재활성화 때문에 다시 새 배지가 생기지는 않는다.

화면과 RE:PLAY 요청에는 숫자 Memory id를 사용해줘. 내부 `mem_...`를 프론트에 전달하지 않는다.
`contexts`의 TIME에는 value가 있고, PLACE는 value 없이 label만 올 수 있다.
artist/memo는 null일 수 있고, 좌표 기반 PLACE label은 장소명 대신 좌표 셀로 표시된다.

Moment 수정·삭제 후 재분석이 끝날 때까지 해당 월의 Memory가 잠시 목록에서 제외될 수 있다.
그동안 열어둔 상세가 `MEMORY_NOT_FOUND` 404면 목록을 갱신해줘.
FastAPI 엔진을 앱에서 직접 호출하지 말고 Spring Memory API만 호출해줘.
로그인·Moment API가 아직 없어서 실제 앱 연동은 승환의 인증·Moment 구현 연결 후 진행한다.

프론트는 이 패키지에서 수정하지 않았다. 기존 lint/typecheck의 CSS 타입 오류와 웹 테마 hook 오류는
Memory 모듈과 별개로 현재 프론트에 남아 있다.
