# coding: utf-8
"""
BERA BD — 스냅샷 시각화 대시보드 (공개 배포).

★엔진 코드(스코어러·gather·DB 접속=moat) 미포함. sanitized 분석 스냅샷만 읽어 시각화한다.
라이브 계산 없음 → 가볍고 코드 노출 없음. 의존: streamlit·pandas·matplotlib(viz.py)·networkx.

로컬:  streamlit run app.py
배포:  Streamlit Community Cloud (public). 데이터=data/<asset>/ (meta.json + 스냅샷).
"""
import glob
import io
import json
import os

import pandas as pd
import streamlit as st

import viz  # 같은 폴더 (matplotlib, 엔진 무관)

st.set_page_config(page_title="BERA BD", layout="wide", page_icon="🧬")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
BLUE = "#3E83FF"
GRADE_BADGE = {"FACT": "🟢 FACT(웹출처)", "REC": "🔵 REC(엔진권고)", "EST": "🟡 EST(추정)"}


@st.cache_data(show_spinner=False)
def discover():
    out = {}
    for mp in sorted(glob.glob(os.path.join(DATA, "*", "meta.json"))):
        try:
            meta = json.load(io.open(mp, encoding="utf-8"))
        except Exception:
            continue
        meta["_dir"] = os.path.dirname(mp)
        out[meta.get("asset", os.path.basename(meta["_dir"]))] = meta
    return out


def _csv(d, name):
    p = os.path.join(d, name)
    return pd.read_csv(p) if os.path.exists(p) else None


def _json(d, name):
    p = os.path.join(d, name)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else None


@st.cache_data(show_spinner=False)
def _ob():
    p = os.path.join(HERE, "ob_patent_index.json")
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {}


def cliff_rows(d):
    """cliff_detail.json + OB 인덱스 → OB 오버레이(DS 원천특허·실만료일·약물명). 엔진 불요."""
    dd = _json(d, "cliff_detail.json")
    if not dd:
        return []
    ob = _ob()
    flat = []
    for comp, rows in dd.get("cliff", {}).items():
        for r in rows:
            pid = str(r["patent_id"])
            row = {"company": comp, "patent_id": r["patent_id"], "title": r.get("title", ""),
                   "est_expiry": r.get("est_expiry", ""), "cites": r.get("cites", 0),
                   "ob_ds": False, "ob_drug": "", "source": "근사(출원+20)"}
            o = ob.get(pid)
            if o:
                row["ob_ds"] = bool(o.get("ds")); row["ob_drug"] = o.get("brand") or ""
                exp = o.get("expiry") or ""
                if exp and exp != "-":
                    row["est_expiry"] = exp
                row["source"] = ("OB 원천특허(DS)" if o.get("ds") else
                                 ("OB 제형(DP)" if o.get("dp") else "OB 등재"))
            flat.append(row)
    flat.sort(key=lambda r: (not r["ob_ds"], -int(r["cites"] or 0), str(r["patent_id"])))
    return flat[:15]


# ── UI ──
st.title("🧬 BERA BD — 스냅샷 대시보드")
st.caption("커밋된 분석 스냅샷 시각화(라이브 계산·DB 없음). 초안(draft) — 미팅급은 큐레이션 필요.")
assets = discover()
if not assets:
    st.error("data/ 자산 없음."); st.stop()

with st.sidebar:
    st.header("자산")
    asset = st.selectbox("분석 자산", list(assets))
    m = assets[asset]; d = m["_dir"]

st.subheader(asset)
with st.expander("📖 용어 설명 — 처음이면 펼쳐보세요"):
    st.markdown("""
- **AoI**(타겟기업 관심도) = need(원천특허 만료=다급) + citation(우리 기술 인용=관심) + clinical(활성 임상=상용화 핏).
- **LO score**: 라이선스-인 후보(gap·interest·activity). **angle**: Co-dev(기전 역량) vs LO(gap).
- **Momentum**: 추세(가속/냉각). **Cross-modality**: 같은 적응증, 다른 모달리티 상업사.
- **Patent Cliff**: 바이어 원천특허 만료(★=FDA Orange Book 검증 실만료·약물명 / ○=출원+20 근사).
- **grade**: 🟢FACT · 🔵REC · 🟡EST.""")

tab_brief, tab_p, tab_ci = st.tabs(["📄 자산 개요", "🤝 파트너링 대상 발굴", "🔬 CI 분석"])

with tab_brief:
    nar = _json(d, "narrative.json") or {}
    for title in [k for k in nar if not k.startswith("_")]:
        s = nar[title]; g = s.get("grade")
        st.markdown(f"### {title}" + (f"  ·  {GRADE_BADGE.get(g, g)}" if g else ""))
        if s.get("keymsg"):
            st.info(s["keymsg"])
        if s.get("cards"):
            cc = st.columns(2)
            for i, card in enumerate(s["cards"]):
                with cc[i % 2]:
                    st.markdown(f"**{card[0]}**"); st.caption(card[1])
        for b in s.get("body", []):
            st.markdown(f"- {b}")
        st.divider()

