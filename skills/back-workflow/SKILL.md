---
name: back-workflow
description: BE(Rails/Grape) 개발 전체 파이프라인 오케스트레이터. 히스토리 파악→탐색·설계→개발 루프→테스트·검증→학습로그→PR 단계를 체크포인트 포함 순차 실행하고, 이미 있는 산출물은 재활용한다. 트리거: "/back-workflow", "BE 워크플로우 시작", "백엔드 워크플로우".
---

# 백엔드 워크플로우

BE 개발 전체 파이프라인을 체크포인트 기반으로 순차 오케스트레이션하는 스킬. [[front-workflow]]의 백엔드 대응판 — Figma/a11y 단계 대신 설계 승인(plan mode)과 backend-log 학습 기록이 들어간다.
단계별 산출물이 이미 있으면 해당 단계를 건너뛴다. `--from=<N>`으로 중간 진입 가능.

## 사용법

```
/back-workflow <과제명>       # Phase 0부터 전체 실행
/back-workflow --from=2      # Phase 2(개발 루프)부터 재진입
/back-workflow --from=3      # 테스트·검증만 재실행
```

트리거: `"/back-workflow"`, `"BE 워크플로우 시작"`, `"백엔드 워크플로우"`, `"back-workflow <과제명>"`

---

## 파이프라인 단계표

| # | 단계 | 에이전트/스킬 | 산출물 | 체크포인트 |
|---|------|--------------|--------|-----------|
| 0 | 히스토리 파악 + 학습로그 착수질문 | context-search | `./context/<task>.md` | 자동(있으면 스킵) + ✋ 착수 질문 2개 |
| 1 | 코드 탐색 & 설계 | Explore/code-architect(병렬) → EnterPlanMode | 승인된 plan 파일 | ✋ 설계 결정 질문 + 플랜 승인 |
| 2 | 개발 루프 | code-writer → code-reviewer → code-simplifier | 코드 변경 | ✋ 청크 단위 승인 |
| 3 | 테스트 & 검증 | test-engineer → rspec/rubocop → impl-verifier | 테스트 결과 리포트 | 자동 (FAIL → Phase 2 복귀) |
| 3.5 | 보안/영향도 리뷰 (선택) | security-reviewer | 리뷰 피드백 | 조건부 |
| 4 | 학습로그 기록 | (직접 수행, `teach` 컨벤션 참조) | ROADMAP.md 갱신 + `work-log/*.md` (+선택 `lessons/*.html`) | ✋ 레슨 파일 작성 여부 |
| 5 | PR 작성 | git-master → pr-write | PR URL | ✋ 최종 확인 |

---

## Phase 0 — 히스토리 파악 + 학습로그 착수 질문

```
context/<task>.md 존재 여부 확인
  ├─ 있음 → "기존 파일 사용합니다: context/<task>.md" 안내 후 다음
  └─ 없음 → context-search 실행 → context/<task>.md 생성
    (입력이 Slack permalink URL이면 검색 생략하고 바로 스레드 읽기)
```

과제명/링크가 인자로 없으면 사용자에게 질문한다.

**✋ 반드시 다음 두 가지를 묻는다** (전역 CLAUDE.md의 백엔드 학습 로그 프로토콜):
1. "이번 작업이 특정 PR/과제인가요? (work-log 기록 여부 확인)"
2. "이번 세션에서 새로 마주칠 개념이 있으면 backend-log ROADMAP.md 체크 목록과 대조해드릴까요?"

두 질문 모두 이후 Phase 4에서 그대로 적용된다 — 1이 "아니오"면 Phase 4는 스킵.

---

## Phase 1 — 코드 탐색 & 설계

FE의 `front-brief`(별도 스킬)에 대응하는 단계지만, 백엔드는 명세 문서 없이 **탐색 → 설계 결정 → plan 승인**을 이 스킬 안에서 바로 처리한다.

