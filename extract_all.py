# -*- coding: utf-8 -*-
"""多品种通用提取：把数据库目录下各品种工作簿转成多品种图表数据。
复用 PTA 的季节性对齐/频率识别逻辑。输出 assets/js/data.js = window.DB={commodities:[...]}"""
import os, re, json, math, datetime, calendar, glob
import openpyxl, xlrd

HERE = os.path.dirname(os.path.abspath(__file__))

def _data_dir():
    """数据目录：环境变量优先，其次站点根目录 数据库/ 或旧布局"""
    env = os.environ.get("COMMODITY_DATA_DIR")
    if env and os.path.isdir(env):
        return os.path.abspath(env)
    for d in [os.path.join(HERE, "数据库"),
              os.path.join(HERE, "..", "pta-update", "数据库"),
              os.path.join(HERE, "..", "数据库")]:
        if os.path.isdir(d):
            return os.path.abspath(d)
    return ""

BASE = _data_dir()
if not BASE:
    raise SystemExit("未找到数据目录：请把所有品种工作簿放到站点根目录的 数据库/ 下，"
                     "或用环境变量 COMMODITY_DATA_DIR 指定目录")
SITE = HERE
OUT = os.path.join(SITE, "assets/js/data.js")

ERROR = {"#N/A", "#VALUE!", "#DIV/0!", "#REF!", "#NAME?", "#NULL!", "#NUM!", "nan", "None", ""}
YEAR_RE = re.compile(r"^(19|20)\d{2}$")
MON_RE = re.compile(r"^\d{1,2}月$")

def meaningful(s):
    if not isinstance(s, str):
        return False
    t = s.strip()
    return len(t) >= 4 and t not in ERROR and not YEAR_RE.match(t) and not MON_RE.match(t)

def is_dt(v):
    return isinstance(v, (datetime.datetime, datetime.date))

def as_date(v):
    return v.date() if isinstance(v, datetime.datetime) else v

_DATE_FMTS = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d",
              "%Y-%m", "%Y/%m", "%Y年%m月%d日", "%Y.%m.%d"]
def to_date(v):
    """日期或文本日期 -> date；失败返回 None"""
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    if isinstance(v, str):
        t = v.strip()
        if not t or t in ERROR:
            return None
        for fmt in _DATE_FMTS:
            try:
                return datetime.datetime.strptime(t, fmt).date()
            except ValueError:
                continue
    return None

def to_num(v):
    """数字或文本数字 -> float；失败返回 None"""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(v) else None
    if isinstance(v, str):
        t = v.strip().replace(",", "").replace("%", "")
        if not t or t in ERROR:
            return None
        try:
            f = float(t)
            return f if math.isfinite(f) else None
        except ValueError:
            return None
    return None

# ---------- 读取工作簿（xlsx 逐表流式 / xls xlrd） ----------
def iter_sheets(path):
    """逐个子表 yield (name, rows)，控制峰值内存"""
    if path.endswith(".xls"):
        wb = xlrd.open_workbook(path)
        for ws in wb.sheets():
            rows = []
            for r in range(ws.nrows):
                row = []
                for c in range(ws.ncols):
                    cell = ws.cell(r, c)
                    if cell.ctype == xlrd.XL_CELL_DATE:
                        try:
                            row.append(xlrd.xldate_as_datetime(cell.value, wb.datemode))
                        except Exception:
                            row.append(None)
                    elif cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_ERROR):
                        row.append(None)
                    else:
                        row.append(cell.value)
                rows.append(tuple(row))
            yield ws.name, rows
            del rows
    else:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for ws in wb.worksheets:
            ws.reset_dimensions()
            rows = list(ws.iter_rows(values_only=True))
            yield ws.title, rows
            del rows
        wb.close()

def get(rows, r, c):
    if 0 <= r < len(rows) and 0 <= c < len(rows[r]):
        return rows[r][c]
    return None

