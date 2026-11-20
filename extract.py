# -*- coding: utf-8 -*-
"""从 PTA数据库.xlsx 提取全部指标序列，生成静态站点数据 data.js"""
import os, glob, openpyxl, datetime, json, math, statistics
from openpyxl.utils import column_index_from_string

HERE = os.path.dirname(os.path.abspath(__file__))

def _find_src():
    """定位 PTA 工作簿：优先环境变量 PTA_XLSX，其次脚本同级的常见数据目录"""
    env = os.environ.get("PTA_XLSX")
    if env and os.path.exists(env):
        return env
    for d in [os.path.join(HERE, "数据库"),
              os.path.join(HERE, "..", "pta-update", "数据库"),
              os.path.join(HERE, "..", "数据库"),
              HERE]:
        if os.path.isdir(d):
            hits = [h for h in glob.glob(os.path.join(d, "*PTA数据库*.xlsx"))
                    if not os.path.basename(h).startswith("~$")]
            if hits:
                return sorted(hits)[0]
    raise SystemExit("未找到 PTA数据库.xlsx：请把数据目录放到站点根目录的 数据库/ 下，"
                     "或用环境变量 PTA_XLSX 指定文件路径")

SRC = _find_src()
OUT = os.path.join(HERE, "pta_curated.json")

wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
cache = {}
def sheet_rows(name):
    if name not in cache:
        ws = wb[name]; ws.reset_dimensions()
        cache[name] = list(ws.iter_rows(values_only=True))
    return cache[name]

def cell(rows, r, c):
    if r-1 < len(rows) and c-1 < len(rows[r-1]):
        return rows[r-1][c-1]
    return None

def extract(sheet, col, start, drop_zero=False):
    """返回 [(date, value)] 升序、去重"""
    rows = sheet_rows(sheet)
    ci = column_index_from_string(col)
    # 找日期列：该列左侧最近的、在 start 行是日期的列
    dcol = None
    for c in range(ci-1, 0, -1):
        if isinstance(cell(rows, start, c), datetime.datetime):
            dcol = c; break
    if dcol is None:
        raise RuntimeError(f"no date col for {sheet}!{col}")
    pairs = {}
    for r in range(start, len(rows)+1):
        dt = cell(rows, r, dcol); v = cell(rows, r, ci)
        if isinstance(dt, datetime.datetime) and isinstance(v, (int, float)) and not isinstance(v, bool):
            if math.isfinite(v) and not (drop_zero and v == 0):
                d = dt.date()
                if d not in pairs:
                    pairs[d] = float(v)
    return sorted(pairs.items())

def stats(series):
    vs = [v for _, v in series]
    if not vs: return "empty"
    return f"n={len(vs)} min={min(vs):.2f} med={statistics.median(vs):.2f} max={max(vs):.2f} last={vs[-1]:.2f}"

