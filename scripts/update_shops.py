"""
파핏 보세샵 상품 자동 업데이트
- 허락받은 쇼핑몰(shops.json)의 상품 목록 페이지를 하루 한 번 읽어서 products.json을 새로 만들어요.
- 어떤 가게를 못 읽어오면 그 가게는 어제 데이터를 그대로 둬요(앱이 비지 않게).
- 품절 상품은 빼요.
"""
import json, re, time, sys, datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml", "Accept-Language": "ko-KR,ko;q=0.9"}
DELAY = 1.0          # 페이지 사이 쉬는 시간(초) - 가게 서버에 부담 안 주게
MAX_PAGES = 30
MAX_ITEMS = 600      # 가게당 최대 상품 수

def get(s, url):
    r = s.get(url, headers={**UA, "Referer": url.split("/product")[0] + "/"}, timeout=20)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text

def price_of(text):
    t = re.sub(r"\s+", " ", text)
    for pat in [r"할인판매가\s*:?\s*(?:KRW|₩)?\s*([\d,]{4,})", r"판매가\s*:?\s*(?:KRW|₩)?\s*([\d,]{4,})",
                r"KRW\s*([\d,]{4,})(?!\s*할인)", r"([\d,]{4,})\s*원(?!\s*할인)"]:
        m = re.search(pat, t)
        if m:
            v = int(m.group(1).replace(",", ""))
            if 5000 <= v < 5_000_000:
                return v
    return 0

def name_of(li):
    for sel in [".name a span", ".name span", ".name a", ".name", ".prd-name", ".description strong"]:
        els = li.select(sel)
        txt = [e.get_text(" ", strip=True) for e in els]
        txt = [x for x in txt if x and not re.match(r"^(상품명|Product name)\s*:?$", x)]
        if txt:
            return re.sub(r"^(상품명|Product name)\s*:\s*", "", txt[-1]).strip()
    return ""

def parse_list(html, base):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    seen = set()
    for a in soup.select('a[href*="product_no="], a[href*="/product/"]'):
        href = a.get("href", "")
        m = re.search(r"product_no=(\d+)", href) or re.search(r"/product/[^/]+/(\d+)/", href)
        if not m:
            continue
        no = int(m.group(1))
        if no in seen:
            continue
        li = a.find_parent("li")
        if li is None or not li.find("img"):
            continue
        seen.add(no)
        text = li.get_text(" ", strip=True)
        if re.search(r"품절|sold\s*out", text, re.I) or li.select_one('img[alt*="품절"], img[src*="soldout"], .soldout'):
            continue
        img = ""
        for im in li.find_all("img"):
            src = im.get("src") or im.get("ec-data-src") or ""
            if "/product/" in src:
                img = urljoin(base, src)
                break
        nm = name_of(li)
        if not nm or not img:
            continue
        out.append([no, nm, price_of(text), img])
    return out

def crawl(shop, s):
    base = shop["url"].rstrip("/")
    home = get(s, base + "/")
    cats = list(dict.fromkeys(re.findall(r"cate_no=(\d+)", home)))
    items = {}
    for x in parse_list(home, base):
        items[x[0]] = x
    for c in cats:
        for p in range(1, MAX_PAGES + 1):
            time.sleep(DELAY)
            try:
                html = get(s, f"{base}/product/list.html?cate_no={c}&page={p}")
            except Exception:
                break
            got = parse_list(html, base)
            new = [x for x in got if x[0] not in items]
            for x in new:
                items[x[0]] = x
            if not got or not new or len(items) >= MAX_ITEMS:
                break
        if len(items) >= MAX_ITEMS:
            break
    return list(items.values())

def main():
    shops = json.load(open("shops.json", encoding="utf-8"))
    try:
        old = json.load(open("products.json", encoding="utf-8"))
    except Exception:
        old = {"shops": []}
    old_by = {x[1]: x for x in old.get("shops", [])}
    s = requests.Session()
    result = []
    for shop in shops:
        name = shop["name"]
        prev = old_by.get(name)
        prev_price = {it[0]: it[2] for it in (prev[3] if prev else [])}
        try:
            items = crawl(shop, s)
            # 목록에서 가격을 못 읽은 상품은 어제 가격을 써요
            for it in items:
                if not it[2] and prev_price.get(it[0]):
                    it[2] = prev_price[it[0]]
            if len(items) < 3 and prev:
                raise RuntimeError(f"too few items ({len(items)})")
            result.append([shop["url"], name, "", items])
            print(f"OK   {name}: {len(items)}개")
        except Exception as e:
            if prev:
                result.append(prev)
            print(f"KEEP {name}: 어제 데이터 유지 ({e})")
    out = {"updated": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M"),
           "shops": result}
    json.dump(out, open("products.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("updated", out["updated"])

if __name__ == "__main__":
    main()
