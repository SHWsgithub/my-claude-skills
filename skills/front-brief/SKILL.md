---
name: front-brief
description: context-search 산출물(./context/<task>.md)을 FE 구현 명세(./context/<task>.brief.md)로 변환하는 스킬. 피그마 링크 타입 확인(무조건 필수), 슬랙 논의만 있을 때 작업 방향 질문, BE 스펙 보완 탐색, plan-analyst 갭 분석 후 brief.md 저장. 트리거: "/front-brief", "FE 명세 뽑아줘", "이 과제 브리핑", "FE 브리프".
---

# FE 과제 브리퍼 (front-brief)

context-search 결과물 → FE 구현 명세(brief.md)로 변환하는 스킬.
피그마·BE 스펙·슬랙 논의를 파싱하고, 조건별 질문으로 정보를 보완한 뒤 `plan-analyst` 에이전트로 갭 분석한다.

## 사용법

```
/front-brief              # 최근 context/*.md 자동 감지
/front-brief <과제명>     # context/<과제명>.md 지정
/front-brief <경로>       # 임의 md 파일 직접 지정
```

트리거: `"/front-brief"`, `"FE 명세 뽑아줘"`, `"이 과제 브리핑"`, `"FE 브리프 작성"`

---

## Step 0 — 입력 파일 확정

| 상황 | 동작 |
|------|------|
| 인자로 과제명/경로 있음 | `./context/<과제명>.md` 또는 지정 경로 직접 읽기 |
| 인자 없음 | `ls -t ./context/*.md` → 최근 파일 1개 후보 제안 후 확인 |
| context/ 없음 | "context-search 먼저 실행" 안내 후 종료 |

---

## Step 1 — 컨텍스트 파싱

context.md에서 다음을 추출한다:

```
- Figma URL 목록 (https://www.figma.com/... 패턴)
- BE 브랜치명 / PR 링크 / API 스펙 언급
- 슬랙 구두 논의 (Figma·BE 없이 텍스트만)
- 과제명, 담당자, 스프린트 기간
```

파싱 결과를 내부 변수로 보관한다. 출력하지 않음.

---

## Step 2 — 조건별 사용자 질문

### 2-A. Figma URL 발견 시 (무조건 필수)

다음을 반드시 사용자에게 확인한다:

```
Figma 링크가 발견되었습니다:
  1. <URL 1>
  2. <URL 2> (있을 경우)

각 링크가 페이지 링크인가요, 컴포넌트(프레임/섹션) 링크인가요?
(페이지 링크: figma.com/design/.../페이지명
 컴포넌트 링크: figma.com/design/...?node-id=XXXXX)
```

> 응답을 받은 뒤 brief.md에 기록:
> - 페이지 링크 → `figma-read` screenshot/layer-walk 전략 권장
> - 컴포넌트 링크 → `figma-plan` 직행 가능

### 2-B. 구두 논의만 있을 때 (Figma·BE 스펙 없음)

```
Figma나 BE 스펙 없이 슬랙 논의만 확인됩니다.
FE 작업 방향을 알려주세요:
  - 어떤 기능/화면을 추가·수정하나요?
  - 완료 조건은 무엇인가요?
```

### 2-C. BE 브랜치/스펙 언급 있을 때 (선택)

```
BE 스펙이 언급되어 있습니다 (<브랜치명> 또는 <PR 링크>).
FE 관련 API 인터페이스·응답 구조를 탐색할까요? (y/n)
```

응답이 y이면: 해당 레포에서 API 엔드포인트·응답 타입·에러 코드를 탐색한다.

---

## Step 3 — plan-analyst 에이전트 호출

사용자 답변 + 파싱 결과 + BE 탐색 내용을 모아 `plan-analyst` 에이전트를 호출한다.

**전달 프롬프트 핵심**:
```
다음 FE 과제의 요구사항 갭을 분석해줘:
- context.md 전문
- 사용자 확인 사항 (Figma 타입, 작업 방향, BE 인터페이스)
분석 항목: 미비 수용기준, 스코프 위험, 불명확한 경계, FE가 독립적으로 확인해야 할 사항
```

---

## Step 4 — brief.md 저장

`./context/<과제명>.brief.md` 에 저장한다.

```markdown
# FE 구현 브리프: <과제명>

_생성: YYYY-MM-DD_

## 작업 방향 (확인됨)

<사용자 답변 또는 컨텍스트 추론 내용>

## Figma 참조

| 링크 | 타입 | 다음 단계 |
|------|------|-----------|
| <URL> | 페이지/컴포넌트 | figma-read 전략 / figma-plan 직행 |

> Figma가 없으면 이 섹션 생략.

## 구현 항목 (번호 = 우선순위)

1. [ ] <기능/컴포넌트> — 완료 조건: <testable 기준>
2. [ ] ...

## FE / BE 역할 경계

| 영역 | 담당 | 비고 |
|------|------|------|
| FE | <FE 책임> | |
| API 의존 | `<엔드포인트>` | 상태: 확인됨/미확인 |

> BE 스펙이 없으면 이 섹션 생략.

## 갭 & 확인 필요 (plan-analyst 분석)

- [ ] <구현 전 명확히 해야 할 사항>
- [ ] <스코프 위험>

## 코딩 규칙 참조

→ `~/Desktop/fe-coding-rules.md` (14개 ppfront 규칙)

이번 과제 관련 핵심 규칙:
- <발췌 — context 기반으로 관련 규칙 번호와 한 줄 요약>
```

---

## 실패 모드 & 폴백

| 상황 | 대응 |
|------|------|
| context.md 없음 | "context-search 먼저 실행하세요" 안내 |
| Figma URL 있는데 사용자가 타입 모름 | "Figma URL에서 `node-id` 파라미터 있으면 컴포넌트, 없으면 페이지" 도움말 제공 |
| plan-analyst 에이전트 응답이 피상적 | "중점 분석 축 (스코프/인터페이스/완료조건) 좁혀서 재실행" 안내 |
| BE 레포 접근 불가 | "BE 스펙 탐색 생략, API 인터페이스는 미확인으로 표시" |

---

## 트리거 예시

```
/front-brief 응답지 분리
/front-brief context/group360_taker_response.md
FE 명세 뽑아줘
이 과제 FE 브리핑
```