# ---------- 频率 / 季节性对齐（同 PTA） ----------
def detect_freq(series):
    ds = [d for d, _ in series]
    if len(ds) < 4:
        return "year"
    gaps = sorted((ds[i + 1] - ds[i]).days for i in range(len(ds) - 1))
    med = gaps[len(gaps) // 2]
    if med <= 4: return "day"
    if med <= 10: return "week"
    if med <= 45: return "month"
    return "year"

# 数据止于该日之前的图表视为「停更」，整条丢弃（用户 2026-11-20 要求）
CUTOFF = datetime.date(2025, 1, 1)

def build_chart(name, unit, series, src="原始数据", max_years=None):
    if not series:
        return None
    if max(d for d, _ in series) < CUTOFF:
        return None
    freq = detect_freq(series)
    full_n = len(series)
    full_range = f"{series[0][0]}~{series[-1][0]}"
    years_all = sorted({d.year for d, _ in series})
    years = [str(y) for y in (years_all if max_years is None else years_all[-max_years:])]
    yset = set(int(y) for y in years)
    pts = [(d, v) for d, v in series if d.year in yset]
    if freq == "year":
        return {"name": name, "unit": unit, "freq": "year", "src": src, "single": True,
                "labels": [str(d.year) for d, _ in series], "years": ["年度"],
                "series": {"年度": [round(v, 4) for _, v in series]},
                "note": f"{full_n} 个观测｜{name}｜区间 {full_range}"}
    if freq == "day":
        keys = [(m, dd) for m in range(1, 13) for dd in range(1, calendar.monthrange(2024, m)[1] + 1)]
        labels = [f"{m}月{dd}日" for m, dd in keys]
        idx = {k: i for i, k in enumerate(keys)}
        pos = lambda d: idx[(d.month, d.day)]
    elif freq == "week":
        keys = sorted({d.isocalendar()[1] for d, _ in pts})
        labels = [f"第{w}周" for w in keys]
        idx = {w: i for i, w in enumerate(keys)}
        pos = lambda d: idx[d.isocalendar()[1]]
    else:
        keys = sorted({d.month for d, _ in pts})
        labels = [f"{m}月" for m in keys]
        idx = {m: i for i, m in enumerate(keys)}
        pos = lambda d: idx[d.month]
    ser = {y: [None] * len(labels) for y in years}
    for d, v in pts:
        ser[str(d.year)][pos(d)] = round(v, 4)
    return {"name": name, "unit": unit, "freq": freq, "src": src,
            "labels": labels, "years": years, "series": ser,
            "note": f"{full_n} 个观测｜{name}｜区间 {full_range}"}

# ---------- 单位推断 ----------
def infer_unit(name):
    n = name
    if "美元/吨" in n or "美元/" in n: return "美元/吨"
    if "元/吨" in n: return "元/吨"
    if "元/千克" in n or "元/克" in n: return "元/克"
    if "万吨" in n: return "万吨"
    if "吨" in n and "万吨" not in n: return "吨"
    if any(k in n for k in ["开工率", "产能利用率", "利用率", "运行率", "同比", "环比", "占比", "库容率", "增长率", "增速", "率:", "率：", "相关度", "可能性"]): return "%"
    if "天" in n: return "天"
    if "张" in n: return "张"
    if "手" in n: return "手"
    if "美元" in n: return "美元"
    if "元" in n: return "元"
    return ""

# ---------- 单表提取 ----------
def extract_sheet(rows):
    """返回该子表的图表列表"""
    nrows = len(rows)
    if nrows < 6:
        return []
    # 真表头行：前25行中 meaningful 字符串最多者
    best, bestscore = -1, 0
    for ri in range(min(25, nrows)):
        score = sum(1 for c in rows[ri] if meaningful(c))
        if score > bestscore:
            bestscore, best = score, ri
    if best < 0 or bestscore < 2:
        return []
    hdr = best
    ncols = max(len(r) for r in rows[:min(nrows, hdr + 8)]) if nrows else 0
    # 日期锚点列：数据区(hdr+2..hdr+7)中 >=2 行为日期的列
    anchors = []
    for ci in range(ncols):
        cnt = sum(1 for ri in range(hdr + 2, min(hdr + 8, nrows)) if to_date(get(rows, ri, ci)) is not None)
        if cnt >= 2:
            anchors.append(ci)
    if not anchors:
        return []
    charts = []
    seen = set()
    for ci in range(ncols):
        # 列名：表头附近最有意义的长字符串
        cand = [get(rows, ri, ci) for ri in range(max(0, hdr - 1), min(hdr + 3, nrows))]
        names = [c.strip() for c in cand if meaningful(c)]
        if not names:
            continue
        name = max(names, key=len)
        # 跳过脚注/来源说明类伪指标
        if any(b in name for b in ["数据来源", "资料来源", "长江证券", "行业协会", "免责", "注：", "说明："]):
            continue
        # 跳过纯日期锚点列本身
        if ci in anchors:
            continue
        left = [a for a in anchors if a < ci]
        if not left:
            continue
        dcol = left[-1]
        # 读取序列
        pairs = {}
        for ri in range(hdr + 1, nrows):
            d = to_date(get(rows, ri, dcol)); v = to_num(get(rows, ri, ci))
            if d is not None and v is not None and d.year >= 1950:
                if d not in pairs:
                    pairs[d] = v
        series = sorted(pairs.items())
        if len(series) < 8:
            continue
        vals = [v for _, v in series]
        if max(vals) == min(vals):
            continue
        # 去重同名（同表内）
        key = name
        if key in seen:
            continue
        seen.add(key)
        ch = build_chart(name, infer_unit(name), series)
        if ch:
            charts.append(ch)
    return charts

# ---------- 品种配置 ----------
# (相对路径, id, 名称, 颜色)
COMMODITIES = [
    ("PTA数据库 .xlsx", "pta", "PTA产业链", "#e0a33e"),       # 用已 curated 的 PTA 数据
    ("甲醇数据库.xlsx", "methanol", "甲醇", "#3f9e8c"),
    ("尿素数据库.xlsx", "urea", "尿素", "#7396c8"),
    ("橡胶数据库.xlsx", "rubber", "橡胶", "#c08a1e"),
    ("沥青数据库.xlsx", "asphalt", "沥青", "#8b5cf6"),
    ("苯乙烯数据库.xlsx", "styrene", "苯乙烯", "#c4482c"),
    ("聚烯烃-2024.xlsx", "polyolefin", "聚烯烃", "#3f9e8c"),
    ("PVC-2024.xlsx", "pvc", "PVC", "#7396c8"),
    ("烧碱.xlsx", "caustic", "烧碱", "#c08a1e"),
    ("纯玻数据库.xlsx", "glass", "纯碱·玻璃", "#8b5cf6"),
    ("丙烯.xlsx", "propylene", "丙烯", "#c4482c"),
    ("原油.xlsx", "crude", "原油", "#a3aec2"),
    ("焦煤数据库.xlsx", "cokingcoal", "焦煤", "#7396c8"),
    ("碳酸锂.xls", "lithium", "碳酸锂", "#3f9e8c"),
    ("黄金.xlsx", "gold", "黄金·白银", "#c08a1e"),
    ("铂钯.xls", "pgm", "铂·钯", "#a3aec2"),
    ("2026/生猪数据库.xlsx", "hog", "生猪", "#c4482c"),
    ("2026/花生数据库.xlsx", "peanut", "花生", "#c08a1e"),
    ("2026/苹果数据库.xlsx", "apple", "苹果", "#c4482c"),
    ("化工基差.xls", "basis", "化工基差", "#7396c8"),
    ("商品市场总览.xlsx", "overview", "市场总览", "#8b5cf6"),
    ("宏观202512.xlsx", "macro", "宏观", "#3f9e8c"),
]

JUNK_SHEET = re.compile(r"^(贸易商|交割库|装置\s*|V风|氯碱|1215|涨跌|声明)$")
TODAY = datetime.date(2026, 11, 18)

def clean_sheet_title(sn):
    t = sn.strip()
    return "综合指标" if re.match(r"^Sheet\d*$", t) else t

def resolve(rel):
    """在 BASE 下解析文件路径，容忍文件名中的空格/大小写差异"""
    p = os.path.join(BASE, rel)
    if os.path.exists(p):
        return p
    stem = os.path.basename(rel).replace(" ", "").rpartition(".")[0].lower()
    d = os.path.dirname(p)
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.startswith("~$"):
                continue
            if f.replace(" ", "").rpartition(".")[0].lower() == stem:
                return os.path.join(d, f)
    return p

report = []
commodities = []
for rel, cid, cname, color in COMMODITIES:
    path = resolve(rel)
    if cid == "pta":
        # 复用 PTA 精细板块快照（由 extract.py 生成）
        snap = os.path.join(SITE, "pta_curated.json")
        if not os.path.exists(snap):
            raise SystemExit("缺少 pta_curated.json：请先运行 python3 extract.py")
        pta = json.load(open(snap, encoding="utf-8"))
        pta["id"] = "pta"
        commodities.append(pta)
        report.append((cname, len(pta["sheets"]), pta["chartCount"], pta["updated"]))
        continue
    if not os.path.exists(path):
        report.append((cname, "MISSING", 0, ""))
        continue
    try:
        sheet_iter = iter_sheets(path)
    except Exception as e:
        report.append((cname, f"ERR {str(e)[:50]}", 0, ""))
        continue
    sections = []
    total = 0
    maxdate = None
    idx = 0
    for sn, rows in sheet_iter:
        if JUNK_SHEET.match(sn.strip()):
            del rows
            continue
        try:
            charts = extract_sheet(rows)
        except Exception:
            charts = []
        del rows
        if not charts:
            continue
        idx += 1
        sid = f"s{idx:02d}"
        title = f"{idx:02d} {clean_sheet_title(sn)}"
        subtitle = "分年季节性叠图｜资料来源：IFIND、隆众资讯、卓创资讯等｜仅供研究参考，不构成投资建议"
        sections.append({"id": sid, "title": title, "subtitle": subtitle, "charts": charts})
        total += len(charts)
        for ch in charts:
            m = re.search(r"区间 \d{4}-\d{2}-\d{2}~(\d{4}-\d{2}-\d{2})", ch["note"])
            if m:
                d = datetime.date.fromisoformat(m.group(1))
                if maxdate is None or d > maxdate:
                    maxdate = d
    if not sections:
        report.append((cname, 0, 0, ""))
        continue
    db = {"id": cid, "name": cname, "color": color,
          "updated": str(min(maxdate, TODAY)) if maxdate else "",
          "sources": "IFIND、隆众资讯、卓创资讯、百川资讯等",
          "sheets": sections, "chartCount": total}
    commodities.append(db)
    report.append((cname, len(sections), total, str(maxdate)))

db = {"commodities": commodities}
with open(OUT, "w", encoding="utf-8") as f:
    f.write("window.DB = " + json.dumps(db, ensure_ascii=False, separators=(",", ":")) + ";")

print(f"{'品种':<12}{'板块':>6}{'图表':>6}  截至")
tc = ts = 0
for name, ns, nc, up in report:
    print(f"{name:<12}{str(ns):>6}{str(nc):>6}  {up}")
    if isinstance(nc, int):
        tc += nc; ts += ns if isinstance(ns, int) else 0
print(f"\nTOTAL: {len(commodities)} 品种, {ts} 板块, {tc} 图表 -> {os.path.getsize(OUT)} bytes")