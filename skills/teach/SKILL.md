---
name: teach
description: 백엔드 학습 워크스페이스에서 개념을 가르친다. backend-log 레포를 teaching workspace로 사용한다.
argument-hint: "무엇을 배우고 싶으신가요? (비우면 zone of proximal development 기준으로 자동 선택)"
---

백엔드 학습 워크스페이스에서 개념을 가르친다. 이 스킬은 stateful하다 — 여러 세션에 걸쳐 학습이 누적된다.

## Teaching Workspace

`/tmp/backend-log/` (또는 gh clone한 경로)를 teaching workspace로 사용한다:

- `MISSION.md`: 학습의 목적과 성공 기준
- `NOTES.md`: 사용자 선호 및 스타일 메모
- `RESOURCES.md`: 신뢰할 수 있는 참고 자료 목록
- `./reference/*.html`: 개념별 레퍼런스 치트시트 (아름답고 출력 가능한 HTML)
- `./learning-records/*.md`: 학습 기록 (ADR 형식)
- `./lessons/*.html`: 레슨 파일 (Tufte 스타일 아름다운 HTML)
- `./assets/*`: 레슨 간 공유 컴포넌트 (스타일시트, 퀴즈 위젯 등)

## Philosophy

1. **지식(Knowledge)** → 고신뢰 자료에서 수집
2. **스킬(Skill)** → 인터랙티브 레슨으로 체화
3. **지혜(Wisdom)** → 실무에서 획득 (이미 진행 중)

fluency(즉각 인출)보다 storage strength(장기 보유)를 목표로 한다:
- 회상 연습 (retrieval practice)
- 간격 반복 (spaced repetition)
- 실무 예시 연결

## 레슨 생성 규칙

- 파일명: `./lessons/NNNN-<dash-case-name>.html` (번호 순 증가, 4자리 zero-padding)
- Tufte 스타일: 깔끔한 타이포그래피, 여백, 읽기 좋은 레이아웃
- 짧고 완결: 한 레슨 = 하나의 개념 = 하나의 tangible win
- 반드시 인터랙티브 퀴즈 포함 (tight feedback loop)
- 레슨 끝에 "궁금한 점을 질문하세요" 안내 포함
- 다른 레슨/레퍼런스로 HTML anchor 링크

## ⚠️ index.html 뷰어 등록 필수

레포에 `index.html` 통합 뷰어가 있다. 새 레슨을 만들면 반드시 `index.html` 안의 `LESSONS` 배열에도 등록해야 한다.

```js
// index.html의 LESSONS 배열에 추가:
{
  id: 'NNNN',                          // 4자리 레슨 번호
  title: '레슨 N — 제목',              // h1과 동일하게
  short: '핵심 태그 · 태그 · 태그',    // lesson-meta 태그 요약 (30자 이내)
  file: 'lessons/NNNN-파일명.html',    // 실제 파일 경로
  category: 'ActiveRecord'             // 아래 카테고리 중 하나
}
```

사용 가능한 카테고리: `Ruby 기초` / `Grape API` / `엔티티·도메인` / `SQL·쿼리` / `ActiveRecord`

새 카테고리가 필요하면 `CATEGORY_ORDER` 배열에도 추가한다.

뷰어 기능: 좌측 카테고리 네비게이터, 우측 TOC 자동 생성, 전체 내용 검색, ← → 키보드 이동.

## Assets 규칙

- 첫 레슨에서 공유 stylesheet를 `./assets/style.css`로 생성
- 이후 레슨은 반드시 이 stylesheet를 링크
- 퀴즈 위젯, 다이어그램 등 재사용 가능한 것은 assets에

## Zone of Proximal Development

인자가 없으면 다음을 읽고 다음 레슨 주제를 자동 결정:
1. `./learning-records/` 읽기
2. `ROADMAP.md` 체크된/안된 항목 파악
3. 가장 적절한 다음 개념 선택

## 사용자 프로필 (NOTES.md에서 로드)

사용자의 배경과 선호는 `NOTES.md`를 먼저 읽어서 파악한다.
