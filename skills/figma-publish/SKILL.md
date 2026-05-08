---
name: figma-publish
description: figma-plan이 만든 plan file을 읽고 아토믹 단위로 구현 → Figma 대조 → 검증 → 커밋까지 실행한다. "피그마 퍼블리시", "Figma 배포", "/figma-publish" 요청에 사용한다.
---

# 피그마 퍼블리시

`figma-plan` 이 만든 plan file 을 읽고 **아토믹 단위로 구현 → Figma 대조 → 검증 → 커밋** 까지 실행한다.
도메인 중립. 모든 스타일은 **styled API + sibling `.styles.ts`** 컨벤션.

## Usage

```
/figma-publish <plan-file-path>
```

또는 "plan 대로 퍼블리싱 실행", "figma 구현 시작" 같은 요청.

---

## 0. 전제

- `figma-plan` 산출물(plan file)이 있어야 한다. 없으면 `/figma-plan` 먼저 호출하도록 안내.
- Figma Dev Mode MCP 가 연결돼 있어야 한다 (구현 직후 재조회용).

---

## 1. Plan → Task

plan §5 "작업 항목 표" 를 읽어 `TaskCreate` 로 각 항목을 Task 로 전개.
추가 Task: "사전 조사", "문서 갱신(선택)", "커밋 분할 마무리".

정렬: **atom → molecule → organism** 순. 하위가 상위를 import 하므로 이 순서가 강제된다.

---

## 2. 컨벤션 가드레일

각 작업 진입 전 plan §3(프로젝트 컨벤션) + §4(파일 분리 규칙) 를 메모리에 로드. 다음 규칙을 **구현 전에 선언적으로 적용**한다.

1. styled import 경로는 plan §3에서 감지된 것만 사용. 임의로 `tss-react`, `makeStyles`, SCSS, `sx={{...}}` 도입 금지.
2. 모든 신규 컴포넌트는 **sibling `.styles.ts`** 분리. JSX 파일에는 `import * as S from "./X.styles"` 한 줄.
3. `.styles.ts` 의 각 styled 선언에 **`fontSize` · `lineHeight` · `fontWeight` 세 값이 함께** 있는지 자체 검사.
4. 디자인 토큰은 하드코딩 금지. `tokens.ts` 또는 공용 상수 참조.

---

## 3. 구현 루프 (per Task)

각 작업 항목(atom/molecule/organism) 1개마다 다음 루프를 돈다.

### 3.1 Figma 재조회 (대조 A)
```
get_metadata(nodeId)       → 프레임 사이즈·간격·구조
get_variable_defs(nodeId)  → 색·폰트·shadow 토큰
```
결과를 작업 컨텍스트에 붙여둔다.

### 3.2 재사용 점검
plan에 "재사용 atom" 으로 표시된 항목이면 해당 파일을 import 만 한다. 스타일 추가·override 는 별도 molecule/organism 레벨에서.

### 3.3 파일 생성/수정
- `ComponentName.tsx` — 로직/JSX/훅. `import * as S from "./ComponentName.styles";`
- `ComponentName.styles.ts` — `export const Container = styled(...)({...})` 모음
- 토큰이 공용 파일에 없으면 `tokens.ts` 업데이트 (별도 atom 커밋 가능성 체크)

### 3.4 Figma 대조 (대조 B — 필수 체크리스트)
구현 직후 **같은 nodeId 로 get_variable_defs 재조회** 하고 아래를 개별 체크:

- [ ] **Color** — fills/strokes/border 색이 Figma 변수와 1:1 (hex 소문자 일치)
- [ ] **Spacing** — padding / gap / margin / radius
- [ ] **Shadow** — offset / blur / spread / color
- [ ] **Font — `fontSize`** (Figma 토큰과 동일 px)
- [ ] **Font — `lineHeight`** (Figma 토큰과 동일 px)
- [ ] **Font — `fontWeight`** (Figma 토큰과 동일 숫자)

체크 실패 시 해당 atom은 "완료" 표시 금지. 원인 해소 후 재대조.

### 3.5 타입·린트 회귀
```bash
npx eslint --fix <변경파일...>
npx tsc --noEmit 2>&1 | grep <변경파일>
```
0 error 확인 후 다음 Task 진입.

---

## 4. 커밋 분할

plan §6 커밋 순서대로:

1. (선택) `feat: 디자인 토큰 tokens.ts 추가`
2. `feat: <atom 이름> atom 추가 (styled colocated)`
3. `feat: <molecule 이름> molecule 추가`
4. `feat: <organism 이름> organism 추가 + 삽입 지점 연결`
5. `docs: ...` (있으면)
6. `fix: ...` (기존 코드 정정 필요한 경우 분리)

한 파일에 두 관심사가 섞이면 **임시 되돌림 → 스테이징 → 커밋 → 재적용** 패턴 사용.

커밋 메시지에 Figma 노드 ID 포함 권장: `feat: Chip atom 추가 (Figma 4910:75xxx)`.

---

## 5. 완료 기준

- plan §5 모든 항목 Task 완료
- plan §7 검증 체크리스트 전 항목 체크
- git status clean (or 다음 PR로 넘길 변경만 남음)
- (선택) `/pr-write` 호출 안내

## Requirements

- `figma-plan` 이 만든 plan file
- Figma Dev Mode MCP 연결
- git (로컬 커밋)
