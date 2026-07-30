# BERA BD — 스냅샷 대시보드 (공개)

BD 분석 결과 **스냅샷 시각화** 전용 대시보드. 엔진 코드(스코어러·gather·DB)는 미포함 —
커밋된 분석 산출물(CSV/JSON)만 읽어 렌더한다. 라이브 계산·DB 접속 없음.

- 로컬: `streamlit run app.py`
- 배포: Streamlit Community Cloud (public), main file `app.py`, python-3.12(runtime.txt).
- 데이터: `data/<asset>/` (meta.json + 스냅샷). 자산별 자산개요·파트너링·CI 시각화.

초안(draft) — 미팅급은 큐레이션·팩트체크 필요.
