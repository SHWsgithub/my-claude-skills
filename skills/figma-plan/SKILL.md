---
name: figma-plan
description: Figma 프레임·컴포넌트 URL을 받아 퍼블리싱 계획(plan file)을 만든다. 디자인 수집 → 코드베이스 탐색 → Atomic 분해 → plan file 템플릿. "피그마 계획", "Figma 계획 짜줘", "/figma-plan" 요청에 사용한다.
---

# 피그마 계획

Figma 프레임/컴포넌트 URL을 받아 **퍼블리싱 계획(plan file)** 을 만든다.
디자인 수집(`figma-read`) → 코드베이스 탐색 → **Atomic 분해** → plan file 템플릿까지.
도메인 중립. 어떤 프로젝트든 동작한다. 프로젝트 고유 컨벤션은 본문 §2 "코드베이스 컨벤션 감지" 단계에서 grep 기반으로 직접 수집한다.

## Usage

```
/figma-plan <figma-url>
```

또는 "이 피그마 퍼블리싱 계획 세워줘", "figma URL을 아토믹으로 분해해서 plan 만들어줘" 같은 요청에 응한다.

---

## 0. 전제 조건 확인

- **대상 Figma URL** — 파일/프레임/노드 단위
- **대상 코드베이스 루트** — 기본 `cwd`. 모노레포면 패키지 경로
- **plan 파일 경로** — 기본 `<CLAUDE_PLAN_DIR>/figma-<slugified-url>.md`. 없으면 `~/.claude/plans/`

---

## 1. 수집 (figma-read 래핑)

내부에서 `/figma-read` 절차를 그대로 호출한다. 최소한 아래 3가지를 수집해 plan file §2에 삽입한다.

1. `get_screenshot(nodeId)` — 시각 참조 (이미지 저장)
2. `get_metadata(nodeId)` — 프레임 트리. 85KB 넘으면 파일로 저장 후 `jq`로 요약
3. `get_variable_defs(nodeId)` — 색/폰트/간격/shadow 토큰

수집 실패 시(`This resource couldn't be accessed`) 사용자에게 다음을 순서대로 안내하고 재시도한다.
- Figma 데스크톱 앱에서 해당 노드 선택
- `/mcp` → `figma-dev-mode-mcp-server` 재인증
- Dev Mode 좌석/파일 권한 확인

---

## 2. 코드베이스 컨벤션 감지

plan file에 포함할 **프로젝트 컨벤션 스냅샷** 을 자동 수집한다.

```bash
# styled API 컨벤션 (레포 감지 예시)
grep -rEn 'from "@mui/material/styles"' src | grep -i styled | wc -l
grep -rEn 'from "@emotion/styled"' src | wc -l
grep -rEn 'from "styled-components"' src | wc -l
grep -rEn '= styled\(' src | wc -l

# 재수출 경로 탐색 (예: material/styles)
find src -path '*material/styles*' -name '*.js' -o -name '*.ts' | head

# atomic/디자인시스템 공용 디렉터리 탐색
find src -type d \( -name atoms -o -name molecules -o -name organisms -o -name styled -o -path '*shared/styled*' \) | head

# 테스트/검증 스크립트
jq -r '.scripts | to_entries[] | select(.key | test("typecheck|lint|tsc|test")) | "\(.key)=\(.value)"' package.json
```

이 결과를 plan §3 `프로젝트 컨벤션 스냅샷` 에 기록한다.

---

## 3. Atomic 분해 (핵심)

Figma 프레임 트리(§2)를 atom → molecule → organism 으로 **수동 분해**한다. 단순 키워드 휴리스틱이 아니라 디자인 구조를 읽는다.

| 레이어 | 예시 | 판정 기준 |
|---|---|---|
| **atom** | 버튼, 아이콘, 입력창, 텍스트, 칩, 아바타 | 더 이상 쪼갤 수 없는 단일 UI primitive. 자체 상태 거의 없음 |
| **molecule** | 카드 헤더, 셀, 요약 행, 라벨+필드, 배지 그룹 | atom 2~5개의 의미있는 조합. 로컬 레이아웃/접근성 계약 가짐 |
| **organism** | 테이블, 리스트, 네비게이션, 섹션, 배너 | molecule/atom 다수의 조합. 데이터 fetch·상태 관리 가능 |

각 atom/molecule 마다 **재사용 후보 검색**:
```bash
# atom 이름 후보 (Figma 레이어명) 기반 grep
grep -rEn "const [A-Z][a-zA-Z]*\s*=\s*styled\(" src | grep -i <layer-name>
# 공용 styled 디렉터리 먼저 확인
ls src/components/shared/styled src/components/styled 2>/dev/null
```

결과를 §5 `작업 항목` 표에 "신규 atom / 재사용 atom / 수정 molecule / 신규 organism" 으로 구분.

---