# ---------- 指标配置 ----------
# (key, sheet, col, start_row, name, unit, src)
RAW = [
 # 调油
 ("gas95","调油","B",20,"新加坡汽油95# FOB价","美元/桶","原始数据"),
 ("gas92","调油","C",20,"新加坡汽油92# FOB价","美元/桶","原始数据"),
 ("brent","调油","D",20,"布伦特原油期货收盘价(连一)","美元/桶","原始数据"),
 ("gas9592","调油","E",20,"汽油95#-92#价差","美元/桶","推算数据"),
 ("gas92brent","调油","F",20,"汽油92#-布伦特价差","美元/桶","推算数据"),
 ("dubai","调油","P",21,"迪拜原油现货价","美元/桶","原始数据"),
 ("naphtha_sg","调油","Q",21,"石脑油新加坡FOB价","美元/桶","原始数据"),
 ("us_gas_inv","调油","T",21,"美国车用汽油库存(周度)","亿桶","原始数据"),
 ("naphtha_jp","调油","AD",21,"石脑油日本CFR中间价","美元/吨","原始数据"),
 ("propane_jp","调油","AE",21,"丙烷(冷冻货)日本CFR价","美元/吨","原始数据"),
 ("us_gas93","调油","AH",21,"美国海湾优质汽油93现货价","美元/桶","原始数据"),
 ("us_gas87","调油","AI",21,"美国海湾普通汽油87现货价","美元/桶","原始数据"),
 ("px_kr","调油","AT",23,"PX韩国FOB中间价","美元/吨","原始数据"),
 ("mx_kr","调油","AU",23,"异构二甲苯(MX)韩国FOB价","美元/吨","原始数据"),
 ("bz_kr","调油","AV",23,"纯苯韩国FOB中间价","美元/吨","原始数据"),
 ("naphtha_kr","调油","AW",23,"石脑油韩国CFR价","美元/吨","原始数据"),
 ("px_nap","调油","AX",23,"PX-石脑油价差","美元/吨","推算数据"),
 ("mx_nap","调油","AY",23,"MX-石脑油价差","美元/吨","推算数据"),
 ("bz_nap","调油","AZ",23,"纯苯-石脑油价差","美元/吨","推算数据"),
 # PX
 ("px_spot","PX","B",20,"PX现货价(华东)","元/吨","原始数据"),
 ("px_cfr","PX","C",20,"PX中国台湾到岸中间价","美元/吨","原始数据"),
 ("usdcny","PX","D",20,"美元兑人民币中间价","","原始数据"),
 ("px_fut","PX","E",20,"PX期货收盘价(活跃合约)","元/吨","原始数据"),
 ("px_basis","PX","F",20,"PX基差(现货-期货)","元/吨","推算数据"),
 ("px_m01","PX","P",22,"PX期货01月合约收盘价","元/吨","原始数据"),
 ("px_m05","PX","Q",22,"PX期货05月合约收盘价","元/吨","原始数据"),
 ("px_m09","PX","R",22,"PX期货09月合约收盘价","元/吨","原始数据"),
 ("px_op_chain","PX","W",20,"PX开工率(聚酯产业链口径)","%","原始数据"),
 ("pta_op","PX","X",20,"PTA开工率(全国)","%","原始数据"),
 ("pet_op_chain","PX","Y",20,"聚酯产品开工率(产业链口径)","%","原始数据"),
 ("weave_op_chain","PX","Z",20,"织造业开工率(产业链口径)","%","原始数据"),
 ("bottle_op_chain","PX","AA",20,"聚酯瓶片产能利用率(产业链口径)","%","原始数据"),
 ("eg_op_chain","PX","AB",20,"乙二醇开工率(综合·产业链口径)","%","原始数据"),
 ("eg_op_oil","PX","AC",20,"乙二醇开工率(石油制)","%","原始数据"),
 ("eg_op_coal","PX","AD",20,"乙二醇开工率(煤制)","%","原始数据"),
 ("eg_op_meoh","PX","AE",20,"乙二醇开工率(甲醇制)","%","原始数据"),
 ("px_op_asia","PX","AG",20,"PX开工率:亚洲","%","原始数据"),
 ("px_op_kr","PX","AH",20,"PX开工率:韩国","%","原始数据"),
 ("px_op_jp","PX","AI",20,"PX开工率:日本","%","原始数据"),
 ("px_op_tw","PX","AJ",20,"PX开工率:中国台湾","%","原始数据"),
 ("px_op_in","PX","AK",20,"PX开工率:印度","%","原始数据"),
 ("px_op","PX","AM",20,"PX开工率(周度)","%","原始数据"),
 ("px_arrival","PX","AN",20,"PX到港量:江阴(周度)","万吨","原始数据"),
 ("px_wprod","PX","AO",20,"PX周产量:中国","万吨","原始数据"),
 ("px_apparent","PX","AY",20,"PX表观消费量(月度)","万吨","原始数据"),
 ("px_netimp_cum","PX","BI",20,"PX净进口量(年内累计)","万吨","原始数据"),
 ("px_cost","PX","BL",20,"PX日度成本:中国","美元/吨","原始数据"),
 ("px_profit","PX","BM",20,"PX日度利润:中国","美元/吨","原始数据"),
 ("px_inv","PX","BW",20,"PX库存(期末值)","万吨","原始数据"),
 # PTA
 ("pta_spot","PTA","B",20,"PTA现货基准价:华东","元/吨","原始数据"),
 ("pta_fut","PTA","C",20,"PTA期货收盘价(活跃合约)","元/吨","原始数据"),
 ("pta_wr","PTA","D",20,"PTA仓单数量:总计","张","原始数据"),
 ("pta_basis","PTA","E",20,"PTA基差(现货-期货)","元/吨","推算数据"),
 ("pta_m01","PTA","O",21,"PTA期货01月合约收盘价","元/吨","原始数据"),
 ("pta_m05","PTA","P",21,"PTA期货05月合约收盘价","元/吨","原始数据"),
 ("pta_m09","PTA","Q",21,"PTA期货09月合约收盘价","元/吨","原始数据"),
 ("pta_15","PTA","R",21,"PTA月差 1-5","元/吨","推算数据"),
 ("pta_59","PTA","S",21,"PTA月差 5-9","元/吨","推算数据"),
 ("pta_91","PTA","T",21,"PTA月差 9-1","元/吨","推算数据"),
 ("pta_inv","PTA","V",20,"PTA社会库存(期末值)","万吨","原始数据"),
 ("pta_wprod","PTA","W",20,"PTA周产量","万吨","原始数据"),
 ("pta_loss","PTA","X",20,"PTA检修损失量(周度)","万吨","原始数据"),
 ("pta_demand","PTA","Y",20,"PTA总需求量(周度)","万吨","原始数据"),
 ("pta_pet_demand","PTA","Z",20,"PTA聚酯需求量(周度)","万吨","原始数据"),
 ("pta_other_demand","PTA","AA",20,"PTA其他需求量(周度)","万吨","原始数据"),
 ("pta_profit","PTA","AK",21,"PTA日度利润:中国","元/吨","原始数据"),
 ("pta_cost","PTA","AL",21,"PTA日度成本:中国","元/吨","原始数据"),
 # 乙二醇
 ("eg_spot","乙二醇","B",20,"乙二醇现货价:华东主流价","元/吨","原始数据"),
 ("eg_fut","乙二醇","C",20,"乙二醇期货收盘价(活跃合约)","元/吨","原始数据"),
 ("eg_wr","乙二醇","D",20,"乙二醇仓单数量:总计","张","原始数据"),
 ("eg_m01","乙二醇","O",22,"乙二醇期货01月合约收盘价","元/吨","原始数据"),
 ("eg_m05","乙二醇","P",22,"乙二醇期货05月合约收盘价","元/吨","原始数据"),
 ("eg_m09","乙二醇","Q",22,"乙二醇期货09月合约收盘价","元/吨","原始数据"),
 ("eg_15","乙二醇","R",22,"乙二醇月差 1-5","元/吨","推算数据"),
 ("eg_59","乙二醇","S",22,"乙二醇月差 5-9","元/吨","推算数据"),
 ("eg_91","乙二醇","T",22,"乙二醇月差 9-1","元/吨","推算数据"),
 ("eg_export","乙二醇","V",20,"乙二醇出口量(月度)","万吨","原始数据"),
 ("eg_import","乙二醇","W",20,"乙二醇进口量(月度)","万吨","原始数据"),
 ("eg_mprod","乙二醇","X",20,"乙二醇产量(月度)","万吨","原始数据"),
 ("eg_apparent","乙二醇","AD",20,"乙二醇表观消费量(产量+净进口)","万吨","推算数据"),
 ("eg_profit_coal","乙二醇","AF",21,"乙二醇日度利润:煤制","元/吨","原始数据"),
 ("eg_profit_ethylene","乙二醇","AG",21,"乙二醇日度利润:乙烯制","元/吨","原始数据"),
 ("eg_profit_meoh","乙二醇","AH",21,"乙二醇日度利润:甲醇制","元/吨","原始数据"),
 ("eg_profit_naphtha","乙二醇","AI",21,"乙二醇日度利润:石脑油制","美元/吨","原始数据"),
 ("eg_inv","乙二醇","AK",21,"乙二醇库存:华东主港","万吨","原始数据"),
 ("eg_op","乙二醇","AM",21,"乙二醇开工率(周度)","%","原始数据"),
 ("eg_op_ethylene","乙二醇","AN",21,"乙二醇开工率:乙烯法","%","原始数据"),
 ("eg_op_nonethylene","乙二醇","AO",21,"乙二醇开工率:非乙烯法","%","原始数据"),
 ("eg_wprod","乙二醇","AP",21,"乙二醇周产量:中国","万吨","原始数据"),
 ("eg_loss","乙二醇","AQ",21,"乙二醇检修损失量(周度)","万吨","原始数据"),
 # 聚酯
 ("poy_inv","聚酯","B",20,"涤纶长丝POY工厂库存天数","天","原始数据"),
 ("fdy_inv","聚酯","C",20,"涤纶长丝FDY工厂库存天数","天","原始数据"),
 ("dty_inv","聚酯","D",20,"涤纶长丝DTY工厂库存天数","天","原始数据"),
 ("sf_inv","聚酯","E",20,"涤纶短纤权益库存","天","原始数据"),
 ("bottle_inv","聚酯","F",20,"聚酯瓶片库存可用天数","天","原始数据"),
 ("chip_inv","聚酯","G",20,"聚酯切片企业库存(期末值)","万吨","原始数据"),
 ("poy_profit","聚酯","I",20,"涤纶长丝POY周度利润","元/吨","原始数据"),
 ("dty_profit","聚酯","J",20,"涤纶长丝DTY周度利润","元/吨","原始数据"),
 ("fdy_profit","聚酯","K",20,"涤纶长丝FDY周度利润","元/吨","原始数据"),
 ("sf_profit","聚酯","L",20,"涤纶短纤周度利润","元/吨","原始数据"),
 ("bottle_profit","聚酯","M",20,"聚酯瓶片周度利润","元/吨","原始数据"),
 ("chip_profit","聚酯","N",20,"聚酯切片周度利润","元/吨","原始数据"),
 ("fil_op","聚酯","P",19,"涤纶长丝开工率","%","原始数据"),
 ("sf_op","聚酯","Q",19,"涤纶短纤开工率","%","原始数据"),
 ("bottle_op","聚酯","R",19,"聚酯瓶片产能利用率","%","原始数据"),
 ("chip_op","聚酯","S",19,"聚酯切片开工率","%","原始数据"),
 ("pet_op","聚酯","T",19,"聚酯产能利用率","%","原始数据"),
 ("fil_wprod","聚酯","V",19,"涤纶长丝周产量","万吨","原始数据"),
 ("sf_wprod","聚酯","W",19,"涤纶短纤周产量","万吨","原始数据"),
 ("bottle_wprod","聚酯","X",19,"聚酯瓶片周产量","万吨","原始数据"),
 ("chip_wprod","聚酯","Y",19,"聚酯切片周产量","万吨","原始数据"),
 ("pet_wprod","聚酯","Z",19,"聚酯行业周产量","万吨","原始数据"),
 ("loom_op","聚酯","AC",19,"江浙织机开工率","%","原始数据"),
 ("weave_raw_inv","聚酯","AM",19,"终端织造原料库存(期末值)","天","原始数据"),
 ("grey_inv","聚酯","AN",19,"终端织造坯布库存天数","天","原始数据"),
 ("retail_cum","聚酯","AP",19,"服装鞋帽针纺织品零售额(年内累计)","亿元","原始数据"),
 ("retail_yoy","聚酯","AQ",19,"服装鞋帽针纺织品零售额累计同比","%","原始数据"),
 ("apparel_exp_cum","聚酯","AR",19,"服装及衣着附件出口额(年内累计)","亿美元","原始数据"),
 ("apparel_exp_yoy","聚酯","AS",19,"服装及衣着附件出口额累计同比","%","原始数据"),
]

