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
def explain_box(what, how, message):
    """분석 친절 해설 — 무엇을/어떻게/그래서. 비전문가도 파악."""
    with st.container(border=True):
        st.markdown(f"📥 **뭘 분석했나** — {what}")
        st.markdown(f"⚙️ **어떻게** — {how}")
        st.markdown(f"💡 **그래서 (메시지)** — {message}")


st.title("🧬 BERA BD — 스냅샷 대시보드")
st.caption("커밋된 분석 스냅샷 시각화(라이브 계산·DB 없음). 초안(draft) — 미팅급은 큐레이션 필요.")
assets = discover()
if not assets:
    st.error("data/ 자산 없음."); st.stop()

with st.sidebar:
    st.header("분석 자산")
    st.caption("자산을 눌러 선택")
    names = list(assets)
    if st.session_state.get("asset") not in assets:
        st.session_state["asset"] = names[0]
    for name in names:
        label = name.split("(")[0].strip()  # 짧은 이름(괄호 앞)
        cur = name == st.session_state["asset"]
        if st.button(label, key=f"pick_{name}", width="stretch",
                     type=("primary" if cur else "secondary")):
            st.session_state["asset"] = name
            st.rerun()
    asset = st.session_state["asset"]
    m = assets[asset]; d = m["_dir"]

st.subheader(asset)

# ── 종합 판단 (Thesis) — 신호를 묶은 판단·권고 (데이터 있을 때만) ──
_nar_top = _json(d, "narrative.json") or {}
_th = _nar_top.get("_thesis")
if _th:
    st.markdown("### 🎯 종합 판단 (Thesis) — 신호를 묶은 판단·권고")
    with st.container(border=True):
        if _th.get("situation"):
            st.markdown(f"**① 상황** &nbsp; {_th['situation']}")
        if _th.get("insight"):
            st.success(f"💡 **② 핵심 인사이트** &nbsp; {_th['insight']}")
        if _th.get("lo_play"):
            st.markdown(f"**③ LO play — 누구·왜·언제** &nbsp; {_th['lo_play']}")
        if _th.get("risk"):
            st.markdown(f"**④ 핵심 리스크** &nbsp; {_th['risk']}")
        if _th.get("evidence"):
            st.caption("근거 신호: " + "　·　".join(_th["evidence"]))
    st.caption("↑ 이게 결론. 아래는 이 판단의 근거. (초안 — 애널리스트 검수)")
    st.divider()

with st.expander("📖 용어 설명 — 처음이면 펼쳐보세요"):
    st.markdown("""
- **AoI**(타겟기업 관심도) = need(원천특허 만료=다급) + citation(우리 기술 인용=관심) + clinical(활성 임상=상용화 핏).
- **LO score**: 라이선스-인 후보(gap·interest·activity). **angle**: Co-dev(기전 역량) vs LO(gap).
- **Momentum**: 추세(가속/냉각). **Cross-modality**: 같은 적응증, 다른 모달리티 상업사.
- **Patent Cliff**: 바이어 원천특허 만료(★=FDA Orange Book 검증 실만료·약물명 / ○=출원+20 근사).
- **grade**: 🟢FACT · 🔵REC · 🟡EST.""")

st.header("📄 자산 개요")
with st.container():
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

