# coding: utf-8
"""
[B-1] 시각화 — 스냅샷 데이터 → matplotlib Figure (BERA 4색, 자산무관).

이전 PoC 시각화(cocitation 네트워크·cliff 타임라인·AoI 기여도)를 일반화. 대시보드/덱에서
호출. 한글 렌더는 번들 Pretendard를 matplotlib에 등록(로컬·Streamlit Cloud 리눅스 공통).
"""
import os

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import networkx as nx

import design_tokens as T

_OTF = os.path.join(T.ASSETS_DIR, "Pretendard-Regular.otf")
if os.path.exists(_OTF):
    try:
        font_manager.fontManager.addfont(_OTF)
        matplotlib.rcParams["font.family"] = "Pretendard"
    except Exception:
        pass
matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["text.parse_math"] = False

BLUE, BLACK, GRAY = T.COLORS["blue"], T.COLORS["black"], T.COLORS["gray"]
SOFT, LGRAY = "#DCE0E6", "#D3D6DA"


def _short(name):
    n = str(name)
    for junk in (" PHARMACEUTICALS", ", INC.", " INC.", ", LTD.", " CO., LTD.", " AG", " LLC", ", LLC"):
        n = n.replace(junk, "")
    return n.title()[:22]


import re as _re


def _disp(s):
    """차트 텍스트 표시용 정규화 — $→'USD ', 범위 '~'→'-', 근사 '~'→'약 ' (앱 _md와 동일 규칙)."""
    s = str(s).replace("$", "USD ")
    s = _re.sub(r"(\d)\s*~\s*(?=\d)", r"-", s)
    s = s.replace("~", "약 ")
    return _re.sub(r"USD +", "USD ", s)


def cocitation_network_fig(coc, target_label="Target", top_nodes=15, edge_min=0.03):
    """co-citation Jaccard 네트워크. 노드=회사(크기∝centrality), 엣지=Jaccard,
    타깃=블루 강조(주변부=독자 IP 공간). coc=cocitation.json dict."""
    cen = {c["company"]: c["centrality"] for c in coc.get("centrality", [])}
    top = [c["company"] for c in coc.get("centrality", [])[:top_nodes]]
    tset = set(top)
    pairs = [p for p in coc.get("pairs", [])
             if p["company_1"] in tset and p["company_2"] in tset and p["jaccard"] >= edge_min]
    tsim = coc.get("target_similarity", [])
    near = tsim[0] if tsim else {"company": None, "jaccard": coc.get("target_max_jaccard", 0.0)}

    Gc = nx.Graph()
    Gc.add_nodes_from(top)
    for p in pairs:
        Gc.add_edge(p["company_1"], p["company_2"], weight=p["jaccard"])
    if Gc.number_of_edges():
        giant = max(nx.connected_components(Gc), key=len)
        G = Gc.subgraph(giant).copy()
    else:
        G = Gc
    TGT = target_label
    G.add_node(TGT)
    if near.get("company") in G:
        G.add_edge(TGT, near["company"], weight=near["jaccard"])
    top = [c for c in top if c in G]

    pos = nx.spring_layout(G, k=1.4, iterations=200, weight="weight", seed=42)
    fig, ax = plt.subplots(figsize=(11.5, 6.2), dpi=190)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    for u, v, w in G.edges(data="weight"):
        if TGT in (u, v):
            continue
        x1, y1 = pos[u]; x2, y2 = pos[v]
        ax.plot([x1, x2], [y1, y2], color=SOFT, lw=0.6 + (w or 0) * 5, alpha=0.7, zorder=1)
    if near.get("company") in pos:
        x1, y1 = pos[TGT]; x2, y2 = pos[near["company"]]
        ax.plot([x1, x2], [y1, y2], color=GRAY, lw=0.8, ls=(0, (2, 3)), alpha=0.6, zorder=1)
    for c in top:
        x, y = pos[c]
        ax.scatter(x, y, s=260 + cen.get(c, 0) * 420, c=GRAY, edgecolors="white",
                   linewidth=1.2, zorder=5, alpha=0.9)
        ax.annotate(_short(c), (x, y), ha="center", va="center", fontsize=7.5, color=BLACK, zorder=6)
    xt, yt = pos[TGT]
    ax.scatter(xt, yt, s=1400, c=BLUE, edgecolors="white", linewidth=2.5, zorder=8)
    ax.annotate(TGT[:8], (xt, yt), ha="center", va="center", fontsize=11,
                fontweight="bold", color="white", zorder=9)
    ax.annotate(f"max Jaccard {near.get('jaccard', 0.0)}\n(독자 IP 공간 — 사실상 미연결)",
                (xt, yt), xytext=(0, -40), textcoords="offset points", ha="center", va="top",
                fontsize=9, color=BLUE, fontweight="bold", zorder=9)
    ax.set_title("Co-citation Network — 타깃은 독자 IP 공간에 위치",
                 fontsize=13, fontweight="bold", color=BLACK, pad=12)
    ax.axis("off")
    ax.text(0.99, 0.01, "노드 크기 = centrality  |  엣지 굵기 = Jaccard 유사도",
            transform=ax.transAxes, fontsize=8.5, color=GRAY, ha="right")
    fig.tight_layout()
    return fig