```
1. Explore 에이전트 최대 3개를 병렬로 실행해 다음을 파악:
   - 변경 대상 파일의 현재 구현 (컨트롤러/모델/서비스/워커, file:line 인용)
   - 같은 파일·같은 도메인에 이미 있는 유사 패턴 (예: 같은 컨트롤러의 다른 엔드포인트가
     쓰는 params 컨벤션, 기존 enum/type 파라미터 네이밍)
   - 관련 스펙 파일(spec/) 현황 — 기존 assertion이 무엇을 고정하고 있는지
   - (선택) code-architect 에이전트로 아키텍처 관점 조언 추가 확보

2. 탐색 결과에서 "여러 유효한 설계가 가능한 지점"이 나오면 AskUserQuestion으로
   반드시 사용자에게 확인한다. 특히:
   - API 계약(파라미터명·필수/옵션·하위호환 여부) — FE와 맞물리는 부분이면 명시
   - 기존 동작 중 "버그처럼 보이지만 의도된 것"이 있으면 유지/수정 여부
   - 응답/알림 문구, 에러 코드 등 사용자 대면 텍스트 변경 여부

3. EnterPlanMode로 전환 → 위 탐색 결과 + 사용자 확정 사항을 바탕으로 plan 파일 작성.
   plan 파일 구조:
   - Context: 왜 이 변경이 필요한지, 배경(Phase 0 context.md 요약)
   - 결정된 방향: 사용자가 확정한 설계 선택
   - 변경 사항: 파일별 diff 스케치 (함수 시그니처, 핵심 로직)
   - 테스트 계획: 어떤 스펙을 추가/수정할지
   - 검증 방법: 실행할 명령 (rspec/rubocop 등)
   - 스코프 밖: 명시적으로 이번 작업에서 제외한 것

4. ExitPlanMode로 승인 요청.
```

**체크포인트**: 설계 결정 질문(2번) + 플랜 승인(4번) 두 번 모두 사용자 확인 필요.

> 💡 코드 탐색 결과가 방대하면(여러 도메인 파일 참조) Phase 2 진입 전 `/compact`로 컨텍스트를 정리하면 개발 루프 캐시 비용을 줄일 수 있다.

---

## Phase 2 — 개발 루프

plan 파일의 변경 사항을 청크(파일 단위 또는 논리적 단위)로 나눠 반복한다.

```
for each 변경 청크 in plan.md 변경 사항:

  1. code-writer → 구현
     - 입력: plan.md 해당 청크 + Phase 1 탐색 결과(file:line 맵)
     - 참조: 프로젝트 루트 CLAUDE.md (Rails/Grape/서비스객체/워커 컨벤션이 있다면)
     - 기존 코드 컨벤션(파라미터 네이밍, 에러 처리, 트랜잭션 경계)을 새로 발명하지 않고 그대로 따름

  2. code-reviewer → severity-rated 리뷰
     - CRITICAL/HIGH → code-writer에게 수정 요청 후 재루프
     - MEDIUM/LOW → 다음 단계 진행 (기록만)
     - N+1 쿼리, 트랜잭션 누락, Strong Parameters 누락 등 Rails 특유 이슈 반드시 점검

  3. code-simplifier → 변경 코드만 단순화
     - behavior 보존 필수
     - 최근 수정 파일만 대상

  [✋ 체크포인트] 청크 완료 → 사용자 승인 → 다음 청크 or Phase 3
  > 💡 청크가 2개 이상 남아있고 세션이 길어졌다면 `/compact` 실행을 제안한다.
```

**루프 재진입**: `--from=2`로 시작하면 plan 파일을 읽어 미완료 청크부터 재개한다.

---

## Phase 3 — 테스트 & 검증

```
1. test-engineer 에이전트(또는 직접) → 기존 스펙 컨벤션(FactoryBot, let_it_be, request/model spec
   구분)을 따라 신규/수정 케이스 작성. 기존 테스트가 고정하고 있던 assertion 중
   설계상 의도적으로 바뀐 것이 있으면 그 스펙도 함께 갱신.
2. 테스트 실행 (프로젝트 커맨드, 예: `docker compose run app /bin/sh -c "./bin/rspec <경로>"`)
3. 린트 실행 (예: `docker compose exec app rubocop <변경 파일>`)
4. impl-verifier 에이전트 → plan.md의 수용 기준이 신선한 증거(테스트 그린, 실제 실행 로그)로
   뒷받침되는지 검증.
```

FAIL이면 Phase 2로 되돌아간다. 같은 원인으로 3회 이상 반복되면 근본원인 재조사(`issue-tracer`/`code-debugger`)로 전환할지 사용자에게 확인한다.

### Phase 3.5 — 보안/영향도 리뷰 (조건부)

다음 중 하나에 해당하면 `security-reviewer` 에이전트를 실행한다:
- 인증/인가(Pundit policy, 토큰 검증) 변경
- 사용자 입력을 그대로 쿼리/명령/URL에 사용하는 코드 추가
- 사용자가 "보안 리뷰" 명시

---

## Phase 4 — 학습로그 기록 (backend-log)

Phase 0에서 "work-log 기록 대상"으로 확인된 경우에만 수행. 대상은
`~/Desktop/backend-log`(GitHub `hyunwoosongHCG/backend-log`, 로컬 클론 경로가 다르면
`find ~ -maxdepth 4 -iname "*backend-log*"`로 재탐색).

