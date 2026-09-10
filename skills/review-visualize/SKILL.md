---
name: review-visualize
description: 대화 컨텍스트의 코드 리뷰 결과를 인터랙티브 HTML 대시보드로 변환한다. "html로 만들어줘", "시각화해줘", "html로 뽑아줘", "/review-visualize" 요청에 사용한다.
---

# review-visualize 스킬

## 트리거

- `/review-visualize`
- "html로 만들어줘" / "시각화해줘" / "html로 뽑아줘" / "html 리포트"
- 코드 리뷰, 분석 결과, 점검 결과가 대화에 있고 HTML 변환을 요청할 때

---

## 실행 흐름

1. **컨텍스트 파악** — 현재 대화에서 리뷰/분석 데이터를 추출한다
   - 이슈 목록 (심각도·제목·위치·as-is·to-be·근거)
   - 좋은 점 목록
   - 완료 항목 평가 (있으면)
   - 체크리스트 항목
   - 메타 정보 (대상 컴포넌트/파일, 날짜, 브랜치)

2. **출력 경로 결정** — 다음 우선순위로 결정한다
   - 사용자가 명시한 경로
   - 현재 프로젝트 루트 + `<kebab-case-subject>-review.html`
   - 없으면 `/tmp/review-report.html`

3. **HTML 생성** — 아래 디자인 시스템과 컴포넌트 명세를 따라 단일 HTML 파일 작성

4. **완료 보고** — 파일 경로와 포함된 이슈 수 요약

---

## 디자인 시스템

### CSS 변수 (필수 — 변경 금지)

```css
:root {
  --bg-base: #0f1117;
  --bg-card: #161b27;
  --bg-card-hover: #1c2235;
  --bg-surface: #1e2433;
  --bg-surface-2: #252b3b;
  --border: #2a3148;
  --border-light: #343d56;
  --text-primary: #e8ecf4;
  --text-secondary: #8b93a8;
  --text-muted: #5c6478;

  --critical: #ef4444;
  --critical-bg: #2d1010;
  --critical-border: #7f1d1d;

  --warning: #f59e0b;
  --warning-bg: #2d1f0a;
  --warning-border: #78350f;

  --info: #3b82f6;
  --info-bg: #0d1a35;
  --info-border: #1e3a6e;

  --purple: #a855f7;
  --purple-bg: #1a0d35;
  --purple-border: #4c1d95;

  --success: #22c55e;
  --success-bg: #0d2d1a;

  --sidebar-width: 260px;
  --header-height: 70px;
}
```

### 폰트 (CDN)

```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet" />
<link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet" />
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-typescript.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-jsx.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-tsx.min.js"></script>
```

- 본문: `Inter`
- 코드: `JetBrains Mono`
- 코드 하이라이팅: Prism.js (prism-tomorrow 테마)

---

## 레이아웃 구조

```
┌─────────────────────────────────────────────┐
│  HEADER (sticky, blur backdrop)              │
│  [아이콘] 제목  부제  날짜 pill  브랜치 pill  │
└─────────────────────────────────────────────┘
┌──────────┬──────────────────────────────────┐
│ SIDEBAR  │  MAIN                            │
│ (fixed,  │  ┌ 요약 카드 4종 (grid) ─────┐   │
│ 260px)   │  │ 중대 / 주의 / 개선 / 파일 │   │
│          │  └───────────────────────────┘   │
│ 목차     │  ┌ 시각화 (도넛+히트맵) ─────┐   │
│ 앵커     │  └───────────────────────────┘   │
│ 링크     │  섹션 1: 완료 항목 평가           │
│          │  섹션 2: 좋은 점                  │
│          │  섹션 3: 개선 필요 (이슈 카드)    │
│          │  섹션 4: 체크리스트               │
└──────────┴──────────────────────────────────┘
```

- 1200px 이상: 사이드바 + 본문 2컬럼
- 1200px 미만: 사이드바 숨김, 본문 풀폭 스택

---

## 컴포넌트 명세

### 1. 헤더

```html
<header class="header">
  <div class="header-icon">🔍</div>
  <div class="header-titles">
    <h1>{{제목}}</h1>
    <p>{{부제 — 분석 대상 파일/컴포넌트명}}</p>
  </div>
  <div class="header-meta">
    <span class="pill pill-date">📅 {{YYYY-MM-DD}}</span>
    <span class="pill pill-branch">⎇ {{브랜치명}}</span>
  </div>
</header>
```

### 2. 요약 카드

4개 고정 카드. 상단에 심각도 색상 accent bar (4px).

| 카드 | 색상 변수 | 아이콘 |
|---|---|---|
| 중대 이슈 N건 | `--critical` | 🚨 |
| 주의 이슈 N건 | `--warning` | ⚠️ |
| 개선 제안 N건 | `--info` | 💡 |
| 분석 파일 N건 | `--purple` | 📁 |

### 3. 시각화 영역

좌우 2컬럼:

**좌: 도넛 차트 (Canvas API)**
- 캔버스 크기: 200×200
- 세그먼트: 중대(빨강) / 주의(노랑) / 개선(파랑) — 이슈 비율로 계산
- 중앙 텍스트: 전체 이슈 수
- 범례: 우측에 색상 dot + 라벨 + 퍼센트