st.divider()
st.header("🤝 파트너링 대상 발굴")
with st.container():
    # 다에셋 회사: 라이브 자산(트랙)마다 기전·적응증이 달라 파트너 후보를 별도 발굴
    _pn = _nar_top.get("_competition") or {}
    _ptracks = [t for t in (_pn.get("tracks") or []) if t.get("partnering")]
    if _ptracks:
        st.markdown("### 🎯 자산별 파트너 후보 — 트랙마다 기전·적응증이 달라 별도 발굴")
        st.caption("이 회사는 라이브 자산이 서로 다른 필드에 있어 하나의 풀로 못 묶음. "
                   "자산(트랙)별로 ①그 기전에 특허 활동하는 상업사 ②그 적응증에 임상 개시하는 sponsor를 각각 데이터로 발굴.")
        for _t in _ptracks:
            _pt = _t["partnering"]
            st.markdown(f"#### ▸ {_t.get('asset', '')}")
            _fk = ", ".join(_pt.get("field_pool_kw", []))
            _pool = _pt.get("field_pool", [])
            _hot = [x["company"].replace(", Inc.", "").replace(" Inc.", "")
                    for x in _pool if x.get("kind") == "company" and x.get("trend") == "가속"][:5]
            explain_box(
                what=f"「{_fk}」 기전에 실제 특허 활동하는 상업사를 데이터로 발굴(학계 제외).",
                how="○ 직전/년 → ● 최근/년(anchor 인용) 덤벨. **파랑=가속(이 영역 데워짐=LO 타이밍)/회색=냉각**.",
                message=f"지금 가속 중 = {', '.join(_hot) or '없음'} → 우선 접근 후보.")
            st.pyplot(viz.momentum_fig([x for x in _pool if x.get("kind") != "academic"]))
            _ind = _pt.get("clinical_ind", "")
            _clin = _pt.get("clinical_momentum", [])
            if _clin:
                st.markdown(f"**📈 임상 개시 추세 — 「{_ind}」** (이 적응증에 임상 연 전체 INDUSTRY sponsor, ct.gov · *특허와 다른 축*)")
                st.pyplot(viz.momentum_fig(_clin))
            st.divider()

    fpool = _json(d, "field_pool.json")
    if fpool and fpool.get("field_pool") and not _ptracks:
        _fk = ", ".join(fpool.get("meta", {}).get("keywords", []))
        _hot = [x["company"].replace(", Inc.", "").replace(" Inc.", "")
                for x in fpool["field_pool"] if x.get("kind") == "company" and x.get("trend") == "가속"][:5]
        st.markdown("### 🎯 특허 모멘텀 기반 파트너 후보")
        explain_box(
            what=f"「{_fk}」 기전에 실제 특허 활동하는 상업사를 데이터로 발굴(소형 바이오텍 포함, 학계 제외).",
            how="○ 직전 평균/년(anchor 인용) → ● 최근 평균/년 덤벨. **파랑=가속(LO 타이밍)/회색=냉각**. 규모+추세를 한 그래프에.",
            message=f"지금 가속 중 = {', '.join(_hot) or '없음'} → 우선 접근 후보.")
        st.pyplot(viz.momentum_fig([x for x in fpool.get("field_pool", []) if x.get("kind") != "academic"]))
        st.divider()
    # 임상 momentum — 데이터기반(적응증 전체 sponsor). 특허 momentum과 다른 축
    cfm = _json(d, "clinical_field_momentum.json")
    if cfm and cfm.get("momentum") and not _ptracks:
        _inds = " · ".join(cfm.get("meta", {}).get("indications", []))
        st.markdown("### 📈 임상 시험 개시 추세 (가속/냉각) — *특허* momentum과 다른 축")
        explain_box(
            what=f"적응증 **「{_inds}」**에 임상시험을 개시한 **전체 INDUSTRY sponsor**({cfm.get('meta', {}).get('n_sponsors', 0)}곳, ct.gov)의 추세. 특허 momentum(위 막대 색)과 다른 임상 축.",
            how="○ 직전 → ● 최근(임상 개시 건수) 덤벨. 파랑=임상 데워짐, 회색=냉각. ★14곳 아니라 적응증 검색=전체 sponsor 데이터기반.",
            message=f"「{_inds}」에서 지금 임상 가속 중 = 이 병에 진심. 특허(위)+임상(여기) 둘 다 가속이면 최우선.")
        st.pyplot(viz.momentum_fig(cfm.get("momentum", [])))
        st.divider()
    with st.expander("구 엔진 스코어 (하드코딩 14곳 · AoI/LO/angle) — 참고용, 데이터 풀이 대체"):
        st.caption("⚠️ 하드코딩 14 buyer 기준이라 분석 타깃과 연관 약하고 대형사 편중. 위 데이터 풀이 대체.")
        aoi = _csv(d, "aoi_output.csv")
        if aoi is not None:
            st.markdown("**Revealed AoI (14곳)**"); st.dataframe(aoi, hide_index=True, width="stretch")
        lo = _csv(d, "lo_output.csv")
        if lo is not None:
            st.markdown("**License-Out Buyer 랭킹 (14곳)**"); st.dataframe(lo, hide_index=True, width="stretch")
        ang = _csv(d, "angle_output.csv")
        if ang is not None:
            st.markdown("**Anchor Signature Angle (14곳)**")
            st.pyplot(viz.angle_venn_fig(ang.to_dict("records"), aoi.to_dict("records") if aoi is not None else None))
    acc = _csv(d, "access_output.csv")
    if acc is not None:
        st.divider(); st.markdown("**Specialty Access (G3) — 상업화 준비도**")
        ac1, ac2 = st.columns([2, 3])
        with ac1:
            st.dataframe(acc, hide_index=True, width="stretch")
        with ac2:
            st.pyplot(viz.access_fig(acc.to_dict("records")))
    bd = _json(d, "bd_trend.json")
    if bd:
        st.divider(); st.markdown("**BD 시장 추세 — LO/M&A 딜 빈도·규모**")
        st.pyplot(viz.bd_trend_fig(bd))
    deals = _json(d, "lo_comparables.json")
    if deals and deals.get("lo_comparables"):
        st.divider(); st.markdown("**Comparable License-Out 딜 — 경제성 벤치**")
        st.dataframe(pd.DataFrame(deals["lo_comparables"]), hide_index=True, width="stretch")