```
1. 이번 작업에서 등장한 백엔드/Ruby/Rails/Grape 개념을 나열한다
   (Phase 1~3에서 이미 세션 중 "ROADMAP.md 어느 항목인지" 언급했던 것들을 모음).
2. ROADMAP.md에서 해당 항목을 grep으로 찾는다:
   - 이미 있는 체크 안 된 항목 → [x]로 체크 + work-log 링크 추가
   - 항목 자체가 없으면 → 가장 가까운 섹션(##/###)에 새 줄 추가
3. work-log/<날짜>-<작업명>.md 작성 (템플릿: work-log/_template.md 준수):
   - 작업 한 줄 요약
   - 이번 작업에서 처음 배운 개념 (ROADMAP 항목과 1:1 대응, 왜/어떻게 배웠는지 서술)
   - 작업하면서 막혔던 것
   - 다음에 더 공부하고 싶은 것
4. **프로덕션 에러(Sentry 등) 근본원인 조사가 이번 작업에 포함되어 있었다면**,
   work-log만으로 끝내지 말고 lessons/ 아래 HTML 레슨 파일도 만들지 사용자에게 확인한다
   (`teach` 스킬의 레슨 컨벤션: `lessons/00NN-주제.html`, index.html LESSONS 배열 등록 필수).
5. git으로 커밋할지는 사용자에게 확인 후 진행 (자동 커밋/푸시 금지).
```

**체크포인트**: 레슨 파일 작성 여부(4번)만 질문. 나머지는 자동 진행 후 결과를 요약 보고.

---

## Phase 5 — PR 작성

검증 통과 후:

```
git-master → commit (청크별 개별 커밋, 프로젝트 커밋 스타일 준수)
          → pr-write 스킬로 PR 본문 작성 (plan.md 변경 사항 기반 체크리스트)
```

**[✋ 체크포인트]**: PR 내용 확인 후 사용자 최종 승인. `git push`, PR 생성 모두 사용자 승인 후 실행.

---

## 재진입 & 산출물 감지

```bash
# 자동 감지 순서
context/<task>.md         → Phase 0 완료 → Phase 1부터
(같은 세션의) plan 파일 승인됨 → Phase 1 완료 → Phase 2부터
work-log/<날짜>-*.md 존재  → Phase 4 완료 → Phase 5부터
없음                       → Phase 0부터
```

plan 파일 경로는 세션마다 무작위 생성되므로, 세션이 끊긴 뒤 재진입할 때는 사용자에게
직전 plan 파일 경로를 물어 읽는다.

`--from=<N>` 지정 시 해당 Phase 이전 산출물을 자동 읽는다.

---

## 선택적 단계 매트릭스

| 조건 | 추가 단계 |
|------|-----------|
| DB 마이그레이션 포함 | Phase 2 code-reviewer에 마이그레이션 안전성(락, 인덱스, 대량 테이블 영향, 롤백 가능 여부) 축 추가 요청 |
| 인증/권한(Pundit) 변경 | Phase 3.5 security-reviewer 병행 |
| Sidekiq 워커 추가/변경 | Phase 3에서 재시도 정책·큐 설정·job 인자 직렬화(Marshal vs JSON) 확인 |
| API 파라미터/응답 변경 | Phase 2에서 Swagger(`desc`/`params`) 최신화 확인 + Phase 5에서 FE 채널 공유 필요 여부 확인 |
| 프로덕션 버그(Sentry) 원인조사 포함 | Phase 4에서 `lessons/` HTML까지 작성할지 질문 (위 4-4 참조) |

---

## 실패 모드 & 폴백

| 상황 | 대응 |
|------|------|
| context-search Slack 접근 실패 | 과제 배경을 사용자에게 직접 입력받아 context.md 수동 작성 |
| API 계약 등 설계 결정이 여러 갈래 | AskUserQuestion으로 확정 후 plan에 기록 — 임의로 하나를 골라 진행 금지 |
| code-writer 구현 후 code-reviewer CRITICAL 반복 | 사용자에게 설계 재검토(plan 파일 수정) 요청 |
| rspec 실패 3회 이상 반복 | 근본원인 재조사(`issue-tracer`/`code-debugger`)로 전환할지 확인 |
| backend-log 로컬 클론 없음/접근 불가 | Phase 4 스킵 안내, 세션 내 개념 목록만 터미널에 요약 |

---

## 트리거 예시

```
/back-workflow 리뷰 알림 대상자관리자 분리
/back-workflow --from=2
BE 워크플로우 시작
백엔드 워크플로우 돌려줘
```
