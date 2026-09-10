---
name: staging-deploy
description: >-
  S 스쿼드 백엔드 레포의 스테이징 배포 워크플로우. (1) 여러 레포 최신 마일스톤을 머지/대기로 슬랙 스레드에 정리,
  (2) dev 최신화 → release/test-staging 재생성·푸시(브랜치 감지) → 배포 PR 생성·공유,
  (3) talenx-log ApiSpec(swagger) 동기화(노이즈 diff 제거). release/test-staging 브랜치는 매 사이클 시작 시 재생성(직전 잔재는 그때 삭제).
  "마일스톤 정리해서 스레드 올려", "배포 상황 업뎃", "배포 PR 만들어", "스테이징 배포하자",
  "talenx-log api spec 업데이트/동기화" 같은 요청에 응한다.
---

# 스테이징 배포 워크플로우 (staging-deploy)

S 스쿼드가 관장하는 백엔드 레포의 스테이징 배포를 자동화한다.
GitHub(`gh`) + 로컬 git, Slack MCP(`slack_send_message_draft`), 로컬 swagger + 정규화 스크립트를 쓴다.

## Usage
```
/staging-deploy [repo...]     # 예) /staging-deploy ppback theplus-back perpl-download
```
또는 "마일스톤 정리해줘", "배포 PR 만들어줘", "talenx-log api spec 동기화" 같은 자연어 요청.

**`/staging-deploy` 단독(인자 없음)으로 호출되면 → 곧장 PHASE 1-0(대상 레포 선택)부터 시작한다.**
"어떤 레포 할까요?"라고 막연히 되묻지 말고, **스쿼드 기본 레포 전체를 후보로 자동 판별**(열린 마일스톤+연결 PR)해서
포함/제외 표를 보여주고 확인받는다. 인자로 레포를 주면 그 목록을 후보로 1-0를 수행한다.

**마일스톤 디제스트 대상 선택 규칙**: 레포는 **(열린 마일스톤이 있고) AND (그 마일스톤에 연결된 PR이 1개 이상)** 일 때만 PHASE 1 대상이 된다. 둘 중 하나라도 아니면 자동 제외(사용자에게 사유 알림). `talenx-log`는 마일스톤을 운영하지 않으므로 디제스트 대상이 아니며, ApiSpec 트랙(PHASE 2)으로만 다룬다.

---

## 💬 진행 방식 (팀 공유용 — 티키타카 규칙)
이 스킬은 여러 사람이 쓴다. **친절하고 예측 가능하게** 움직인다.
- **한 PHASE 끝날 때마다 짧게 결과 요약** + 다음 단계 한 줄 안내. 장황하지 않게.
- **사용자가 안 준 정보는 추측하지 말고 묻는다** — 특히 ① 대상 레포 ② 슬랙 스레드 링크.
- **파괴적/외부영향 작업(커밋·푸시·브랜치 삭제·force·CodePipeline)은 실행 직전에 무엇을 할지 보여주고 확인받는다.** 함부로 진행 금지.
- 표/이모지로 머지 상태를 한눈에. PR은 항상 `#번호` 링크.
- 실수 줄이려고 각 단계 전 **사전점검 결과를 먼저 보여주고** 진행한다 (브랜치 존재/ahead 커밋/중복 PR 등).
- 에러나 누락(서버 안 뜸, 마일스톤 없음 등)은 **숨기지 말고 명확히 알리고** 대안을 제시한다.

---

