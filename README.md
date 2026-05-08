# my-claude-skills

Claude Code용 커스텀 스킬 & 에이전트 툴킷.  
`~/.claude/skills/` 와 `~/.claude/agents/` 에 복사해 사용한다.

## 구조

```
skills/          # /skill-name 트리거로 실행되는 워크플로우
agents/          # 전문화된 서브에이전트 정의
```

## 스킬 목록

| 스킬 | 설명 |
|---|---|
| `code-review` | PR 4축 리뷰 (구조·데드코드·변수명·로직중복) + 인라인 코멘트 반영 추적 |
| `context-search` | SSQ 스프린트 과제 슬랙 히스토리 자동 수집 |
| `figma-plan` | Figma URL → 퍼블리싱 계획 파일 생성 |
| `figma-read` | Figma 프레임·컴포넌트 디자인 데이터 수집 |
| `figma-publish` | Figma 계획 기반 아토믹 구현 → 검증 → 커밋 |
| `front-brief` | 컨텍스트 산출물 → FE 구현 명세 변환 |
| `front-workflow` | 기획→피그마→개발→검증→PR 전체 파이프라인 |
| `omc-reference` | OMC 에이전트 카탈로그·팀 파이프라인·스킬 레지스트리 |
| `pr-write` | PR 본문 자동 작성 (템플릿 포함) |
| `ultrawork` | 병렬 실행 엔진 |
| `vercel-react-best-practices` | Vercel React/Next.js 성능 최적화 가이드 |

## 에이전트 목록

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
| `figma-publisher` | opus | Figma end-to-end 퍼블리싱 오케스트레이터 |
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
