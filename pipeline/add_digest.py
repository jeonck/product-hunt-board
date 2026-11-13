#!/usr/bin/env python3
"""Product Hunt 일일 다이제스트 게시판 도구.

아침 크론이 만든 다이제스트 로그(workspace/goals/product-hunt/hidden_files/
YYYY-MM-DD.md, 아래 '새 형식')를 data/digests.json에 한 줄로 추가하고
index.html 게시판을 다시 만든다.

    python3 pipeline/add_digest.py <log.md>          # 로그 1개를 추가 + 게시판 재생성
    python3 pipeline/add_digest.py --rebuild-only    # 게시판만 재생성

로그 형식(새 형식, 2026-11-07 이후 일부):
  # Product Hunt 일일 다이제스트 — YYYY-MM-DD
  - 오늘 보드 특징: ... (있을 때만)
  ## 선정 제품
  1. **이름** (#1) — https://www.producthunt.com/products/slug
     - 한 줄: ...
     - Pain point: ...
     - 해결 아이디어: ...
  또는 한 줄 요약형:
  1. 이름 — 태그라인 (https://...)
  ## 접목 제안 (CK 관점)
  1. 제안 문장

형식이 안 맞으면 실패로 끝나고 아무것도 기록하지 않는다 — 내용을 지어내지 않는다.
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "digests.json"
INDEX = ROOT / "index.html"

# 11/12·11/13형: 1. **이름** (#1) — URL
FULL_RE = re.compile(r"^(\d+)\.\s+\*\*(.+?)\*\*\s*(?:\(([^)]*)\))?\s*—\s*(https?://\S+)\s*$")
# 11/10·11/11형: 1. 이름 — 태그라인 (URL)
SHORT_RE = re.compile(r"^(\d+)\.\s+(.+?)\s+—\s+(.+?)\s*\((https?://\S+)\)\s*$")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
DETAIL_RE = re.compile(r"^\s+-\s+([^:]+):\s*(.*)$")
GRAFT_RE = re.compile(r"^(\d+)\.\s+(.+)$")


def parse_log(path):
    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines()
    m = DATE_RE.search(lines[0] if lines else "")
    if not m:
        raise ValueError(f"날짜를 찾을 수 없음: {path} (첫 줄: {lines[0] if lines else ''!r})")
    date = m.group(1)
    theme = ""
    for line in lines:
        if line.startswith("- 오늘 보드 특징:"):
            theme = line.split(":", 1)[1].strip()
            break
    products, grafts = [], []
    section = None
    current = None
    for line in lines:
        if line.startswith("## 선정 제품"):
            section = "products"
            continue
        if line.startswith("## 접목 제안"):
            section = "grafts"
            continue
        if line.startswith("## "):
            section = None
            continue
        if section == "products":
            fm = FULL_RE.match(line)
            sm = SHORT_RE.match(line) if not fm else None
            if fm:
                current = {"name": fm.group(2).strip(), "rank": (fm.group(3) or "").strip(),
                           "url": fm.group(4).strip(), "tagline": "", "summary": "",
                           "pain": "", "idea": "", "notes": []}
                products.append(current)
            elif sm:
                current = {"name": sm.group(2).strip(), "rank": "", "url": sm.group(4).strip(),
                           "tagline": sm.group(3).strip(), "summary": "", "pain": "",
                           "idea": "", "notes": []}
                products.append(current)
            elif current is not None:
                dm = DETAIL_RE.match(line)
                if dm:
                    key, val = dm.group(1).strip(), dm.group(2).strip()
                    if key == "한 줄":
                        current["summary"] = val
                    elif key == "Pain point":
                        current["pain"] = val
                    elif key == "해결 아이디어":
                        current["idea"] = val
                    else:
                        current["notes"].append(f"{key}: {val}")
        elif section == "grafts":
            gm = GRAFT_RE.match(line)
            if gm:
                grafts.append(gm.group(2).strip())
    if not products:
        raise ValueError(f"선정 제품을 찾지 못함: {path}")
    if not grafts:
        raise ValueError(f"접목 제안을 찾지 못함: {path}")
    for p in products:
        if not p["url"].startswith("http"):
            raise ValueError(f"제품 URL 누락/이상: {p['name']} in {path}")
    return {"date": date, "theme": theme, "products": products, "grafts": grafts}


def load():
    if DATA.exists():
        return json.loads(DATA.read_text(encoding="utf-8"))
    return {"entries": []}


def save(data):
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def esc(s):
    return html.escape(s or "")


PAGER_JS = """<script>
(function(){
var secs = Array.prototype.slice.call(document.querySelectorAll('section'));
var per = 7, page = 0, pages = Math.max(1, Math.ceil(secs.length / per));
var info = document.getElementById('pageInfo');
var prev = document.getElementById('prevBtn'), next = document.getElementById('nextBtn');
function show(){
  secs.forEach(function(s, i){ s.style.display = (i >= page*per && i < (page+1)*per) ? '' : 'none'; });
  info.textContent = (page+1) + ' / ' + pages + ' 페이지';
  prev.disabled = page === 0; next.disabled = page >= pages-1;
  window.scrollTo(0, 0);
}
prev.onclick = function(){ if(page > 0){ page--; show(); } };
next.onclick = function(){ if(page < pages-1){ page++; show(); } };
show();
})();
</script>"""


def render(data):
    entries = sorted(data["entries"], key=lambda e: e["date"], reverse=True)
    latest = entries[0] if entries else None
    days = ""
    for e in entries:
        prods = ""
        for p in e["products"]:
            rank = f" <span class='rank'>{esc(p['rank'])}</span>" if p.get("rank") else ""
            tag = esc(p.get("summary") or p.get("tagline") or "")
            pain = f"<div><b>Pain:</b> {esc(p['pain'])}</div>" if p.get("pain") else ""
            idea = f"<div><b>해결:</b> {esc(p['idea'])}</div>" if p.get("idea") else ""
            notes = "".join(f"<div class='note'>{esc(n)}</div>" for n in p.get("notes", []))
            prods += (f"<div class='prod'><a href='{esc(p['url'])}'><b>{esc(p['name'])}</b></a>"
                      f"{rank}<div>{tag}</div>{pain}{idea}{notes}</div>\n")
        grafts = "".join(f"<li>{esc(g)}</li>" for g in e["grafts"])
        theme = f"<p class='theme'>{esc(e['theme'])}</p>" if e.get("theme") else ""
        days += (f"<section><h2>{e['date']}</h2>{theme}{prods}"
                 f"<h3>접목 제안</h3><ol>{grafts}</ol></section>\n")
    latest_line = (f"최신 다이제스트: {latest['date']} · {len(latest['products'])}개 제품"
                   if latest else "아직 다이제스트 없음")
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Product Hunt 일일 아이디어 인사이트</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;max-width:880px;margin:0 auto;padding:24px 16px;color:#1a1a1a;line-height:1.6}}
h1{{font-size:1.5rem;margin-bottom:4px}} .sub{{color:#666;margin-top:0}}
section{{border-top:1px solid #eee;padding:18px 0}} section h2{{margin-top:0}}
.theme{{color:#555}} .prod{{border:1px solid #e5e5e5;border-radius:10px;padding:12px;margin:10px 0}}
.prod a{{color:#1a0dab}} .rank{{color:#666;font-size:.85rem}} .note{{color:#666;font-size:.85rem}}
.pager{{margin:8px 0 20px;text-align:center}} .pager button{{padding:6px 14px;margin:0 8px;cursor:pointer}} .pager button:disabled{{opacity:.4;cursor:default}}
footer{{color:#666;font-size:.85rem;margin-top:28px;border-top:1px solid #eee;padding-top:12px}}
</style>
</head>
<body>
<h1>💡 Product Hunt 일일 아이디어 인사이트</h1>
<p class="sub">매일 Product Hunt 신규 제품의 pain point와 해결 아이디어를 정리하고, CK가 가져다 쓸 만한 아이디어를 골라 접목 방안을 제안합니다. {esc(latest_line)} · 원본 데이터: <a href="data/digests.json">digests.json</a></p>
{days}
<div class="pager" id="pager"><button id="prevBtn">← 이전</button><span id="pageInfo"></span><button id="nextBtn">다음 →</button></div>
{PAGER_JS}
<footer>
출처: Product Hunt (producthunt.com) 및 각 제품 페이지. 제품 설명·수치는 원출처 기준이며, 메이커 주장 수치는 그대로 표기합니다. ·
<a href="https://github.com/jeonck/product-hunt-board">GitHub 저장소</a>
</footer>
</body>
</html>
"""


def main():
    args = sys.argv[1:]
    if args == ["--rebuild-only"]:
        data = load()
        INDEX.write_text(render(data), encoding="utf-8")
        print(f"index.html 재생성 완료 ({len(data['entries'])}일치)")
        return 0
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    entry = parse_log(args[0])
    data = load()
    if any(e["date"] == entry["date"] for e in data["entries"]):
        print(f"{entry['date']} 다이제스트는 이미 기록됨 — 추가하지 않음")
        return 0
    data["entries"].append(entry)
    data["entries"].sort(key=lambda e: e["date"])
    save(data)
    INDEX.write_text(render(data), encoding="utf-8")
    print(f"{entry['date']} 다이제스트 기록됨 — 제품 {len(entry['products'])}개, 접목 제안 {len(entry['grafts'])}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