DROP_ZERO = {"px_m01", "px_m05", "px_m09"}  # 未上市交易日价格为0，剔除
data = {}
print("=== RAW STATS ===")
for key, sheet, col, start, name, unit, src in RAW:
    s = extract(sheet, col, start, drop_zero=(key in DROP_ZERO))
    data[key] = {"name": name, "unit": unit, "src": src, "series": s}
    print(f"{key:20s} {stats(s)}  {s[0][0] if s else ''} ~ {s[-1][0] if s else ''}")

# 产能（年度，合并两个块，取更长历史）
cap = {}
for key, colA, colF, name in [("cap_px","B","G","PX(对二甲苯)产能"),
                               ("cap_pta","C","H","PTA有效年产能"),
                               ("cap_pet","D","I","聚酯有效产能")]:
    sa = dict(extract("产能", colA, 19))
    sf = dict(extract("产能", colF, 19))
    merged = {**sa, **sf}
    s = sorted(merged.items())
    cap[key] = {"name": name, "unit": "万吨", "src": "原始数据", "series": s}
    print(f"{key:20s} {stats(s)}")
data.update(cap)

# ---------- 推算序列 ----------
def derive(key, name, unit, fn, deps):
    ds = [dict(data[d]["series"]) for d in deps]
    common = set(ds[0])
    for d in ds[1:]: common &= set(d)
    s = sorted((d, fn(*[dd[d] for dd in ds])) for d in common)
    data[key] = {"name": name, "unit": unit, "src": "推算数据", "series": s}
    print(f"{key:20s} {stats(s)}")