def cliff_timeline_fig(cliff_rows, expiry_window=(2026, 2031)):
    """원천특허 만료 타임라인. x=만료연도, y=회사, 점 크기=피인용. cliff_rows=cliff_output 표."""
    def yr(d):
        try:
            return int(str(d)[:4]) + (int(str(d)[5:7]) - 1) / 12.0
        except Exception:
            return None
    pts = [(r["company"], yr(r["est_expiry"]), int(r["cites"]), bool(r.get("ob_ds")),
            (r.get("ob_drug") or "")[:14]) for r in cliff_rows if yr(r.get("est_expiry"))]
    if not pts:
        fig, ax = plt.subplots(figsize=(11.5, 2.0)); ax.text(0.5, 0.5, "cliff 데이터 없음",
                 ha="center", color=GRAY); ax.axis("off"); return fig
    order = {}
    for c, y, cit, ds, dr in pts:
        order[c] = max(order.get(c, 0), cit)
    comps = sorted(order, key=lambda c: order[c])
    cy = {c: i for i, c in enumerate(comps)}
    yrs = [y for _, y, _, _, _ in pts]
    y0 = min(int(min(yrs)), expiry_window[0]); y1 = max(int(max(yrs)) + 1, expiry_window[1])

    fig, ax = plt.subplots(figsize=(11.5, 0.6 + 0.42 * len(comps)), dpi=190)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    for c in comps:
        ax.axhline(cy[c], color="#EEF1F4", lw=8, zorder=0)
    for c, y, cit, ds, dr in pts:
        # OB DS-verified(진짜 시판약 원천특허·실만료일)=blue·star / 근사(출원+20)=gray·o
        ax.scatter(y, cy[c], s=(60 if ds else 40) + cit * 3.0,
                   c=(BLUE if ds else LGRAY), alpha=(0.95 if ds else 0.6),
                   marker=("*" if ds else "o"), edgecolors=(BLACK if ds else "white"),
                   linewidth=(1.1 if ds else 1), zorder=(6 if ds else 5))
        if ds and dr:            # DS 스타 옆에 약물명(어떤 API의 cliff인지)
            ax.annotate(dr, (y, cy[c]), xytext=(0, 9), textcoords="offset points",
                        ha="center", va="bottom", fontsize=6.8, color=BLUE, fontweight="bold", zorder=7)
    seen = set()
    for c, y, cit, ds, dr in sorted(pts, key=lambda t: -t[2]):
        if c in seen:
            continue
        seen.add(c)
        ax.annotate(f"{cit}", (y, cy[c]), fontsize=7.5, ha="center", va="center",
                    color=(BLACK if ds else "white"), fontweight="bold", zorder=8)
    ax.set_yticks(range(len(comps))); ax.set_yticklabels(comps, fontsize=10, color=BLACK)
    ax.set_xlim(y0 - 0.3, y1 + 0.3); ax.set_xticks(range(y0, y1 + 1))
    ax.set_xticklabels([str(y) for y in range(y0, y1 + 1)], fontsize=8.5, color=GRAY)
    ax.set_xlabel("원천특허 만료연도 — 임박할수록 BD 압력↑ (★=OB 실만료, ○=출원+20 근사)",
                  fontsize=11, color=BLACK)
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRAY)
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], marker="*", color="w", markerfacecolor=BLUE,
                              markeredgecolor=BLACK, markersize=12, label="OB 원천특허(DS)·실만료일"),
                       Line2D([], [], marker="o", color="w", markerfacecolor=LGRAY,
                              markersize=9, label="근사(출원+20, 미검증)")],
              loc="lower right", fontsize=8.5, frameon=False)
    ax.set_title("Patent Cliff — 바이어 원천특허 만료 (★=FDA Orange Book 검증, 점 크기=피인용)",
                 fontsize=13, fontweight="bold", color=BLACK, pad=10)
    fig.tight_layout()
    return fig


