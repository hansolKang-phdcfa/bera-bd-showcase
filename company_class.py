# coding: utf-8
"""
[showcase 독립] 회사 카테고리·시가총액 tier 분류 + 색상 — 모든 회사 그래프 공통 색 코드.

한인수 8/4 피드백:
  · 관심모멘텀·경쟁서열 등 그래프에서 회사를 색상으로 분류(빅파마/바이오텍/스타트업/학계)해
    한눈에 파악되게 (req: 색상 분류).
  · cross-modality: 총합 순 아닌 **시가총액 tier(메가/라지/미들/스몰캡)** 로 분류. 스몰캡↓=협업↓.
  · KR 3-tier: LG화학·한미가 특허 많은 건 회사가 커서지 도메인 강해서가 아님 → 규모(cap tier) 함께.

★엔진 무관·공개정보(회사 카테고리/상장/규모는 public). 스코어링 moat 아님.
★규모 tier·상장상태는 근사(공개상식 기준) — 정밀 시가총액 아님. 인수/상장상태는 변동하므로
  거래처 송부 전 최신 확인 전제.
"""
import re

# ── 카테고리 색 (그래프 공통 범례) ──────────────────────────────
# 브랜드 4색 원칙이나 데이터 그래프는 카테고리 구분색 허용(viz PAL과 동일 취지).
CAT = {
    "big_pharma":  {"color": "#3E83FF", "ko": "빅파마",        "order": 0},
    "biotech":     {"color": "#00A3B4", "ko": "상장 바이오텍",  "order": 1},  # NASDAQ/KOSDAQ 중·소형
    "startup":     {"color": "#F5A623", "ko": "스타트업/비상장", "order": 2},
    "academic":    {"color": "#A5A5A5", "ko": "학계/TTO",       "order": 3},
    "acquired":    {"color": "#8C8C8C", "ko": "인수됨",         "order": 4},
    "non_pharma":  {"color": "#E8544B", "ko": "비제약(오탐)",    "order": 5},
    "unknown":     {"color": "#C3CAD3", "ko": "미확인",         "order": 6},
}

# ── 시가총액 tier 색 (cross-modality용, 블루 계열 농담) ──────────
CAP_TIER = {
    "mega":  {"color": "#0C216A", "ko": "메가캡",  "rank": 5},  # 초대형(≈$100B+)
    "large": {"color": "#3E83FF", "ko": "라지캡",  "rank": 4},  # 대형(≈$10-100B)
    "mid":   {"color": "#00A3B4", "ko": "미들캡",  "rank": 3},  # 중형(≈$1-10B)
    "small": {"color": "#F5A623", "ko": "스몰캡",  "rank": 2},  # 소형(≈$0.1-1B)
    "micro": {"color": "#E8544B", "ko": "마이크로캡", "rank": 1},  # 초소형(<$0.1B)·협업↓
    "unknown": {"color": "#C3CAD3", "ko": "규모미확인", "rank": 0},
}

