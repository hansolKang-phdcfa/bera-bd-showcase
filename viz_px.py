# coding: utf-8
"""
[B-1 인터랙티브] Plotly 버전 시각화 — 드래그/핀치 줌 지원 (공개 showcase 동일 적용).

matplotlib viz.py(정적 PNG·덱용)는 그대로 두고, 대시보드에서 확대가 필요한 핵심 차트만
Plotly Figure로 반환. st.plotly_chart(fig, use_container_width=True, config=PX_CONFIG).
데이터 계약은 viz.py의 대응 함수와 동일.
"""
import re

import plotly.graph_objects as go

import design_tokens as T

BLUE, BLACK, GRAY = T.COLORS["blue"], T.COLORS["black"], T.COLORS["gray"]
SOFT, LGRAY = "#DCE0E6", "#C3CAD3"
PAL = [BLUE, "#E8544B", "#F5A623", "#2BB673", "#7B61FF", "#00A3B4", "#C86DD7", GRAY]
FONT = "Pretendard, -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"

# 대시보드에서 st.plotly_chart(..., config=PX_CONFIG) 로 사용 — 스크롤/드래그 줌 on.
PX_CONFIG = {"scrollZoom": True, "displayModeBar": True, "displaylogo": False,
             "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
             "toImageButtonOptions": {"scale": 2}}


def _disp(s):
    """표시용 정규화 — $→'USD ', 근사 '~'→'약 ', 범위 '~'→'-' (앱 _md와 동일)."""
    s = str(s).replace("$", "USD ")
    s = re.sub(r"(?:^|(?<=[\s(]))~", "약 ", s)
    s = s.replace("~", "-")
    return re.sub(r"USD +", "USD ", s)


def _short(name):
    n = str(name)
    for junk in (" PHARMACEUTICALS", ", INC.", " INC.", ", LTD.", " CO., LTD.", " AG", " LLC", ", LLC"):
        n = n.replace(junk, "")
    return n.title()[:24]


def _ylab(name):
    """차트 y축 라벨 — 긴 회사명은 중간 공백에서 2줄(<br>)로 접어 모바일 가로폭 절약. 풀네임은 hover에."""
    s = _short(name)
    if len(s) <= 13:
        return s
    spaces = [i for i, ch in enumerate(s) if ch == " "]
    if spaces:
        mid = len(s) / 2.0
        sp = min(spaces, key=lambda i: abs(i - mid))
        return s[:sp] + "<br>" + s[sp + 1:]
    return s[:15] + "…"


def _empty_px(msg):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(size=14, color=GRAY, family=FONT))
    fig.update_layout(height=160, paper_bgcolor="white", plot_bgcolor="white",
                      xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(l=10, r=10, t=10, b=10))
    return fig


def _layout(fig, title="", xtitle="", ytitle="", height=400, legend=True):
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=BLACK, family=FONT), x=0.01, xanchor="left"),
        font=dict(family=FONT, size=13, color=BLACK),
        paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(l=10, r=24, t=52, b=46), height=height, dragmode="zoom",
        hoverlabel=dict(font_size=13, font_family=FONT, bgcolor="white"),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1.0, font=dict(size=12)),
        bargap=0.3,
    )
    fig.update_xaxes(title=dict(text=xtitle, font=dict(size=12.5, color=BLACK)), showgrid=True,
                     gridcolor="#EEF1F4", zeroline=False, ticks="outside", tickcolor="#CFD6DE",
                     linecolor="#DDE2E8", tickfont=dict(size=12.5, color=BLACK))
    fig.update_yaxes(title=dict(text=ytitle, font=dict(size=12.5, color=BLACK)), showgrid=False,
                     zeroline=False, tickfont=dict(size=12.5, color=BLACK))
    return fig


