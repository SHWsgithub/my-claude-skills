# my-claude-skills

Claude Code용 커스텀 스킬 & 에이전트 툴킷.
`~/.claude/skills/` 와 `~/.claude/agents/` 에 복사해 사용한다.

프론트엔드 출신으로 백엔드까지 실무 범위를 넓히면서, 반복되는 워크플로우(기획 컨텍스트 수집 → Figma 퍼블리싱 → PR 리뷰 → 배포)를 스킬로 굳힌 것들이다. 개별 스킬보다 **파이프라인으로 엮여서** 쓰이는 경우가 많아, 아래 목록은 실제 조합 관계를 기준으로 묶었다.

## 구조

```
skills/          # /skill-name 트리거 또는 자연어 트리거로 실행되는 워크플로우
agents/          # 전문화된 서브에이전트 정의
```

## 스킬 — 파이프라인별 정리

### 프론트엔드 파이프라인
과제 배경 파악부터 PR까지 이어지는 4단 파이프라인. 뒷 단계는 앞 단계의 산출물을 입력으로 받는다.

| 순서 | 스킬 | 역할 |
|---|---|---|
| 1 | `context-search` | 스프린트 과제명을 슬랙 교차채널로 검색해 흩어진 히스토리·기획 배경을 검증된 타임라인 + 근거 링크 + 핵심 결정사항으로 정리(`./context/<task>.md`). |
| 2 | `front-brief` | 위 산출물을 FE 구현 명세(`./context/<task>.brief.md`)로 변환. Figma 링크 타입 확인, BE 스펙 보완 탐색, `plan-analyst` 갭 분석을 거친다. |
| 3 | `figma-read` / `figma-plan` / `figma-publish` | Figma URL 하나로 디자인 데이터 수집 → 퍼블리싱 계획(plan file) 작성 → 아토믹 단위 구현·Figma 대조·커밋까지. 세 스킬은 보통 사용자가 개별 호출하기보다 `figma-publisher` 에이전트가 파이프라인으로 엮어 end-to-end 실행한다. |
| 4 | `front-workflow` | 기획 → 피그마 → 개발 → 검증 → PR 전체를 체크포인트 기반으로 순차 오케스트레이션하는 최상위 파이프라인. 이미 있는 산출물(context/brief/plan)은 재활용한다. |

### 백엔드 파이프라인
프론트 파이프라인의 백엔드 대응판 + 배포 자동화.

| 스킬 | 역할 |
|---|---|
| `back-workflow` | `front-workflow`의 BE(Rails/Grape) 대응판. 히스토리 파악 → 탐색·설계 → 개발 루프 → 테스트·검증 → 학습 로그 → PR을 체크포인트로 순차 실행한다. |
| `backend-staging` | 여러 백엔드 레포의 스테이징 배포 자동화. (1) 마일스톤 취합해 슬랙 스레드로 정리 (2) `dev` 최신화 → 배포 브랜치 재생성·PR 생성 (3) 로그서버 ApiSpec(swagger) 동기화까지 한 사이클로 처리한다. |
| `teach` | 백엔드 학습 워크스페이스에서 개념을 가르치는 stateful 스킬. 학습 이력이 여러 세션에 걸쳐 학습 로그 레포에 누적된다. |

### 코드 리뷰 & PR
| 스킬 | 역할 |
|---|---|
| `code-review` | PR을 구조 · 데드코드 · 변수명 · 로직 중복 4축으로 리뷰하고, 인라인 코멘트 반영 상태와 머지 후 revert까지 추적한다. 가장 자주 쓰는 스킬. |
| `pr-write` | 현재/지정 브랜치의 작업 범위를 정리해 `gh` CLI로 PR을 생성하거나 기존 PR 본문을 갱신한다(템플릿 포함). |
| `web-e2e` | 백엔드 엔드포인트나 기능명에서 출발해 프론트엔드의 실제 사용처·라우트를 찾아내고, Playwright로 화면을 열어 검증까지 한다. |

### 기획 & 문서
| 스킬 | 역할 |
|---|---|
| `prd-write` | JTBD·유저스토리 기반 15섹션 구조의 PRD를 작성한다. 사람 팀과 AI 프로토타이핑 툴(Cursor/v0/Lovable/bolt.new) 양쪽에서 바로 쓸 수 있게 산문은 자연스러운 한글로 윤문한다. |
| `review-visualize` | 대화 컨텍스트에 있는 코드 리뷰 결과를 인터랙티브 HTML 대시보드로 변환한다. |

### 유틸리티
| 스킬 | 역할 |
|---|---|
| `ultrawork` | 독립적인 작업들을 여러 에이전트로 동시 실행하는 병렬 실행 엔진. 영속성·검증 루프 자체는 없고 병렬성과 모델 라우팅만 담당하는 컴포넌트다. |
| `vercel-react-best-practices` | Vercel Engineering의 React/Next.js 성능 최적화 가이드라인. 컴포넌트/페이지 작성·리뷰·리팩토링 시 자동 적용된다. |

## 에이전트 목록

`figma-publisher`처럼 여러 스킬을 파이프라인으로 묶어 실행하는 에이전트가 있고, 나머지는 Phase(탐색·구현·리뷰·검증) 단위로 호출되는 전문 서브에이전트다.

| 에이전트 | 모델 | 역할 |
|---|---|---|
| `a11y-reviewer` | — | 웹 접근성(WCAG 2.1 AA) 리뷰 |
| `code-architect` | — | 코드 구조 탐색·아키텍처 분석 |
| `code-debugger` | — | 버그 루트코즈 분석 |
| `code-reviewer` | opus | severity 등급 코드 리뷰 |
| `code-simplifier` | — | 코드 단순화·정제 |
| `code-writer` | — | 명세 기반 구현 |
| `critic` | opus | 최종 품질 게이트 (gap analysis 포함) |
| `designer` | — | UI/UX 디자이너-개발자 |
| `document-specialist` | — | 외부 문서·레퍼런스 전문가 |
| `explore` | — | 코드베이스 검색 전문가 |
| `figma-publisher` | opus | `figma-read`·`figma-plan`·`figma-publish` 스킬을 파이프라인으로 묶어 실행하는 end-to-end 퍼블리싱 오케스트레이터 |
| `git-master` | — | 원자 커밋·리베이스·히스토리 관리 |
| `impl-verifier` | — | 증거 기반 완료 검증 |
| `issue-tracer` | — | 경쟁 가설 기반 인과 추적 |
| `plan-analyst` | opus | 요구사항 갭 분석·수용 기준 도출 |
| `planner` | — | 전략 플래닝 |
| `qa-tester` | — | CLI 인터랙티브 테스트 |
| `scientist` | — | 데이터 분석·연구 |
| `security-reviewer` | opus | OWASP Top 10·취약점 탐지 |
| `test-engineer` | — | 테스트 전략·TDD |
| `writer` | haiku | 기술 문서 작성 |

## 설치

```bash
# 스킬 복사
cp -r skills/* ~/.claude/skills/

# 에이전트 복사
cp -r agents/* ~/.claude/agents/
```