def aoi_contrib_fig(aoi_rows, weights):
    """AoI 3신호 기여도 누적막대. aoi_rows=aoi_output 표, weights={clinical,citation,need}."""
    rows = [r for r in aoi_rows if float(r["aoi_score"]) > 0][::-1]
    if not rows:
        fig, ax = plt.subplots(figsize=(11.5, 2.0)); ax.text(0.5, 0.5, "AoI 데이터 없음",
                 ha="center", color=GRAY); ax.axis("off"); return fig
    comp = [r["company"] for r in rows]
    need_c = [weights.get("need", 0) * float(r["need_signal"]) for r in rows]
    cit_c = [weights.get("citation", 0) * float(r["citation_signal"]) for r in rows]
    clin_c = [weights.get("clinical", 0) * float(r["clinical_signal"]) for r in rows]
    tot = [float(r["aoi_score"]) for r in rows]
    y = range(len(comp))
    fig, ax = plt.subplots(figsize=(11.5, 0.6 + 0.42 * len(comp)), dpi=190)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    ax.barh(y, need_c, color=BLUE, label=f"need·원천특허 만료 ({weights.get('need',0):.2f})", height=0.62)
    ax.barh(y, cit_c, left=need_c, color=GRAY, label=f"citation·anchor 인용 ({weights.get('citation',0):.2f})", height=0.62)
    ax.barh(y, clin_c, left=[a + b for a, b in zip(need_c, cit_c)], color=LGRAY,
            label=f"clinical·활성 임상 ({weights.get('clinical',0):.2f})", height=0.62)
    for i, t in enumerate(tot):
        ax.text(t + 0.008, i, f"{t:.3f}", va="center", ha="left", fontsize=9.5,
                fontweight="bold", color=BLACK)
    ax.set_yticks(list(y)); ax.set_yticklabels(comp, fontsize=10, color=BLACK)
    ax.set_xlim(0, (max(tot) or 1) * 1.16); ax.set_xlabel("AoI score (가중합)", fontsize=11, color=BLACK)
    ax.tick_params(axis="x", labelsize=11, colors=BLACK)
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRAY)
    ax.set_title("Revealed AoI — 3신호 기여도 (가중합)", fontsize=13, fontweight="bold", color=BLACK, pad=10)
    ax.legend(loc="lower right", fontsize=9, frameon=False)
    fig.tight_layout()
    return fig


def _empty(msg, h=2.4):
    fig, ax = plt.subplots(figsize=(11.5, h))
    ax.text(0.5, 0.5, msg, ha="center", va="center", color=GRAY, fontsize=11)
    ax.axis("off")
    return fig


def angle_venn_fig(angle_rows, aoi_rows=None, top=12):
    """Anchor Signature Angle (LO vs Co-dev) 벤다이어그램형 파트너 지도.

    왼쪽 원 = LO 후보(도메인 anchor 인용 없음 = 기전 역량 gap → 자산 in-license 각),
    오른쪽 원 = Co-dev(anchor 인용 축적 = 기전 역량 보유 → 플랫폼 공동개발 각),
    겹침 = 하이브리드(인용 일부). 버블 크기 = AoI 관심도. angle_rows=angle_output 표."""
    from collections import defaultdict
    from matplotlib.patches import Circle
    aoi = {r["company"]: float(r.get("aoi_score", 0) or 0) for r in (aoi_rows or [])}
    rows = []
    for r in angle_rows:
        rows.append({"c": r["company"], "tc": float(r.get("total_cit", 0) or 0),
                     "aoi": aoi.get(r["company"], 0.0)})
    if not rows:
        return _empty("angle 데이터 없음")
    rows = sorted(rows, key=lambda x: -x["tc"])[:top]
    nz = sorted(r["tc"] for r in rows if r["tc"] > 0)
    med = nz[len(nz) // 2] if nz else 1
    for r in rows:
        r["zone"] = "lo" if r["tc"] == 0 else ("codev" if r["tc"] >= med else "mid")

    fig, ax = plt.subplots(figsize=(11.5, 6.4), dpi=190)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    ax.add_patch(Circle((0.40, 0.48), 0.35, color=GRAY, alpha=0.12, zorder=1))
    ax.add_patch(Circle((0.60, 0.48), 0.35, color=BLUE, alpha=0.12, zorder=1))
    ax.text(0.17, 0.93, "LO 후보", ha="center", fontsize=12, color=BLACK, fontweight="bold")
    ax.text(0.17, 0.885, "기전 역량 gap → 자산 in-license", ha="center", fontsize=8.5, color=GRAY)
    ax.text(0.83, 0.93, "Co-dev", ha="center", fontsize=12, color=BLUE, fontweight="bold")
    ax.text(0.83, 0.885, "anchor 인용 보유 → 플랫폼 공동개발", ha="center", fontsize=8.5, color=GRAY)

    zone_x = {"lo": 0.25, "mid": 0.50, "codev": 0.75}
    buckets = defaultdict(list)
    for r in rows:
        buckets[r["zone"]].append(r)
    smax = max((r["aoi"] for r in rows), default=1) or 1
    for zone, items in buckets.items():
        items = sorted(items, key=lambda x: -x["aoi"])
        n = len(items)
        for i, r in enumerate(items):
            jit = 0.055 * ((i % 2) * 2 - 1) if n > 3 else 0
            x = zone_x[zone] + jit
            y = 0.48 + (i - (n - 1) / 2) * (0.60 / max(n, 1))
            s = 260 + r["aoi"] / smax * 900
            col = BLUE if zone == "codev" else (GRAY if zone == "lo" else "#7FA8E8")
            ax.scatter(x, y, s=s, c=col, alpha=0.9, edgecolors="white", linewidth=1.5, zorder=5)
            ax.annotate(_short(r["c"]), (x, y), ha="center", va="center", fontsize=7.3,
                        color="white", fontweight="bold", zorder=6)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.set_title("Anchor Signature Angle — LO vs Co-dev 분기 (버블 크기 = AoI 관심도)",
                 fontsize=13, fontweight="bold", color=BLACK, pad=8)
    ax.text(0.5, 0.015, "왼쪽 = 역량 gap(자산 도입 각) · 가운데 = 하이브리드 · 오른쪽 = 기전 역량 보유(공동개발 각)",
            ha="center", fontsize=8.5, color=GRAY)
    fig.tight_layout()
    return fig


def lo_candidates_fig(lo_rows, top=12):
    """License-Out Buyer 후보 — gap·interest·activity 3성분 누적막대(왜 후보인지 분해).
    lo_rows=lo_output 표(rank·company·license_out_score·gap·interest·activity)."""
    rows = [r for r in lo_rows if float(r.get("license_out_score", 0) or 0) > 0]
    if not rows:
        return _empty("LO 데이터 없음")
    rows = sorted(rows, key=lambda r: float(r["license_out_score"]))[-top:]
    comp = [r["company"] for r in rows]
    gap = [float(r.get("gap", 0) or 0) for r in rows]
    interest = [float(r.get("interest", 0) or 0) for r in rows]
    activity = [float(r.get("activity", 0) or 0) for r in rows]
    score = [float(r["license_out_score"]) for r in rows]
    y = range(len(comp))
    fig, ax = plt.subplots(figsize=(11.5, 0.6 + 0.44 * len(comp)), dpi=190)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    ax.barh(y, gap, color=BLUE, height=0.6, label="gap · 파이프라인 공백(cliff)")
    ax.barh(y, interest, left=gap, color=GRAY, height=0.6, label="interest · 도메인 인용")
    ax.barh(y, activity, left=[a + b for a, b in zip(gap, interest)], color=LGRAY,
            height=0.6, label="activity · 임상 활성")
    for i, r in enumerate(rows):
        tot = gap[i] + interest[i] + activity[i]
        ax.text(tot + 0.02, i, f"score {score[i]:.2f}", va="center", ha="left",
                fontsize=9, fontweight="bold", color=BLACK)
    ax.set_yticks(list(y)); ax.set_yticklabels(comp, fontsize=10, color=BLACK)
    ax.set_xlim(0, (max(g + i + a for g, i, a in zip(gap, interest, activity)) or 1) * 1.2)
    ax.set_xlabel("gap + interest + activity (LO 후보 근거 분해)", fontsize=11, color=BLACK)
    ax.tick_params(axis="x", labelsize=11, colors=BLACK)
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRAY)
    ax.set_title("License-Out Buyer 후보 — 근거 3성분 분해", fontsize=13, fontweight="bold", color=BLACK, pad=10)
    ax.legend(loc="lower right", fontsize=9, frameon=False)
    fig.tight_layout()
    return fig


