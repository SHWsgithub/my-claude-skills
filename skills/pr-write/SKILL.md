---
name: pr-write
description: PR 생성 및 본문 작성 스킬. 현재 브랜치나 지정 브랜치의 작업 범위를 정리해 gh CLI로 PR을 만들거나 기존 PR 본문을 갱신한다. "PR 만들어줘", "PR 내용 채워줘", "PR 본문 정리", "PR 올려줘" 같은 요청에 사용.
---

# PR 생성 / 본문 작성 스킬

## Usage
```
/PR-작성
```
트리거: "PR 만들어줘", "PR 내용 채워줘", "PR 본문 정리", "PR 올려줘"

---

## 0. 컨텍스트 판별

### 0-1. 어느 레포인가
| 실행 위치 | 동작 |
|---|---|
| `ssq-docs` 루트 | 사용자에게 대상 서브레포를 질문 (`ppfront`, `talenx-admin`, `ppback`, `theplus-back`, `perpl-notification`, `perpl-download`) 후 해당 서브레포로 `cd` |
| 서브레포 내부 | `git rev-parse --show-toplevel` 로 확정, 질문 생략 |
| 그 외 | `gh repo view --json nameWithOwner` 로 추정, 불명확하면 확인 |

### 0-2. 어느 브랜치인가
- 서브레포 내부 호출 → `git branch --show-current` (질문 생략)
- ssq-docs에서 호출 → 브랜치명 질문 후 해당 서브레포에서 확인
- 원격에 없으면 `git push -u origin <branch>` 여부 1회 확인

### 0-3. 베이스 브랜치
우선순위:
1. 기존 PR의 `baseRefName`
2. 레포 기본(대개 `dev`, 일부 `dev-ssq`/`dev-pp`/`dev-ap`)
3. `git merge-base` 최근 분기점

불확실하면 사용자에게 1회 확인.

### 0-4. 슬랙 스레드 URL 수집 (선택이지만 **항상 묻는다**)
"과제 슬랙 스레드 URL 있나요? (없으면 skip)"
- 제공 시 → §3 파싱 단계 진행
- 미제공 → `## 레퍼런스` 섹션에서 관련 줄 생략

---

## 1. PR 존재 확인

```bash
gh pr list --repo hcgtheplus/<repo> --head <branch> --state all \
  --json number,url,body,baseRefName,title
```
- 있으면 **갱신 모드** (`gh pr edit`)
- 없으면 **신규 생성 모드** (`gh pr create`)

---

## 2. 작업 범위 수집

```bash
BASE=<base>
git log --oneline --no-merges origin/$BASE..<branch>

# 기존 PR
gh pr view <num> --json files \
  -q '.files[] | "\(.changeType)\t+\(.additions)/-\(.deletions)\t\(.path)"'

# PR 없을 때
git diff --name-status origin/$BASE...<branch>
git diff --stat origin/$BASE...<branch>
```

`ADDED` / `MODIFIED` / `DELETED` / `RENAMED` 을 분리해서 정리.

### 라우트·영역 매핑 (프론트)
- `src/components/objective/list/**` → `/objectives` 리스트
- `src/components/objective/show/**` → `/objectives/:id`
- `src/components/objective/map/**` → `/objectives/map`
- `src/components/performance/**` → `/performance/**`
- `src/containers/**` → 해당 페이지 배선
- `src/locales/**` → i18n
- `src/hooks/**`, `src/lib/**`, `src/components/shared/**` → 공용 자원

---

## 3. 슬랙 스레드 파싱 (URL 제공 시)

- URL 형식: `https://hcgtheplus.slack.com/archives/<CHANNEL>/p<TS>` → `message_ts = TS 앞10자리 + "." + 뒤6자리`
- `mcp__plugin_slack_slack__slack_read_thread` 로 읽어 추출:
  - **피그마 링크**: `figma.com/design/...` / `figma.com/board/...` URL 최초 1개
  - **백엔드 브랜치**: 코드블록 내 `ppback: <branch>`, `endpoint:`, `method:` 패턴
  - **짝 레포 작업**: 동명 브랜치가 있는지 `gh api repos/hcgtheplus/<repo>/branches/<name>`

