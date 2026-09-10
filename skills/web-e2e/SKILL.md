---
name: web-e2e
description: 백엔드 엔드포인트나 기능명으로 시작해 프론트엔드의 API 사용처와 라우트를 찾아내고, Playwright로 실제 화면을 열어 검증한다. 목표뿐 아니라 리뷰·360 피드백·평가·근태 등 모든 기능에 적용된다. 트리거 "/web-e2e", "플레이라이트로 확인", "화면에서 확인해줘", "프론트 어디서 쓰는지 찾아서 테스트".
argument-hint: [기능명 또는 엔드포인트]
---

# 웹 E2E — 사용처 추적 후 화면 검증

백엔드 변경이 **실제 화면에서 어떻게 보이는지**를 확인하는 스킬.
curl로 응답만 보는 [[api-test]]와 짝이다 — 이 스킬은 브라우저를 띄운다.

핵심은 세 단계다: **엔드포인트 → 프론트 호출처 → 라우트(URL)** 를 찾고, 그 URL을 열어 검증한다.
라우트를 추측하지 않는다. 아래 매핑 규칙으로 **코드에서 찾아낸다.**

## 인자

`$ARGUMENTS` — 기능명(예: "목표 일괄 승인", "360 피드백 응답")이나 엔드포인트(예: `objectives/batch_approval`).
없으면 현재 브랜치의 변경된 컨트롤러에서 대상을 뽑는다.

```bash
git diff dev...HEAD --name-only | grep -E "app/controllers/"
git diff dev...HEaD -- app/controllers/ | grep "^+" | grep -oE "(get|post|put|patch|delete) ['\"][^'\"]+"
```

---

## 로컬 환경

포트가 여러 개 겹쳐 있어 **매번 확인**한다. 아래는 확인된 기준값이다.

| 대상 | URL | 정체 |
|---|---|---|
| 사용자 화면 | `http://localhost:3000` | `ppfront` (vite dev) |
| 로그인·공통 셸 | `http://localhost:3001/sign_in` | `theplus-front` — 3000 접속 시 여기로 리다이렉트 |
| 관리자 콘솔 | `http://localhost:8001` | `talenx-admin` (vite dev) |
| ppback API | `http://localhost:4000/api/...` | `ppback-web-1` (nginx → Rails) |
| 로그인 서버 | `http://localhost:8095/login` | TTID 쿠키 발급 |
| Sidekiq | `http://localhost:4000/sidekiq` | 비동기 작업 확인 |

### 어느 체크아웃이 서비스 중인지 먼저 확인한다

`talenx-admin`은 **체크아웃이 여러 개**다(`~/Desktop/talenx-admin`, `~/Desktop/Eggplant/Eggplant-admin`).
8001을 누가 서비스하는지에 따라 코드를 읽을 위치가 달라진다. 브랜치도 다를 수 있다.

```bash
for p in 3000 3001 8001; do
  pid=$(lsof -nP -iTCP:$p -sTCP:LISTEN -t | head -1)
  dir=$(lsof -a -p "$pid" -d cwd -Fn | grep ^n | sed 's/^n//')
  echo "$p → $dir  ($(git -C "$dir" branch --show-current 2>/dev/null))"
done
```

닫혀 있으면 해당 레포에서 `yarn start`(둘 다 `env-cmd -e development ... vite`)를 사용자에게 요청한다.
**dev 서버는 임의로 띄우지 않는다** — 포트 충돌과 빌드 캐시를 건드릴 수 있다.

### 테스트 계정

로컬 시드 계정. 비밀번호는 계정마다 둘 중 하나이고, 실패하면 반대쪽으로 재시도한다.

| 이메일 | 이름 | 역할 | 비밀번호 |
|---|---|---|---|
| yj@perpl.io | 손예진 | **HR 어드민** (어드민 콘솔 접근) | `HCGhcg123` |
| sh@perpl.io | 최성희 | 승인자·관리자 | `HCGhcg123` |
| js@perpl.io | 유재석 | 담당자·조직장 | `HCGhcg123` |
| kh@perpl.io | 황광희 | 구성원 | `HCGhcg123` |
| sw@perpl.io | 이서우 | 구성원 | `HCGhcg11!!` |
| ws@perpl.io | 정우성 | 승인자 | `HCGhcg11!!` |
| ai@perpl.io | 유아인 | 담당자 | `HCGhcg11!!` |
| ksg@perpl.io | 강슬기 | 담당자 | `HCGhcg11!!` |
| psy@perpl.io | 박수영 | 승인자 | `HCGhcg11!!` |
| jh@perpl.io | 문정혁 | 담당자 | `HCGhcg11!!` |