def kr_tier_fig(kr_rows, top=18, tier_filter=None, domains=None):
    """KR 경쟁 3-tier — 회사별 도메인(IPC)별 특허 건수 stacked 막대(색=도메인). y라벨 ·T=티어."""
    from matplotlib.patches import Patch
    rows = [r for r in kr_rows if float(r.get("total_focus", 0) or 0) > 0 and r.get("tier") in (1, 2, 3)]
    if tier_filter in (1, 2, 3):
        rows = [r for r in rows if r.get("tier") == tier_filter]
    if not rows:
        return _empty(f"KR {'Tier' + str(tier_filter) if tier_filter else '3-tier'} 데이터 없음")
    META = {"assignee", "tier", "tier_label", "total_focus", "partner_role"}
    if domains:
        core = [d for d in domains if any(d in r for r in rows)]
    else:
        keys = set()
        for r in rows:
            keys |= set(r.keys())
        core = sorted(k for k in keys if k not in META and not k.startswith("m_")
                      and not k.startswith("recent"))
    rows = sorted(rows, key=lambda r: (r.get("tier", 9), -float(r.get("total_focus", 0))))[:top]
    rows = rows[::-1]
    comp = [f"{_short(r['assignee'])}  ·T{r.get('tier')}" for r in rows]
    PAL = [BLUE, "#E8544B", "#F5A623", "#2BB673", "#7B61FF", "#00A3B4", "#C86DD7", GRAY]
    dcol = {d: PAL[i % len(PAL)] for i, d in enumerate(core)}
    y = list(range(len(rows)))
    fig, ax = plt.subplots(figsize=(11.5, 0.7 + 0.42 * len(rows)), dpi=190)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    left = [0.0] * len(rows)
    for d in core:
        vals = [float(r.get(d, 0) or 0) for r in rows]
        ax.barh(y, vals, left=left, color=dcol[d], height=0.66)
        left = [l + v for l, v in zip(left, vals)]
    xmax = max(left) or 1
    for i in y:
        ax.text(left[i] + xmax * 0.008, i, f"{int(left[i])}", va="center", fontsize=8, color=BLACK)
    ax.set_yticks(y); ax.set_yticklabels(comp, fontsize=10, color=BLACK)
    ax.set_xlabel("도메인(IPC)별 특허 건수 — stacked (한 특허가 여러 IPC면 각각 카운트)", fontsize=11, color=BLACK)
    ax.tick_params(axis="x", labelsize=11, colors=BLACK)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.legend(handles=[Patch(color=dcol[d], label=d) for d in core], loc="lower right",
              fontsize=8, frameon=False, title="IPC 도메인", ncol=2)
    ax.set_title("KR 3-tier — 위=Tier1(직접), 아래=Tier3(잠재) · 티어 내 특허건수순",
                 fontsize=12, fontweight="bold", color=BLACK, pad=10)
    fig.tight_layout()
    return fig