derive("eg_basis","乙二醇基差(现货-期货)","元/吨", lambda a,b: a-b, ["eg_spot","eg_fut"])
# PX 月差由清洗后的合约价格重算（原始列含未上市0值干扰）
derive("px_15","PX月差 1-5","元/吨", lambda a,b: a-b, ["px_m01","px_m05"])
derive("px_59","PX月差 5-9","元/吨", lambda a,b: a-b, ["px_m05","px_m09"])
derive("px_91","PX月差 9-1","元/吨", lambda a,b: a-b, ["px_m09","px_m01"])

def monthly_from_cum(series):
    """年内累计 -> 当月值（1月=累计值，其余=差分）"""
    out = []
    prev = None; prev_year = None
    for d, v in sorted(series):
        if prev_year == d.year and prev is not None:
            out.append((d, v - prev))
        else:
            out.append((d, v))
        prev = v; prev_year = d.year
    return out

for key, name, unit in [("px_netimp","PX净进口量(当月)","万吨"),
                         ("retail_m","服装鞋帽针纺织品零售额(月度·1-2月合并)","亿元"),
                         ("apparel_exp_m","服装及衣着附件出口额(月度·1-2月合并)","亿美元")]:
    src_key = {"px_netimp":"px_netimp_cum","retail_m":"retail_cum","apparel_exp_m":"apparel_exp_cum"}[key]
    s = monthly_from_cum(data[src_key]["series"])
    data[key] = {"name": name, "unit": unit, "src": "推算数据", "series": s}
    print(f"{key:20s} {stats(s)}")

