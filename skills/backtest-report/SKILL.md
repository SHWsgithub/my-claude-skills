---
name: backtest-report
description: 백테스트 산출물(equity/trades/summary)과 전략 명세로부터 단일 HTML 리포트를 생성한다. 수익률 지표·자본곡선·거래 규칙·거래 저널을 표준 디자인으로 묶는다. 트리거 — "백테스트 리포트", "report.html 만들어", "수익률 + 거래방법 리포트", "/backtest-report".
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
---

# /backtest-report — 백테스트 HTML 리포트 생성기

`backtests/<run_id>/{equity.csv, trades.csv, summary.json, config.json}` + 전략 명세 파일(`STRATEGY.md` 또는 사용자 지정)을 입력으로 받아 **단일 자립형 HTML 리포트**를 만든다. 기본 템플릿은 `volume_entry_bear_market.html` 형식.

## 출력 파일 위치
- 기본: `backtests/<run_id>/report.html`
- 사용자 지정 시 절대경로 그대로 사용

## 입력 자동 탐지
1. 인자에 `<run_id>` 또는 `<path-to-backtest-dir>` 받으면 그 디렉터리 사용
2. 없으면 `backtests/` 하위 가장 최근 mtime 디렉터리 사용
3. 누락 파일이 있으면 어떤 파일이 없는지 보고 후 중단 (NEEDS_CONTEXT)

## 필수 섹션 순서

```
1. <h1> 제목 + <p class="subtitle"> 한 줄 요약
2. legend-box (지표·색상 가이드)
3. <h2> 핵심 지표 — summary-grid (3-col): CAGR / Sharpe / MDD 카드
4. <h2> 자본곡선 + Drawdown — chart-card 2개 (Plotly)
5. <h2> 거래 규칙 — rule-grid: 매수 조건 / 매도 조건 / 레짐 카드
6. <h2> 메트릭 표 — metric-table (전략 vs 벤치마크)
7. <h2> 거래 저널 요약 — 상위 reason 분포 + 최근 20건 표
```

## 디자인 시스템 (고정 규약)

| 토큰 | 값 |
|---|---|
| 폰트 | `-apple-system, BlinkMacSystemFont, sans-serif` |
| 본문 배경 | `#f7f9fc` |
| 텍스트 | `#1a1a1a` |
| 카드 배경 | `#ffffff` |
| 카드 모서리 | `border-radius: 10~12px` |
| 카드 그림자 | `box-shadow: 0 1px 3px rgba(0,0,0,0.08)` |
| 표 헤더 | `#2E86AB` (배경) / `white` (글자) |
| 강조 양수 | `#06A77D` |
| 강조 경고 | `#f4a261` (legend 좌측 바) |
| 강조 음수 | `#d62828` |
| max-width | `1320px` |
| 반응형 | `@media (max-width:1000px) → 1열` |

## 차트 규약
- 라이브러리: Plotly CDN `https://cdn.plot.ly/plotly-2.27.0.min.js` (head)
- 자본곡선: 전략(굵은 선) + 벤치마크(흐린 선) 동일 축, 시작값 100으로 정규화
- Drawdown: 음수 영역 fill, 색 `#d62828`
- 시계열 X축: date, Y축: 우측 정렬, hover tooltip 한국어 라벨

## 거래 규칙 카드 형식
명세(STRATEGY.md 또는 사용자 전달본)의 B*/S* 표를 그대로 변환:
```html
<div class="rule-card">
  <h3>매수 조건 (모두 만족)</h3>
  <ol class="rule-list">
    <li><b>B1</b> 시가총액 ≤ 1,000억원</li>
    <li><b>B2</b> 직전 3개 사업연도 영업이익 합 ≤ -100억</li>
    ...
  </ol>
</div>
```
- 약어 풀어쓰기(메모리 `feedback_no_abbreviations_in_make_alpha.md`) 준수
- 매수/매도/레짐은 별도 카드, rule-grid (2-col 또는 3-col)

## 거래 저널 요약 형식
- **reason 분포**: `trades['reason'].value_counts()` 결과를 가로 막대로 시각화 (Plotly bar)
- **최근 20건 표**: date / ticker / side / shares / price / reason / pnl
- 손실(pnl<0) 행은 `style="color:#d62828"`, 익절은 `#06A77D`

## 메트릭 표 컬럼
필수: `구간 / 전략명 / 기간 / 기간수익률 / 최대낙폭 / 최대낙폭일 / 변동성(연환산) / 최악일 / 최고일`
선택: Sharpe, Sortino, Calmar, 승률, 회전율

## 한국어 / 인코딩
- `<meta charset="UTF-8">` + `<html lang="ko">` 필수
- 모든 라벨 한국어. 약어는 풀네임(예: "최대낙폭" not "MDD", "샤프지수" not "Sharpe ratio"는 예외 — 고유명사로 허용)
- 숫자: 백분율 소수점 2자리(`-12.67%`), 금액 천단위 콤마

## 자립성 (offline-friendly)
- 외부 의존성은 Plotly CDN 하나만
- CSS는 전부 `<style>` 인라인
- 이미지 사용 시 base64 embed
- 단일 파일로 브라우저에서 바로 열림

## 생성 절차

### 1단계: 입력 수집
```bash
RUN_DIR="${1:-$(ls -td backtests/*/ | head -1)}"
RUN_DIR="${RUN_DIR%/}"
for f in equity.csv trades.csv summary.json; do
  [ -f "$RUN_DIR/$f" ] || echo "MISSING: $RUN_DIR/$f"
done
```
누락 보고 후 사용자 확인.