def momentum_fig(mom_rows, top=12):
    """Anchor 인용 Momentum — prior_per_yr → recent_per_yr 덤벨(가속/냉각).
    절대량이 아니라 '늘고 있나/줄고 있나' 방향. mom_rows=momentum.json[momentum]."""
    from matplotlib.patches import Patch
    rows = [r for r in mom_rows
            if (r.get("recent_per_yr", 0) or 0) > 0 or (r.get("prior_per_yr", 0) or 0) > 0]
    if not rows:
        return _empty("momentum 데이터 없음(anchor 피인용 희박)")
    rows = sorted(rows, key=lambda r: (r.get("recent_per_yr", 0) or 0))[-top:]
    comp = [r["company"] for r in rows]
    prior = [float(r.get("prior_per_yr", 0) or 0) for r in rows]
    recent = [float(r.get("recent_per_yr", 0) or 0) for r in rows]
    tcol = {"가속": BLUE, "냉각": GRAY, "유지": LGRAY}
    y = range(len(comp))
    fig, ax = plt.subplots(figsize=(11.5, 0.6 + 0.46 * len(comp)), dpi=190)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    xmax = max(max(prior), max(recent), 0.1)
    for i in y:
        r = rows[i]; tr = r.get("trend", "유지"); col = tcol.get(tr, LGRAY)
        ax.plot([prior[i], recent[i]], [i, i], color=SOFT, lw=3, zorder=1, solid_capstyle="round")
        ax.scatter(prior[i], i, s=42, c=LGRAY, edgecolors="white", linewidth=1, zorder=3)
        ax.scatter(recent[i], i, s=170, c=col, edgecolors="white", linewidth=1.4, zorder=4)
        acc = r.get("acceleration")
        lbl = tr + (f" {acc}x" if acc not in (None, 0.0) else "")
        ax.text(max(prior[i], recent[i]) + xmax * 0.02, i, lbl, va="center",
                fontsize=8.2, color=col if tr != "유지" else GRAY, fontweight="bold")
    ax.set_yticks(list(y)); ax.set_yticklabels(comp, fontsize=10, color=BLACK)
    ax.set_xlim(-xmax * 0.03, xmax * 1.25)
    ax.set_xlabel("연간 anchor 인용 건수  (○ 직전 평균 → ● 최근 평균)", fontsize=11, color=BLACK)
    ax.tick_params(axis="x", labelsize=11, colors=BLACK)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRAY)
    ax.legend(handles=[Patch(color=BLUE, label="가속 (≥1.2x)"),
                       Patch(color=GRAY, label="냉각 (<0.8x)"),
                       Patch(color=LGRAY, label="유지")],
              loc="lower right", fontsize=9, frameon=False)
    ax.set_title("Anchor 인용 Momentum — 그 영역 관심이 가속/냉각 중인가 (● 최근 · 색=추세)",
                 fontsize=13, fontweight="bold", color=BLACK, pad=10)
    fig.tight_layout()
    return fig


def access_fig(access_rows):
    """Specialty Access(G3) — 실현가능 매출($M) 막대(상업화 준비도=P3 인프라+marketed).
    access_rows=score_access 산출(company·access_score·realizable_rev_M·access_note)."""
    rows = [r for r in access_rows]
    if not rows:
        return _empty("access 데이터 없음")
    rows = sorted(rows, key=lambda r: float(r.get("realizable_rev_M", 0) or 0))
    comp = [r["company"] for r in rows]
    rev = [float(r.get("realizable_rev_M", 0) or 0) for r in rows]
    y = range(len(comp))
    fig, ax = plt.subplots(figsize=(11.5, 0.6 + 0.5 * len(comp)), dpi=190)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    ax.barh(y, rev, color=BLUE, height=0.58)
    for i, r in enumerate(rows):
        ax.text(rev[i] + (max(rev) or 1) * 0.01, i, str(r.get("access_note", "")),
                va="center", fontsize=8.3, color=BLACK)
    ax.set_yticks(list(y)); ax.set_yticklabels(comp, fontsize=10, color=BLACK)
    ax.set_xlim(0, (max(rev) or 1) * 1.35)
    ax.set_xlabel("실현가능 매출 ($M) = access_score × peak_market (상업화 능력 proxy)",
                  fontsize=11, color=BLACK)
    ax.tick_params(axis="x", labelsize=11, colors=BLACK)
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRAY)
    ax.set_title("Specialty Access (G3) — 상업화 준비도 × 실현 매출",
                 fontsize=13, fontweight="bold", color=BLACK, pad=10)
    fig.tight_layout()
    return fig


