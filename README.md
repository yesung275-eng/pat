# 파핏 (FIND FIT)

추구미를 찾아주고, 그 스타일에 맞는 옷을 듀프·보세샵으로 추천하는 서비스.

## 파일
- `index.html` : 앱
- `products.json` : 보세샵 상품 (매일 자동 업데이트)
- `shops.json` : 허락받은 보세샵 목록 — 새 가게를 허락받으면 여기에 한 줄 추가
- `scripts/update_shops.py` : 상품을 가져오는 프로그램
- `.github/workflows/update.yml` : 매일 새벽 3시(한국시간)에 위 프로그램을 자동 실행

## 새 가게 추가하기
1. `shops.json`에 `{"name": "가게이름", "url": "https://가게주소"}` 한 줄 추가
2. `index.html` 안의 `ALLOWED_SHOPS` 목록에도 가게 이름 추가 (Claude에게 부탁해도 됨)
3. Actions 탭 → "보세샵 상품 자동 업데이트" → Run workflow
