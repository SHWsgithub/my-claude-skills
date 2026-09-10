import json, re, sys
from collections import defaultdict, deque

DW = re.compile(r'data_wrapper_\d+')
# 휘발성 ISO8601 타임스탬프/날짜 (swagger 생성시각이 example에 박혀 매번 바뀜)
# → 유효한 고정 placeholder로 치환해 파일은 valid + 매 동기화 diff 노이즈 0.
DT = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})')
DATE = re.compile(r'\d{4}-\d{2}-\d{2}')
SENTINEL_DT = '2000-01-01T00:00:00.000Z'
SENTINEL_DATE = '2000-01-01'

def sig(v):
    return json.dumps(v.get('properties', {}).get('data'), sort_keys=True, ensure_ascii=False)

def walk_refs(paths):
    """paths 내 data_wrapper $ref를 (위치키, wrapper명) 목록으로. 위치키=(path, method, json-pointer)."""
    out = []
    def rec(node, loc):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == '$ref' and isinstance(v, str) and v.startswith('#/definitions/data_wrapper_'):
                    out.append((tuple(loc), v.split('/')[-1]))
                else:
                    rec(v, loc + [k])
        elif isinstance(node, list):
            for i, v in enumerate(node):
                rec(v, loc + [i])
    for p, methods in paths.items():
        for m, spec in methods.items():
            rec(spec, [p, m])
    return out

def normalize(spec, ref_spec=None):
    spec = json.loads(json.dumps(spec))
    if ref_spec is not None:
        # 기존(ref) 정보: 시그니처별 이름 큐 + 위치→이름 + 최대번호
        old_by_sig = defaultdict(deque); old_nums = []
        for k, v in ref_spec.get('definitions', {}).items():
            if k.startswith('data_wrapper_'):
                old_by_sig[sig(v)].append(k); old_nums.append(int(k.split('_')[-1]))
        old_max = max(old_nums) if old_nums else 0
        old_loc = {loc: name for loc, name in walk_refs(ref_spec.get('paths', {}))}
        old_sig_of = {k: sig(v) for k, v in ref_spec.get('definitions', {}).items() if k.startswith('data_wrapper_')}

        rename = {}; used_names = set()
        # 1단계: 참조 위치가 같고 시그니처가 같으면 기존 번호 그대로 유지 (churn 방지)
        for loc, lname in walk_refs(spec.get('paths', {})):
            if lname in rename:
                continue
            cname = old_loc.get(loc)
            if cname and cname not in used_names and old_sig_of.get(cname) == sig(spec['definitions'][lname]):
                rename[lname] = cname; used_names.add(cname)
        # 2단계: 위치매칭 안 된 wrapper는 시그니처 FIFO(이미 쓴 이름 제외)
        used = defaultdict(int); unmatched = []
        for k in [d for d in spec.get('definitions', {}) if d.startswith('data_wrapper_')]:
            if k in rename:
                continue
            s = sig(spec['definitions'][k]); q = old_by_sig.get(s)
            cand = None
            if q:
                while used[s] < len(q):
                    c = q[used[s]]; used[s] += 1
                    if c not in used_names:
                        cand = c; break
            if cand: rename[k] = cand; used_names.add(cand)
            else: unmatched.append(k)
        # 3단계: 진짜 신규 wrapper → 기존 최대번호 이어서 +20
        nxt = old_max
        for k in unmatched: nxt += 20; rename[k] = f'data_wrapper_{nxt}'
        def remap(s): return DW.sub(lambda m: rename.get(m.group(0), m.group(0)), s)
        nd = {}
        for k, v in spec['definitions'].items():
            nk = rename.get(k, k); vv = json.loads(remap(json.dumps(v, ensure_ascii=False)))
            if nk.startswith('data_wrapper_'): vv['description'] = f'{nk} model'
            nd[nk] = vv
        spec['definitions'] = nd
        spec['paths'] = json.loads(remap(json.dumps(spec['paths'], ensure_ascii=False)))
        out = {}
        for k in ref_spec['definitions']:
            if k in spec['definitions']: out[k] = spec['definitions'][k]
        for k in spec['definitions']:
            if k not in out: out[k] = spec['definitions'][k]
        spec['definitions'] = out
        spec = {k: spec[k] for k in ref_spec if k in spec}
    s = json.dumps(spec, indent=2, ensure_ascii=False)
    # 휘발성 날짜/시각 → 유효한 고정 placeholder (2단계 토큰으로 겹침 방지)
    s = DT.sub('@@DT@@', s)          # 먼저 datetime
    s = DATE.sub('@@D@@', s)         # 그다음 순수 날짜
    s = s.replace('@@DT@@', SENTINEL_DT)
    s = s.replace('@@D@@', SENTINEL_DATE)
    s = re.sub(r'("example": -?\d+)\.0(?=[,\n\]])', r"\1", s)  # example 정수.0 -> 정수
    return s

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'self':
        print(normalize(json.load(open(sys.argv[2]))))
    elif mode == 'against':
        print(normalize(json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))))