def momentum_px(rows, top=12):
    """Anchor 인용 Momentum 덤벨 — ○직전 → ●최근, 색=추세(가속 BLUE/신규 소프트블루/냉각 GRAY/유지 LGRAY)."""
    rows = [r for r in rows if (r.get("recent_per_yr", 0) or 0) > 0 or (r.get("prior_per_yr", 0) or 0) > 0]
    rows = sorted(rows, key=lambda r: (r.get("recent_per_yr", 0) or 0))[-top:]
    if not rows:
        return _empty_px("momentum 데이터 없음 (anchor 피인용 희박)")
    comps = [_ylab(r["company"]) for r in rows]
    full = [_disp(r["company"]) for r in rows]
    prior = [float(r.get("prior_per_yr", 0) or 0) for r in rows]
    recent = [float(r.get("recent_per_yr", 0) or 0) for r in rows]
    fig = go.Figure()
    for i in range(len(rows)):                       # 연결선
        fig.add_trace(go.Scatter(x=[prior[i], recent[i]], y=[comps[i], comps[i]], mode="lines",
                                 line=dict(color=SOFT, width=4), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=prior, y=comps, mode="markers", name="직전 평균/년",
                             marker=dict(color=LGRAY, size=10, line=dict(color="white", width=1)),
                             customdata=full, hovertemplate="%{customdata}<br>직전 %{x:.1f}건/년<extra></extra>"))
    for tr, col in [("가속", BLUE), ("신규", "#8FB4FF"), ("냉각", GRAY), ("유지", LGRAY)]:
        idx = [i for i, r in enumerate(rows) if r.get("trend") == tr]
        if not idx:
            continue
        acc = [rows[i].get("acceleration") for i in idx]
        fig.add_trace(go.Scatter(
            x=[recent[i] for i in idx], y=[comps[i] for i in idx], mode="markers", name=f"최근 · {tr}",
            marker=dict(color=col, size=17, line=dict(color="white", width=1.5)),
            customdata=[[prior[i], (f"{a}x" if a not in (None, 0.0) else "—"), full[i]] for i, a in zip(idx, acc)],
            hovertemplate="%{customdata[2]}<br>최근 %{x:.1f}건/년 · 직전 %{customdata[0]:.1f}<br>" + tr + " (%{customdata[1]})<extra></extra>"))
    _layout(fig, title="관심 Momentum — ● 최근 vs ○ 직전 (색 = 가속/신규/냉각)",
            xtitle="연간 anchor 인용 건수", height=118 + 40 * len(rows))
    fig.update_yaxes(categoryorder="array", categoryarray=comps)
    fig.update_xaxes(rangemode="tozero")
    return fig


_STAGE_X = {"중단": -1.2, "전임상": 0, "Preclinical": 0, "IND": 1, "IND (Phase 1)": 1,
            "Phase 1": 2, "Ph1": 2, "Phase 2": 3.5, "Ph2": 3.5, "Phase 3": 5, "Ph3": 5,
            "Market": 6.5, "승인": 6.5, "시판": 6.5}


def competition_ladder_px(data):
    """경쟁 서열 — 기전 동일 시 개발 단계로 줄세우기. ★파랑=우리 자산, 회색=활성, 빨강X=이전세대."""
    players = list((data or {}).get("players", []))
    prior = [dict(p, _prior=True) for p in (data or {}).get("prior_gen", [])]
    rows = players + prior
    if not rows:
        return _empty_px("경쟁 서열 데이터 없음 (임상단계 정보 필요)")
    rows = sorted(rows, key=lambda r: _STAGE_X.get(r.get("stage"), 0))
    ylab = [_ylab(r["company"]) for r in rows]
    full = [_disp(f"{r['company']} ({r.get('asset', '')})") for r in rows]
    xs = [_STAGE_X.get(r.get("stage"), 0) for r in rows]
    fig = go.Figure()
    for i in range(len(rows)):
        fig.add_trace(go.Scatter(x=[-1.5, xs[i]], y=[ylab[i], ylab[i]], mode="lines",
                                 line=dict(color=SOFT, width=2), hoverinfo="skip", showlegend=False))
    groups = [("★ 우리 자산", "star", BLUE, lambda r: r.get("is_target")),
              ("이전세대 실패/중단", "x", "#E8544B", lambda r: r.get("_prior") and not r.get("is_target")),
              ("활성 경쟁", "circle", GRAY, lambda r: not r.get("is_target") and not r.get("_prior"))]
    for name, sym, col, pred in groups:
        idx = [i for i, r in enumerate(rows) if pred(r)]
        if not idx:
            continue
        fig.add_trace(go.Scatter(
            x=[xs[i] for i in idx], y=[ylab[i] for i in idx], mode="markers", name=name,
            marker=dict(symbol=sym, size=[22 if rows[i].get("is_target") else 15 for i in idx],
                        color=col, line=dict(color="white", width=1.5)),
            customdata=[[_disp(rows[i].get("stage", "")), _disp(rows[i].get("note", "") or "—"), full[i]] for i in idx],
            hovertemplate="%{customdata[2]}<br>단계: %{customdata[0]}<br>%{customdata[1]}<extra></extra>"))
    _layout(fig, title="경쟁 서열 — 오른쪽일수록 개발 단계 앞섬", xtitle="개발 단계 →",
            height=140 + 46 * len(rows))
    ticks = [("중단", -1.2), ("전임상", 0), ("Ph1", 2), ("Ph2", 3.5), ("Ph3", 5), ("시판", 6.5)]
    fig.update_xaxes(tickmode="array", tickvals=[t[1] for t in ticks], ticktext=[t[0] for t in ticks],
                     range=[-3.7, 7.6], showgrid=True)
    fig.update_yaxes(categoryorder="array", categoryarray=ylab)
    return fig


