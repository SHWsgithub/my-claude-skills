---
name: front-workflow
description: FE 개발 전체 파이프라인 오케스트레이터. 기획→피그마→개발→검증→PR 단계를 체크포인트 포함 순차 실행하고, 이미 있는 산출물은 재활용한다. 트리거: "/front-workflow", "FE 워크플로우 시작", "워크플로우 돌려줘".
---

# 프론트 워크플로우

FE 개발 전체 파이프라인을 체크포인트 기반으로 순차 오케스트레이션하는 스킬.
단계별 산출물이 이미 있으면 해당 단계를 건너뛴다. `--from=<N>`으로 중간 진입 가능.

## 사용법

```
/front-workflow <과제명>       # Phase 0부터 전체 실행
/front-workflow --from=3      # Phase 3(구조 탐색)부터 재진입
/front-workflow --from=4      # 개발 루프만 재실행
```

트리거: `"/front-workflow"`, `"FE 워크플로우 시작"`, `"워크플로우 돌려줘"`, `"front-workflow <과제명>"`

---

## 파이프라인 단계표

| # | 단계 | 에이전트/스킬 | 산출물 | 체크포인트 |
|---|------|--------------|--------|-----------|
| 0 | 히스토리 파악 | context-search | `./context/<task>.md` | 자동 (이미 있으면 스킵) |
| 1 | FE 명세 | front-brief | `./context/<task>.brief.md` | ✋ Figma 타입 + 작업 방향 질문 포함 |
| 2 | Figma 확인 | figma-read → figma-plan | figma-out/ + plan | ✋ brief.md에 Figma 링크 있을 때만 |
| 3 | 구조 탐색 | code-architect | 코드 구조 리포트 (대화) | 자동 |
| 4 | 개발 루프 | code-writer → code-reviewer → code-simplifier | 코드 변경 | ✋ 청크 단위 승인 |
| 5 | 접근성 리뷰 | a11y-reviewer | 리뷰 피드백 | 선택적 (UI 변경 시) |
| 6 | 검증 | impl-verifier | 검증 리포트 | 자동 |
| 7 | PR 작성 | git-master → GitHub | PR URL | ✋ 최종 확인 |

---

## Phase 0 — 히스토리 파악

```
context/<task>.md 존재 여부 확인
  ├─ 있음 → "기존 파일 사용합니다: context/<task>.md" 안내 후 Phase 1
  └─ 없음 → context-search 실행 → context/<task>.md 생성
```

과제명이 인자로 없으면 사용자에게 질문한다.

---

## Phase 1 — FE 명세 (front-brief)

```
context/<task>.brief.md 존재 여부 확인
  ├─ 있음 → "기존 brief.md 사용합니다" 확인 후 스킵 또는 재생성 선택
  └─ 없음 → front-brief 실행
```

**체크포인트**: front-brief 내부에서 Figma 링크 타입 질문 + 작업 방향 확인이 발생한다.
brief.md가 완성되면 내용을 요약 출력하고 Phase 2 진행 여부를 확인한다.

---

## Phase 2 — Figma 확인 (선택적)

brief.md의 `## Figma 참조` 섹션 확인:

```
Figma 링크 있음
  ├─ 타입: 페이지 → figma-read (screenshot + layer-walk) → figma-plan
  └─ 타입: 컴포넌트 → figma-plan 직행
Figma 링크 없음 → Phase 2 건너뜀
```

**체크포인트**: figma-plan 결과 확인 후 "구현 진행할까요?" 질문.

> 💡 **컨텍스트 절약**: Figma 읽기는 JSON·이미지 데이터를 대량 소비한다. Phase 3 진입 전 `/compact`를 실행하면 이후 개발 루프에서 캐시 비용을 크게 줄일 수 있다.

---

## Phase 3 — 구조 탐색 (code-architect)

`code-architect` 에이전트에게 다음을 요청한다:

```
brief.md의 구현 항목을 기반으로:
1. 수정 예정 파일 목록 (파일명:예상 라인 범위)
2. 관련 컴포넌트 의존성 트리
3. 공유 타입/유틸 영향 범위
4. 주의해야 할 기존 패턴 (fe-coding-rules.md 기준)
```

code-architect 리포트는 Phase 4 개발 루프의 입력으로 사용된다.

---