def crossmod_fig(cm, top=14):
    """Cross-modality — 회사별 모달리티별 특허 건수 stacked 막대(색=모달리티). by_modality 사용."""
    from matplotlib.patches import Patch
    import re
    _ACAD = re.compile(r'univ|institut|hospital|united states|department|dept of|helmholtz|zentrum|'
                       r'national inst|cancer (center|institut)|academ|foundation|대학|연구|병원|정부', re.I)
    rows = cm.get("crossmod", []) if isinstance(cm, dict) else cm
    rows = [r for r in rows if (r.get("n_patents", 0) or 0) > 0 and not _ACAD.search(r.get("company", ""))]
    rows = rows[:top][::-1]
    if not rows:
        return _empty("cross-modality 상업사 데이터 없음(학계 제외 후)")
    mods = list((cm.get("meta", {}).get("other_modalities") if isinstance(cm, dict) else None) or [])
    for r in rows:
        for mm in (r.get("by_modality") or {}):
            if mm not in mods:
                mods.append(mm)
    PAL = [BLUE, "#E8544B", "#F5A623", "#2BB673", "#7B61FF", "#00A3B4", "#C86DD7", GRAY]
    mcol = {mm: PAL[i % len(PAL)] for i, mm in enumerate(mods)}
    comp = [_short(r["company"]) for r in rows]
    y = list(range(len(rows)))
    fig, ax = plt.subplots(figsize=(11.5, 0.7 + 0.44 * len(rows)), dpi=190)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    left = [0.0] * len(rows)
    for mm in mods:
        vals = [float((r.get("by_modality") or {}).get(mm, 0) or 0) for r in rows]
        if sum(vals) == 0:
            continue
        ax.barh(y, vals, left=left, color=mcol[mm], height=0.64)
        left = [l + v for l, v in zip(left, vals)]
    xmax = max(left) or 1
    for i in y:
        ax.text(left[i] + xmax * 0.008, i, f"{int(left[i])}", va="center", fontsize=8, color=BLACK)
    ax.set_yticks(y); ax.set_yticklabels(comp, fontsize=10, color=BLACK)
    ax.set_xlabel("모달리티별 특허 건수 — stacked (같은 적응증, 다른 모달리티)", fontsize=11, color=BLACK)
    ax.tick_params(axis="x", labelsize=11, colors=BLACK)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    used = [mm for mm in mods if any((r.get("by_modality") or {}).get(mm) for r in rows)]
    ax.legend(handles=[Patch(color=mcol[mm], label=mm) for mm in used], loc="lower right",
              fontsize=8, frameon=False, title="모달리티", ncol=2)
    ax.set_title("Cross-modality — 회사별 모달리티 분해 (색=모달리티)",
                 fontsize=12, fontweight="bold", color=BLACK, pad=10)
    fig.tight_layout()
    return fig


