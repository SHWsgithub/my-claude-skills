---
description: 현재 브랜치에서 변경된 API 엔드포인트를 실제 API 콜로 검증하고 pass/fail 결과를 정리합니다 (도구는 curl)
argument-hint: [endpoint-filter]
allowed-tools: [Read, Glob, Grep, Bash, Edit]
---

# API 테스트

현재 작업 브랜치에서 추가/변경된 API 엔드포인트를 자동으로 파악하고, 실제 API 콜(curl)로 검증하여 결과를 정리합니다. (curl은 도구일 뿐, 목적은 변경된 엔드포인트의 동작 검증)

## Arguments

사용자가 전달한 인자: $ARGUMENTS
- 인자가 있으면 해당 엔드포인트만 필터링하여 테스트
- 인자가 없으면 브랜치 전체 변경된 API를 대상으로 테스트

## 실행 절차

### 1단계: 브랜치 분석

현재 브랜치에서 dev(메인) 대비 변경된 API 엔드포인트를 파악합니다.

```bash
# 변경된 컨트롤러 파일 확인
git diff dev..HEAD --name-only | grep -E "controllers/"

# 새로운/변경된 엔드포인트 추출 (get/post/put/delete)
git diff dev..HEAD -- app/controllers/ | grep "^+" | grep -E "(get |post |put |delete |patch )"
```

변경된 컨트롤러 파일을 읽고 엔드포인트 경로, HTTP 메서드, 파라미터를 파악합니다.

### 2단계: 테스트 환경 준비

#### 로그인 및 토큰 획득

로컬 환경 기준으로 다음 테스트 계정을 사용합니다:

| 계정 | 역할 | 비밀번호 |
|------|------|----------|
| yj@perpl.io | HR 어드민 (손예진) | HCGhcg123 |
| js@perpl.io | 일반 사용자/조직장 (유재석) | HCGhcg123 |
| kh@perpl.io | 일반 사용자/구성원 (황광희) | HCGhcg123 |

로그인 방법:
```bash
TTID=$(curl -s -i -X POST http://localhost:8095/login \
  -H "Content-Type: application/json" \
  -d '{"loginId": "<email>", "password": "HCGhcg123"}' 2>&1 \
  | grep -o 'TTID=[^;]*' | head -1 | sed 's/TTID=//')
```

Rails API 호출 시 인증:
```bash
curl -s "http://localhost:4000/api/..." -H "Cookie: TTID=$TTID"
```

- 워크스페이스: 로컬 퍼플앤컴퍼니 (id: 2, hash_id: `04dfe596cb2bc3f10b70606fd80b8068`)
- **주의**: user id 1은 수퍼어드민이므로 테스트 데이터에서 제외

#### 테스트 데이터 생성 (★ API 호출 우선)

**원칙: 테스트 데이터는 가능한 한 실제 API 호출(curl)로 생성한다.**
Rails runner로 DB에 직접 insert하면 모델 콜백·검증·연관 생성이 누락되어 운영과 어긋난 데이터가 만들어진다.
(예: 리뷰 생성 시 `create_response` 콜백으로 응답 자동생성 / 세션 시작 시 스냅샷 워커 / origin_id·상태전이 등)
API로 만들면 운영과 동일한 경로를 타므로 누락이 없다.

> **엔드포인트·payload는 "프론트엔드 실제 호출" 기준으로 고른다.**
> 백엔드 라우트엔 deprecated/미사용 엔드포인트가 섞여 있을 수 있어, 라우트만 보고 쓰면 실제와 어긋난다.
> 그 기능이 노출되는 **화면의 프론트엔드 `src/config/api/*`** 에서 실제 호출하는 경로·payload·필드명(camel↔snake 변환 포함)을 확인해 쓸 것.
> - **사용자 화면** 기능 → `ppfront`
> - **어드민 화면** 기능 → `talenx-admin`
> - 기능에 따라 둘 중 하나. **setup 데이터 생성 / 테스트 대상 엔드포인트 모두** 동일 원칙.

```bash
# 응답에서 id를 jq로 추출해 다음 단계로 체이닝
RESP=$(curl -s -X POST "http://localhost:4000/api/v2/workspaces/$WS/..." \
  -H "Cookie: TTID=$TTID" -H "Content-Type: application/json" -d '{...}')
ID=$(echo "$RESP" | jq -r '.data.id')
```

API 생성 시 주의:
- **역할별 토큰**: 작성자/검토자 등 writer에 따라 데이터가 달라지는 흐름은 각 계정으로 로그인해 각자 토큰으로 호출 (예: 리뷰는 assignee가 생성·자기응답, manager가 자기응답+snapshot). 응답 id는 `GET :id` 상세로 받아서 사용.
- **비동기 생성**(job_id 반환)은 bulk polling으로 완료 대기 후 다음 단계.
- 201이 body 없이 오면 목록/상세 GET으로 생성된 id를 조회.

