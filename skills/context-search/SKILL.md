---
name: context-search
description: SSQ 스프린트 과제의 히스토리와 기획 컨텍스트를 슬랙 교차채널 검색으로 자동 수집하고, 검증된 타임라인+근거 링크+핵심 결정사항으로 정리하는 스킬(과제 컨텍스트 서쳐). "컨텍스트 서쳐", "컨텍스트 링커", "과제 히스토리 정리", "기획 파악", "과제 링킹", "컨텍스트 수집", "이 과제 배경이 뭐야", "관련 스레드 찾아줘", 스프린트 과제명을 언급하면서 맥락/배경/히스토리를 물어볼 때 반드시 이 스킬을 사용한다. 슬랙 스레드 permalink URL을 직접 입력해도 동작한다.
---

# 과제 컨텍스트 서쳐 (Claude Code)

SSQ 스프린트 과제의 분산된 히스토리를 슬랙 교차채널 검색으로 수집하고, 검증된 타임라인으로 정리하는 에이전트 스킬.

## 전제 조건

- **Slack MCP 연결 필요**: `claude mcp add slack --transport http https://mcp.slack.com/mcp` 후 `/mcp`로 인증

## 핵심 동작 규칙 (절대 생략 불가)

### 규칙 1: 스레드 내 링크는 반드시 따라간다
- 스레드 메시지에 슬랙 permalink(`https://hcgtheplus.slack.com/archives/...`)이 포함되어 있으면, 해당 링크의 채널 ID와 message_ts를 추출하여 `slack_read_thread`로 원본 내용을 읽는다.
- 단순 검색 결과의 snippet만으로 컨텍스트를 구성하지 않는다.
- 링크 안의 링크도 1단계까지 추적한다 (최대 depth 2).

### 규칙 2: 채널명은 ID로 검증한다
- 검색 결과에 "#channeltalk", "#cx" 등의 채널명이 텍스트로 나오더라도, 반드시 `slack_read_channel` (limit=1)로 채널 ID를 확인한 뒤 정확한 채널명을 표기한다.
- 출력에는 항상 `#채널명 (채널ID)` 형식으로 표기한다.

### 규칙 3: 모든 근거에 정확한 permalink을 첨부한다
- 타임라인의 모든 항목, 핵심 결정사항의 모든 항목에 슬랙 thread permalink을 첨부한다.
- permalink 형식: `https://hcgtheplus.slack.com/archives/{channel_id}/p{message_ts}?thread_ts={parent_ts}&cid={channel_id}`
- permalink이 확보되지 않은 항목은 "permalink 미확인"으로 명시한다.

### 규칙 4: 외부 리소스 URL은 원문 보존
- 스레드에서 발견된 **Figma URL, GitHub(PR/이슈/커밋) 링크, Notion URL, 구글 문서/시트 URL**은 요약에 녹이지 말고, 해당 타임라인 항목 본문에 `🎨 Figma: <URL>`, `🐙 PR: <URL>`, `📝 Notion: <URL>` 형태로 **원문 그대로 노출**한다.
- 후속 스킬(`task-triangulator`, `release-note` 등)이 이 URL을 정규식으로 바로 뽑아 쓸 수 있도록 하기 위함이다.

## 실행 절차

### Phase 1: 메인 스레드 탐색
1. **입력이 permalink URL인 경우**: 채널 ID와 message_ts를 추출하여 `slack_read_thread`로 바로 읽는다. 검색을 생략하고 Phase 2로 진행.
2. **입력이 과제명/키워드인 경우**: `slack_search_public_and_private`로 검색한다.
3. 메인 과제 스레드(가장 답글이 많은 것)를 찾아 `slack_read_thread`로 전문을 읽는다.

### Phase 2: 링크 추적
4. 메인 스레드에서 발견된 모든 슬랙 링크를 목록화한다.
5. 각 링크에 대해:
   a. 채널 ID 추출 → `slack_read_channel` (limit=1)로 채널명 확인
   b. message_ts 추출 → `slack_read_thread`로 원본 스레드 내용 읽기
6. 읽은 스레드 내에서 추가 링크가 발견되면 1단계까지 더 추적한다.
7. **GitHub PR 링크**: 슬랙 도구로 직접 읽을 수 없으므로 PR 번호와 URL만 기록하여 출력에 포함한다.

### Phase 3: 교차채널 보강
8. 과제명으로 다른 채널에서 추가 검색한다:
   - `in:#sq-perf` (과제 분장)
   - `in:#sq-appr` (구현 논의)
   - `in:#ch-ux` (디자인)
   - `in:#cx` (고객 VOC)
   - `in:#channeltalk` (고객 문의 원본)
9. 각 검색 결과에서 관련 스레드를 읽고, 메인 스레드와의 연결점을 파악한다.

### Phase 4: 출력 형식 선택 (필수)