def bd_trend_fig(bd):
    """BD 시장 추세 — 2패널: (위)딜 빈도 (아래)총 딜 규모($M). 각 LO vs M&A 스택.
    bd=bd_trend.json. LO=blue, M&A=dark. 최신연도(기록지연 가능)는 반투명. 시장 단위."""
    DARK = T.COLORS["dark"]
    yearly = bd.get("yearly", {})
    years = sorted(int(y) for y in yearly)
    if not years:
        return _empty("BD 딜 데이터 없음")
    cur = bd.get("meta", {}).get("cur", 2024)
    xs = [str(y) for y in years]
    lo_n = [yearly[str(y)].get("lo_n", 0) for y in years]
    ma_n = [yearly[str(y)].get("ma_n", 0) for y in years]
    lo_s = [yearly[str(y)].get("lo_size", 0) for y in years]
    ma_s = [yearly[str(y)].get("ma_size", 0) for y in years]
    alpha = [1.0 if y <= cur else 0.4 for y in years]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11.5, 6.4), dpi=190, sharex=True)
    fig.patch.set_facecolor("white")
    for ax in (ax1, ax2):
        ax.set_facecolor("white")
        for sp in ["top", "right", "left"]:
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color(GRAY)
        ax.set_yticks([])

    def stacked(ax, lo, ma, fmt):
        for i in range(len(xs)):
            ax.bar(xs[i], lo[i], color=BLUE, width=0.76, alpha=alpha[i], zorder=2)
            ax.bar(xs[i], ma[i], bottom=lo[i], color=DARK, width=0.76, alpha=alpha[i], zorder=2)
            tot = lo[i] + ma[i]
            if tot > 0:
                ax.text(i, tot + max([l + m for l, m in zip(lo, ma)] + [1]) * 0.02,
                        fmt(tot), ha="center", fontsize=7.5, color=BLACK)

    stacked(ax1, lo_n, ma_n, lambda v: str(int(v)))
    rec, pri = bd.get("recent_per_yr"), bd.get("prior_per_yr")
    if rec is not None:
        ax1.axhline(rec, color=BLUE, lw=1.2, ls=(0, (4, 3)), zorder=3)
        ax1.text(len(xs) - 0.5, rec, f" recent {rec}/yr", va="bottom", ha="right",
                 fontsize=8, color=BLUE, fontweight="bold")
    if pri is not None:
        ax1.axhline(pri, color=GRAY, lw=1.2, ls=(0, (4, 3)), zorder=3)
        ax1.text(0, pri, f"prior {pri}/yr ", va="bottom", ha="left", fontsize=8, color=GRAY, fontweight="bold")
    from matplotlib.patches import Patch
    ax1.legend(handles=[Patch(color=BLUE, label="LO·파트너십"), Patch(color=DARK, label="M&A(인수)")],
               loc="upper left", fontsize=8.5, frameon=False, ncol=2)
    tr, acc = bd.get("trend", ""), bd.get("acceleration")
    ax1.set_title(f"BD 시장 추세 — (위) 딜 빈도  (recent/prior {acc}x · {tr}, 총 {bd.get('total')}건)",
                  fontsize=12, fontweight="bold", color=BLACK, pad=8)

    stacked(ax2, lo_s, ma_s, lambda v: f"${int(v)}M" if v >= 1 else "")
    ax2.set_title(f"(아래) 총 딜 규모 $M  (priced ${int(bd.get('total_size_priced_m', 0))}M · ~17% 딜만 금액공개)",
                  fontsize=11, fontweight="bold", color=BLACK, pad=6)
    ax2.tick_params(axis="x", labelsize=8, colors=GRAY)
    ax2.text(0.5, -0.22, f"파랑=LO·파트너십 · 남색=M&A · 반투명={cur + 1}~(기록지연 가능, 빈도비율서 제외)",
             transform=ax2.transAxes, ha="center", fontsize=8, color=GRAY)
    fig.tight_layout()
    return fig

def kr_cocitation_fig(data, top=12):
    """KR 경쟁사 발굴 — kr_patents 정밀키워드 매칭 랭킹(초기 한국자산 US cocitation 빈칸 대체).
    자국(KR) 강조/해외(KR 출원) 구분. data=kr_cocitation.json."""
    from matplotlib.patches import Patch
    comps = (data or {}).get("kr_competitors", [])[:top]
    if not comps:
        return _empty("KR 경쟁사 매칭 없음 — 키워드 정밀도 확인")
    comps = comps[::-1]
    names = [c["company"].replace(" CO LTD", "").replace(" INC", "").replace(" CORP", "")[:28]
             for c in comps]
    vals = [c.get("n_patents", 0) for c in comps]
    KR_C = "#E8544B"
    cols = [KR_C if c.get("country") == "KR" else BLUE for c in comps]
    fig, ax = plt.subplots(figsize=(10, 0.7 + 0.44 * len(comps)), dpi=190)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    ax.barh(range(len(comps)), vals, color=cols)
    xmax = max(vals) or 1
    for i, v in enumerate(vals):
        ax.text(v + xmax * 0.012, i, str(v), va="center", fontsize=8.5, color=GRAY)
    ax.set_yticks(range(len(comps))); ax.set_yticklabels(names, fontsize=9.5, color=BLACK)
    ax.set_xlabel("KR 특허 출원 건수 (같은 기전/타깃 키워드)", fontsize=11, color=BLACK)
    ax.tick_params(axis="x", labelsize=11, colors=BLACK)
    ax.legend(handles=[Patch(color=KR_C, label="KR(자국)"), Patch(color=BLUE, label="해외(KR 출원)")],
              fontsize=8, loc="lower right", frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_xlim(0, xmax * 1.16)
    fig.tight_layout()
    return fig


def field_pool_fig(data, top=16):
    """데이터 기반 필드 풀 — 도메인 활동 주체(하드코딩 buyer 대체). 색=momentum(가속 BLUE/냉각 GRAY), (학계) 태그."""
    from matplotlib.patches import Patch
    pool = [p for p in (data or {}).get("field_pool", []) if p.get("kind") != "academic"][:top]
    if not pool:
        return _empty("필드 풀 없음 — 키워드 확인")
    pool = pool[::-1]

    def lab(p):
        return p["company"].replace(", Inc.", "").replace(" Inc.", "").replace(" LLC", "").replace(" Ltd.", "")[:30]
    names = [lab(p) for p in pool]
    vals = [p["n_patents"] for p in pool]
    tcol = {"가속": BLUE, "냉각": GRAY, "유지": LGRAY}
    cols = [tcol.get(p.get("trend"), LGRAY) for p in pool]
    fig, ax = plt.subplots(figsize=(10, 0.6 + 0.42 * len(pool)), dpi=190)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    ax.barh(range(len(pool)), vals, color=cols)
    xmax = max(vals) or 1
    for i, p in enumerate(pool):
        ax.text(vals[i] + xmax * 0.01, i, p.get("trend", ""), va="center",
                fontsize=7.5, color=tcol.get(p.get("trend"), GRAY))
    ax.set_yticks(range(len(pool))); ax.set_yticklabels(names, fontsize=10, color=BLACK)
    ax.set_xlabel("도메인 anchor 인용 특허 수 (활동 규모)", fontsize=11, color=BLACK)
    ax.tick_params(axis="x", labelsize=11, colors=BLACK)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend(handles=[Patch(color=BLUE, label="가속"), Patch(color=GRAY, label="냉각"),
                       Patch(color=LGRAY, label="유지")], fontsize=8, loc="lower right",
              frameon=False, title="momentum")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_xlim(0, xmax * 1.18); fig.tight_layout()
    return fig


def field_heat_fig(data):
    """타깃 필드 열기 곡선 — 도메인 인용 특허 수/년(검증·과열 추세)."""
    heat = (data or {}).get("field_heat", {})
    if not heat:
        return _empty("필드 열기 데이터 없음")
    yrs = sorted(int(y) for y in heat)
    vals = [heat[str(y)] for y in yrs]
    fig, ax = plt.subplots(figsize=(9, 3.0), dpi=190)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    ax.fill_between(yrs, vals, color=BLUE, alpha=0.16)
    ax.plot(yrs, vals, color=BLUE, lw=2.2, marker="o", ms=5)
    ax.set_xlabel("출원(filing) 연도", fontsize=11, color=BLACK)
    ax.set_ylabel("도메인 인용 특허 수 / 년", fontsize=11, color=BLACK)
    ax.set_title("타깃 필드 열기 곡선 (검증·과열 추세)", fontsize=12, fontweight="bold", color=BLACK, pad=10)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=11, colors=BLACK)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.margins(x=0.02); fig.tight_layout()
    return fig