---

## 4. 짝 PR / 백엔드 짝 탐지

```bash
# 프론트↔어드민
for r in ppfront talenx-admin; do
  gh pr list --repo hcgtheplus/$r --head <branch> --state all \
    --json number,url,title
done

# 백엔드
for r in ppback theplus-back; do
  gh api repos/hcgtheplus/$r/branches/<branch> 2>/dev/null \
    && gh pr list --repo hcgtheplus/$r --head <branch> --json number,url,title
done
```

- 짝 PR 발견 → **요약** 블록 안에 링크
- 백엔드 브랜치만 존재 → `tree/<branch>` URL + `(PR 미생성)`

---

## 5. 본문 작성

### 템플릿 로드
레포별 템플릿은 `templates/` 에 있다. 없으면 `templates/default.md` 사용:

- `templates/ppfront.md`
- `templates/talenx-admin.md`
- `templates/default.md`  ← 백엔드·기타

### 작성 원칙
- **짝 PR / 백엔드 짝 브랜치는 `## 요약` 안에** (레퍼런스 아님)
- **과제 슬랙 스레드 / 피그마는 `## 레퍼런스`에**
- 레포 템플릿의 "안내 / 셀프 PR 점검 / `↑↑↑ 위 내용 확인...↑↑↑`" 같은 가이드 블록은 **전부 삭제**
- "이 풀리퀘가 어떤 작업인지 설명합니다" 같은 placeholder 문구 삭제
- 변경 기원(고객사 요청/로드맵)이 명확하면 요약에 한 줄
- 요약 첫 문장은 **사용자 관점 변화**, 내부 리팩토링이면 개발자 관점
- 차이점: Before → After 대비, 숫자 있는 건 숫자로
- 작업 범위: 신규/수정 구분, 경로 백틱, 같은 영역은 묶음
- 테스트 방법: 번호 절차, 엣지 케이스(긴 문자열·권한·빈 상태·다국어) 최소 1개
- **참고 이미지 섹션은 이미지가 실제로 있을 때만 포함** (없으면 섹션 자체 생략)

---

## 6. 제목

- 기존 PR → 제목 유지 (사용자 변경 요청 없을 시)
- 신규 생성 → `gh pr list --state merged --limit 10` 로 해당 레포 스타일 확인
  - ppfront/talenx-admin: `[모듈] 작업 키워드` 또는 `모듈: 작업 키워드`
  - 백엔드: 레포별 스타일 따라감

---

## 7. 실행

```bash
cat > /tmp/pr-<repo>.md <<'EOF'
<생성된 본문>
EOF

# 신규
gh pr create --repo hcgtheplus/<repo> \
  --base <base> --head <branch> \
  --title "<title>" --body-file /tmp/pr-<repo>.md

# 갱신
gh pr edit <num> --repo hcgtheplus/<repo> --body-file /tmp/pr-<repo>.md
```

---

## 8. 확인

```bash
gh pr view <num> --repo hcgtheplus/<repo> --json url -q .url
```
URL을 사용자에게 회신.

이미지 요청이 별도로 있으면 Playwright 캡쳐 → gist 업로드 또는 수동 드래그앤드롭 제안 (기본 비활성).

---

## 컨벤션 체크리스트

- [ ] 짝 PR / 백엔드 짝 브랜치 → `## 요약`
- [ ] 과제 스레드 / 피그마 → `## 레퍼런스`
- [ ] 템플릿 안내문·체크리스트 전부 삭제
- [ ] `Co-Authored-By: Claude` 트레일러 금지 (글로벌 규칙)
- [ ] base 브랜치 사용자 확인 (dev / dev-ssq / dev-pp / dev-ap)
- [ ] 슬랙 스레드 URL 제공 여부 질문했는가