## 4. 파일 분리 컨벤션 (plan file에 박아둘 규칙)

에이전트/후속 스킬이 코드 작성 시 따를 규칙을 plan file §4에 명시.

### 4.1 styled API
- **1순위**: 레포에서 감지된 컨벤션 (예: `material/styles` 재수출 같은 프로젝트 고유 래퍼가 있으면 그것). 1순위가 있으면 무조건 그걸 사용.
- **폴백**: `@mui/material/styles` → `@emotion/styled` → 마지막 `styled-components`.
- **금지**: `tss-react/makeStyles`, `useStyles`, SCSS 파일, `sx={{...}}` inline (디자인 토큰 재사용 어려움)

### 4.2 Colocation
- atom/molecule/organism 단위로 **sibling `.styles.ts` 파일** 생성:
  ```
  ComponentName.tsx              ← 로직 + JSX + data-fetching
  ComponentName.styles.ts        ← styled() 선언만
  ```
- JSX에서 사용: `import * as S from "./ComponentName.styles";` → `<S.Container>`, `<S.Row>`.
- 재사용되는 atom은 공용 디렉터리(예: `src/components/shared/styled/` 또는 `src/components/styled/`) 로 승격.

### 4.3 디자인 토큰
- Figma `get_variable_defs` 결과를 `tokens.ts` 또는 theme extension으로 추출. 하드코딩 금지.
- 네이밍: Figma 토큰명을 TS 상수에 1:1 매핑 (예: `Gray.Cgray600 = "#8A8D9E"`).

### 4.4 폰트 3종 세트
styled 선언마다 **반드시 세 값을 함께** 명시:
```ts
export const Title = styled("h3")({
  fontSize: "16px",     // Figma sh5
  lineHeight: "20px",
  fontWeight: 600,
});
```
`fontSize`만 쓰고 `lineHeight`·`fontWeight` 누락 금지.

---

## 5. Plan file 템플릿

아래 구조로 plan file을 작성한다 (한국어).

```markdown
# <과제명> — Figma 퍼블리싱 계획

> **Figma 대상**: `<nodeName>` (id `<nodeId>`, WxH)
> **브랜치**: `<branch>` (기반 `<base>`)
> **작성**: YYYY-MM-DD

## 0. 선행 — Figma MCP 연결
(figma-read §1 절차 그대로)

## 1. Context
왜 이 퍼블리싱이 필요한가 / 어떤 outcome을 기대하는가.

## 2. Figma 참조 (수집본)
### 2.1 디자인 토큰
(get_variable_defs 결과 테이블)
### 2.2 프레임 구조
(get_metadata 트리 요약)

## 3. 프로젝트 컨벤션 스냅샷
| 항목 | 감지 결과 |
|---|---|
| styled API | material/styles 재수출 (116곳 사용) |
| colocation | 미도입 (도입 제안) |
| typecheck 스크립트 | 없음 → `npx tsc --noEmit` 사용 |
| lint 스크립트 | lint-staged pre-commit |

## 4. 파일 분리 컨벤션
(§4 규칙 요약)

## 5. 작업 항목 (Atomic 분해)
| # | 레이어 | 이름 | 경로 | 상태 | Figma 노드 |
|---|---|---|---|---|---|
| 1 | atom | Chip | src/components/shared/styled/Chip.ts | 재사용 | 4910:... |
| 2 | molecule | SummaryRow | Objective/SummaryRow.tsx + .styles.ts | 신규 | 4971:... |
| 3 | organism | ObjectiveSummaryTable | Objective/ObjectiveSummaryTable.tsx + .styles.ts | 신규 | 4971:12579 |

각 항목마다:
- Figma 노드 ID
- 재사용 후보 grep 결과
- 토큰 매핑 (color, padding, 폰트 3종)
- 삽입 지점 (파일:라인)

## 6. 커밋 분할
항목별 1 커밋. 순서: atom → molecule → organism → docs.

## 7. 검증
- 각 항목 구현 직후 `get_variable_defs`/`get_metadata` 재조회 diff 0
- 폰트 3종 개별 체크박스
- typecheck + eslint
- (선택) parity-check / 기존 UI 스냅샷

## 8. 명시적 제외
## 9. 미해결 질문
## 10. 참조 라인
```

---

## 6. 플로우

1. 전제 확인 (§0)
2. figma-read 호출 (§1)
3. 코드베이스 컨벤션 감지 (§2)
4. atomic 분해 (§3)
5. plan file 템플릿 작성 (§5)
6. 모호한 결정 지점은 AskUserQuestion으로 확정 (예: 공용 디렉터리 승격 기준, 재사용 vs 신규)
7. ExitPlanMode — 사용자 승인 요청

## Requirements

- Figma Dev Mode MCP (figma-read 전제)
- Plan file 쓰기 권한
- git (브랜치 정보 수집용, 선택)