## Phase 4 — 개발 루프

brief.md의 구현 항목을 청크(논리적 단위)로 나눠 반복한다.

```
for each 구현 청크 in brief.md 구현 항목:

  1. code-writer → 구현
     - 입력: brief.md 해당 항목 + code-architect 리포트 (파일:라인 맵)
     - 참조: ~/Desktop/fe-coding-rules.md (15개 규칙)
     - 제약: 절대경로 import, 평면 props, props spread 금지 등

  2. code-reviewer → severity-rated 리뷰
     - CRITICAL/HIGH → code-writer에게 수정 요청 후 재루프
     - MEDIUM/LOW → 다음 단계 진행 (기록만)
     - 코딩 규칙 위반 시 반드시 지적 (fe-coding-rules.md 기준)

  3. code-simplifier → 변경 코드만 단순화
     - behavior 보존 필수
     - 최근 수정 파일만 대상

  [✋ 체크포인트] 청크 완료 → 사용자 승인 → 다음 청크 or 완료
  > 💡 청크가 2개 이상 남아있고 세션이 길어졌다면 `/compact` 실행을 제안한다.
```

**루프 재진입**: `--from=4`로 시작하면 code-architect 리포트와 brief.md를 읽어 중단된 청크부터 재개한다.

---

## Phase 5 — 접근성 리뷰 (선택적)

다음 중 하나에 해당하면 `a11y-reviewer` 에이전트를 실행한다:

- brief.md에 UI 컴포넌트(모달, 폼, 테이블, 네비게이션) 변경이 포함됨
- code-reviewer가 ARIA 관련 이슈를 제기함
- 사용자가 "접근성 리뷰" 명시

```
a11y-reviewer → CRITICAL/MAJOR 있으면 code-writer 수정 요청
              → MINOR/NIT는 별도 섹션으로 기록
```

---

## Phase 6 — 검증 (verifier)

`impl-verifier` 에이전트에게 다음을 요청한다:

```
1. brief.md의 모든 구현 항목 완료 여부 확인
2. code-reviewer CRITICAL/HIGH 이슈 모두 수정됐는지 확인
3. a11y-reviewer CRITICAL/MAJOR 이슈 수정 여부 (Phase 5 실행 시)
4. fe-coding-rules.md 핵심 규칙 준수 여부 샘플 확인
```

impl-verifier 판정이 FAIL이면 Phase 4로 되돌아간다.

---

## Phase 7 — PR 작성

verifier 통과 후:

```
git-master → commit (각 청크별 개별 커밋, 커밋 메시지는 커밋 참조 규칙 준수)
          → PR 본문 (brief.md 구현 항목 기반 체크리스트 자동 생성)
```

**[✋ 체크포인트]**: PR 내용 확인 후 사용자 최종 승인.

---

## 재진입 & 산출물 감지

```bash
# 자동 감지 순서
context/<task>.brief.md  → Phase 1 완료 → Phase 2부터
context/<task>.md        → Phase 0 완료 → Phase 1부터
없음                     → Phase 0부터
```

`--from=<N>` 지정 시 해당 Phase 이전 산출물을 자동 읽는다.

---

## 선택적 단계 매트릭스

| 조건 | 추가 단계 |
|------|-----------|
| UI 컴포넌트 변경 | Phase 5 a11y-reviewer |
| 테스트 작성 요청 | Phase 4 루프 후 테스트 엔지니어 |
| 인증/권한 관련 | Phase 4 병행 security-reviewer |
| 성능 민감 목록/테이블 | Phase 4 code-reviewer에 perf 축 추가 요청 |

---

## 실패 모드 & 폴백

| 상황 | 대응 |
|------|------|
| context-search 채널 접근 실패 | 과제 배경을 사용자에게 직접 입력받아 context.md 수동 생성 |
| figma-plan 결과 빈 diff | "Figma 토큰 확인 또는 /figma-read 먼저 실행" 안내 |
| code-writer 구현 후 code-reviewer CRITICAL 반복 | 사용자에게 설계 재검토 요청 |
| impl-verifier FAIL 3회 | 사용자에게 현재 상태 보고 후 계속 여부 확인 |

---

## 트리거 예시

```
/front-workflow 응답지 분리
/front-workflow --from=4
FE 워크플로우 시작
워크플로우 돌려줘
```