### 2단계: 명세 파일 식별
- 우선순위: `STRATEGY.md` > `BASELINE.md` > 사용자 지정 경로
- 매수/매도/레짐 표 추출 → 카드로 변환

### 3단계: 메트릭 산출
Python 스니펫으로 summary.json + equity.csv에서:
- 전체 CAGR, Sharpe, MDD, Calmar, 승률, 평균 보유일, 회전율
- 벤치마크와 동일 기간 비교 (벤치마크 csv는 사용자 지정 또는 `data/processed/benchmark_*.parquet`)

### 4단계: HTML 렌더
- Python `pandas.DataFrame.to_html(classes='dataframe metric-table', escape=False)` 활용 가능
- Plotly Figure → `to_html(include_plotlyjs=False, div_id='chart_0', full_html=False)`
- 모든 조각을 f-string으로 합성

### 5단계: 저장 + 검증
```bash
python -c "from pathlib import Path; p=Path('$RUN_DIR/report.html'); print('OK', p.stat().st_size, 'bytes')"
```
파일이 50KB 미만이면 데이터 누락 의심 → 사용자에게 확인.

## 스타터 템플릿 (생성 시 base로 사용)

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif;
         max-width: 1320px; margin: 0 auto; padding: 24px;
         background: #f7f9fc; color: #1a1a1a; }
  h1 { font-size: 28px; margin-bottom: 8px; }
  h2 { font-size: 20px; margin-top: 30px; }
  .subtitle { color: #666; margin-bottom: 24px; }
  .summary-grid, .rule-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
    margin-bottom: 24px;
  }
  @media (max-width: 1000px) {
    .summary-grid, .rule-grid { grid-template-columns: 1fr; }
  }
  .summary-card-period, .rule-card, .summary-card, .chart-card {
    background: white; border-radius: 10px; padding: 18px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 20px;
  }
  .summary-card-period h3, .rule-card h3 {
    margin: 0 0 12px 0; font-size: 16px;
  }
  .stat-row {
    display: flex; justify-content: space-between;
    padding: 6px 0; font-size: 14px;
  }
  .stat-row b { font-weight: 600; }
  .summary-card-period hr {
    border: none; border-top: 1px solid #eee; margin: 10px 0;
  }
  .metric-table { border-collapse: collapse; width: 100%; font-size: 13px; }
  .metric-table th {
    background: #2E86AB; color: white; padding: 8px; text-align: left;
  }
  .metric-table td { padding: 8px; border-bottom: 1px solid #eee; }
  .metric-table tr:nth-child(even) { background: #f8f9fa; }
  .legend-box {
    background: #fff8e1; border-left: 4px solid #f4a261;
    padding: 12px 16px; margin: 0 0 20px 0;
    border-radius: 6px; font-size: 13px;
  }
  .rule-list { margin: 0; padding-left: 18px; font-size: 14px; line-height: 1.8; }
  .pos { color: #06A77D; } .neg { color: #d62828; }
</style>
</head>
<body>

<h1>{title}</h1>
<p class="subtitle">{subtitle}</p>

<div class="legend-box">
  <b>지표 해석</b> — CAGR: 연복리 수익률 / 샤프지수: 위험조정 수익 / 최대낙폭: 정점→저점 손실폭
</div>

<h2>핵심 지표</h2>
<div class='summary-grid'>{summary_cards}</div>

<h2>자본곡선 + 최대낙폭</h2>
<div class="chart-card"><div id="chart_equity"></div></div>
<div class="chart-card"><div id="chart_drawdown"></div></div>

<h2>거래 규칙</h2>
<div class='rule-grid'>{rule_cards}</div>

<h2>메트릭 표</h2>
<div class="summary-card">{metric_table_html}</div>

<h2>거래 저널</h2>
<div class="chart-card"><div id="chart_reason"></div></div>
<div class="summary-card">{recent_trades_html}</div>

<script>
{plotly_scripts}
</script>

</body>
</html>
```

## 약속

- **데이터 위조 금지** — summary.json 없으면 CAGR 추정·날조하지 말 것. 누락 시 보고 후 사용자 입력 요청.
- **벤치마크 라벨 정확성** — KR 백테스트에 QQQ/NDX 벤치마크 두지 말 것. KR이면 KOSDAQ TR / KOSPI / KODEX150, US면 시장별 적정 인덱스 사용 (예: small-cap = IWM, NDX 전략 = QQQ).
- **재실행 가능** — 같은 입력 → 같은 HTML 출력. 랜덤·시간 의존 요소 금지(생성 시각 footer는 예외).
- **상대 경로 X** — 보고서 내부 링크는 절대경로 또는 임베드. 다른 디렉터리로 옮겨도 깨지지 않아야 함.

## 완료 조건

- [ ] HTML 파일이 `backtests/<run_id>/report.html` 또는 사용자 지정 경로에 생성됨
- [ ] 7개 필수 섹션 모두 존재
- [ ] Plotly 차트 3개(자본곡선·낙폭·reason 분포) 정상 렌더
- [ ] 거래 규칙이 명세 표와 정확히 일치 (B*/S* 번호 보존)
- [ ] 메트릭 표에 전략 + 벤치마크 모두 행으로 존재
- [ ] 한국어 라벨, UTF-8, lang="ko"
- [ ] 파일 크기 ≥ 50KB (Plotly 데이터 인라인 후 정상치)
- [ ] 브라우저에서 단일 파일로 열림 (외부 리소스 = Plotly CDN뿐)
