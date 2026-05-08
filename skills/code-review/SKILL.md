---
name: code-review
description: PR을 4축(구조·데드코드·변수명·로직중복)으로 리뷰하고 인라인 코멘트 반영 상태와 머지 revert까지 추적한다. "리뷰", "/code-review", "PR 리뷰해줘", "리뷰 시작", "이 PR 검토" 같은 요청에 사용.
---

# PR 리뷰 스킬

## Usage
```
/code-review            # 현재 브랜치 PR
/code-review <PR번호>    # 지정 PR
```

트리거: "리뷰 시작", "이 PR 리뷰", "PR 검토", "/code-review"

---

## 0. PR 식별

| 입력 | 동작 |
|---|---|
| 인자로 PR 번호 있음 | `gh pr view <N>` 로 진행 |
| 인자 없음 | `gh pr list --head $(git branch --show-current) --json number,title,url,body,state` 로 자동 조회 |
| 현재 디렉토리가 레포 아님 | `gh repo view --json nameWithOwner` 확인 후 질문 |

PR이 draft/closed 면 사용자에게 한 번 확인.

---

## 1. 자료 수집 (병렬 실행)

```bash
gh pr view <N> --json additions,deletions,changedFiles,comments,reviews,reviewRequests,files,baseRefName,headRefName
gh pr diff <N>
gh api repos/<owner>/<repo>/pulls/<N>/comments --paginate   # 인라인 쓰레드 전체
git log --oneline <base>..HEAD                              # 브랜치 커밋 목록
git log HEAD..origin/<headRef> 2>/dev/null                  # 로컬 미-pull 커밋 감지
```

- diff가 크면 `/tmp/pr<N>.diff` 로 저장 후 `awk` 로 파일별 분리.
- 인라인 코멘트 JSON은 `in_reply_to_id` 기준으로 스레드 재조립.

---

## 2. 반영 상태 매핑

각 리뷰 인라인 코멘트에 대해 3단계 검증:

1. **답변 존재 여부** — 스레드에 대응 답변/커밋 링크 있는지
2. **대응 커밋 식별** — `git log --oneline -S "<key-symbol>"` 또는 `git log -p --since=<review-date>` 로 추적
3. **현재 파일 반영 여부** — 실제 `git show HEAD:<file>` 로 확인

### 머지 커밋 revert 검증

브랜치에 머지 커밋이 있으면 (`git log --merges <base>..HEAD`):

```bash
git show -m <merge-sha> -- <리뷰픽스가_있던_파일>
```

parent별 diff 중 리뷰 픽스가 **역방향(- + 반대)으로 나타나면 revert된 것**. 쓰레드는 "수정하였습니다" 인데 코드가 되돌아간 경우를 탐지.

### 로컬 ↔ origin 동기화

- `git log HEAD..origin/<headRef>` 가 비어있지 않으면 로컬이 뒤처진 상태.
- PR은 origin 기준이므로 리뷰도 origin 기준. 필요 시 `git fetch origin <headRef>` 후 `origin/<headRef>` 내용으로 재검증.

---

## 3. 4축 체크 (주 포커스)

| 축 | 점검 대상 |
|---|---|
| ① **구조 변경** | 새 컴포넌트·헬퍼·타입 경계가 책임 분리되어 있는가. 파생 state 가 setState 경로 없이 stale 위험을 남기지 않는가. |
| ② **데드코드** | 미사용 핸들러·props·state·style 클래스·i18n 키·import 남아있는가. 핸들러 제거 시 호출자도 제거됐는가. |
| ③ **변수명** | 이름이 "데이터 사실"을 뜻하는지 "표시 조건"을 뜻하는지 혼재하지 않는가. 조건적으로만 참인 이름(`responsesWithoutTaker`가 조건 false일 땐 taker 포함) 같은 오해 소지 없는가. |
| ④ **로직 중복·꼬임** | 삼항 3중 중첩, create/edit 분기에서 동일 배열 조립 2회, 유사 타입 컴포넌트에서 option 매핑 복붙 등. |

