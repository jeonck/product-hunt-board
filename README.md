# Product Hunt 일일 아이디어 인사이트

매일 Product Hunt 신규 제품의 pain point와 해결 아이디어를 정리하고, CK가 가져다 쓸 만한 아이디어를 골라 접목 방안을 제안하는 게시판.

**사이트:** https://jeonck.github.io/product-hunt-board/

## 어떻게 돌아가나

1. 매일 아침 7시(CST) Muse 크론(`product-hunt-daily-digest`)이 Product Hunt를 보고 한국어 다이제스트를 만든다.
2. 같은 실행에서 다이제스트 로그를 `pipeline/add_digest.py`로 `data/digests.json`에 추가하고 `index.html`을 다시 만든 뒤 이 저장소에 푸시한다.
3. GitHub Pages(Deploy from a branch, main)가 푸시될 때마다 게시판을 다시 보여준다. 별도 Actions 워크플로 없음.

## 파일

- `index.html` — 게시판 (자동 생성, 직접 고치지 말 것)
- `data/digests.json` — 모든 일일 다이제스트 (유일한 원본)
- `pipeline/add_digest.py` — 다이제스트 로그 파싱·추가·게시판 생성

## 백필

2026-11-10 ~ 11-13, 4일치로 시작했다. 그 전 27일치(10/14~11/09)는 `workspace/goals/product-hunt/hidden_files/` 로그에 있지만 형식이 일정하지 않아 자동 변환하지 않았다.