st.divider()
st.header("🔬 CI 분석")
with st.container():
    _comp = _nar_top.get("_competition")
    if _comp and (_comp.get("players") or _comp.get("tracks")):
        st.markdown("### 🏁 경쟁 서열 — 기전 × 개발 단계 (누가 앞섰나)")
        explain_box(
            what="이 자산과 같은 기전의 실제 경쟁 자산을 개발 단계로 줄세움 (웹 검증·큐레이션).",
            how="X축=개발 단계(오른쪽=앞섬), ★파랑=우리 자산, 회색=활성 경쟁, 빨강X=이전세대 실패/중단. "
                "co-citation Jaccard가 아니라 '누가 실제로 앞서 있나'를 직접.",
            message="선두·차별화·타이밍이 한눈에. **다에셋 회사는 에셋마다 타깃·경쟁이 달라 ▸별로 분리** 표시.")
        for _t in (_comp.get("tracks") or [_comp]):
            if _t.get("asset"):
                st.markdown(f"**▸ {_t['asset']}**" + (f"  ·  {_t['axis']}" if _t.get("axis") else ""))
            elif _t.get("axis"):
                st.caption(_t["axis"])
            st.pyplot(viz.competition_ladder_fig(_t))
            if _t.get("excluded"):
                st.caption("제외: " + "　·　".join(f"{e['company']} — {e['reason']}" for e in _t["excluded"]))
        st.divider()
    _fp_ci = _json(d, "field_pool.json")
    if _fp_ci and _fp_ci.get("field_heat"):
        st.markdown("### 🌡️ 타깃 필드 열기 — 검증·과열 추세 (데이터 기반)")
        st.pyplot(viz.field_heat_fig({"field_heat": _fp_ci["field_heat"]}))
        st.divider()
    ta = m.get("ta_label", "")
    with st.expander("🔒 Patent Cliff (구 · 하드코딩 14곳 · broad-TA 노이즈) — 참고용", expanded=False):
        st.caption("⚠️ AoI/LO처럼 하드코딩 14 buyer 기준 + broad-TA라 자산 무관 약(예: TRINTELLIX=Lundbeck 항우울제)도 "
                   "섞이는 약한 신호. '바이어 원천특허 만료=파이프라인 공백' 가설 — 참고용. (★=OB 검증 실만료 / ○=근사)")
        cr = cliff_rows(d)
        if cr:
            drugs = [(r["ob_drug"], r["company"], r["est_expiry"]) for r in cr if r.get("ob_ds") and r.get("ob_drug")]
            if drugs:
                st.markdown("**OB 검증 = 어떤 약(API)의 cliff:** " +
                            "  ·  ".join(f"**{x}** ({c},~{e})" for x, c, e in drugs[:12]))
            st.pyplot(viz.cliff_timeline_fig(cr, (2026, 2031)))
            st.dataframe(pd.DataFrame(cr)[["company", "ob_drug", "patent_id", "est_expiry", "cites", "source"]],
                         hide_index=True, width="stretch")
        else:
            st.caption("cliff 스냅샷 없음.")
    # co-citation(Jaccard 네트워크) 제거 — 초기 한국자산엔 대부분 빈칸/독자공간이라 무의미(사용자 피드백).
    #   경쟁지형 = 위 '경쟁 서열' + 아래 3개(KR발굴/3-tier/Cross-modality)로 대체.
    krc = _json(d, "kr_cocitation.json")
    if krc and krc.get("kr_competitors"):
        st.divider(); st.markdown("### 🇰🇷 KR 경쟁사 발굴 — 같은 기전을 KR 특허에 쓰는 회사")
        _kw = ", ".join(krc.get("meta", {}).get("keywords", []))
        st.caption(f"질문: 이 기전(「{_kw}」)을 KR 특허에 실제 쓰는 회사가 누구? = 국내+한국출원 글로벌 직접 경쟁. "
                   f"자사 {krc.get('self_count', 0)}건 · {krc.get('n_companies', 0)}개사. 빨강=국내/파랑=해외.")
        st.pyplot(viz.kr_cocitation_fig(krc))
    kr = _json(d, "kr_tiers.json")
    if kr:
        st.divider(); st.markdown("### 🇰🇷 KR 3-tier — 기술 분류(IPC)로 본 국내 경쟁 계층")
        _ipc = " · ".join(f"{k}({', '.join(v)})" for k, v in (m.get("kr_domains") or {}).items())
        st.caption(f"질문: 기전 키워드 아니라 **기술 분류(IPC)**로 봤을 때 국내 경쟁 계층? Tier1 직접/Tier2 인접/Tier3 다른 modality(=잠재 co-dev). "
                   f"위 'KR 발굴'(키워드)과 달리 넓은 기술지형." + (f"　★사용 IPC: {_ipc}" if _ipc else ""))
        opt = st.segmented_control("티어", ["전체", "Tier1", "Tier2", "Tier3"], default="전체",
                                   key=f"kr_{asset}", label_visibility="collapsed")
        st.pyplot(viz.kr_tier_fig(kr.get("kr_tiers", []), tier_filter={"Tier1": 1, "Tier2": 2, "Tier3": 3}.get(opt),
                                  domains=list((m.get("kr_domains") or {}).keys())))
    cm = _json(d, "crossmod.json")
    if cm:
        st.divider()
        st.markdown(f"**Cross-modality 경쟁·co-dev — 적응증 「{ta}」, 다른 모달리티** (상업사)")
        if m.get("indications_display"):
            st.caption(f"적응증(좁힘 질환/타깃): {m['indications_display']}")
        st.pyplot(viz.crossmod_fig(cm))
        _cmm = cm.get("meta", {})
        st.caption(f"자산 모달리티={_cmm.get('own_modality')} → **다른 모달리티**"
                   f"({', '.join(_cmm.get('other_modalities', []))})로 위 적응증을 치는 상업사. "
                   f"cocitation(같은 인용공간)·KR(IPC)이 못 잡는 축 = 경쟁 위협이자 잠재 co-dev"
                   f"(예: 소분자 자산인데 CAR-T/ADC로 같은 병 치는 회사).")
        with st.expander("cross-modality 상세 표"):
            st.dataframe(pd.DataFrame([{"회사": r["company"], "건수": r["n_patents"],
                                        "모달리티": " · ".join(r.get("modalities", []))}
                                       for r in cm.get("crossmod", [])]),
                         hide_index=True, width="stretch")

st.divider()
st.caption("BERA BD · 스냅샷 시각화 전용(엔진 코드 미포함) · 초안, 미팅급은 큐레이션 필요")