with tab_p:
    aoi = _csv(d, "aoi_output.csv")
    if aoi is not None:
        st.markdown("**Revealed AoI — 파트너 타깃 랭킹**")
        c1, c2 = st.columns([3, 2])
        with c1:
            st.dataframe(aoi, hide_index=True, use_container_width=True)
        with c2:
            st.bar_chart(aoi.set_index("company")["aoi_score"], color=BLUE, horizontal=True)
        st.pyplot(viz.aoi_contrib_fig(aoi.to_dict("records"), m.get("weights", {})))
        st.caption("⚠️ need·citation은 volume비례→대형사 편중. raw top vs precedent Lead(개요 전략권고)와 함께 볼 것.")
    lo = _csv(d, "lo_output.csv")
    if lo is not None:
        st.divider(); st.markdown("**License-Out Buyer 랭킹**")
        lc1, lc2 = st.columns([2, 3])
        with lc1:
            st.dataframe(lo, hide_index=True, use_container_width=True)
        with lc2:
            st.pyplot(viz.lo_candidates_fig(lo.to_dict("records")))
    ang = _csv(d, "angle_output.csv")
    if ang is not None:
        st.markdown("**Anchor Signature Angle — LO vs Co-dev**")
        st.pyplot(viz.angle_venn_fig(ang.to_dict("records"), aoi.to_dict("records") if aoi is not None else None))
    mom, cmom = _json(d, "momentum.json"), _json(d, "clinical_momentum.json")
    if mom or cmom:
        st.divider(); st.markdown("### 📈 Momentum — 가속/냉각 (추세)")
        if mom:
            st.markdown("**특허 anchor 인용**"); st.pyplot(viz.momentum_fig(mom.get("momentum", [])))
        if cmom:
            st.markdown("**임상 시험 개시**"); st.pyplot(viz.momentum_fig(cmom.get("momentum", [])))
    acc = _csv(d, "access_output.csv")
    if acc is not None:
        st.divider(); st.markdown("**Specialty Access (G3) — 상업화 준비도**")
        ac1, ac2 = st.columns([2, 3])
        with ac1:
            st.dataframe(acc, hide_index=True, use_container_width=True)
        with ac2:
            st.pyplot(viz.access_fig(acc.to_dict("records")))
    bd = _json(d, "bd_trend.json")
    if bd:
        st.divider(); st.markdown("**BD 시장 추세 — LO/M&A 딜 빈도·규모**")
        st.pyplot(viz.bd_trend_fig(bd))
    deals = _json(d, "lo_comparables.json")
    if deals and deals.get("lo_comparables"):
        st.divider(); st.markdown("**Comparable License-Out 딜 — 경제성 벤치**")
        st.dataframe(pd.DataFrame(deals["lo_comparables"]), hide_index=True, use_container_width=True)

with tab_ci:
    ta = m.get("ta_label", "")
    st.markdown(f"**Patent Cliff — 원천특허 만료** (★=OB 검증 실만료·약물명 / ○=근사) · TA 「{ta}」")
    cr = cliff_rows(d)
    if cr:
        drugs = [(r["ob_drug"], r["company"], r["est_expiry"]) for r in cr if r.get("ob_ds") and r.get("ob_drug")]
        if drugs:
            st.markdown("**OB 검증 = 어떤 약(API)의 cliff:** " +
                        "  ·  ".join(f"**{x}** ({c},~{e})" for x, c, e in drugs[:12]))
            st.caption("↑ 자산 타깃과 실제 관련되는 약의 만료가 진짜 BD 기회(무관 약=broad-TA 노이즈).")
        st.pyplot(viz.cliff_timeline_fig(cr, (2026, 2031)))
        with st.expander("cliff 상세 표"):
            st.dataframe(pd.DataFrame(cr)[["company", "ob_drug", "patent_id", "est_expiry", "cites", "source"]],
                         hide_index=True, use_container_width=True)
    else:
        st.info("cliff 스냅샷 없음.")
    coc = _json(d, "cocitation.json")
    if coc:
        st.divider(); st.markdown("**Co-citation — 경쟁 vs 상호보완**")
        if float(coc.get("target_max_jaccard") or coc.get("yuhan_max_jaccard") or 0) < 0.003:
            st.warning("⚠️ 타깃 특허 풋프린트 희박(초기사) → 상위 노드는 키워드노이즈 가능, 참고용.")
        st.pyplot(viz.cocitation_network_fig(coc, asset.split("(")[0].split()[0][:12]))
    kr = _json(d, "kr_tiers.json")
    if kr:
        st.divider(); st.markdown("**KR 경쟁 3-tier**")
        opt = st.segmented_control("티어", ["전체", "Tier1", "Tier2", "Tier3"], default="전체",
                                   key=f"kr_{asset}", label_visibility="collapsed")
        st.pyplot(viz.kr_tier_fig(kr.get("kr_tiers", []), tier_filter={"Tier1": 1, "Tier2": 2, "Tier3": 3}.get(opt)))
    cm = _json(d, "crossmod.json")
    if cm:
        st.divider()
        st.markdown(f"**Cross-modality 경쟁·co-dev — 적응증 「{ta}」, 다른 모달리티** (상업사)")
        if m.get("indications_display"):
            st.caption(f"적응증: {m['indications_display']}")
        st.pyplot(viz.crossmod_fig(cm))

st.divider()
st.caption("BERA BD · 스냅샷 시각화 전용(엔진 코드 미포함) · 초안, 미팅급은 큐레이션 필요")
