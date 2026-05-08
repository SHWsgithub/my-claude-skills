---
name: figma-read
description: Figma 파일·프레임·컴포넌트에서 디자인 데이터·이미지·컨텍스트를 가져오는 워크플로우. "피그마 읽어줘", "이 Figma URL 분석해줘", "/figma-read" 요청에 사용한다.
---

# 피그마 읽기

Figma 파일/프레임/컴포넌트에서 **디자인 데이터·이미지·컨텍스트**를 가져오는 워크플로우.
Code → Figma 쓰기는 범위에서 제외하고, **Figma → Code 단방향 읽기**에만 집중한다.

## Usage

```
/figma-read
```

또는 대화 중에 "피그마에서 ~ 가져와", "이 Figma URL 분석해줘" 같은 요청이 오면 이 스킬의 절차를 따른다.

---

## 0. 전제 조건 확인

사용자에게 아래 정보를 확인한다 (이미 제공된 경우 스킵):

- **대상 Figma URL** — 파일/프레임/노드 단위 어떤 것이든 가능
  - 예: `https://www.figma.com/design/<fileKey>/<name>?node-id=<nodeId>`
- **목적** — 무엇을 가져올지 명확히
  - `data` (구조/텍스트/토큰) / `image` (PNG·SVG 스크린샷) / `context` (개발용 컨텍스트)
- **출력 위치** — 이미지 저장 경로, 데이터 파일 경로 (기본: `./figma-out/`)

URL에서 파일 키(fileKey)와 노드 ID(nodeId)를 즉시 파싱해 두고 시작한다.

```
https://www.figma.com/design/<fileKey>/<name>?node-id=1-234
                            ^^^^^^^^           ^^^^^
                            fileKey            nodeId (1:234로 변환)
```

> 💡 URL 상의 `node-id=1-234`는 Plugin/REST API에서는 `1:234`로 표기된다. 하이픈을 콜론으로 치환해서 사용한다.

---

## 1. MCP 서버 선택 — seat 에 따라 세 갈래

Figma MCP 는 **seat(권한 등급)** 에 따라 쓸 수 있는 것이 다르다. `/mcp` 로 설치 상태를, Figma 계정 설정에서 본인 seat 를 확인한다.

| MCP 이름 | 전송 | 인증 | seat 요건 | 대표 도구 |
|---|---|---|---|---|
| `figma-framelink` (figma-developer-mcp) | STDIO (로컬) | Personal Access Token | ✅ **무료·Viewer·Collab 포함 전부** | `get_figma_data`, `download_figma_images` |
| `figma-dev-mode-mcp-server` | SSE (데스크톱 앱) | 데스크톱 로그인 | ❌ Dev / Full seat 전용 | `get_design_context`, `get_screenshot`, `get_variable_defs` |
| `figma-remote-mcp` (mcp.figma.com) | HTTP | OAuth | ❌ Dev / Full seat 전용 (무료·Viewer 는 월 6회) | `get_design_context`, `get_screenshot`, `generate_figma_design` |

**선택 규칙 (seat 기준 분기):**

- **Dev/Full seat 사용자**: 시각/변수 포함 풀 컨텍스트가 필요하면 `figma-dev-mode-mcp-server` 또는 `figma-remote-mcp`. 구조·텍스트·토큰 추출만이면 `figma-framelink` 로도 충분하고 rate limit 덜 탄다.
- **Viewer/Collab/무료 사용자**: **`figma-framelink` 가 유일한 실용 경로.** 나머지 두 개는 "This resource couldn't be accessed" / 월 6회 제한으로 실전 사용 불가.

### 설치 확인·추가

```bash
# 현재 등록된 MCP 확인
claude mcp list

# (Dev/Full seat) 공식 원격 MCP 추가
claude mcp add --transport http figma-remote-mcp https://mcp.figma.com/mcp

# (전 seat) Framelink 추가 — PAT 기반, 무료 계정 OK
#   flag 순서 주의: `-e` 는 variadic 이라 이름보다 먼저,
#   그리고 반드시 -s/-- 같은 다른 옵션으로 끊어야 파싱됨.
claude mcp add -e FIGMA_API_KEY=<PAT> -s user figma-framelink -- npx -y figma-developer-mcp --stdio

# 인증 필요 시 Claude Code 내부에서 /mcp 실행
```

> PAT 는 Figma → Settings → Security → Personal access tokens 에서 생성.
> 최소 scope: `file_content:read` + `file_dev_resources:read`.
> PAT 는 `~/.claude.json` 에 평문 저장되므로 유출 시 즉시 회전.

> 인증 토큰이 만료됐거나 `401` 계열 에러가 나면 `/mcp` 에서 재인증을 요청한다.

### PAT 안전 취급 — 전사에 노출되지 않게

Claude Code 에서 **사용자가 보낸 메시지·에이전트가 실행한 Bash 명령·그 stdout** 은 모두 두 곳에 기록된다:
- **로컬 JSONL 전사** `~/.claude/projects/<encoded>/<sessionId>.jsonl`
- **Anthropic 서버 사본** (안전/남용 모니터링 목적 보관, 사용자 통제 불가)

