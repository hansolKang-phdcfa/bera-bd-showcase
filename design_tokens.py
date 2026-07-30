# coding: utf-8
"""
[B-1] BERA 프레젠테이션 디자인 토큰 — DESIGN.md를 데이터로.

HTML 미리보기 렌더러와 PPTX 최종 렌더러가 **공유하는 단일 정본**. 여기 값을 바꾸면
두 렌더러가 함께 바뀜(미리보기 ↔ 최종 어긋남 방지). 원본 스펙: docs/DESIGN.md
"""
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
# 리포 내부 assets/ 를 기본으로 해석(패키지 상대) → 어느 머신에서든 이식 가능.
# 다른 위치의 에셋을 쓰려면 환경변수 BD_DECK_ASSETS 로 오버라이드.
ASSETS_DIR = os.environ.get("BD_DECK_ASSETS") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "assets")  # showcase: 같은 폴더 assets/
CLOSING_MSG = "미지의 영역에서 데이터기반 시장으로,  제약산업의 효율적 BD를 돕겠습니다."
CONTACT = "Contact)  E-mail: yooroh0419@gmail.com   |   Call: 010-8806-0419"

# ── evidence grade 배지(4색 재매핑) ──
GRADE_FILL = {"FACT": "blue", "HYPO": "gray", "REC": "black"}
GRADE_TAG = {"FACT": "실데이터", "HYPO": "가정", "REC": "권고"}


def rgb(token_or_hex):
    """'blue' 토큰명 또는 '#RRGGBB' → (r,g,b) 튜플 (pptx RGBColor용)."""
    h = COLORS.get(token_or_hex, token_or_hex).lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