def field_heat_px(data):
    """타깃 필드 열기 곡선 — 도메인 인용 특허 수/년(검증·과열 추세)."""
    heat = (data or {}).get("field_heat", {})
    if not heat:
        return _empty_px("필드 열기 데이터 없음")
    yrs = sorted(int(y) for y in heat)
    vals = [heat[str(y)] for y in yrs]
    fig = go.Figure(go.Scatter(x=yrs, y=vals, mode="lines+markers", line=dict(color=BLUE, width=2.6),
                               marker=dict(color=BLUE, size=7), fill="tozeroy",
                               fillcolor="rgba(62,131,255,0.14)",
                               hovertemplate="%{x}년 · %{y}건<extra></extra>"))
    _layout(fig, title="타깃 필드 열기 곡선 (검증·과열 추세)", xtitle="출원(filing) 연도",
            ytitle="도메인 인용 특허 수 / 년", height=360, legend=False)
    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(rangemode="tozero")
    return fig


def _stacked_h(rows, cats, val_of, ylab_of, title, xtitle, hover_unit="건"):
    fig = go.Figure()
    for i, c in enumerate(cats):
        vals = [float(val_of(r, c) or 0) for r in rows]
        if sum(vals) == 0:
            continue
        fig.add_trace(go.Bar(y=[ylab_of(r) for r in rows], x=vals, name=c, orientation="h",
                             marker_color=PAL[i % len(PAL)],
                             hovertemplate="%{y}<br>" + str(c) + ": %{x}" + hover_unit + "<extra></extra>"))
    fig.update_layout(barmode="stack")
    _layout(fig, title=title, xtitle=xtitle, height=140 + 40 * len(rows))
    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(categoryorder="array", categoryarray=[ylab_of(r) for r in rows])
    return fig


def kr_tier_px(kr_rows, top=18, tier_filter=None, domains=None):
    """KR 3-tier — 회사별 IPC 도메인 stacked. 위=Tier1(직접) → 아래=Tier3(잠재)."""
    rows = [r for r in kr_rows if float(r.get("total_focus", 0) or 0) > 0 and r.get("tier") in (1, 2, 3)]
    if tier_filter in (1, 2, 3):
        rows = [r for r in rows if r.get("tier") == tier_filter]
    if not rows:
        return _empty_px(f"KR {'Tier' + str(tier_filter) if tier_filter else '3-tier'} 데이터 없음")
    META = {"assignee", "tier", "tier_label", "total_focus", "partner_role"}
    if domains:
        core = [d for d in domains if any(d in r for r in rows)]
    else:
        keys = set()
        for r in rows:
            keys |= set(r.keys())
        core = sorted(k for k in keys if k not in META and not k.startswith("m_") and not k.startswith("recent"))
    _bar = lambda r: sum(float(r.get(dd, 0) or 0) for dd in core)   # 화면 막대 길이(표시 도메인 합)로 정렬 = 시각 일치
    rows = sorted(rows, key=lambda r: (r.get("tier", 9), -_bar(r)))[:top][::-1]
    return _stacked_h(rows, core, lambda r, d: r.get(d, 0),
                      lambda r: f"{_ylab(r['assignee'])} ·T{r.get('tier')}",
                      "KR 3-tier — 위=Tier1(직접) → 아래=Tier3(잠재)", "도메인(IPC)별 특허 건수")


def crossmod_px(cm, top=14):
    """Cross-modality — 회사별 모달리티별 특허 건수 stacked (같은 적응증, 다른 모달리티)."""
    _ACAD = re.compile(r'univ|institut|hospital|united states|department|dept of|helmholtz|zentrum|'
                       r'national inst|cancer (center|institut)|academ|foundation|대학|연구|병원|정부', re.I)
    rows = cm.get("crossmod", []) if isinstance(cm, dict) else cm
    rows = [r for r in rows if (r.get("n_patents", 0) or 0) > 0 and not _ACAD.search(r.get("company", ""))]
    rows = rows[:top][::-1]
    if not rows:
        return _empty_px("cross-modality 상업사 데이터 없음(학계 제외 후)")
    mods = list((cm.get("meta", {}).get("other_modalities") if isinstance(cm, dict) else None) or [])
    for r in rows:
        for mm in (r.get("by_modality") or {}):
            if mm not in mods:
                mods.append(mm)
    return _stacked_h(rows, mods, lambda r, mm: (r.get("by_modality") or {}).get(mm, 0),
                      lambda r: _ylab(r["company"]),
                      "Cross-modality — 같은 적응증, 다른 모달리티", "모달리티별 특허 건수")