# ── KB: 이름(소문자 키워드) → (category, cap_tier) ─────────────
# 글로벌 빅파마 (cap_tier: mega=초대형, large=대형).
_BIG_PHARMA = {
    "j&j": "mega", "johnson": "mega", "janssen": "mega", "roche": "mega", "genentech": "mega",
    "chugai": "large", "pfizer": "mega", "merck": "mega", "msd": "mega", "novartis": "mega",
    "abbvie": "mega", "abb vie": "mega", "bristol": "mega", "bms": "mega", "celgene": "large",
    "astrazeneca": "mega", "medimmune": "large", "sanofi": "mega", "genzyme": "large",
    "amgen": "mega", "eli lilly": "mega", "glaxo": "mega", "gsk": "mega", "smithkline": "large",
    "takeda": "large", "gilead": "large", "boehringer": "large", "eisai": "mid",
    "astellas": "large", "daiichi": "large", "bayer": "large", "otsuka": "large",
    "sumitomo": "mid", "biogen": "large", "vertex": "large", "incyte": "mid",
    "servier": "large", "ucb": "mid", "lundbeck": "mid", "modernatx": "large", "moderna": "large",
    "ono ": "mid", "regeneron": "large",
}
# 한국 제약/바이오 (cap_tier). ★LG화학=화학 대기업(특허 많음=규모 탓, 도메인 강함 아님).
_KR_PHARMA = {
    "lg chem": ("big_pharma", "large"), "lg화학": ("big_pharma", "large"),
    "samsung": ("big_pharma", "mega"), "celltrion": ("big_pharma", "large"), "셀트리온": ("big_pharma", "large"),
    "yuhan": ("big_pharma", "large"), "유한": ("big_pharma", "large"),
    "hanmi": ("big_pharma", "mid"), "한미": ("big_pharma", "mid"),
    "daewoong": ("big_pharma", "mid"), "대웅": ("big_pharma", "mid"),
    "chong kun dang": ("big_pharma", "mid"), "종근당": ("big_pharma", "mid"),
    "green cross": ("big_pharma", "mid"), "녹십자": ("big_pharma", "mid"),
    "sk chemical": ("big_pharma", "mid"), "sk bio": ("big_pharma", "large"), "boryung": ("big_pharma", "mid"),
    "dong-a": ("big_pharma", "mid"), "dong a": ("big_pharma", "mid"), "동아": ("big_pharma", "mid"),
    "ildong": ("big_pharma", "small"), "chong": ("big_pharma", "mid"),
    "hk inno": ("big_pharma", "mid"), "jw ": ("big_pharma", "small"),
    # 집중형 소·중형 바이오텍(규모 대비 도메인 집약 = 진짜 신호)
    "voronoi": ("biotech", "small"), "oscotec": ("biotech", "small"), "오스코텍": ("biotech", "small"),
    "abl bio": ("biotech", "small"), "alteogen": ("biotech", "mid"), "알테오젠": ("biotech", "mid"),
    "pinotbio": ("startup", "small"), "genexine": ("biotech", "small"), "medpacto": ("startup", "small"),
    "toolgen": ("biotech", "small"), "올릭스": ("startup", "small"), "olix": ("startup", "small"),
}
# 글로벌 바이오텍 (category, cap_tier). 상장 중·소형=biotech / 비상장·전임상=startup.
_BIOTECH = {
    "immatics": ("biotech", "mid"), "xencor": ("biotech", "mid"), "biohaven": ("biotech", "mid"),
    "fate": ("biotech", "mid"), "krystal": ("biotech", "mid"), "arcus": ("biotech", "mid"),
    "cue biopharma": ("startup", "micro"), "oncosec": ("startup", "micro"),
    "immunesensor": ("startup", "small"), "actym": ("startup", "small"), "stingray": ("startup", "small"),
    "stinginn": ("startup", "small"), "precision biologics": ("startup", "small"),
    "gensun": ("startup", "small"), "nammi": ("startup", "small"), "aduro": ("biotech", "small"),
    "chinook": ("biotech", "mid"), "galapagos": ("biotech", "mid"), "chemocentryx": ("biotech", "mid"),
    "landos": ("startup", "small"), "aldeyra": ("startup", "small"), "genfit": ("biotech", "small"),
    "cyteir": ("startup", "small"), "biotheryx": ("startup", "small"), "avotres": ("startup", "small"),
    "philogen": ("biotech", "small"), "mymd": ("startup", "micro"), "receptos": ("biotech", "mid"),
}
# 이미 인수됨(독립 파트너 아님) → 인수사.
_ACQUIRED = {
    "immunomedics": "Gilead(2020)", "altor": "NantCell(2017)", "receptos": "Celgene(2015)",
    "pharmacyclics": "AbbVie(2015)", "achillion": "Alexion(2019)", "arena": "Pfizer(2022)",
    "chemocentryx": "Amgen(2022)", "ganymed": "Astellas(2016)", "chinook": "Novartis(2023)",
    "aduro": "Chinook(2020)", "landos": "AbbVie(2024)", "magenta": "Dianthus(2023)",
    "pharmacyclic": "AbbVie(2015)", "receptos ": "Celgene(2015)", "kala": "피인수/전환",
    "first wave": "청산/축소", "chinook therapeutics": "Novartis(2023)",
}
# 비제약(오탐).
_NON_PHARMA = {
    "leidos": "방산/IT(정부 R&D)", "cleerly": "심장 CT AI", "providence health": "병원",
    "city of hope": "암병원/연구소",
}
# 학계/TTO 패턴.
_ACADEMIC = re.compile(
    r"univ|institut|hospital|academ|college|research (center|and development|foundation)|"
    r"vzw|vib|yeda|helmholtz|zentrum|national (inst|lab)|foundation|of health|"
    r"대학|연구원|연구소|병원|재단", re.I)