PAT 가 어느 한쪽에 한 번 들어가면 **유출된 것으로 간주하고 회전** 해야 한다. 비용은 재발급 1분, 대안은 없음.

**지키는 원칙:**

1. **PAT 값을 채팅 메시지로 받지 않는다.** 사용자가 붙여넣으려 하면 즉시 중단하고 "Claude Code 밖 별도 터미널에서 `claude mcp add ...` 를 실행해 달라" 고 안내한다.
2. **MCP 등록 명령은 세션 밖에서 실행.** 세션 안에서 Bash 로 `claude mcp add -e FIGMA_API_KEY=<PAT> ...` 를 실행하면 그 명령 문자열이 그대로 JSONL·서버에 남는다. 에이전트가 대신 실행하지 않는다.
3. **등록 이후에는 MCP 툴콜만 사용.** `mcp__figma-framelink__get_figma_data` 같은 툴 호출은 토큰 값을 노출하지 않는다 (MCP 서버 프로세스가 환경변수로 직접 읽음).
4. **REST API 우회가 필요하면 환경변수 참조로만.** 사용자가 사전에 셸에서 `export FIGMA_PAT=...` 해두고, 명령에는 `$FIGMA_PAT` 만 쓴다:
   ```bash
   # 전사에 평문 박힘 — 금지
   curl -H "X-Figma-Token: figd_..." "https://api.figma.com/..."

   # 값은 셸 변수, 전사에는 $FIGMA_PAT 만 — 허용
   curl -H "X-Figma-Token: $FIGMA_PAT" "https://api.figma.com/..."
   ```
5. **이미 받아버린 경우.** 사용자가 붙여넣은 뒤에야 알아챘다면 즉시 고지:
   > "이 PAT 는 로컬 JSONL + Anthropic 서버 사본 두 곳에 이미 기록됐으며 회수 불가. Figma Settings → Security 에서 revoke + 새 PAT 발급 후, 새 터미널에서 `claude mcp add ...` 로 재등록을 권장합니다."

   작업은 멈추지 말고 이어가되, 회전 완료 전까진 해당 PAT 가 살아 있다는 전제로 진행한다.

### MCP 툴이 세션에 아직 안 실린 경우 (REST API 우회)

`claude mcp add` 직후에는 **현재 세션**에는 툴이 로드되지 않는다. 새 세션을 여는 게 원칙이지만, 급할 때는 REST API 로 동일 데이터를 확보할 수 있다 (반드시 위 "PAT 안전 취급" §4 의 환경변수 참조 원칙 준수):

```bash
curl -H "X-Figma-Token: $FIGMA_PAT" \
  "https://api.figma.com/v1/files/<fileKey>/nodes?ids=<nodeId>&depth=<n>"
```

Viewer seat 에서도 `role: "viewer"` + HTTP 200 으로 응답한다 (파일 보기 권한이 있다는 전제). TEXT 노드만 필터해 `style.fontFamily/fontSize/lineHeightPx/fontWeight` + `fills[0].color` 를 추출하면 Framelink `get_figma_data` 와 사실상 같은 결과.

---

## 2. 읽기 시나리오별 절차

### 시나리오 A — 프레임 구조·텍스트·레이아웃 가져오기

사용자가 "이 화면의 구조를 뽑아줘", "텍스트·색·폰트 정리해줘"라고 할 때.

1. `figma` MCP의 `get_figma_data` 호출
   - 인자: `fileKey`, `nodeId`(있으면 해당 프레임만), `depth`(기본 2~3, 큰 파일은 1)
2. 응답에서 다음을 추출·요약
   - 프레임 치수, `layoutMode`, `itemSpacing`, padding
   - 텍스트 노드: `characters`, `fontName`, `fontSize`, `fills`
   - 색상/효과: `fills`, `strokes`, `effects`
   - 컴포넌트 인스턴스 여부(`type === 'INSTANCE'`)와 마스터 이름
3. 결과를 `figma-out/<fileKey>-<nodeId>.json`에 원본 저장 + 요약 마크다운 생성

> ⚠️ `depth`를 너무 크게 주면 응답이 수 MB에 달할 수 있다. 필요한 서브트리만 `nodeId`로 타겟팅한다.

### 시나리오 B — 이미지(PNG/SVG) 다운로드

"이 프레임 PNG로 떠줘", "아이콘 SVG 가져와줘"라고 할 때.

1. 대상 노드 ID 확보 (시나리오 A의 1번을 거치면서 수집해 두면 효율적)
2. `figma` MCP의 `download_figma_images` 호출
   - 인자: `fileKey`, `nodeIds[]`, `format`(`png`|`svg`), `scale`(1~4)
3. 저장 경로를 명시 — 기본 `./figma-out/images/<nodeId>.<ext>`
4. 큰 파일은 `scale=2` 이상이면 시간이 오래 걸리므로, 먼저 1배로 받고 필요 시 고해상도 재요청

### 시나리오 C — 개발용 디자인 컨텍스트