**Rails runner는 보조로만:**
- 읽기 전용 조회(기존 id 확인): `docker compose exec app rails runner "..."` — 워크스페이스는 `Workspace.find_by!(id: 2)` (find는 hash_id)
- API로 만들 수 없는 데이터의 최후 수단 (이때 콜백 누락 가능성 명시)
- user id 1(수퍼어드민) 제외

**정리(cleanup):** 생성한 테스트 데이터는 가능한 한 **API DELETE로 정리**해 net-zero 유지. (소프트삭제가 연관까지 discard 안 하는 경우만 runner로 보강 discard)

#### Sidekiq 확인

비동기 작업이 있는 API라면 Sidekiq 상태를 확인합니다:

```bash
# 큐 및 워커 상태 확인
docker compose exec app rails runner "
info = Sidekiq::ProcessSet.new
info.each { |p| puts 'busy: ' + p['busy'].to_s + '/' + p['concurrency'].to_s }
"
```

워커가 꽉 찬 경우(busy == concurrency) 좀비 job일 수 있으므로:
```bash
docker compose restart sidekiq
```

#### Sidekiq job polling

`job_id`를 반환하는 비동기 API의 완료 여부는 bulk polling 엔드포인트로 확인합니다. **레포별로 경로가 다르니 현재 작업 레포에 맞는 것을 사용하세요:**

- **theplus-back**: `V1::Bulk` → `GET /api/v1/bulk?workspace_hash_id=<hash>&job_id=<job_id>`
- **ppback**: `GET /api/v2/workspaces/:workspace_id/bulk?job_id=<job_id>`

```bash
# theplus-back 예시
curl -s "http://localhost:4000/api/v1/bulk?workspace_hash_id=$WS_HASH&job_id=$JOB_ID" \
  -H "Cookie: TTID=$TTID"
# ppback 예시
# curl -s "http://localhost:4000/api/v2/workspaces/$WS/bulk?job_id=$JOB_ID" -H "Cookie: TTID=$TTID"
# 응답 예: {"job_id":"...","total":0,"at":0,"progress":0,"status":"complete"}
# status: queued | working | complete | failed
```

### 3단계: 테스트 케이스 생성 및 실행

각 엔드포인트마다 아래 케이스를 기본으로 포함합니다:

#### 필수 케이스
- **정상 요청**: 올바른 파라미터와 권한으로 요청 → 예상 status code 확인
- **401 Unauthorized**: 인증 없이 요청
- **403 Forbidden**: 권한 없는 유저로 요청 (일반 유저가 어드민 API 호출 등)
- **404 Not Found**: 존재하지 않는 리소스 ID로 요청

#### 선택 케이스 (엔드포인트 특성에 따라)
- **덮어쓰기 확인**: 동일 리소스에 재요청 시 기존 데이터 교체 확인
- **빈 데이터 요청**: 빈 배열/빈 body 요청
- **비동기 작업 polling**: bulk 엔드포인트로 완료 여부 확인 (status: queued/working/complete/failed). theplus-back은 `GET /api/v1/bulk?workspace_hash_id=&job_id=`, ppback은 `GET /api/v2/workspaces/:workspace_id/bulk?job_id=`
- **데이터 정합성**: 저장된 데이터를 조회하여 입력과 일치 확인
- **정렬/필터**: position, 날짜 등 정렬 조건 확인

#### curl 실행 패턴

```bash
# status code + body 한번에 확인
RESPONSE=$(curl -s -w "\n%{http_code}" -X <METHOD> \
  "http://localhost:4000/api/..." \
  -H "Cookie: TTID=$TTID" \
  -H "Content-Type: application/json" \
  -d '<body>')
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')
echo "[$HTTP_CODE] $BODY"
```

### 4단계: 결과 정리

모든 테스트 실행 후 아래 형식으로 정리합니다:

```
| # | 테스트 | 예상 | 실제 | 결과 |
|---|--------|------|------|------|
| 1 | 정상 요청 (HR어드민) | 200 | 200 | ✅ PASS |
| 2 | 401 인증 없이 | 401 | 401 | ✅ PASS |
| 3 | 403 권한 없는 유저 | 403 | 403 | ✅ PASS |
| 4 | 404 없는 리소스 | 404 | 404 | ✅ PASS |

전체 N/N PASS
```

FAIL이 발생하면:
- 예상 vs 실제 차이를 명시
- 관련 로그 (sidekiq, rails) 확인
- 원인 분석 및 수정 제안

### 5단계: 후속 조치

- 결과에 FAIL이 있으면 원인 분석 후 코드 수정 여부를 사용자에게 확인
- 전체 PASS이면 슬랙 공유 여부를 사용자에게 확인