def classify(name):
    """회사명 → {category, cap_tier, color, cat_ko, cap_ko, note}. 우선순위:
    학계 → 비제약 → 인수됨 → 빅파마(글로벌/KR) → 바이오텍(글로벌/KR) → 미확인."""
    nl = (name or "").strip().lower()
    if not nl:
        return _mk("unknown", "unknown", "")
    if _ACADEMIC.search(name or ""):
        return _mk("academic", "unknown", "")
    for kw, note in _NON_PHARMA.items():
        if kw in nl:
            return _mk("non_pharma", "unknown", note)
    for kw, who in _ACQUIRED.items():
        if kw in nl:
            return _mk("acquired", "unknown", f"{who} 인수")
    # KR
    for kw, (cat, tier) in _KR_PHARMA.items():
        if kw in nl:
            return _mk(cat, tier, "KR")
    # 글로벌 빅파마
    for kw, tier in _BIG_PHARMA.items():
        if _hit(kw, nl):
            return _mk("big_pharma", tier, "")
    # 글로벌 바이오텍
    for kw, (cat, tier) in _BIOTECH.items():
        if kw in nl:
            return _mk(cat, tier, "")
    return _mk("unknown", "unknown", "")


def _hit(kw, nl):
    """짧은 키워드(≤4자)는 단어경계로 오탐 방지(예 'bms','gsk','ono ')."""
    if len(kw.strip()) <= 4:
        return re.search(r"\b" + re.escape(kw.strip()) + r"\b", nl) is not None
    return kw in nl


def _mk(cat, cap, note):
    return {"category": cat, "cap_tier": cap, "color": CAT[cat]["color"],
            "cat_ko": CAT[cat]["ko"], "cap_ko": CAP_TIER[cap]["ko"],
            "cap_color": CAP_TIER[cap]["color"], "note": note}


def color_of(name):
    return classify(name)["color"]


def cap_tier_of(name):
    return classify(name)["cap_tier"]


# 라벨 앞에 붙일 카테고리 색점(플롯 tick 개별색 미지원 우회 — 유니코드 원).
_DOT = {"big_pharma": "🔵", "biotech": "🟢", "startup": "🟠",
        "academic": "⚪", "acquired": "◾", "non_pharma": "🔴", "unknown": "▫️"}


def dot(name):
    return _DOT.get(classify(name)["category"], "▫️")


def legend_html():
    """그래프 위/아래 공통 색 범례(HTML). 카테고리 색점 + 라벨."""
    items = sorted(CAT.items(), key=lambda kv: kv[1]["order"])
    spans = "  ".join(
        f'<span style="color:{v["color"]};font-weight:700">●</span>&nbsp;{v["ko"]}'
        for _, v in items)
    return f'<div style="font-size:12.5px;color:#555;margin:2px 0 6px">회사 분류: {spans}</div>'


def cap_legend_html():
    items = sorted(CAP_TIER.items(), key=lambda kv: -kv[1]["rank"])
    spans = "  ".join(
        f'<span style="color:{v["color"]};font-weight:700">●</span>&nbsp;{v["ko"]}'
        for k, v in items if k != "unknown")
    return f'<div style="font-size:12.5px;color:#555;margin:2px 0 6px">시가총액: {spans} · 스몰/마이크로캡↓=협업가능성 낮음</div>'