"이 컴포넌트 Code Connect 매핑 확인해줘", "이 프레임을 코드로 옮기기 위한 컨텍스트 달라"라고 할 때.

1. `figma-remote-mcp`의 `get_design_context` 호출
   - 인자: `fileKey`, `nodeId`
2. 응답에 포함될 수 있는 것들:
   - 컴포넌트 이름·variant·프로퍼티
   - Code Connect로 매핑된 소스 컴포넌트 경로
   - 디자인 토큰(Variables) 참조
3. 매핑이 있다면 해당 소스 파일을 직접 읽어서 대조

### 시나리오 D — 시각 확인용 스크린샷

"지금 그 프레임 보여줘", "시각적으로 어떤지 확인만 하자"라고 할 때.

1. `figma-remote-mcp`의 `get_screenshot` 호출 (또는 `figma`의 `download_figma_images` PNG)
2. 결과를 사용자에게 보여주고, 후속 작업 결정
   - 코드화할지 / 토큰만 뽑을지 / 수정 제안만 할지

---

## 3. 추출 결과 정리 템플릿

각 시나리오가 끝나면 아래 형식으로 요약을 제시한다.

```markdown
# Figma 읽기 결과

**파일:** <fileKey>
**노드:** <nodeId> (<프레임 이름>)
**URL:** <원본 URL>
**수집 일시:** YYYY-MM-DD HH:mm

## 개요
- 프레임 크기: WxH
- 레이아웃: (VERTICAL|HORIZONTAL|NONE), gap=N, padding=T/R/B/L

## 컴포넌트 트리 (요약)
- <ComponentA> (INSTANCE → master: <ComponentA>)
- <ComponentB> (INSTANCE)
- ...

## 텍스트
| 노드 | 텍스트 | 폰트 | 크기 | 색상 |
|---|---|---|---|---|
| <nodeId> | <text snippet> | <font-family> | <px> | <hex> |

## 색상/토큰
- <color-token-1> — <usage>
- <color-token-2> — <usage>
- ...

## 이미지 저장
- `figma-out/images/<nodeId>.png`

## 특이사항
- 중첩 인스턴스에서 텍스트 오버라이드가 있는 경우 주의
- 누락된 variant / detached instance 여부
```

---

## 4. 흔한 함정·해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `get_figma_data` 응답이 너무 큼 | `depth` 과다 또는 파일 전체 스캔 | `nodeId` 지정 + `depth` 낮춤 |
| 텍스트가 `characters` 대신 `???`로 나옴 | 폰트 미로딩 또는 override 누락 | 마스터 컴포넌트도 같이 조회 |
| `download_figma_images` 404 | 잘못된 `nodeId` 포맷 (`1-234` vs `1:234`) | URL의 `-`를 `:`으로 치환 |
| `get_design_context` 권한 에러 | 원격 MCP 미인증 | `/mcp`에서 `figma-remote-mcp` 인증 |
| `This resource couldn't be accessed` (데스크톱/원격 MCP) | seat 부족 (View/Collab/무료) 또는 파일 view 권한 없음 | §1 의 `figma-framelink` (PAT) 경로로 전환. 파일 view 권한 자체가 없으면 공유 요청 |
| MCP 툴 리스트에 방금 등록한 서버가 안 뜸 | Claude Code 세션 시작 이후 등록됨 | 새 세션으로 재진입, 또는 §1 의 REST API 우회 임시 사용 |
| 중첩 인스턴스 식별 불안정 | ID 기반 접근이 느슨 | `type === 'TEXT'` + 위치(절대 좌표) 기반 탐색 |
| 컴포넌트 인스턴스인데 마스터 이름이 비어 있음 | detached instance | 원본 컴포넌트 찾아 별도 조회 |

---

## 5. 출력 원칙

- **원본 JSON은 항상 파일로 저장**한다. 대화에 전부 풀어놓지 않는다 (컨텍스트 소모).
- 사용자에게는 **요약 + 핵심 표/코드 스니펫**만 제시하고, 필요 시 파일 경로를 안내한다.
- 읽기 결과가 코드 생성이나 토큰 동기화로 이어질 때는 **별도 작업**으로 분리한다. 이 스킬은 읽기까지만 책임진다.

---

## Requirements

- 대상 Figma 파일에 대한 **보기 권한** (필수, seat 에 관계없이)
- 아래 MCP 중 **최소 하나**가 Claude Code 에 설치·인증돼 있을 것
  - Dev/Full seat: `figma-dev-mode-mcp-server` 또는 `figma-remote-mcp` (시각·변수 풀 컨텍스트)
  - **Viewer/Collab/무료 seat: `figma-framelink` (figma-developer-mcp + PAT) — 유일한 실용 경로**
- (선택) `./figma-out/` 같은 결과 저장 디렉토리 쓰기 권한

## 참고

이 스킬의 절차는 hwsong이 경험한 Figma MCP 읽기 경로를 기반으로 한다. 쓰기(Code → Figma, H-컴포넌트 조립 등)는
별도 스킬에서 다룬다.
