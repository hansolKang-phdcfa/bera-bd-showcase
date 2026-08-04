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
import re

import pandas as pd
import streamlit as st

import viz  # 같은 폴더 (matplotlib, 엔진 무관)
import viz_px  # Plotly 인터랙티브 버전 (드래그/핀치 줌)
import company_class as ccls  # 회사 카테고리·시총 tier 색 (그래프 공통 범례) — cc는 st.columns에서 이미 씀

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
_BULLETS = "①②③④⑤⑥⑦⑧⑨⑩"


def _md(s):
    """표시용 정규화 — $→'USD ', 근사 '~'(앞 공백/'('/시작)→'약 ', 범위 '~'→'-'."""
    s = str(s).replace("$", "USD ")
    s = re.sub(r"(?:^|(?<=[\s(]))~", "약 ", s)
    s = s.replace("~", "-")
    return re.sub(r"USD +", "USD ", s)


def _para(s):
    """thesis/keymsg 렌더 — 개조식(명시적 줄바꿈)은 구조 보존, 구형 telegraphic은 문장·번호·★ 단위 자동 줄바꿈."""
    s = _md(s)
    if "\n" in s:
        return s.strip()
    for b in _BULLETS:
        s = s.replace(b, "\n\n" + b)
    s = s.replace("★", "\n\n★")
    s = re.sub(r"(?<=[.。])\s+(?=\S)", "\n\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _bd(s):
    """본문(body) 항목 — 항목 안의 ★ 앞에서 같은 항목 내 줄바꿈(하드 브레이크)."""
    return re.sub(r"(?<=\S)\s*★", "  \n★", _md(s))


def _px(fig):
    """인터랙티브 차트 렌더 — 드래그 박스줌·스크롤줌·모바일 핀치 지원."""
    st.plotly_chart(fig, use_container_width=True, config=viz_px.PX_CONFIG)


def explain_box(what, how, message):
    """분석 친절 해설 — 무엇을/어떻게/그래서. 비전문가도 파악."""
    with st.container(border=True):
        st.markdown(f"📥 **뭘 분석했나** — {what}")
        st.markdown(f"⚙️ **어떻게** — {how}")
        st.markdown(f"💡 **그래서 (메시지)** — {message}")


def _pool_msg(hot):
    """가속 상업사 유무로 파트너 후보 메시지 분기 — 빈 필드는 white-space로 프레이밍."""
    if hot:
        return f"현재 가속 중인 곳은 {', '.join(hot)}이며, 우선 접근 후보로 볼 수 있음."
    return ("지금 가속 중인 상업사가 없음 = 이 기전은 특허 활동이 얇은 white space임"
            "(크라우딩 없음의 이점이자, 활성 파트너가 드물다는 경고). "
            "이 자산은 momentum보다 종합 판단(thesis)·경쟁 지형으로 봐야 함.")


def _match_domain(match, *, max_each=8):
    """gather match dict(indication/modality/mechanism_like, %와일드카드) → 읽기 좋은 도메인 라벨.
    한인수 점1: BD 추세·비교딜이 '정확히 어느 시장(도메인)의 historical BD냐' 병기용."""
    if not match:
        return ""
    parts = []
    for key, lab in (("mechanism_like", "기전"), ("indication_like", "적응증"), ("modality_like", "모달리티")):
        vals = [str(v).strip("%").strip() for v in (match.get(key) or []) if str(v).strip("%").strip()]
        if vals:
            parts.append(f"{lab}: {' · '.join(vals[:max_each])}")
    return "  |  ".join(parts)


st.title("🧬 BERA BD — 파트너링 분석 대시보드")
st.caption("자산별 파트너 후보·경쟁 지형·라이선스 비교를 특허·임상·딜 데이터로 발굴합니다.")
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
    st.caption("이 자산에 대한 결론. 아래는 이 판단을 뒷받침하는 근거입니다.")
    with st.container(border=True):
        if _th.get("situation"):
            st.markdown("**①  지금 상황**")
            st.markdown(_para(_th["situation"]))
            st.markdown("")
        if _th.get("insight"):
            st.markdown("**②  핵심 인사이트**")
            st.success(_para(_th["insight"]))
        if _th.get("lo_play"):
            st.markdown("**③  그래서 딜은 — 누구·왜·언제**")
            st.markdown(_para(_th["lo_play"]))
            st.markdown("")
        if _th.get("risk"):
            st.markdown("**④  핵심 리스크**")
            st.markdown(_para(_th["risk"]))
        if _th.get("evidence"):
            with st.expander("📎 근거 신호 (아래 분석에서 확인)"):
                for e in _th["evidence"]:
                    st.markdown(f"- {_md(e)}")
    st.divider()

with st.expander("📖 용어 설명 — 처음이면 펼쳐보세요"):
    st.markdown("""
- **AoI**(타겟기업 관심도) = need(원천특허 만료=다급) + citation(우리 기술 인용=관심) + clinical(활성 임상=상용화 핏).
- **LO score**: 라이선스-인 후보(gap·interest·activity). **angle**: Co-dev(기전 역량) vs LO(gap).
- **Momentum**: 추세(가속/냉각). **Cross-modality**: 같은 적응증, 다른 모달리티 상업사.
- **Patent Cliff**: 바이어 원천특허 만료(★=FDA Orange Book 검증 실만료·약물명 / ○=출원+20 근사).""")

st.header("📄 자산 개요")
with st.container():
    nar = _json(d, "narrative.json") or {}
    for title in [k for k in nar if not k.startswith("_")]:
        s = nar[title]; g = s.get("grade")
        st.markdown(f"### {title}")
        if s.get("keymsg"):
            st.info(_para(s["keymsg"]))
        if s.get("cards"):
            cc = st.columns(2)
            for i, card in enumerate(s["cards"]):
                with cc[i % 2]:
                    st.markdown(f"**{_md(card[0])}**"); st.caption(_para(card[1]))
        for b in s.get("body", []):
            st.markdown(f"- {_bd(b)}")
        st.divider()

st.divider()
st.header("🤝 파트너링 대상 발굴")
with st.container():
    # 다에셋 회사: 라이브 자산(트랙)마다 기전·적응증이 달라 파트너 후보를 별도 발굴
    _pn = _nar_top.get("_competition") or {}
    _ptracks = [t for t in (_pn.get("tracks") or []) if t.get("partnering")]
    if _ptracks:
        st.markdown("### 🎯 자산별 파트너 후보")
        st.caption("자산(트랙)마다 (1) 그 기전에 특허 활동하는 상업사와 (2) 그 적응증에 임상을 개시하는 sponsor를 각각 데이터로 발굴함. "
                   "회사명 앞 색점 = 회사 분류.")
        st.markdown(ccls.legend_html(), unsafe_allow_html=True)
        for _t in _ptracks:
            _pt = _t["partnering"]
            st.markdown(f"#### ▸ {_t.get('asset', '')}")
            _pool = _pt.get("field_pool", [])
            _hot = [x["company"].replace(", Inc.", "").replace(" Inc.", "")
                    for x in _pool if x.get("kind") == "company" and x.get("trend") == "가속"][:5]
            explain_box(
                what="이 자산의 기전에 실제로 특허 활동을 하는 상업사를 데이터로 발굴한 것임(학계·공공기관 제외).",
                how="각 회사의 연간 특허 활동을 직전(○)과 최근(●)으로 이어 표시함. 점이 오른쪽으로 갈수록 활동이 늘고 있다는 뜻이고, "
                    "파랑은 가속(이 영역이 활발해지는 중이며 라이선스 아웃 타이밍), 회색은 냉각임.",
                message=_pool_msg(_hot))
            _px(viz_px.momentum_px([x for x in _pool if x.get("kind") != "academic"]))
            _ind = _pt.get("clinical_ind", "")
            _clin = _pt.get("clinical_momentum", [])
            if _clin:
                st.markdown(f"**📈 임상 개시 추세 — 「{_ind}」** (이 적응증에 임상 연 전체 INDUSTRY sponsor, ct.gov · *특허와 다른 축*)")
                _px(viz_px.momentum_px(_clin))
            st.divider()

    fpool = _json(d, "field_pool.json")
    if fpool and fpool.get("field_pool") and not _ptracks:
        _hot = [x["company"].replace(", Inc.", "").replace(" Inc.", "")
                for x in fpool["field_pool"] if x.get("kind") == "company" and x.get("trend") == "가속"][:5]
        _kw = fpool.get("meta", {}).get("keywords", [])
        _kwlabel = " · ".join(_kw) if _kw else ta
        st.markdown("### 🎯 특허 모멘텀 기반 파트너 후보")
        st.caption(f"🔎 타깃 필드(anchor 인용 도메인) = **{_kwlabel}** — 이 도메인들을 인용한 제약 특허 주체를 발굴한 것임.")
        explain_box(
            what=f"이 자산의 기전(「{_kwlabel}」)에 실제로 특허 활동을 하는 상업사를 데이터로 발굴한 것임(소형 바이오텍 포함, 학계 제외).",
            how="각 회사의 연간 특허 활동을 직전 평균(○)과 최근 평균(●)으로 이어 표시함. ●가 오른쪽에 있고 클수록 활발하며, "
                "파랑은 가속(라이선스 아웃 타이밍), 회색은 냉각임. 활동 규모와 추세를 한 그래프에 담음. "
                "회사명 앞 색점 = 회사 분류(빅파마/바이오텍/스타트업/학계).",
            message=_pool_msg(_hot))
        st.markdown(ccls.legend_html(), unsafe_allow_html=True)
        _px(viz_px.momentum_px([x for x in fpool.get("field_pool", []) if x.get("kind") != "academic"]))
        st.divider()
    # 임상 momentum — 데이터기반(적응증 전체 sponsor). 특허 momentum과 다른 축
    cfm = _json(d, "clinical_field_momentum.json")
    if cfm and cfm.get("momentum") and not _ptracks:
        _inds = " · ".join(cfm.get("meta", {}).get("indications", []))
        st.markdown("### 📈 임상 시험 개시 추세 (가속/냉각) — *특허* momentum과 다른 축")
        explain_box(
            what=f"적응증 「{_inds}」에 임상시험을 개시한 전체 산업계 sponsor({cfm.get('meta', {}).get('n_sponsors', 0)}곳, ClinicalTrials.gov)의 추세임. "
                 "최근 3년과 직전 5년을 비교했으며, 위의 특허 모멘텀과는 다른 '임상' 축임.",
            how="각 sponsor의 연간 임상 개시 건수를 직전 평균(○)과 최근 평균(●)으로 이어 표시함. 파랑은 임상이 늘고 있는 곳, 회색은 줄고 있는 곳임. "
                "적응증 검색으로 잡은 전체 sponsor 기준임.",
            message=f"「{_inds}」에서 지금 임상을 늘리는 회사는 그만큼 이 질환에 집중하고 있다는 뜻임. 특허와 임상이 모두 가속 중이라면 최우선 접근 대상임.")
        _px(viz_px.momentum_px(cfm.get("momentum", [])))
        st.divider()
    with st.expander("참고 지표 — 대형 바이어 기준 스코어 (보조)"):
        st.caption("대형 바이어 고정 기준의 보조 스코어임 (참고용).")
        aoi = _csv(d, "aoi_output.csv")
        if aoi is not None:
            st.markdown("**Revealed AoI (대형 바이어)**"); st.dataframe(aoi, hide_index=True, width="stretch")
        lo = _csv(d, "lo_output.csv")
        if lo is not None:
            st.markdown("**License-Out Buyer 랭킹 (대형 바이어)**"); st.dataframe(lo, hide_index=True, width="stretch")
        ang = _csv(d, "angle_output.csv")
        if ang is not None:
            st.markdown("**Anchor Signature Angle (대형 바이어)**")
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
        _bddom = _match_domain(bd.get("meta", {}).get("match", {}))
        if _bddom:
            st.caption(f"📌 집계 시장(어떤 도메인의 historical BD인가) — {_bddom}  "
                       f"·  이 조건에 매칭된 lo_backtest 딜의 연도별 빈도·규모임(LO=라이선스·파트너십 / M&A=인수). "
                       "규모는 total 금액 있는 딜만(~17%)이라 빈도보다 표본 작음.")
        st.pyplot(viz.bd_trend_fig(bd))
    deals = _json(d, "lo_comparables.json")
    if deals and deals.get("lo_comparables"):
        st.divider(); st.markdown("**License-Out 딜 경제성 — 치료영역·단계 매칭 시장 벤치**")
        _lodom = _match_domain(deals.get("meta", {}).get("match", {}))
        if _lodom:
            st.caption(f"📌 매칭 도메인(어떤 시장의 비교딜인가) — {_lodom}")
        _lodf = pd.DataFrame(deals["lo_comparables"])
        _locols = [c for c in ["lo_date", "buyer", "seller", "indication", "stage",
                               "upfront_usd_m", "milestone_usd_m", "total_usd_m", "upfront_pct", "territory"]
                   if c in _lodf.columns]
        st.dataframe(_lodf[_locols] if _locols else _lodf, hide_index=True, width="stretch")
        st.caption("자산의 치료영역·개발단계에 매칭된 실제 LO 딜의 경제성임(선지급·마일스톤·총액·선지급 비중). "
                   "딜 본문에서 자동 인식된 개별 약물명·기전은 신뢰도가 낮아 표기하지 않음(특정 자산 comparable이 아니라 시장 단가 맥락). "
                   "헤드라인 총액보다 upfront 비중(구조)이 핵심임.")

st.divider()
st.header("🔬 CI 분석")
with st.container():
    _comp = _nar_top.get("_competition")
    if _comp and (_comp.get("players") or _comp.get("tracks")):
        st.markdown("### 🏁 경쟁 서열 — 기전 × 개발 단계 (누가 앞섰나)")
        explain_box(
            what="이 자산과 같은 기전의 실제 경쟁 자산을 개발 단계로 줄세움 (웹 검증·큐레이션).",
            how="X축은 개발 단계이며 오른쪽일수록 앞섬, ★파랑=우리 자산, 회색=활성 경쟁, 빨강X=이전세대 실패/중단. "
                "특허 인용망이 아니라 **'누가 실제로 앞서 있나'를 개발 단계로 직접** 배치.",
            message="한눈에 **선두가 누구인지, 우리 자산이 어디쯤인지, 이전세대가 왜 실패했는지**. "
                    "다에셋 회사는 자산마다 타깃·경쟁이 달라 ▸별로 분리해 보여줌.")
        st.markdown(ccls.legend_html(), unsafe_allow_html=True)
        for _t in (_comp.get("tracks") or [_comp]):
            if _t.get("asset"):
                st.markdown(f"**▸ {_md(_t['asset'])}**" + (f"  ·  {_md(_t['axis'])}" if _t.get("axis") else ""))
            elif _t.get("axis"):
                st.caption(_md(_t["axis"]))
            _px(viz_px.competition_ladder_px(_t))
            if _t.get("excluded"):
                st.caption("제외: " + "　·　".join(f"{_md(e['company'])} — {_md(e['reason'])}" for e in _t["excluded"]))
        st.divider()
    _fp_ci = _json(d, "field_pool.json")
    if _fp_ci and _fp_ci.get("field_heat"):
        _kw2 = _fp_ci.get("meta", {}).get("keywords", [])
        _kw2label = " · ".join(_kw2) if _kw2 else m.get("ta_label", "")
        st.markdown(f"### 🌡️ 타깃 필드 열기 — 「{_kw2label}」 인용 특허 추세")
        st.caption(f"타깃 필드 = anchor 인용 도메인 **{_kw2label}** (이 기전 키워드를 인용한 제약 특허 건수/년). "
                   "곡선이 오를수록 이 분야에 R&D·검증이 몰리는 중(과열), 평평/희박하면 white space.")
        _fh = _fp_ci["field_heat"]; _yrs = len(_fh); _tot = sum(_fh.values())
        if _yrs < 3:   # 데이터 희박 — 곡선 대신 안내
            st.info(f"이 기전을 인용한 제약 특허가 전 기간 통틀어 {_tot}건(연도 {_yrs}개)에 불과해 추세 곡선은 의미가 없음. "
                    "이 분야에 R&D가 거의 몰리지 않는다는 뜻으로, 경쟁자가 드문 white space 신호일 수 있음(반대로 아무도 못 푼 난제 영역일 수도 있으니 별도 판단 필요).")
        else:
            _px(viz_px.field_heat_px({"field_heat": _fh}))
        st.divider()
    ta = m.get("ta_label", "")
    with st.expander("🔒 Patent Cliff (참고용 · 고정 대형 바이어 · 광범위 TA 노이즈)", expanded=False):
        st.caption("⚠️ 위 참고 지표처럼 고정 대형 바이어 기준 + 광범위 TA라 자산 무관 약(예: TRINTELLIX=Lundbeck 항우울제)도 "
                   "섞이는 약한 신호. '바이어 원천특허 만료=파이프라인 공백' 가설 — 참고용. (★=OB 검증 실만료 / ○=근사)")
        cr = cliff_rows(d)
        if cr:
            drugs = [(r["ob_drug"], r["company"], r["est_expiry"]) for r in cr if r.get("ob_ds") and r.get("ob_drug")]
            if drugs:
                st.markdown("**OB 검증 = 어떤 약(API)의 cliff:** " +
                            "  ·  ".join(f"**{x}** ({c}, {e} 만료)" for x, c, e in drugs[:12]))
            st.pyplot(viz.cliff_timeline_fig(cr, (2026, 2031)))
            st.dataframe(pd.DataFrame(cr)[["company", "ob_drug", "patent_id", "est_expiry", "cites", "source"]],
                         hide_index=True, width="stretch")
        else:
            st.caption("cliff 데이터 없음.")
    # co-citation(Jaccard 네트워크)·KR 경쟁사 발굴(kr_cocitation) 둘 다 제거 — 초기 한국자산엔
    #   대부분 빈칸/독자공간이라 무의미(사용자 피드백). 경쟁지형 = '경쟁 서열' + KR 3-tier + Cross-modality.
    kr = _json(d, "kr_tiers.json")
    if kr:
        st.divider(); st.markdown("### 🇰🇷 KR 3-tier — 기술 분류(IPC)로 본 국내 경쟁 계층")
        st.caption("특허 기술분류(IPC)를 기준으로 국내 출원인을 경쟁 근접도에 따라 세 계층으로 나눈 지도임. "
                   "Tier 1은 같은 기술영역의 직접 경쟁, Tier 2는 인접 영역, Tier 3은 다른 모달리티로 경쟁이라기보다 잠재적 공동개발 후보에 가까움. "
                   "위에서 아래로 Tier 1 → 2 → 3 순이며, 같은 계층 안에서는 특허 건수가 많은 순으로 정렬함. "
                   "앞의 'KR 경쟁사 발굴'이 키워드 기반이라면, 이 지도는 더 넓은 기술 지형을 보여줌.")
        opt = st.segmented_control("티어", ["전체", "Tier1", "Tier2", "Tier3"], default="전체",
                                   key=f"kr_{asset}", label_visibility="collapsed")
        _px(viz_px.kr_tier_px(kr.get("kr_tiers", []), tier_filter={"Tier1": 1, "Tier2": 2, "Tier3": 3}.get(opt),
                                  domains=list((m.get("kr_domains") or {}).keys())))
    cm = _json(d, "crossmod.json")
    if cm:
        st.divider()
        st.markdown(f"**Cross-modality 경쟁·co-dev — 적응증 「{ta}」, 다른 모달리티** (상업사)")
        if m.get("indications_display"):
            st.caption(f"적응증(좁힘 질환/타깃): {m['indications_display']}")
        st.caption("막대=다른 모달리티 특허수, **색=시가총액 tier**(상단 대형→하단 소형). "
                   "스몰/마이크로캡·인수됨·비제약은 실제 협업/매입 가능성이 낮음 → 규모로 걸러 봄. 회사명 앞 색점=회사 분류.")
        st.markdown(ccls.cap_legend_html(), unsafe_allow_html=True)
        _px(viz_px.crossmod_px(cm))
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
st.caption("BERA BD · 특허·임상·딜 데이터 기반 파트너링 분석")