# 产能同比
for key, base, name in [("cap_px_yoy","cap_px","PX产能同比"),
                         ("cap_pta_yoy","cap_pta","PTA产能同比"),
                         ("cap_pet_yoy","cap_pet","聚酯产能同比")]:
    s = data[base]["series"]; out = []
    for i in range(1, len(s)):
        d0, v0 = s[i-1]; d1, v1 = s[i]
        if d1.year - d0.year == 1 and v0:
            out.append((d1, (v1/v0-1)*100))
    data[key] = {"name": name, "unit": "%", "src": "推算数据", "series": out}
    print(f"{key:20s} {stats(out)}")

wb.close()

# ---------- 频率判定 ----------
def detect_freq(series):
    ds = [d for d, _ in series]
    if len(ds) < 4: return "year"
    gaps = sorted((ds[i+1]-ds[i]).days for i in range(len(ds)-1))
    med = gaps[len(gaps)//2]
    if med <= 4: return "day"
    if med <= 10: return "week"
    if med <= 45: return "month"
    return "year"

# ---------- 季节性对齐 ----------
# 数据止于该日之前的图表视为「停更」，整条丢弃（用户 2026-11-20 要求）
CUTOFF = datetime.date(2025, 1, 1)

def build_chart(key, max_years=None):
    d = data[key]
    series = d["series"]
    if not series: return None
    if max(dt for dt, _ in series) < CUTOFF: return None
    freq = detect_freq(series)
    full_n = len(series)
    full_range = f"{series[0][0]}~{series[-1][0]}"
    years_all = sorted({dt.year for dt, _ in series})
    years = [str(y) for y in (years_all if max_years is None else years_all[-max_years:])]
    yset = set(int(y) for y in years)
    pts = [(dt, v) for dt, v in series if dt.year in yset]

    if freq == "year":
        # 年度图展示全部历史
        labels = [str(dt.year) for dt, _ in series]
        return {"name": d["name"], "unit": d["unit"], "freq": "year", "src": d["src"],
                "single": True, "labels": labels, "years": ["年度"],
                "series": {"年度": [round(v, 4) for _, v in series]},
                "note": f"{full_n} 个观测｜{d['name']}｜区间 {full_range}"}

    if freq == "day":
        # 与参考站一致：全年固定日历网格（含2月29日），各年按日历日对齐
        import calendar
        keys = [(m, dd) for m in range(1, 13) for dd in range(1, calendar.monthrange(2024, m)[1] + 1)]
        labels = [f"{m}月{dd}日" for m, dd in keys]
        idx = {k: i for i, k in enumerate(keys)}
        def pos(dt): return idx[(dt.month, dt.day)]
    elif freq == "week":
        keys = sorted({dt.isocalendar()[1] for dt, _ in pts})
        labels = [f"第{w}周" for w in keys]
        idx = {w: i for i, w in enumerate(keys)}
        def pos(dt): return idx[dt.isocalendar()[1]]
    else:
        keys = sorted({dt.month for dt, _ in pts})
        labels = [f"{m}月" for m in keys]
        idx = {m: i for i, m in enumerate(keys)}
        def pos(dt): return idx[dt.month]

    ser = {y: [None]*len(labels) for y in years}
    for dt, v in pts:
        ser[str(dt.year)][pos(dt)] = round(v, 4)
    return {"name": d["name"], "unit": d["unit"], "freq": freq, "src": d["src"],
            "labels": labels, "years": years, "series": ser,
            "note": f"{full_n} 个观测｜{d['name']}｜区间 {full_range}"}

# ---------- 板块定义 ----------
SECTIONS = [
 ("s01","01 产能·产业链","PX、PTA 与聚酯年度产能及增速，2004–2025｜资料来源：IFIND、公开资料整理",
  ["cap_px","cap_pta","cap_pet","cap_px_yoy","cap_pta_yoy","cap_pet_yoy"]),
 ("s02","02 油端·原油与石脑油","原油、石脑油、丙烷等油端成本价格，日度分年叠图｜资料来源：IFIND",
  ["dubai","brent","naphtha_sg","naphtha_jp","naphtha_kr","propane_jp"]),
 ("s03","03 调油·汽油与价差","新加坡汽油、美国汽油与调油价差、美国汽油库存，分年叠图｜资料来源：IFIND",
  ["gas95","gas92","gas9592","gas92brent","us_gas93","us_gas87","us_gas_inv"]),
 ("s04","04 芳烃·PX/MX/纯苯","韩国芳烃现货价格与对石脑油价差，日度分年叠图｜资料来源：IFIND",
  ["px_kr","mx_kr","bz_kr","px_nap","mx_nap","bz_nap"]),
 ("s05","05 PX·价格与基差","PX 现货、期货与基差、汇率，日度分年叠图｜资料来源：IFIND",
  ["px_spot","px_cfr","px_fut","px_basis","usdcny"]),
 ("s06","06 PX·月差与合约","PX 期货 01/05/09 合约收盘价与月差，日度分年叠图｜资料来源：IFIND",
  ["px_m01","px_m05","px_m09","px_15","px_59","px_91"]),
 ("s07","07 PX·开工与产量","PX 中国与亚洲主要地区开工率、周产量、到港量，周度分年叠图｜资料来源：IFIND、隆众资讯",
  ["px_op","px_op_asia","px_op_kr","px_op_jp","px_op_tw","px_op_in","px_wprod","px_arrival"]),
 ("s08","08 PX·进口库存与利润","PX 表观消费量、净进口、库存、成本与利润｜资料来源：IFIND、隆众资讯",
  ["px_apparent","px_netimp_cum","px_netimp","px_inv","px_cost","px_profit"]),
 ("s09","09 PTA·价格与基差","PTA 现货、期货、基差与仓单，日度分年叠图｜资料来源：IFIND、卓创资讯",
  ["pta_spot","pta_fut","pta_basis","pta_wr"]),
 ("s10","10 PTA·月差与合约","PTA 期货 01/05/09 合约收盘价与月差，日度分年叠图｜资料来源：IFIND",
  ["pta_m01","pta_m05","pta_m09","pta_15","pta_59","pta_91"]),
 ("s11","11 PTA·供需与库存","PTA 开工率、周产量、检修损失、社会库存与需求，分年叠图｜资料来源：IFIND、隆众资讯",
  ["pta_op","pta_wprod","pta_loss","pta_inv","pta_demand","pta_pet_demand","pta_other_demand"]),
 ("s12","12 PTA·成本与利润","PTA 日度成本与利润，日度分年叠图｜资料来源：IFIND、隆众资讯",
  ["pta_cost","pta_profit"]),
 ("s13","13 乙二醇·价格与基差","乙二醇现货、期货、基差与仓单，日度分年叠图｜资料来源：IFIND",
  ["eg_spot","eg_fut","eg_basis","eg_wr"]),
 ("s14","14 乙二醇·月差与合约","乙二醇期货 01/05/09 合约收盘价与月差，日度分年叠图｜资料来源：IFIND",
  ["eg_m01","eg_m05","eg_m09","eg_15","eg_59","eg_91"]),
 ("s15","15 乙二醇·供需与进出口","乙二醇月度产量、进出口、表观消费量、周产量、检修损失与主港库存，月度/周度分年叠图｜资料来源：IFIND、隆众资讯",
  ["eg_mprod","eg_import","eg_export","eg_apparent","eg_wprod","eg_loss","eg_inv"]),
 ("s16","16 乙二醇·开工率","乙二醇综合与分工艺开工率，周度分年叠图｜资料来源：IFIND、隆众资讯",
  ["eg_op","eg_op_ethylene","eg_op_nonethylene"]),
 ("s17","17 乙二醇·工艺利润","乙二醇煤制、乙烯制、甲醇制、石脑油制日度利润｜资料来源：IFIND、隆众资讯",
  ["eg_profit_coal","eg_profit_ethylene","eg_profit_meoh","eg_profit_naphtha"]),
 ("s18","18 聚酯·库存天数","涤纶长丝、短纤、瓶片、切片工厂库存天数，周度分年叠图｜资料来源：IFIND、隆众资讯",
  ["poy_inv","fdy_inv","dty_inv","sf_inv","bottle_inv","chip_inv"]),
 ("s19","19 聚酯·周度利润","涤纶长丝、短纤、瓶片、切片周度利润，周度分年叠图｜资料来源：IFIND、隆众资讯",
  ["poy_profit","fdy_profit","dty_profit","sf_profit","bottle_profit","chip_profit"]),
 ("s20","20 聚酯·开工与产量","聚酯各产品开工率与周产量，周度分年叠图｜资料来源：IFIND、隆众资讯",
  ["pet_op","fil_op","sf_op","bottle_op","chip_op","pet_wprod","fil_wprod","sf_wprod","bottle_wprod","chip_wprod"]),
 ("s21","21 织造·终端需求","江浙织机开工率、织造库存、服装零售与出口，周度/月度分年叠图｜资料来源：IFIND、隆众资讯",
  ["loom_op","weave_raw_inv","grey_inv","retail_cum","retail_m","retail_yoy","apparel_exp_cum","apparel_exp_m","apparel_exp_yoy"]),
 ("s22","22 产业链开工率对比","聚酯产业链各环节开工率（产业链口径），分年叠图｜资料来源：隆众资讯",
  ["px_op_chain","pta_op","pet_op_chain","bottle_op_chain","eg_op_chain","eg_op_oil","eg_op_coal","eg_op_meoh","weave_op_chain"]),
]

sheets = []
total_charts = 0
# 数据截至：全部非年度序列的最新日期
updated = max(data[k]["series"][-1][0] for k in data
              if data[k]["series"] and detect_freq(data[k]["series"]) != "year")
# 若 PTA 合约数据明显滞后，在板块说明中注明
pta_m_end = data["pta_m01"]["series"][-1][0]
stale_note = f"（合约数据更新至 {pta_m_end}）" if (updated - pta_m_end).days > 60 else ""
for sid, title, subtitle, keys in SECTIONS:
    if sid == "s10" and stale_note:
        subtitle = subtitle.replace("，日度分年叠图", stale_note + "，日度分年叠图")
    charts = []
    for k in keys:
        c = build_chart(k)
        if c: charts.append(c)
    if not charts:            # 板块内图表全部停更 → 整个板块不输出
        continue
    total_charts += len(charts)
    sheets.append({"id": sid, "title": title, "subtitle": subtitle + "｜仅供研究参考，不构成投资建议", "charts": charts})

db = {
  "name": "PTA产业链",
  "color": "#e0a33e",
  "updated": str(updated),
  "sources": "IFIND、隆众资讯、卓创资讯、百川资讯等",
  "sheets": sheets,
  "chartCount": total_charts,
}
import os
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, separators=(",", ":"))
print(f"\nDONE: {total_charts} charts, {len(sheets)} sections -> {OUT} ({os.path.getsize(OUT)} bytes)")