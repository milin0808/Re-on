# 적용 방법 — Memory 구현 추가 v0.4

`Reon_API_명세서_v0.4.md`에 맞춰 김민정 담당 코드를 추가했다.
수정 기준은 `minjoung` f544ecd 및 `choiseunghwan` 9a80dbf다.

## 덮어쓰기

1. 압축을 풀고 기존 `C:\Users\milan\reon\Re-on`을 열어둔다.
2. 압축 안의 **backend**, **memory-engine**을 Re-on 루트의 같은 이름 폴더에 복사·덮어쓴다.
   기존 memory-engine 폴더를 삭제하지 않는다. 이번 ZIP에는 엔진 변경 파일만 있다.
3. `TEAM_HANDOFF.md`, `APPLY_README.md`, `FILE_LIST.md`, `VALIDATION.md`도 루트에 복사하면 PR에서 확인하기 편하다.
4. `backend/MEMORY_IMPLEMENTATION.md`에 적힌 환경변수를 설정하고 mysql 프로필로 실행한다.

현재 minjoung PR에는 backend가 없어, 승환 브랜치의 실행 기반과 기존 음악 코드를 그대로 포함했다.
Memory 구현 외의 기존 음악 API 동작은 유지했다. 동일한 Core 브랜치를 나중에 합칠 때 수정한 설정
파일은 충돌할 수 있으므로 `FILE_LIST.md`의 변경 파일을 기준으로 Memory 설정을 유지한다.
승환 코드에 연결할 인증·Moment 조회·변경 훅은 `TEAM_HANDOFF.md`에 정리했다.

## 추가한 범위

- FastAPI: 명세의 music.artist/originalUrl 및 좌표형 location 지원, 기존 채널/프론트 형식 호환.
- Spring: Memory 목록·상세·읽음 API 3개와 명세 응답 DTO, 소유자·활성 여부 검증.
- Memory Entity/Repository/Service와 Memory 상세 Moment 스냅샷 저장.
- Memory DB 저장·갱신·비활성화·재활성화. 읽음 및 숫자 ID 유지.
- 사용자별 revision 행 잠금, 최신 revision 검증과 결과 전체 반영을 같은 트랜잭션에서 처리.
- 사용자·월·Moment ID·날짜·곡 ID·비활성 대상 검증. 오래된 분석 결과는 전체 폐기.
- Moment 변경 트랜잭션과 함께 저장되는 재분석 대기 월, 커밋 이후 자동 분석 및 오류 재시도.
- RE:PLAY 담당 코드가 사용할 본인 활성 Memory의 videoId 조회 메서드.
- 설치 SQL, 테스트, 연결 문서와 팀 전달용 문구.

## 확인한 결과

- FastAPI 단위·회귀 테스트 **67개 통과**.
- Spring **48개 통과**: 기존 24개 + Memory 단위·DB 테스트 23개 + 실제 FastAPI HTTP 통합 1개.
- `bootJar` 빌드 성공. 환경·검증 범위는 `VALIDATION.md`에 적었다.
- H2 MySQL 모드에서 설치 SQL 실행 및 Hibernate 스키마 validate, 실제 DB 영속화 테스트를 수행했다.
- 동시 revision 증가, 오래된 결과 차단, Core 트랜잭션 실패 롤백, 읽음 유지, 사용자 접근 제한,
  빈 월/날짜 이동/회원 삭제, 상세 응답 형식, 실제 FastAPI 분석 결과 반영을 검증했다.
- 기존 프론트 lint/typecheck는 CSS 타입 선언 2건 및 웹 테마 hook 1건 때문에 실패한다.
  프론트 파일은 수정하지 않았고 Memory 변경으로 생긴 오류는 아니다.

실제 MySQL 서버 및 실제 Google 인증·Moment DB·YouTube Playlist까지의 전체 통합은 이번 환경에서 검증하지 않았다.
아직 승환 브랜치에 Auth/Moment가 없으므로 **실제 로그인과 Moment DB의 연결 훅이 추가되어야 자동 분석이 시작된다.**
가짜 인증/운영 샘플 Moment는 넣지 않았다. 연결 전 HTTP Memory 요청은 인증 Principal이 없으면 401이다.

## 테스트 후 push

```powershell
cd C:\Users\milan\reon\Re-on\memory-engine
python -m unittest discover -s tests -v
cd ..\backend
.\gradlew.bat test
.\gradlew.bat bootJar
cd ..
git status
git add backend memory-engine TEAM_HANDOFF.md APPLY_README.md FILE_LIST.md VALIDATION.md
git commit -m "feat: Memory API와 영속화 및 revision 검증 구현"
git push origin minjoung
```

기존 PR #1의 설명 중 Memory DB 처리·조회가 Core 담당이라고 적힌 부분은 이제 김민정 담당으로 수정하면 된다.
Secret, DB 비밀번호, .env 파일은 코드에 넣지 않는다. `.env.example`은 자동 로딩되지 않는다.