수집이 끝나면 조립 **전에** 사용자에게 아래 3가지 선택지를 제시한다. 사용자가 이미 요청 메시지에서 형식을 명시한 경우(예: "md로 저장", "html로 만들어줘", "터미널에만 보여줘", 파일 경로 포함) 이 단계를 생략하고 바로 해당 형식으로 진행한다.

```
수집 완료 — 출력 형식을 선택해주세요:

  1) 📺 터미널에만 출력 (마크다운)
  2) 📄 마크다운 파일로 저장 (./context/<task-slug>.md)
  3) 🌐 HTML 파일로 저장 (./context/<task-slug>.html)

원하는 번호를 입력하거나 "1/2/3", "터미널/md/html"로 답해주세요.
저장 경로를 직접 지정하고 싶으면 경로를 함께 적어주세요.
```

선택지별 동작:
- **1) 터미널**: 아래 "출력 포맷 — 마크다운" 섹션에 따라 터미널에 직접 출력. 파일 저장 없음.
- **2) 마크다운 파일**: `./context/` 디렉토리가 없으면 생성 → `./context/<task-slug>.md`에 저장 → 터미널에는 "저장 완료: <경로>" + 핵심 요약 3~5줄만 출력.
- **3) HTML 파일**: `./context/` 디렉토리가 없으면 생성 → 아래 "출력 포맷 — HTML" 템플릿에 따라 `./context/<task-slug>.html`에 저장 → 터미널에는 "저장 완료: <경로>" + 핵심 요약 3~5줄만 출력.

`<task-slug>`은 과제명을 kebab-case로 변환(한글은 로마자 또는 영문 키워드로 축약, 공백/특수문자는 `-`로 치환).

### Phase 5: 출력 조립
10. 수집된 모든 정보를 시간순으로 정렬한다.
11. Phase 4에서 선택된 형식으로 결과물을 생성한다.

## 검색 대상 채널

| 채널명 | 채널 ID | 역할 |
|--------|---------|------|
| #sq-strategy | C08VCM8TL76 | 메인 과제 스레드, 과제 분장 |
| #sq-perf | C60TEJMB7 | 백엔드 과제 분장 |
| #sq-appr | C01A1FYK0D7 | 평가 관련 구현 논의 |
| #ch-ux | C04QBUUNZ5H | 디자인 방향 및 과제 배분 |
| #cx | C01AVJ2CJBW | 고객 VOC, SC 검토 |
| #channeltalk | C06ULEEM88M | 고객 문의 원본 |

> 과제 성격에 따라 검색 채널을 추가/제외할 수 있다. 검색 결과에서 새로운 채널이 발견되면 `slack_read_channel`로 확인 후 추가한다.

## 출력 포맷 — 마크다운

터미널 출력(선택지 1) 및 .md 파일 저장(선택지 2) 모두 동일한 구조를 사용한다.

```markdown
# 과제 컨텍스트 서쳐: <과제명>

**담당**: <담당자> · **스프린트**: #<번호> · **상태**: <상태>

---

## 검증된 타임라인

### <날짜> — `#<채널명>` (<채널ID>) · <참여자>
<1~2문장 요약>

🔗 [permalink](<슬랙 thread URL>)

---

## 핵심 결정사항

- **<결정 내용>** — [근거](<permalink>)

---

## 미결 이슈

- 🔸 <이슈 설명>

---

## 관련 GitHub PR (링크만 기록)

- PR #<번호>: <URL>

---

## 검색 채널 (ID 검증됨)

- `#sq-strategy` (C08VCM8TL76) — <역할>

---