`correctness·performance·security·test` 는 **눈에 띄면 별도 섹션에 언급만**, 4축 분석을 우선.

---

## 4. 출력 포맷 (한국어)

### 1. 완료된 작업 (As-is → To-be)

표 컬럼: `# | 변경 | As-is | To-be | 상태`
- 상태: ✅ 완료 / ⚠️ 부분 / ❌ 미반영

### 2. 좋은 점

- 유지·재활용할 판단. 리뷰어가 칭찬할 만한 포인트.
- 구체적 파일·패턴 명시 (`file_path:line`).

### 3. 개선 필요

각 항목:
```
#### 🚨 중대 / ⚠️ 주의 / 💡 개선 — <제목>

**위치**: `path/to/file.ext:L123-L145`

**As-is**
```<lang>
<기존 코드>
```

**To-be**
```<lang>
<권고 코드>
```

**근거**: `<short-sha> <커밋 메시지 제목>` (또는 리뷰 쓰레드 `#discussion_rXXX`)
```

### 4. 리뷰어가 확인해야 할 사항

- [ ] 체크리스트 형태
- 의견 조율 필요 항목은 옵션 A/B 제시
- 머지 전 필수 항목 명시

### 요약 체크리스트 (머지 전 필수)

- [ ] 핵심 블로커만 3–5개 이내

---

## 5. 표기 규약

| 규약 | 형식 |
|---|---|
| 커밋 참조 | **해쉬 + 커밋명 한 번에**: `634db5f57 Merge branch 'group360_takerResponse_separation' ...` |
| 파일 인용 | `file_path:line_number` (예: `src/shared/Block.tsx:71`) |
| 제안 | **as-is / to-be 코드 블록 필수** |
| 언어 | **한국어** 기본 |
| 리뷰 쓰레드 | `#discussion_r<id>` 로 참조 |

---

## 6. 정정 프로토콜

리뷰 진행 중 이전 주장이 틀렸다고 판명되면:

- 4번 섹션에 **`[정정]` 항목으로 명시**하고 철회
- 왜 틀렸는지 근거 (커밋 해쉬 인용)
- 조치 불필요면 명시

예:
```
### ③ [정정] "ResponseDetailModal compareByResponsesTakerGiver prop 누락" 철회

이전 리뷰에서 `ElementResponses.tsx:204` 에 prop 미전달이라고 적었으나,
`1ab9c1046 상세보기 모달에서 본인응답 컬러 표시...` 에서 이미 추가됨 (L217).
로컬 HEAD 가 해당 커밋 이전이라 놓친 것. 조치 불필요.
```

---

## 7. 안티패턴 — 하지 말 것

- ❌ 전체 diff 를 나열하듯 훑기 — "뭐가 변했는가" 가 아니라 **"4축 관점에서 무엇이 문제인가"** 를 적는다.
- ❌ 코멘트만 읽고 실제 파일 미확인 — "수정하였습니다" 답변을 그대로 믿지 말고 현재 파일을 확인한다.
- ❌ 커밋 해쉬만 / 커밋 제목만 인용 — 항상 둘 다.
- ❌ 작업 범위 외 지적 (린트·포맷 외 취향) — 요청된 포커스에 집중.
- ❌ 테스트/보안/퍼포먼스를 주 섹션으로 올리기 — 4축이 우선, 나머지는 부록.

---

## 8. 전형적인 실행 흐름 (예시)

```
User: /code-review

1. gh pr list --head <current> → PR #10892
2. 병렬 수집: view / diff / comments API / git log
3. 인라인 코멘트 7건 매핑 → 4건 반영, 2건 머지 revert, 1건 정정 대상
4. 4축 체크:
   - 구조: derived state 제거 ✅
   - 데드코드: handleToggle* 4개 제거 ✅
   - 변수명: compareByResponseTakerGiver → compareByResponsesTakerGiver ✅
   - 중복: Request.jsx L836 vs L864 동일 조립 ⚠️
5. 출력: 4개 섹션 + 체크리스트
```