**우: 파일별 이슈 히트맵 테이블**
- 행: 분석 파일명 (`파일명.tsx`)
- 열: 🚨 중대 / ⚠️ 주의 / 💡 개선
- 셀: 해당 파일에 해당 심각도 이슈가 있으면 색상 pill(count), 없으면 회색 `-`

### 4. 이슈 카드

각 이슈는 독립 카드. 심각도에 따라 좌측 border 색상 적용.

```html
<div class="issue-card severity-{{critical|warning|info}}">
  <div class="issue-header" onclick="toggle(this)">
    <span class="severity-badge">🚨 중대</span>
    <span class="issue-title">{{제목}}</span>
    <div class="issue-meta">
      <span class="location-pill">{{파일명:라인}}</span>
      <span class="chevron">▾</span>
    </div>
  </div>
  <div class="issue-body">
    <!-- as-is / to-be diff 블록 -->
    <div class="diff-grid">
      <div class="diff-panel diff-asis">
        <div class="diff-label">As-is</div>
        <pre><code class="language-tsx">{{기존 코드}}</code></pre>
      </div>
      <div class="diff-panel diff-tobe">
        <div class="diff-label">To-be</div>
        <pre><code class="language-tsx">{{개선 코드}}</code></pre>
      </div>
    </div>
    <div class="rationale">
      <span class="rationale-label">근거</span>
      {{근거 텍스트}}
    </div>
  </div>
</div>
```

- as-is 패널 배경: `#2d1010` (critical-bg), 상단 border: `--critical`
- to-be 패널 배경: `#0d2d1a` (success-bg), 상단 border: `--success`
- 기본 상태: 펼침. 헤더 클릭 시 body 토글, chevron 회전

코드 없이 설명만 있는 이슈는 diff-grid 대신 설명 텍스트 블록으로 대체한다.

### 5. 좋은 점 카드

```html
<div class="good-card">
  <div class="good-icon">✓</div>
  <div class="good-content">
    <strong>{{제목}}</strong>
    <p>{{설명}} <code>{{파일:라인}}</code></p>
  </div>
</div>
```

좌측 border: `--success` 4px.

### 6. 체크리스트

```html
<div class="checklist">
  <div class="checklist-progress">
    <div class="progress-bar">
      <div class="progress-fill" style="width: 0%"></div>
    </div>
    <span class="progress-label">0 / N 완료</span>
  </div>
  <label class="check-item severity-critical">
    <input type="checkbox" />
    <span class="check-marker"></span>
    <span class="check-text">🚨 {{항목 텍스트}}</span>
  </label>
  ...
</div>
```

- 체크박스 클릭 시: 텍스트에 `line-through` + `--text-muted` 색상, 진행률 바 업데이트
- 심각도별 좌측 border 색상 적용

### 7. 사이드바 목차

```html
<nav class="sidebar">
  <ul>
    <li><a href="#section-summary">요약</a></li>
    <li><a href="#section-completed">완료 항목</a></li>
    <li><a href="#section-good">좋은 점</a></li>
    <li><a href="#section-issues">개선 필요</a>
      <ul>
        <li><a href="#issue-0">🚨 {{이슈 제목 축약}}</a></li>
        ...
      </ul>
    </li>
    <li><a href="#section-checklist">체크리스트</a></li>
  </ul>
</nav>
```

- `IntersectionObserver`로 활성 섹션 자동 감지 → `.active` 클래스 토글
- 활성 링크: `--info` 색상 + 좌측 2px 인디케이터

---

## 데이터 추출 규칙

대화 컨텍스트에서 다음을 파악한다:

| 데이터 | 추출 기준 |
|---|---|
| 이슈 심각도 | 🚨 = critical, ⚠️ = warning, 💡 = info |
| 파일 위치 | `파일명.tsx:L123` 패턴 |
| as-is 코드 | "As-is" 또는 "기존" 코드 블록 |
| to-be 코드 | "To-be" 또는 "권고" 코드 블록 |
| 코드 없는 이슈 | 설명 텍스트만 있는 항목 |
| 체크리스트 | `- [ ]` 패턴 항목 |
| 좋은 점 | "좋은 점" 섹션 하위 항목 |
| 분석 파일 수 | 위치 pill에서 고유 파일명 집계 |

리뷰가 아닌 다른 분석(아키텍처 분석, 접근성 점검 등)이라면 섹션명을 맥락에 맞게 조정한다. 이슈 심각도 체계는 동일하게 유지한다.

---

## 품질 기준

- 외부 의존성은 CDN만 사용 (로컬 파일 참조 금지)
- 모든 JS는 `<script>` 인라인 — 별도 파일 없음
- 모든 CSS는 `<style>` 인라인
- 코드 블록은 반드시 Prism.js 클래스 적용 (`language-tsx`, `language-ts` 등)
- 빈 섹션(데이터 없음)은 렌더링하지 않는다
- 파일 크기 목표: 50~100KB 단일 파일

---

## 출력 예시 (완료 메시지)

```
`/path/to/output.html` 생성 완료 (58KB)

포함 내용:
- 중대 1건 / 주의 3건 / 개선 3건
- 분석 파일 6종
- 체크리스트 5항목
```
