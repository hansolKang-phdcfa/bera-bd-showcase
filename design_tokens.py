# coding: utf-8
"""
[B-1] BERA 프레젠테이션 디자인 토큰 — DESIGN.md를 데이터로.

HTML 미리보기 렌더러와 PPTX 최종 렌더러, 대시보드 차트(viz/viz_px)가 **공유하는 단일 정본**.
여기 값을 바꾸면 전부 함께 바뀜(미리보기 ↔ 최종 ↔ 대시보드 어긋남 방지). 스펙: docs/DESIGN.md
덱 렌더러는 `bd_asset_pipeline.deck.design_tokens`(이 파일 재수출 shim)로 계속 접근한다.
"""
import io
import os

# ── 4색 (이외 색 금지) + 서피스 ──
COLORS = {
    "blue":  "#3E83FF",   # 유일 액센트(챕터·키수치·헤더룰·강조)
    "black": "#262626",   # 본문
    "k0":    "#000000",   # 제목
    "gray":  "#A5A5A5",   # 캡션·출처
    "white": "#FFFFFF",   # 기본 배경
    "soft":  "#F1F2F1",   # 카드·표 zebra
    "dark":  "#0C216A",   # 표지·클로징 배경 only
    "hairline": "#E3E8EE",
}

FONT = "Pretendard"

# ── 크기 계층(pt) ──
SIZES = {"cover": 44, "sub": 24, "chapter": 20, "section": 20,
         "heading": 18, "body": 16, "caption": 12, "src": 13}

# ── 슬라이드/레이아웃(inch) ──
SLIDE = {"w_in": 13.333, "h_in": 7.5}
LAYOUT = {"rule_top_in": 0.0, "rule_bot_in": 0.85,
          "chapter_x_in": 0.72, "section_x_in": 3.45,
          "content_x0_in": 0.5, "content_x1_in": 12.83,
          "content_y0_in": 1.0, "content_y1_in": 7.1, "src_y_in": 7.04}

# ── 브랜드 문구/자산 ──
# 이 파일은 엔진(bd_asset_pipeline/ui/)과 showcase 배포본(리포 루트)에서 **같은 내용**으로
# 쓰이므로 경로를 상대 깊이로 고정하지 않고 위로 올라가며 assets/ 를 찾는다.
# 다른 위치의 에셋을 쓰려면 환경변수 BD_DECK_ASSETS 로 오버라이드.
def _find_assets():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(4):
        cand = os.path.join(d, "assets")
        if os.path.isdir(cand):
            return cand
        d = os.path.dirname(d)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


ASSETS_DIR = os.environ.get("BD_DECK_ASSETS") or _find_assets()
CLOSING_MSG = "미지의 영역에서 데이터기반 시장으로,  제약산업의 효율적 BD를 돕겠습니다."

# 연락처는 배포 단위로 다름(엔진 덱=작성자 / showcase=배포자) → 파일 옆 contact.txt 나
# 환경변수 BERA_CONTACT 로 오버라이드. 없으면 아래 기본값.
_CONTACT_DEFAULT = "Contact)  E-mail: kanghansol93@gmail.com   |   Call: 010-4804-2436"


def _load_contact():
    v = os.environ.get("BERA_CONTACT")
    if v:
        return v
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contact.txt")
    if os.path.exists(p):
        try:
            with io.open(p, encoding="utf-8") as f:
                t = f.read().strip()
            if t:
                return t
        except Exception:
            pass
    return _CONTACT_DEFAULT


CONTACT = _load_contact()

# ── evidence grade 배지(4색 재매핑) ──
GRADE_FILL = {"FACT": "blue", "HYPO": "gray", "REC": "black"}
GRADE_TAG = {"FACT": "실데이터", "HYPO": "가정", "REC": "권고"}


def rgb(token_or_hex):
    """'blue' 토큰명 또는 '#RRGGBB' → (r,g,b) 튜플 (pptx RGBColor용)."""
    h = COLORS.get(token_or_hex, token_or_hex).lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