def competition_ladder_fig(data):
    """경쟁 서열 맵 — 기전 동일 시 개발 단계로 줄세우기(co-citation Jaccard network 대체).
    타깃 강조(파랑 ★), 활성 경쟁사(회색), 이전세대 실패/중단(빨강 X). data=_competition."""
    STAGE_X = {"중단": -1.2, "전임상": 0, "Preclinical": 0, "IND": 1, "IND (Phase 1)": 1,
               "Phase 1": 2, "Ph1": 2, "Phase 2": 3.5, "Ph2": 3.5, "Phase 3": 5, "Ph3": 5,
               "Market": 6.5, "승인": 6.5, "시판": 6.5}
    xof = lambda s: STAGE_X.get(s, 0)
    players = list((data or {}).get("players", []))
    prior = [dict(p, _prior=True) for p in (data or {}).get("prior_gen", [])]
    rows = players + prior
    if not rows:
        return _empty("경쟁 서열 데이터 없음 (임상단계 enrichment 필요)")
    rows = sorted(rows, key=lambda r: xof(r.get("stage")))  # 아래=초기, 위=선두
    n = len(rows)
    fig, ax = plt.subplots(figsize=(10.5, 0.7 + 0.52 * n), dpi=190)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    for i, r in enumerate(rows):
        x = xof(r.get("stage"))
        tgt, pg = r.get("is_target"), r.get("_prior")
        col = BLUE if tgt else ("#E8544B" if pg else GRAY)
        ax.plot([-1.35, x], [i, i], color=SOFT, lw=1, zorder=1)
        ax.scatter(x, i, s=(340 if tgt else 150), c=col, edgecolors="white", lw=1.4,
                   marker=("X" if pg else "o"), zorder=3)
        lbl = _disp(f"{r['company']} ({r.get('asset', '')})") + ("  ★자산" if tgt else "")
        ax.text(-1.5, i, lbl, ha="right", va="center", fontsize=9.6,
                color=(BLUE if tgt else BLACK), fontweight=("bold" if tgt else "normal"))
        if r.get("note"):
            ax.text(x + 0.18, i, _disp(r["note"]), va="center", fontsize=8.8, color=BLACK)
    ax.set_yticks([]); ax.set_ylim(-0.7, n - 0.3)
    ticks = [("중단", -1.2), ("전임상", 0), ("Ph1", 2), ("Ph2", 3.5), ("Ph3", 5), ("시판", 6.5)]
    ax.set_xticks([t[1] for t in ticks]); ax.set_xticklabels([t[0] for t in ticks], fontsize=11, color=BLACK)
    ax.set_xlim(-3.4, 8.2)
    ax.set_xlabel("개발 단계 →  (오른쪽=앞선 경쟁)", fontsize=11, color=BLACK)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    return fig