_규칙 적용: ①링크 추적 N개 ②채널 ID 검증 N건 ③permalink 첨부 완료_
_검색 N회 + 스레드 읽기 N회_
```

## 출력 포맷 — HTML

선택지 3(HTML 파일 저장)에서 사용한다. 아래 템플릿의 `{{...}}` 플레이스홀더를 실제 데이터로 치환하여 `./context/<task-slug>.html`에 저장한다. 스타일은 인라인 `<style>` 블록으로 포함해 외부 에셋 없이 브라우저에서 바로 열 수 있게 한다.

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>과제 컨텍스트: {{task_name}}</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Pretendard", sans-serif; max-width: 860px; margin: 40px auto; padding: 0 24px; color: #1f2328; line-height: 1.65; }
  h1 { border-bottom: 2px solid #d0d7de; padding-bottom: 12px; }
  h2 { border-bottom: 1px solid #d0d7de; padding-bottom: 8px; margin-top: 36px; }
  h3 { margin-top: 24px; color: #0969da; }
  .meta { color: #656d76; font-size: 14px; margin-bottom: 24px; }
  .timeline-item { margin-bottom: 20px; padding-left: 16px; border-left: 3px solid #d0d7de; }
  .timeline-item .date { font-weight: 600; color: #0969da; }
  .timeline-item .channel { color: #8250df; font-family: "SF Mono", Menlo, monospace; font-size: 13px; }
  .permalink { display: inline-block; margin-top: 6px; font-size: 13px; }
  a { color: #0969da; text-decoration: none; }
  a:hover { text-decoration: underline; }
  ul { padding-left: 20px; }
  li { margin-bottom: 6px; }
  .open-issue { color: #bf8700; }
  .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #d0d7de; font-size: 12px; color: #656d76; }
  code { background: #f6f8fa; padding: 2px 6px; border-radius: 4px; font-size: 13px; }
</style>
</head>
<body>
  <h1>과제 컨텍스트 서쳐: {{task_name}}</h1>
  <div class="meta">
    <strong>담당</strong>: {{owner}} · <strong>스프린트</strong>: #{{sprint}} · <strong>상태</strong>: {{status}}
  </div>

  <h2>검증된 타임라인</h2>
  <!-- 타임라인 항목 반복 -->
  <div class="timeline-item">
    <div><span class="date">{{date}}</span> — <span class="channel">#{{channel_name}} ({{channel_id}})</span> · {{participants}}</div>
    <p>{{summary}}</p>
    <a class="permalink" href="{{permalink}}">🔗 permalink</a>
  </div>

  <h2>핵심 결정사항</h2>
  <ul>
    <li><strong>{{decision}}</strong> — <a href="{{permalink}}">근거</a></li>
  </ul>

  <h2>미결 이슈</h2>
  <ul>
    <li class="open-issue">🔸 {{open_issue}}</li>
  </ul>

  <h2>관련 GitHub PR</h2>
  <ul>
    <li>PR #{{pr_number}}: <a href="{{pr_url}}">{{pr_url}}</a></li>
  </ul>

  <h2>검색 채널 (ID 검증됨)</h2>
  <ul>
    <li><code>#{{channel_name}}</code> ({{channel_id}}) — {{role}}</li>
  </ul>

  <div class="footer">
    규칙 적용: ①링크 추적 {{link_count}}개 ②채널 ID 검증 {{channel_count}}건 ③permalink 첨부 완료<br>
    검색 {{search_count}}회 + 스레드 읽기 {{thread_count}}회
  </div>
</body>
</html>
```

## 품질 체크리스트 (출력 전 확인)

- [ ] 타임라인의 모든 항목에 permalink이 있는가?
- [ ] 채널명이 ID로 검증되었는가?
- [ ] 스레드 내 링크를 모두 따라갔는가?
- [ ] 핵심 결정사항에 근거 링크가 있는가?
- [ ] 미결 이슈가 누락되지 않았는가?
- [ ] Phase 4에서 출력 형식을 사용자에게 물었거나, 사용자 메시지에 이미 형식이 명시되었는가?

## 사용 예시

**입력**: `"태그 이름 노출 과제 링킹해줘"`
**동작**: "태그 이름 노출"로 교차채널 검색 → 메인 스레드 읽기 → 링크 3개 추적 → 수집 완료 후 사용자에게 출력 형식 선택 요청 → 선택된 형식으로 출력

**입력**: `"https://hcgtheplus.slack.com/archives/C60TEJMB7/p1775631220812969 여기에 스킬 적용. html로 만들어줘"`
**동작**: permalink에서 채널 ID + message_ts 추출 → 스레드 직접 읽기 → 링크 추적 → 형식 선택 생략(이미 html 명시) → `./context/<slug>.html`에 저장 + 요약 출력

**입력**: `"hunel Package 과제 배경이 뭐야. ./context/hunel.md에 저장"`
**동작**: "hunel Package"로 검색 → 메인 스레드 + GitHub PR 링크 기록 → 형식 선택 생략(경로 .md 명시) → `./context/hunel.md`에 저장 + 터미널 요약

**입력**: `"360 피드백 점수 로직 컨텍스트 터미널에만 뽑아줘"`
**동작**: 전체 절차 → 형식 선택 생략(터미널만 명시) → 마크다운 전체를 터미널에 직접 출력, 파일 저장 없음

## claude.ai 버전과의 차이

claude.ai 버전과 **동작 로직은 완전히 동일**하다. 차이는 세 가지:

1. **출력 포맷 선택 가능**: 수집 완료 후 사용자에게 터미널 / 마크다운 파일 / HTML 파일 중 선택지 제공
2. **저장 경로**: `/mnt/user-data/outputs/` → `./context/` (선택지 2·3 또는 명시 요청 시에만)
3. **GitHub PR**: 슬랙 도구로 직접 읽지 않고 URL만 기록

GitHub `gh` CLI 통합, `git log`/`git blame` 활용 등의 확장은 **검증 전이므로 포함하지 않는다**. 향후 실제 테스트 케이스로 검증된 뒤 별도 모듈로 덧붙일 수 있다.