- 워크스페이스: **로컬 퍼플앤컴퍼니** (id `2`, hash_id `04dfe596cb2bc3f10b70606fd80b8068`)
- **user id 1은 수퍼어드민** — 테스트 대상에서 제외
- 손예진은 워크스페이스가 2개다. 로그인 직후 선택 화면에서 반드시 **로컬 퍼플앤컴퍼니** 입장

### 로그인 직후 팝업

Playwright가 여기서 막히는 일이 잦다. 화면 조작 전에 처리한다.

- "비밀번호 변경 필요" → **다음에 변경**
- "약관 동의" → **모두 동의합니다** 체크 → **확인**

---

## 1단계 — 엔드포인트에서 프론트 호출처 찾기

**백엔드 라우트만 보고 고르지 않는다.** deprecated·미사용 엔드포인트가 섞여 있어 실제와 어긋난다.
프론트가 실제로 부르는 경로·payload·필드명(camel↔snake 변환 포함)을 확인해야 한다.

기능이 어느 화면에 있느냐로 레포가 갈린다.

| 화면 | 레포 | API 경로 상수 |
|---|---|---|
| 사용자 화면 | `ppfront` | `src/config/api.js` (940여 개 상수) |
| 관리자 콘솔 | `talenx-admin` | `src/config/host.ts` |

```bash
# 엔드포인트 조각으로 상수를 찾는다
grep -rn "batch_approval" ~/Desktop/ppfront/src/config/api.js
#   → api.js:173  OBJECTIVE_APPROVE_BULK: "/workspaces/:workspaceId/objectives/batch_approval"

# 그 상수를 쓰는 호출처로 넘어간다
grep -rn "OBJECTIVE_APPROVE_BULK" ~/Desktop/ppfront/src
#   → modules/objectives.js:1226  OBJECTIVES.OBJECTIVE_APPROVE_BULK.replace(":workspaceId", workspaceId)
```

`api.js`는 상수를 **그룹 객체 66개**로 묶어 export한다(`export const OBJECTIVES = { ... }`).
그래서 호출처에서는 `OBJECTIVES.OBJECTIVE_APPROVE_BULK`처럼 네임스페이스가 붙는다 —
grep은 상수명만으로 하면 정의와 호출처가 함께 잡힌다.

**어느 API 버전인지 같이 확인한다.** 같은 파일에 호스트가 나뉘어 있다.

```
HOST    = ${VITE_API_URL}/api/v1     ← v1
HOST_V2 = ${VITE_API_URL}/api/v2     ← v2
```

호출처에서 `HOST`를 쓰는지 `HOST_V2`를 쓰는지 봐야 실제로 어느 컨트롤러가 타는지 확정된다.
ppback에 v1·v2 같은 이름의 엔드포인트가 둘 다 있는 경우가 있다.

`ppfront`는 상수 → `src/modules/**`(Redux) 또는 `src/hooks/**`에서 호출하고,
컴포넌트는 `src/hooks/useSubmit*.ts` 같은 훅을 쓴다. axios 인스턴스는 `src/lib/axiauth.js`.

경로 상수로 못 찾으면 **엔드포인트 문자열을 레포 전체에서** 찾는다(템플릿 리터럴로 조립된 경우).

```bash
grep -rn "objectives/batch" ~/Desktop/ppfront/src | head
```

---

## 2단계 — 호출처에서 라우트(URL) 찾기

### ppfront — React Router v5, 명시적 라우트

라우트가 `src/App.jsx`와 `src/containers/**/Layout.jsx`에 `<Route path="...">`로 선언돼 있다.

```bash
grep -rn 'path="' ~/Desktop/ppfront/src/App.jsx ~/Desktop/ppfront/src/containers/user_page/Layout.jsx \
  | grep -iE "objective|review|feedback|multi_source"
```

사용자 화면 URL은 대개 `/workspaces/:workspaceId/...` 형태다. `:workspaceId`에 **hash_id**를 넣는다.

```
/workspaces/04dfe596cb2bc3f10b70606fd80b8068/multi_source_feedbacks
```

호출처 컴포넌트 파일 경로로 역추적하는 것도 빠르다 — `src/containers/<기능>/...`이 그 라우트의 element다.

### talenx-admin — 파일 기반 라우팅

`src/containers/route/RoutesList.tsx`가 `import.meta.glob("/src/pages/**/*.tsx")`로 라우트를 만든다.
**파일 경로가 곧 URL**이다. 변환 규칙은 이렇다.

