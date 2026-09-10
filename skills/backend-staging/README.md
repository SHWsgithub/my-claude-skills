# staging-deploy 스킬 — 개요 & 치트시트

S 스쿼드 백엔드 스테이징 배포 자동화. 상세 절차는 `SKILL.md`, 핵심 로직은 `scripts/normalize_apispec.py`.

```
~/.claude/skills/staging-deploy/
├── SKILL.md                       # 워크플로우 본문 (Claude가 따라 실행)
├── README.md                      # (이 문서) 사람용 요약/치트시트
└── scripts/normalize_apispec.py   # talenx-log ApiSpec 노이즈 제거 정규화기
```

## 호출
```
/staging-deploy ppback theplus-back perpl-download
```
또는 자연어: "마일스톤 정리해서 스레드 올려줘" / "배포 PR 만들어줘" / "talenx-log api spec 동기화해줘"

## 4줄 요약
1. **마일스톤 디제스트** — 레포별 최신 마일스톤 PR을 ✅머지/☑️대기로 슬랙 스레드에 초안 정리
2. **배포 준비** — dev 최신화 → `release/test-staging` 재생성 → 푸시(AWS 브랜치 감지, 자동배포 아님) → PR → 슬랙 공유
3. **talenx-log ApiSpec** — ppback/theplus-back swagger 동기화, 노이즈 제거하고 진짜 변경만
4. **릴리즈** — 브랜치 푸시는 감지만, 실제 릴리즈는 AWS 콘솔 **수동 버튼** 클릭 + 완료 알림
   *(release/test-staging 정리는 별도 종료 단계가 아니라 **다음 사이클 시작 시** 재분기 전에 처리)*

## 스쿼드 레포
| 레포 | 언어 | PR base | PR 제목 | 비고 |
|---|---|---|---|---|
| ppback | Rails | main | Release/test-staging | |
| theplus-back | Rails | main | Release/test-staging | |
| perpl-download | Ruby | main | Release/test-staging | |
| perpl-notification | Ruby | **master** | Release/test-staging | 마일스톤 없으면 skip |
| talenx-log | Java | **dev** | **`<MMDD> S모듈 변경사항 반영`** | 마일스톤 X. ApiSpec 동기화 |

- 고정: org `hcgtheplus` / 슬랙 `C08VCM8TL76`(#sq-strategy) / 브랜치 `release/test-staging`
- 레포 선택 = **열린 마일스톤 + 연결 PR ≥1** 일 때만 (talenx-log는 예외, API 변경 시 진행)

## talenx-log ApiSpec 한눈에
- 대상: `ppApiSpec.json`(:4000 ppback), `peApiSpec.json`(:4001 theplus-back = "People Theplus")
- 트리거: ppback/theplus-back에 API **추가·삭제·수정**(파라미터/응답 변경 포함) 있으면 무조건
- 전제: 두 레포 로컬 **dev 최신화** 후 swagger 떠야 의미 (서버 재기동은 보통 불필요, hot reload)
- 노이즈 제거: `data_wrapper` 번호 복원 / 한글·`>` 이스케이프 / 키순서 / 생성일 날짜→`2000-01-01` 고정 / `example` 정수.0
- **최초 1회는 2커밋 분리**: `포맷 정규화(의미변경 X)` + `실제 API 변경`. 이후엔 단일·깨끗.
- 커밋 전 가드: `grep -c __GENERATED_TS__ <file>` == 0, JSON 파싱 통과 확인.

## ⚠️ 함정 모음 (실전에서 겪은 것)
- `gh api issues?milestone=` 는 **`--paginate` 필수** (기본 10개만 와서 PR 누락).
- 슬랙 MCP엔 **메시지 수정/삭제 API 없음** → 항상 **초안만**, 보내기는 사용자. 위젯 "Message sent"는 거짓말, draft임.
- PR 링크는 **`#번호`** 텍스트로 (PR 제목이 "Release/test-staging"이라 슬랙 unfurl이 헷갈림).
- dev 최신화 직후 Rails 서버 **500 = 마이그레이션 미적용** → `bin/rails db:migrate`.
- **swagger 출력 자체가 진실** — "소스 .rb에 X 있으니 swagger에도 있어야 한다"고 단정 금지. grape-swagger가 다르게 렌더링함(예: delete에 `success model: DeletedMemberEntity` 있어도 swagger는 `204`). 현재성은 **이번 PR의 고유 마커(신규 path/문구)가 live에 있는지**로 확인.
- 서버는 도커(OrbStack)+호스트 bind-mount. 보통 최신이지만, puma가 옛 정의를 들고 있으면 `bootsnap 캐시 삭제 + app --force-recreate`. 멀쩡한데 재기동하지 말 것(헛걸음).
- **grape-swagger boot 순서 비결정성**: enum/속성 순서가 부팅마다 다름(의미 동일). 재동기화 시 순서만 다른 미세 diff는 무시.
- 정규화 출력은 **유효 JSON이어야 함**. 비교용 토큰을 파일에 쓰면 안 됨 (`__GENERATED_TS__` 버그 전적 있음 → 가드 추가됨).
- 커밋/푸시/브랜치삭제/CodePipeline = **사용자 확인 후**. 함부로 금지.

## 검증 기록 (2026-06-05 첫 실전)
- 마일스톤 디제스트 + 배포 PR: ppback #5451 / theplus-back #1287 / perpl-download #407
- talenx-log ApiSpec 동기화: [PR #73](https://github.com/hcgtheplus/talenx-log/pull/73)
  - 노이즈 제거 효과: ppback 3685→755줄, theplus-back 506→132줄
  - 잡힌 진짜 변경: ppback 신규2(그룹360 다운로드)+수정#5433 / theplus-back 수정#1281+삭제204
  - 2커밋 분리 적용 (포맷 정규화 + 실제 변경)