## 0. 고정 설정
- **GitHub org**: `hcgtheplus`  /  **Slack 채널**: `C08VCM8TL76` (#sq-strategy)
- **배포 브랜치**: 전 레포 `release/test-staging`  /  **PR 제목**: `Release/test-staging` (통일)
- **기본 채널 = `C08VCM8TL76` (#sq-strategy)** — 거의 항상 여기. 스레드 링크 없으면 여기에 스레드 생성(확인 후).
- **슬랙은 항상 초안(draft)만** 만든다. 보내기는 사용자 몫. (예외: 스레드 루트 부모 메시지만 실제 전송 — §1-2b, 전송 전 확인)
  - ⚠️ Slack MCP엔 메시지 **수정/삭제 API 없음.** "업뎃" = 같은 스레드 새 초안 답글, 이전 건은 수동 삭제.
  - ⚠️ 위젯에 "Message sent"로 떠도 실제는 draft. 헷갈리면 슬랙에서 직접 확인하라고 안내.
- **스레드 ts**: 슬랙 링크 `.../p1780534755700419` → `1780534755.700419` (앞10.뒤6)

### 스쿼드 레포 & 특이사항
| 레포 | 언어 | PR base | 로컬경로(예) | 비고 |
|---|---|---|---|---|
| `ppback` | Rails | `main` | `~/workspace/ppback` | |
| `theplus-back` | Rails | `main` | `~/workspace/theplus-back` | |
| `perpl-download` | Ruby | `main` | `~/workspace/perpl-download` | |
| `perpl-notification` | Ruby | `master` | `~/workspace/perpl-notification` | main 없음. 마일스톤 없으면 skip |
| `talenx-log` | Java | `dev` | `~/workspace/talenx-log` | 마일스톤 운영 안 함. ppback/theplus-back API 변경 시 ApiSpec 동기화(PHASE 2) |

로컬 경로는 `find ~ -maxdepth 5 -type d -name <repo>` 로 확인.

---

## PHASE 1 · 마일스톤 체크 & 스레드 정리 (반복 호출)

### 1-0. 대상 레포 확정 (자동 선택 → 사용자 확인) ★  ← `/staging-deploy` 단독 시 여기서 시작
**후보 레포**: 인자로 받은 목록. 없으면 **스쿼드 기본 전체** = `ppback theplus-back perpl-download perpl-notification`
(talenx-log는 마일스톤 트랙 아님 → 제외, PHASE 2에서 별도). 후보를 자동 판별한 뒤
**무엇을 포함/제외했는지 표로 보여주고 확인받는다.** 바로 진행하지 말 것.
```bash
for repo in ${ARGS:-ppback theplus-back perpl-download perpl-notification}; do
  m=$(gh api repos/hcgtheplus/$repo/milestones --jq '[.[]][0] | "\(.number)\t\(.title)"' 2>/dev/null)
  [ -z "$m" ] && { echo "$repo: 열린 마일스톤 없음 → 제외"; continue; }
  num=${m%%	*}; title=${m#*	}
  prs=$(gh api "repos/hcgtheplus/$repo/issues?milestone=$num&state=all&per_page=100" --paginate --jq '[.[]|select(.pull_request)]|length')
  [ "$prs" -gt 0 ] && echo "$repo: v$title, 연결 PR ${prs}개 → 포함" || echo "$repo: v$title, 연결 PR 0개 → 제외"
done
```
결과를 표로 정리해 보여주고 — 예) `포함: ppback(v0.174.0), theplus-back(v3.121.0) / 제외: perpl-notification(마일스톤 없음)` —
**"이대로 진행할까요?"** 확인. 사용자가 레포를 추가/제외하면 반영. talenx-log는 마일스톤 트랙이 아니므로 여기 미포함(PHASE 2에서 다룸).

### 1-1. 각 레포 최신 마일스톤
```bash
gh api repos/hcgtheplus/<repo>/milestones --jq '.[] | {number, title, due_on, open_issues, closed_issues}'
```
- 열린 마일스톤이 **1개면** 그대로 사용.
- **여러 개면** 자동으로 고르지 말고 → 목록(제목·due·연결 PR 수)을 보여주고 **어느 걸 배포할지 사용자에게 물어본다.** (기본 추천은 due 가장 가까운 것)
- **없으면** 그 레포 skip ("열린 마일스톤 없어 스킵" 알림).

### 1-2. 마일스톤 PR 분류
```bash
gh api "repos/hcgtheplus/<repo>/issues?milestone=<num>&state=all&per_page=100" --paginate \
  --jq '.[] | "\(.number)\t\(.state)\t\(if .pull_request.merged_at then "MERGED" else "OPEN" end)\t\(.title)"'
```
- **반드시 `--paginate`** (기본 10개만 와서 누락 사고 있었음).
- `merged_at` 有 → ✅머지 / open → ⏳대기. `milestone:null`로 빠진 건 제외.

### 1-2b. 슬랙 스레드 확보 (정리 올리기 전 1회)
정리를 담을 스레드를 확보한다. 두 경우:
- **스레드 링크를 받았으면** → 그 `thread_ts` 사용 (기존 방식).
- **없으면** → 기본 채널 **`C08VCM8TL76` (#sq-strategy)** 에 스레드를 새로 만든다.
  1. 🛑 **반드시 멈추고 확인받는다 (HARD STOP).** "sq-strategy에 배포 스레드 만들까요? (메시지 실제 전송됨)" 라고 묻고
     **사용자가 명시적으로 OK 하기 전에는 `slack_send_message`를 호출하지 말 것.** "바로 보낼게" 식으로 통보하고 진행 금지.
     (실전 피드백: 확인 없이 바로 만들어버린 사고 있었음 → outward-facing이라 무조건 승인 대기)
  2. OK 받으면 `slack_send_message(channel_id=C08VCM8TL76, message="🚀 <날짜> 스테이징 배포 스레드")` **실제 전송** → 반환된 `ts`를 thread_ts로 고정
  3. 이후 모든 정리/공유/알림은 이 thread_ts 아래 **초안(draft)** 으로.
- 부모 메시지(스레드 루트)만 실제 전송이고, **그 아래 댓글은 전부 초안** (사용자 검토 후 전송).

### 1-3. 슬랙 초안
`slack_send_message_draft(channel_id=C08VCM8TL76, thread_ts=<위에서 확보한 ts>, message=...)`
```
📦 <날짜> 스테이징 배포 예정 (최신 마일스톤 기준)

🟦 <repo> — v<버전> (due M/D)
✅ 머지 완료
• [#5448](https://github.com/hcgtheplus/<repo>/pull/5448) <PR 제목 원문 그대로>
⏳ 리뷰/머지 대기
• [#5446](...) <제목>
```
- 링크 텍스트는 `#번호` (PR 제목이 "Release/test-staging"이라 unfurl 혼동 방지).
- **완료 신호**: 전부 머지되면 헤더에 `🎉 모두 머지 완료, 배포 준비 OK` 표시 (별도 알림/폴링 없음).
- "업뎃" 재호출 → 직전 대비 새로 머지된 것/남은 것 짚고 새 초안.
- 전부 머지될 때까지 PHASE 1 반복.

---

## PHASE 2 · talenx-log ApiSpec 동기화 (ppback, theplus-back)   ※ talenx-log 한정

talenx-log(Java 로그서버)는 각 백엔드 swagger 스펙 JSON 보유. API **추가/삭제/수정(변경)** 시 갱신해야 로그가 정확히 잡힘.
talenx-log는 마일스톤을 운영하지 않는다. **ppback / theplus-back 에 API 추가·삭제·수정(파라미터/응답 스키마 변경 포함)이 있으면 무조건 진행한다.**
(예: 신규 엔드포인트, 엔드포인트 제거, 기존 엔드포인트의 파라미터·응답 필드·설명 변경 등 swagger에 반영되는 모든 변화.)
스쿼드 관장 ApiSpec = **ppback, theplus-back 두 개.**

| 파일 | localhost swagger | 백엔드 |
|---|---|---|
| `src/main/resources/json/ppApiSpec.json` | `http://localhost:4000/swagger_doc` | ppback |
| `src/main/resources/json/peApiSpec.json` | `http://localhost:4001/swagger_doc` | theplus-back (swagger title "People Theplus", 조직/구성원) |

### ⚠️ 전제 — live swagger가 최신 dev를 반영하는지 확인 후 동기화
swagger는 **로컬에 떠 있는 백엔드 프로세스의 코드**를 반영한다. 서버는 보통 도커(OrbStack)에서
**호스트 소스를 bind-mount** 하므로 dev pull만 해도 대개 최신이다. 순서:
1. **ppback / theplus-back 로컬 dev 최신화** (`git checkout dev && git pull origin dev`)
2. **live가 최신인지 마커로 확인** (아래 "현재성 검증"). 최신이면 바로 동기화.
3. 마커가 없으면(=puma가 옛 정의 보유) 그때만 bootsnap 캐시 삭제 + app 재기동.

**현재성 검증 (live가 최신 dev를 반영하는지 — 동기화 전 1회):**
- 올바른 방법: **이번 스프린트에 머지된 PR의 고유 마커**(신규 엔드포인트 경로, 또는 PR이 바꾼 description/summary 문구)가
  live swagger에 있는지 확인. 예) `curl :4001/swagger_doc | grep '<이번 PR이 추가한 문구>'`.
  → 있으면 live는 최신. 없으면 그때만 stale 의심.
- ⚠️ **하지 말 것**: "소스(`*.rb`의 `desc`/`success` 블록)에 X가 있으니 swagger에도 X가 있어야 한다"는 단정.
  grape-swagger는 소스 annotation을 그대로 안 옮기는 경우가 있다.
  (실제: members.rb delete에 `success model: DataWrapper.new(DeletedMemberEntity)`가 있어도
  swagger는 `204`로 렌더링됨. 소스≠swagger는 정상일 수 있으니 **swagger 출력 자체를 진실로** 삼는다.)
- 서버는 보통 도커(OrbStack) 컨테이너 + 호스트 소스 bind-mount. dev pull 후에도 puma가 옛 정의를 들고 있으면
  `docker exec <app> rm -rf /var/www/app/tmp/cache/bootsnap && docker compose up -d --force-recreate app`.
  단, **대부분은 이미 최신이다 — 마커 확인으로 먼저 판단하고, 멀쩡한데 재기동하지 말 것.**

**boot 순서 노이즈**: grape-swagger는 부팅마다 enum 값/일부 속성 순서를 다르게 출력한다(의미 동일).
재동기화 시 순서만 다른 미세 diff는 무시. 로그 동작과 무관(Jackson map 파싱).

### 노이즈 문제 (핵심)
그냥 복붙하면 diff 수천 줄 = 대부분 노이즈: `data_wrapper_<번호>` 재넘버링, 한글/`>` 이스케이프,
키 순서, 생성일 타임스탬프·날짜(example), `example` 정수→`정수.0`.
→ **정규화 스크립트로 양쪽(기존+신규)을 같은 형식 통과 → diff에 진짜 새 API만.**
(검증: pp 4184→1604줄(진짜 신규 8개), pe 518→144줄)

### 절차
```bash
REPO=~/workspace/talenx-log;  JSON=$REPO/src/main/resources/json
SC=~/.claude/skills/staging-deploy/scripts/normalize_apispec.py
# 로컬서버 확인 (죽었으면 사용자에 띄워달라 요청)
for p in 4000 4001; do curl -s -m5 -o /dev/null -w ":$p %{http_code}\n" http://localhost:$p/swagger_doc; done
for pair in "4000:ppApiSpec.json" "4001:peApiSpec.json"; do
  port=${pair%%:*}; file=${pair#*:}
  curl -s -m15 "http://localhost:$port/swagger_doc" -o /tmp/live_$file
  python3 $SC self    "$JSON/$file"                  > /tmp/old_$file        # 비교용(기존 정규화)
  python3 $SC against /tmp/live_$file "$JSON/$file"   > "$JSON/$file"         # 결과 반영(신규를 기존 번호 기준 정규화)
  echo "### $file diff:"; diff /tmp/old_$file "$JSON/$file" | grep -cE '^[<>]'
done
```
- diff 남은 게 진짜 추가/변경 API인지 사람 1회 확인. 신규 path: `diff ... | grep -E '^>' | grep -oE '"/api/[^"]+"'`.
- 일련번호는 **기존 것 따라감** (신규 wrapper만 +20). 스크립트 자동.
- 갱신된 json은 PHASE 3 ④에서 release/test-staging 에 커밋.

스크립트 사용법:
- `python3 normalize_apispec.py self <file>` → 그 파일을 정규화만 (비교 기준 생성)
- `python3 normalize_apispec.py against <live> <committed>` → live를 committed 번호 기준으로 정규화
- 출력은 **그대로 파일에 써도 되는 유효한 JSON**이다. 휘발성 날짜/시각은 비교용 토큰이 아니라 **유효한 고정값**(`2000-01-01...`)으로 치환됨. (※ 과거 토큰 `__GENERATED_TS__`를 파일에 쓰던 버그 있었음 — 절대 파일에 토큰이 남으면 안 됨. 커밋 전 `grep __GENERATED_TS__`로 0 확인.)

### ★ 최초 1회: 포맷 정규화 커밋 분리 (옵션 A · 기본)
커밋된 ApiSpec이 아직 정규화 안 된 상태(손편집 포맷)면, 첫 동기화엔 포맷 churn이 불가피하게 섞인다.
**리뷰 가능하도록 2커밋으로 분리한다:**
```bash
# 커밋1 — 포맷 정규화 (의미 변경 없음)
python3 $SC self /tmp/committed_<file> > "$JSON/<file>"   # 각 파일
git commit -m "chore(apispec): ApiSpec 포맷 정규화 (의미 변경 없음)"
# 커밋2 — 실제 API 변경
python3 $SC against /tmp/live_<file> /tmp/committed_<file> > "$JSON/<file>"
git commit -m "feat(apispec): ppback/theplus-back API 변경 반영"
```
→ 리뷰어는 **커밋2만** 보면 됨. 머지 후 dev가 canonical이 되므로 **다음 동기화부터는 단일 커밋·깨끗한 diff**.
(이미 정규화된 파일이면 이 분리 불필요 — 바로 against 1커밋.)
커밋 전 검증: `grep -c __GENERATED_TS__ <file>`=0, `python3 -c "import json;json.load(open('<file>'))"` 통과.

---

## PHASE 3 · 배포 준비 (레포별)   ※ dev 최신화 + 브랜치 재생성 + PR

📛 **용어**: 이 단계는 "**배포 준비**"다. 실제 배포(릴리즈)는 PHASE 4에서 사람이 AWS 버튼을 눌러야 진행됨.
사용자/슬랙에 말할 때 "배포 진행"이라 하지 말고 "**배포 준비**"라고 한다.

**사전조건**: 마일스톤 작업이 리모트 dev에 머지 완료 (수동, 스킬 발동 전).
아래 ②③⑤(삭제·푸시)는 실행 전 사용자에게 "이거 할게요" 확인받는다.

```bash
cd <repo 로컬경로>

# ① dev 최신화
git checkout dev
git pull origin dev

# ② 기존 release/test-staging 정리 (분기 전에!)  — 5개 레포 모두 대상
git branch -D release/test-staging 2>/dev/null || true                 # 로컬 (있으면)
git push origin --delete release/test-staging 2>/dev/null || true      # 리모트 (있으면)
#   ⚠️ 직전 사이클 PR이 안 닫혔으면 경고 후 사용자 확인하고 삭제

# ③ dev → release/test-staging 새로 분기
git checkout -b release/test-staging

# ④ (talenx-log만) PHASE 2 결과 커밋
#   git add src/main/resources/json/ppApiSpec.json src/main/resources/json/peApiSpec.json
#   git commit -m "talenx-log ApiSpec 동기화 (ppback, theplus-back 신규/삭제 API 반영)"

# ⑤ release/test-staging 브랜치 푸시 (AWS가 브랜치 감지 = 소스 스테이지 준비)
git push -u origin release/test-staging
#   ※ 푸시 자체가 배포를 자동 트리거하지 않는다. AWS는 브랜치를 감지만 하고,
#     실제 릴리즈는 PHASE 4에서 AWS 콘솔의 릴리즈 버튼을 사람이 눌러야 진행됨.
```
이후:
```bash
# ⑥ 배포 PR (사전점검: ahead 커밋 수, 중복 PR 확인 후)
gh pr create --repo hcgtheplus/<repo> --base <base> --head release/test-staging \
  --title "<제목>" --body "<description>"
#   base: ppback/theplus-back/perpl-download=main · perpl-notification=master · talenx-log=dev
#   제목: 대부분 "Release/test-staging".
#         단 talenx-log 는 기존 컨벤션 "<MMDD> S모듈 변경사항 반영" (날짜 prefix, 예: "0605 S모듈 변경사항 반영")
#   description = 마일스톤 작업목록(제목+링크). talenx-log = 신규/삭제 API 엔드포인트 목록.
```
사전점검: `gh api repos/.../compare/<base>...release/test-staging --jq '{ahead_by}'`,
중복 `gh pr list --repo hcgtheplus/<repo> --head release/test-staging --state open`.

### ⑦ 백엔드에 공유 (슬랙 초안)
버전 빼고, PR은 `#번호` 링크, 브랜치명은 플레인 텍스트:
```
🚀 스테이징 배포 PR (base: main)

• <repo>
   PR: [#5451](https://github.com/hcgtheplus/<repo>/pull/5451)
   브랜치명: release/test-staging
```

---

## PHASE 4 · 릴리즈 (수동) + 완료 알림
- **배포 트리거는 브랜치 감지 방식이지 푸시-자동배포가 아니다.** 브랜치를 올려두면 AWS가 감지만 하고,
  실제 릴리즈는 **각 레포 파이프라인에서 사람이 AWS 콘솔의 릴리즈 버튼을 눌러야** 진행됨 (수동, 안내만).
- 배포 완료 시 담당자 멘션으로 마일스톤(배포) 스레드에 완료 초안:
  `<@담당자> 세 레포(<repos>) 스테이징 배포 완료했습니다! 🚀`

---

## (브랜치 정리) — 별도 "종료 단계" 아님
release/test-staging 삭제는 **다음 사이클 시작 시 PHASE 3 ②에서** 처리한다 (재분기 전에 직전 잔재를 지움).
즉 이번 사이클이 끝났다고 일부러 지우러 돌아오지 않는다 — **다음 배포 준비 때 ②가 알아서 정리**한다.
필요하면(예: 브랜치 깔끔히 비우고 싶을 때) 수동으로 삭제할 수 있으나(아래), 기본 흐름에선 불필요.
```bash
git -C <repo> checkout dev
git -C <repo> branch -D release/test-staging
git -C <repo> push origin --delete release/test-staging   # 또는 gh api -X DELETE .../git/refs/heads/release/test-staging
```
- ⚠️ 수동 삭제 시: PR 머지/릴리즈 완료 확인 후. 미배포면 경고.

---

## (참고) 릴리즈 테스트 체크리스트 캔버스
별도 요청 시: 릴리즈 테스트 스레드 체크리스트 캔버스 2개(사용자/어드민)의 `## 릴리즈 사항` 섹션에
백엔드 PR 목록을 **양쪽 동일하게** append (백엔드는 화면 구분 없음).
`slack_read_canvas`로 섹션 ID 확보 → `slack_update_canvas(action=append, section_id=릴리즈사항)`.
인프라/테스트/리팩토링 제외, 기능/버그만.

---

## 주의사항 요약
- `gh api issues?milestone=` → **항상 `--paginate`**.
- 슬랙은 **초안만**. "Message sent" 위젯 문구에 속지 말 것. PR 링크는 `#번호`.
- 브랜치 = 전 레포 `release/test-staging`. PR제목 = 대부분 `Release/test-staging`, **단 talenx-log는 `<MMDD> S모듈 변경사항 반영`** (날짜 prefix).
- base: 대부분 `main`, perpl-notification `master`, talenx-log `dev`.
- dev 최신화 = `git checkout dev && git pull origin dev`.
- release/test-staging은 **브랜치 감지 방식** → 푸시해두면 AWS가 감지만, 실제 릴리즈는 콘솔 수동 버튼. 사이클마다 재생성/삭제.
- talenx-log ApiSpec = **ppback(ppApiSpec/:4000), theplus-back(peApiSpec/:4001)**. API 추가·삭제·수정(파라미터/응답 변경 포함) 있으면 무조건 진행.
  **전제: 두 레포 로컬 dev 최신화 + 서버 재기동 후** swagger 떠야 의미. 정규화로 노이즈 제거, 일련번호 기존 것 따라감.
- **커밋/푸시/삭제/CodePipeline은 사용자 확인 후.** 진행 시 무엇을 할지 먼저 보여주기.