| 파일 | URL |
|---|---|
| `src/pages/performance/objective/records/index.tsx` | `/performance/objective/records` |
| `src/pages/appraisal/ratings/[appraisalRatingId].tsx` | `/appraisal/ratings/:appraisalRatingId` |
| `src/pages/foo/[...rest].tsx` | `/foo/*` |

전체 라우트를 한 번에 뽑는다.

```bash
cd <8001을 서비스하는 admin 체크아웃>
find src/pages -name "*.tsx" \
  | sed 's|^src/pages||; s|/index\.tsx$||; s|\.tsx$||; s|\[\([a-zA-Z]*\)\]|:\1|g' \
  | grep -iE "objective|review|feedback|appraisal" | sort
```

자주 쓰는 목적지(확인된 값):

| 기능 | 관리자 콘솔 URL |
|---|---|
| 목표 현황 | `/performance/objective/records` |
| 목표 설정 | `/performance/objective/settings` |
| 핵심성과 현황 | `/performance/objective/key_result_records` |
| 목표 주기 | `/performance/objective/cycles` |
| 리뷰 현황·설정·템플릿 | `/performance/review/records` · `/settings` · `/templates` |
| 360 피드백 설정·현황 | `/multi_source_feedback/settings` · `/records` · `/group` |
| 360 평가자 기록 | `/multi_source_feedback/assessor_records` |
| 평가 설정·템플릿 | `/appraisal/settings` · `/appraisal/templates` |
| 상시 피드백 | `/performance/feedback/records` · `/settings` |
| 1:1 | `/performance/one_on_one/records` |

---

## 3단계 — Playwright로 검증

`mcp__playwright__*` 도구를 쓴다. 순서를 지킨다.

1. `browser_navigate` → 로그인 URL
2. `browser_snapshot`으로 **접근성 트리를 먼저 읽는다** (셀렉터를 추측하지 않는다)
3. `browser_fill_form`으로 로그인 → 팝업 처리 → 워크스페이스 선택
4. 1·2단계에서 찾은 URL로 `browser_navigate`
5. 조작(`browser_click` / `browser_type` / `browser_select_option`)
6. 검증
   - `browser_snapshot` — 화면 상태
   - `browser_network_requests` — **의도한 엔드포인트가 실제로 호출됐는지, 응답 코드**
   - `browser_console_messages` — 프론트 에러
   - `browser_take_screenshot` — 증거

### 비동기 작업이 끼면 기다린다

체크인 자동 반영처럼 워커가 처리하는 기능은 **승인 직후 화면에 반영되지 않는 게 정상**이다.
화면을 새로고침하기 전에 큐가 비었는지 확인한다.

```bash
docker compose exec -T app rails runner 'puts KeyResultReflectionEvent.unprocessed.count'
# 또는 http://localhost:4000/sidekiq 의 talenx_default 큐
```

`browser_wait_for`로 텍스트가 나타날 때까지 기다리는 편이 `sleep`보다 안정적이다.

### 에러 표시를 검증할 때

4xx 응답에서 **프론트가 실제로 사용자에게 무엇을 보여주는지**가 관심사다.
`browser_network_requests`로 응답 코드·본문을 확인하고, `browser_snapshot`으로
스낵바·토스트·인라인 메시지가 떴는지 본다. **네트워크는 실패했는데 화면은 조용한** 경우가 흔한 결함이다.

---

## 보고 형식

- **경로 추적**: 엔드포인트 → 상수(파일:행) → 호출처(파일:행) → 라우트(파일:행) → URL
- **검증 결과**: 시나리오별 pass/fail, 실제 호출된 요청과 응답 코드
- **증거**: 스크린샷, 콘솔 에러, 네트워크 로그
- 화면에서 재현하지 못한 시나리오는 **왜 못 했는지**를 적는다(데이터 부재 / 권한 / dev 서버 미구동)

## 경계

- **읽기와 화면 조작만 한다.** 시드 데이터를 새로 만들어야 하면 [[api-test]]의 원칙대로
  **실제 API 호출**로 만든다. `rails runner`로 DB에 직접 insert하면 콜백·검증·연관 생성이 누락돼
  운영과 어긋난 데이터가 된다.
- dev 서버·docker 컨테이너를 **임의로 재시작하지 않는다.** 필요하면 사용자에게 요청한다.
- 프론트 코드를 고치지 않는다. 프론트 결함을 찾으면 **파일:행과 재현 절차로 보고**한다.
- `.playwright-mcp/` 산출물은 커밋 대상이 아니다. ppback의 `.gitignore`에 없으니 주의한다.
- 스크린샷·네트워크 로그에 계정 이메일이 찍힐 수 있다. **외부에 공유하기 전에 확인**한다.
