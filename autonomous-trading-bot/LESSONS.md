# BAI HOC TU JOURNAL (tu dong)

> Sinh boi `python tools/learn_review.py`. Nguong chan: xem `logs/lessons.json`.
> Muc do NGUOI viet nam trong 2 marker `<!-- HUMAN -->` se KHONG bi ghi de.

## So lieu

- So lenh da dong doc duoc: **938**
- To hop DIEU KIEN dang theo doi: **34**
- Lenh CLOSE khong co OPEN (DUST / ke thua) â€” DA LOAI khoi thong ke: **2396**
- To hop DANG CHAN (du mau + ky vong am): **7**

## Rut kinh nghiem

**NEN TRANH (ky vong am):**
-   - B_BREAKOUT_RETEST | BOS_UP | UPTREND | LONG: n=10 avgR=-0.276 WR=40% PnL=-11.18
-   - NONE | BOS_DOWN | COMPRESSION | SHORT: n=10 avgR=-0.252 WR=60% PnL=-12.42
-   - D_RANGE_REVERSAL | NONE | COMPRESSION | SHORT: n=22 avgR=-0.247 WR=36% PnL=-48.68  [DANG CHAN]
-   - NONE | NONE | BREAKOUT | LONG: n=8 avgR=-0.231 WR=50% PnL=-24.75
-   - NONE | NONE | SIDEWAY | SHORT: n=19 avgR=-0.222 WR=47% PnL=-43.43
-   - NONE | BOS_UP | UPTREND | LONG: n=15 avgR=-0.212 WR=40% PnL=-30.97
-   - B_BREAKOUT_RETEST | BOS_UP | BREAKOUT | LONG: n=20 avgR=-0.177 WR=45% PnL=-29.63  [DANG CHAN]
-   - NONE | BOS_UP | DOWNTREND | SHORT: n=23 avgR=-0.162 WR=39% PnL=-26.86  [DANG CHAN]
**NEN UU TIEN (ky vong duong):**
-   - B_BREAKOUT_RETEST | BOS_DOWN | DOWNTREND | SHORT: n=32 avgR=+0.446 WR=94% PnL=+136.42
-   - NONE | NONE | BREAKDOWN | SHORT: n=7 avgR=+0.415 WR=86% PnL=+29.03
-   - B_BREAKOUT_RETEST | BOS_DOWN | SIDEWAY | SHORT: n=6 avgR=+0.305 WR=83% PnL=+18.40
-   - D_RANGE_REVERSAL | NONE | COMPRESSION | LONG: n=7 avgR=+0.171 WR=71% PnL=+11.96
-   - NONE | BOS_UP | COMPRESSION | LONG: n=11 avgR=+0.132 WR=46% PnL=+14.55
-   - D_RANGE_REVERSAL | BOS_UP | COMPRESSION | SHORT: n=17 avgR=+0.112 WR=82% PnL=+3.80
-   - B_BREAKOUT_RETEST | BOS_DOWN | BREAKDOWN | SHORT: n=87 avgR=+0.108 WR=59% PnL=+88.42
-   - NONE | BOS_UP | COMPRESSION | SHORT: n=20 avgR=+0.098 WR=80% PnL=+25.04

## Ky nang da rut ra (`/evolve`)

| Ky nang | loai | n | avgR | WR | PnL |
|---|---|---|---|---|---|
| uu_tien: B_BREAKOUT_RETEST / BOS_DOWN / DOWNTREND / SHORT | uu_tien | 32 | +0.446 | 94% | +136.42 |
| uu_tien: COMPRESSION / SHORT | uu_tien | 171 | +0.063 | 64% | +82.08 |
| uu_tien: B_BREAKOUT_RETEST / BOS_DOWN / BREAKDOWN / SHORT | uu_tien | 87 | +0.108 | 59% | +88.42 |
| tranh: DOWNTREND / SHORT | tranh | 123 | -0.053 | 55% | -58.02 |
| tranh: D_RANGE_REVERSAL / COMPRESSION / SHORT | tranh | 22 | -0.247 | 36% | -48.68 |
| tranh: UPTREND / LONG | tranh | 86 | -0.063 | 55% | -8.33 |

## To hop dang chan

| Mã | To hop | n | avgR | WR | PnL |
|---|---|---|---|---|---|
| EV-2677E0 | D_RANGE_REVERSAL | NONE | COMPRESSION | SHORT | 22 | -0.247 | 36% | -48.68 |
| EV-826A02 | B_BREAKOUT_RETEST | BOS_UP | BREAKOUT | LONG | 20 | -0.177 | 45% | -29.63 |
| EV-2BB958 | NONE | BOS_UP | DOWNTREND | SHORT | 23 | -0.162 | 39% | -26.86 |
| EV-509F50 | B_BREAKOUT_RETEST | BOS_DOWN | COMPRESSION | SHORT | 30 | -0.095 | 57% | -14.69 |
| EV-517508 | B_BREAKOUT_RETEST | BOS_UP | COMPRESSION | LONG | 23 | -0.083 | 61% | -18.96 |
| EV-C17372 | NONE | NONE | UPTREND | LONG | 86 | -0.063 | 55% | -8.33 |
| EV-C3375C | NONE | NONE | DOWNTREND | SHORT | 123 | -0.053 | 55% | -58.02 |

_Truy nguoc bang chung cua 1 ma (vd `EV-2677E0`):_ `python tools/trace_trade.py --key "<to hop>"`

## Ghi chu cua nguoi van hanh

<!-- HUMAN -->
` se KHONG bi ghi de.

## So lieu

- So lenh da dong doc duoc: **852**
- To hop DIEU KIEN dang theo doi: **34**
- Lenh CLOSE khong co OPEN (DUST / ke thua) â€” DA LOAI khoi thong ke: **92**
- To hop DANG CHAN (du mau + ky vong am): **5**

## Rut kinh nghiem

**NEN TRANH (ky vong am):**
-   - NONE | NONE | BREAKOUT | LONG: n=6 avgR=-0.448 WR=33% PnL=-26.85
-   - NONE | BOS_UP | UPTREND | LONG: n=13 avgR=-0.267 WR=31% PnL=-31.69
-   - NONE | BOS_DOWN | COMPRESSION | SHORT: n=10 avgR=-0.252 WR=60% PnL=-12.42
-   - D_RANGE_REVERSAL | NONE | COMPRESSION | SHORT: n=22 avgR=-0.247 WR=36% PnL=-48.68  [DANG CHAN]
-   - NONE | NONE | SIDEWAY | SHORT: n=18 avgR=-0.244 WR=44% PnL=-43.88
-   - NONE | BOS_DOWN | UPTREND | LONG: n=13 avgR=-0.194 WR=54% PnL=-25.25
-   - B_BREAKOUT_RETEST | BOS_UP | BREAKOUT | LONG: n=16 avgR=-0.177 WR=44% PnL=-27.87
-   - NONE | BOS_UP | DOWNTREND | SHORT: n=23 avgR=-0.162 WR=39% PnL=-26.86  [DANG CHAN]
**NEN UU TIEN (ky vong duong):**
-   - B_BREAKOUT_RETEST | BOS_DOWN | DOWNTREND | SHORT: n=31 avgR=+0.433 WR=94% PnL=+134.35
-   - NONE | NONE | BREAKDOWN | SHORT: n=7 avgR=+0.415 WR=86% PnL=+29.03
-   - B_BREAKOUT_RETEST | BOS_DOWN | SIDEWAY | SHORT: n=6 avgR=+0.305 WR=83% PnL=+18.40
-   - NONE | BOS_DOWN | DOWNTREND | SHORT: n=8 avgR=+0.193 WR=75% PnL=+15.47
-   - D_RANGE_REVERSAL | NONE | COMPRESSION | LONG: n=7 avgR=+0.171 WR=71% PnL=+11.96
-   - NONE | BOS_UP | COMPRESSION | LONG: n=11 avgR=+0.132 WR=46% PnL=+14.55
-   - D_RANGE_REVERSAL | BOS_UP | COMPRESSION | SHORT: n=17 avgR=+0.112 WR=82% PnL=+3.80
-   - B_BREAKOUT_RETEST | BOS_DOWN | BREAKDOWN | SHORT: n=81 avgR=+0.109 WR=62% PnL=+86.83

## Ky nang da rut ra (`/evolve`)

| Ky nang | loai | n | avgR | WR | PnL |
|---|---|---|---|---|---|
| uu_tien: B_BREAKOUT_RETEST / BOS_DOWN / DOWNTREND / SHORT | uu_tien | 31 | +0.433 | 94% | +134.35 |
| uu_tien: B_BREAKOUT_RETEST / BOS_DOWN / BREAKDOWN / SHORT | uu_tien | 81 | +0.109 | 62% | +86.83 |
| uu_tien: COMPRESSION / SHORT | uu_tien | 159 | +0.050 | 64% | +75.30 |
| tranh: DOWNTREND / SHORT | tranh | 123 | -0.053 | 55% | -58.02 |
| tranh: D_RANGE_REVERSAL / COMPRESSION / SHORT | tranh | 22 | -0.247 | 36% | -48.68 |
| tranh: SIDEWAY / SHORT | tranh | 18 | -0.244 | 44% | -43.88 |

## To hop dang chan

| Mã | To hop | n | avgR | WR | PnL |
|---|---|---|---|---|---|
| EV-2677E0 | D_RANGE_REVERSAL | NONE | COMPRESSION | SHORT | 22 | -0.247 | 36% | -48.68 |
| EV-2BB958 | NONE | BOS_UP | DOWNTREND | SHORT | 23 | -0.162 | 39% | -26.86 |
| EV-509F50 | B_BREAKOUT_RETEST | BOS_DOWN | COMPRESSION | SHORT | 30 | -0.095 | 57% | -14.69 |
| EV-517508 | B_BREAKOUT_RETEST | BOS_UP | COMPRESSION | LONG | 23 | -0.083 | 61% | -18.96 |
| EV-C3375C | NONE | NONE | DOWNTREND | SHORT | 123 | -0.053 | 55% | -58.02 |

_Truy nguoc bang chung cua 1 ma (vd `EV-2677E0`):_ `python tools/trace_trade.py --key "<to hop>"`

## Ghi chu cua nguoi van hanh

<!-- HUMAN -->
` se KHONG bi ghi de.

## So lieu

- So lenh da dong doc duoc: **852**
- To hop DIEU KIEN dang theo doi: **34**
- Lenh CLOSE khong co OPEN (DUST / ke thua) â€” DA LOAI khoi thong ke: **92**
- To hop DANG CHAN (du mau + ky vong am): **5**

## Rut kinh nghiem

**NEN TRANH (ky vong am):**
-   - NONE | NONE | BREAKOUT | LONG: n=6 avgR=-0.448 WR=33% PnL=-26.85
-   - NONE | BOS_UP | UPTREND | LONG: n=13 avgR=-0.267 WR=31% PnL=-31.69
-   - NONE | BOS_DOWN | COMPRESSION | SHORT: n=10 avgR=-0.252 WR=60% PnL=-12.42
-   - D_RANGE_REVERSAL | NONE | COMPRESSION | SHORT: n=22 avgR=-0.247 WR=36% PnL=-48.68  [DANG CHAN]
-   - NONE | NONE | SIDEWAY | SHORT: n=18 avgR=-0.244 WR=44% PnL=-43.88
-   - NONE | BOS_DOWN | UPTREND | LONG: n=13 avgR=-0.194 WR=54% PnL=-25.25
-   - B_BREAKOUT_RETEST | BOS_UP | BREAKOUT | LONG: n=16 avgR=-0.177 WR=44% PnL=-27.87
-   - NONE | BOS_UP | DOWNTREND | SHORT: n=23 avgR=-0.162 WR=39% PnL=-26.86  [DANG CHAN]
**NEN UU TIEN (ky vong duong):**
-   - B_BREAKOUT_RETEST | BOS_DOWN | DOWNTREND | SHORT: n=31 avgR=+0.433 WR=94% PnL=+134.35
-   - NONE | NONE | BREAKDOWN | SHORT: n=7 avgR=+0.415 WR=86% PnL=+29.03
-   - B_BREAKOUT_RETEST | BOS_DOWN | SIDEWAY | SHORT: n=6 avgR=+0.305 WR=83% PnL=+18.40
-   - NONE | BOS_DOWN | DOWNTREND | SHORT: n=8 avgR=+0.193 WR=75% PnL=+15.47
-   - D_RANGE_REVERSAL | NONE | COMPRESSION | LONG: n=7 avgR=+0.171 WR=71% PnL=+11.96
-   - NONE | BOS_UP | COMPRESSION | LONG: n=11 avgR=+0.132 WR=46% PnL=+14.55
-   - D_RANGE_REVERSAL | BOS_UP | COMPRESSION | SHORT: n=17 avgR=+0.112 WR=82% PnL=+3.80
-   - B_BREAKOUT_RETEST | BOS_DOWN | BREAKDOWN | SHORT: n=81 avgR=+0.109 WR=62% PnL=+86.83

## Ky nang da rut ra (`/evolve`)

| Ky nang | loai | n | avgR | WR | PnL |
|---|---|---|---|---|---|
| uu_tien: B_BREAKOUT_RETEST / BOS_DOWN / DOWNTREND / SHORT | uu_tien | 31 | +0.433 | 94% | +134.35 |
| uu_tien: B_BREAKOUT_RETEST / BOS_DOWN / BREAKDOWN / SHORT | uu_tien | 81 | +0.109 | 62% | +86.83 |
| uu_tien: COMPRESSION / SHORT | uu_tien | 159 | +0.050 | 64% | +75.30 |
| tranh: DOWNTREND / SHORT | tranh | 123 | -0.053 | 55% | -58.02 |
| tranh: D_RANGE_REVERSAL / COMPRESSION / SHORT | tranh | 22 | -0.247 | 36% | -48.68 |
| tranh: SIDEWAY / SHORT | tranh | 18 | -0.244 | 44% | -43.88 |

## To hop dang chan

| Mã | To hop | n | avgR | WR | PnL |
|---|---|---|---|---|---|
| EV-2677E0 | D_RANGE_REVERSAL | NONE | COMPRESSION | SHORT | 22 | -0.247 | 36% | -48.68 |
| EV-2BB958 | NONE | BOS_UP | DOWNTREND | SHORT | 23 | -0.162 | 39% | -26.86 |
| EV-509F50 | B_BREAKOUT_RETEST | BOS_DOWN | COMPRESSION | SHORT | 30 | -0.095 | 57% | -14.69 |
| EV-517508 | B_BREAKOUT_RETEST | BOS_UP | COMPRESSION | LONG | 23 | -0.083 | 61% | -18.96 |
| EV-C3375C | NONE | NONE | DOWNTREND | SHORT | 123 | -0.053 | 55% | -58.02 |

_Truy nguoc bang chung cua 1 ma (vd `EV-2677E0`):_ `python tools/trace_trade.py --key "<to hop>"`

## Ghi chu cua nguoi van hanh

<!-- HUMAN -->
` se KHONG bi ghi de.

## So lieu

- So lenh da dong doc duoc: **834**
- To hop DIEU KIEN dang theo doi: **34**
- Lenh CLOSE khong co OPEN (DUST / ke thua) â€” DA LOAI khoi thong ke: **91**
- To hop DANG CHAN (du mau + ky vong am): **4**

## Rut kinh nghiem

**NEN TRANH (ky vong am):**
-   - NONE | NONE | BREAKOUT | LONG: n=6 avgR=-0.448 WR=33% PnL=-26.85
-   - NONE | BOS_UP | UPTREND | LONG: n=12 avgR=-0.286 WR=33% PnL=-31.41
-   - NONE | NONE | SIDEWAY | SHORT: n=16 avgR=-0.282 WR=44% PnL=-45.08
-   - NONE | BOS_DOWN | COMPRESSION | SHORT: n=10 avgR=-0.252 WR=60% PnL=-12.42
-   - D_RANGE_REVERSAL | NONE | COMPRESSION | SHORT: n=22 avgR=-0.247 WR=36% PnL=-48.68  [DANG CHAN]
-   - NONE | BOS_DOWN | UPTREND | LONG: n=13 avgR=-0.194 WR=54% PnL=-25.25
-   - B_BREAKOUT_RETEST | BOS_UP | BREAKOUT | LONG: n=16 avgR=-0.177 WR=44% PnL=-27.87
-   - NONE | BOS_UP | DOWNTREND | SHORT: n=18 avgR=-0.126 WR=50% PnL=-12.23
**NEN UU TIEN (ky vong duong):**
-   - B_BREAKOUT_RETEST | BOS_DOWN | DOWNTREND | SHORT: n=30 avgR=+0.443 WR=93% PnL=+132.88
-   - NONE | NONE | BREAKDOWN | SHORT: n=7 avgR=+0.415 WR=86% PnL=+29.03
-   - B_BREAKOUT_RETEST | BOS_DOWN | SIDEWAY | SHORT: n=6 avgR=+0.305 WR=83% PnL=+18.40
-   - D_RANGE_REVERSAL | BOS_UP | COMPRESSION | SHORT: n=15 avgR=+0.275 WR=93% PnL=+26.10
-   - NONE | BOS_DOWN | DOWNTREND | SHORT: n=8 avgR=+0.193 WR=75% PnL=+15.47
-   - D_RANGE_REVERSAL | NONE | COMPRESSION | LONG: n=7 avgR=+0.171 WR=71% PnL=+11.96
-   - NONE | BOS_UP | COMPRESSION | LONG: n=11 avgR=+0.132 WR=46% PnL=+14.55
-   - B_BREAKOUT_RETEST | BOS_DOWN | BREAKDOWN | SHORT: n=80 avgR=+0.114 WR=62% PnL=+90.04

## Ky nang da rut ra (`/evolve`)

| Ky nang | loai | n | avgR | WR | PnL |
|---|---|---|---|---|---|
| uu_tien: B_BREAKOUT_RETEST / BOS_DOWN / DOWNTREND / SHORT | uu_tien | 30 | +0.443 | 93% | +132.88 |
| uu_tien: COMPRESSION / SHORT | uu_tien | 155 | +0.062 | 66% | +91.78 |
| uu_tien: B_BREAKOUT_RETEST / BOS_DOWN / BREAKDOWN / SHORT | uu_tien | 80 | +0.114 | 62% | +90.04 |
| tranh: DOWNTREND / SHORT | tranh | 123 | -0.053 | 55% | -58.02 |
| tranh: D_RANGE_REVERSAL / COMPRESSION / SHORT | tranh | 22 | -0.247 | 36% | -48.68 |
| tranh: SIDEWAY / SHORT | tranh | 16 | -0.282 | 44% | -45.08 |

## To hop dang chan

| To hop | n | avgR | WR | PnL |
|---|---|---|---|---|
| D_RANGE_REVERSAL | NONE | COMPRESSION | SHORT | 22 | -0.247 | 36% | -48.68 |
| B_BREAKOUT_RETEST | BOS_DOWN | COMPRESSION | SHORT | 30 | -0.095 | 57% | -14.69 |
| B_BREAKOUT_RETEST | BOS_UP | COMPRESSION | LONG | 23 | -0.083 | 61% | -18.96 |
| NONE | NONE | DOWNTREND | SHORT | 123 | -0.053 | 55% | -58.02 |

## Ghi chu cua nguoi van hanh

<!-- HUMAN -->
` se KHONG bi ghi de.

## So lieu

- So lenh da dong doc duoc: **834**
- To hop DIEU KIEN dang theo doi: **34**
- Lenh CLOSE khong co OPEN (DUST / ke thua) — DA LOAI khoi thong ke: **91**
- To hop DANG CHAN (du mau + ky vong am): **4**

## Rut kinh nghiem

**NEN TRANH (ky vong am):**
-   - NONE | NONE | BREAKOUT | LONG: n=6 avgR=-0.448 WR=33% PnL=-26.85
-   - NONE | BOS_UP | UPTREND | LONG: n=12 avgR=-0.286 WR=33% PnL=-31.41
-   - NONE | NONE | SIDEWAY | SHORT: n=16 avgR=-0.282 WR=44% PnL=-45.08
-   - NONE | BOS_DOWN | COMPRESSION | SHORT: n=10 avgR=-0.252 WR=60% PnL=-12.42
-   - D_RANGE_REVERSAL | NONE | COMPRESSION | SHORT: n=22 avgR=-0.247 WR=36% PnL=-48.68  [DANG CHAN]
-   - NONE | BOS_DOWN | UPTREND | LONG: n=13 avgR=-0.194 WR=54% PnL=-25.25
-   - B_BREAKOUT_RETEST | BOS_UP | BREAKOUT | LONG: n=16 avgR=-0.177 WR=44% PnL=-27.87
-   - NONE | BOS_UP | DOWNTREND | SHORT: n=18 avgR=-0.126 WR=50% PnL=-12.23
**NEN UU TIEN (ky vong duong):**
-   - B_BREAKOUT_RETEST | BOS_DOWN | DOWNTREND | SHORT: n=30 avgR=+0.443 WR=93% PnL=+132.88
-   - NONE | NONE | BREAKDOWN | SHORT: n=7 avgR=+0.415 WR=86% PnL=+29.03
-   - B_BREAKOUT_RETEST | BOS_DOWN | SIDEWAY | SHORT: n=6 avgR=+0.305 WR=83% PnL=+18.40
-   - D_RANGE_REVERSAL | BOS_UP | COMPRESSION | SHORT: n=15 avgR=+0.275 WR=93% PnL=+26.10
-   - NONE | BOS_DOWN | DOWNTREND | SHORT: n=8 avgR=+0.193 WR=75% PnL=+15.47
-   - D_RANGE_REVERSAL | NONE | COMPRESSION | LONG: n=7 avgR=+0.171 WR=71% PnL=+11.96
-   - NONE | BOS_UP | COMPRESSION | LONG: n=11 avgR=+0.132 WR=46% PnL=+14.55
-   - B_BREAKOUT_RETEST | BOS_DOWN | BREAKDOWN | SHORT: n=80 avgR=+0.114 WR=62% PnL=+90.04

## Ky nang da rut ra (`/evolve`)

| Ky nang | loai | n | avgR | WR | PnL |
|---|---|---|---|---|---|
| uu_tien: B_BREAKOUT_RETEST / BOS_DOWN / DOWNTREND / SHORT | uu_tien | 30 | +0.443 | 93% | +132.88 |
| uu_tien: COMPRESSION / SHORT | uu_tien | 155 | +0.062 | 66% | +91.78 |
| uu_tien: B_BREAKOUT_RETEST / BOS_DOWN / BREAKDOWN / SHORT | uu_tien | 80 | +0.114 | 62% | +90.04 |
| tranh: DOWNTREND / SHORT | tranh | 123 | -0.053 | 55% | -58.02 |
| tranh: D_RANGE_REVERSAL / COMPRESSION / SHORT | tranh | 22 | -0.247 | 36% | -48.68 |
| tranh: SIDEWAY / SHORT | tranh | 16 | -0.282 | 44% | -45.08 |

## To hop dang chan

| To hop | n | avgR | WR | PnL |
|---|---|---|---|---|
| D_RANGE_REVERSAL | NONE | COMPRESSION | SHORT | 22 | -0.247 | 36% | -48.68 |
| B_BREAKOUT_RETEST | BOS_DOWN | COMPRESSION | SHORT | 30 | -0.095 | 57% | -14.69 |
| B_BREAKOUT_RETEST | BOS_UP | COMPRESSION | LONG | 23 | -0.083 | 61% | -18.96 |
| NONE | NONE | DOWNTREND | SHORT | 123 | -0.053 | 55% | -58.02 |

## Ghi chu cua nguoi van hanh

<!-- HUMAN -->
` se KHONG bi ghi de.

## So lieu

- So lenh da dong doc duoc: **906**
- To hop dieu kien dang theo doi: **35**
- To hop DANG CHAN (du mau + ky vong am): **4**

## Rut kinh nghiem

**NEN TRANH (ky vong am):**
-   - NONE | NONE | BREAKOUT | LONG: n=6 avgR=-0.448 WR=33% PnL=-26.85
-   - NONE | BOS_DOWN | COMPRESSION | SHORT: n=9 avgR=-0.303 WR=56% PnL=-14.49
-   - NONE | BOS_UP | UPTREND | LONG: n=12 avgR=-0.286 WR=33% PnL=-31.41
-   - NONE | NONE | SIDEWAY | SHORT: n=16 avgR=-0.282 WR=44% PnL=-45.08
-   - D_RANGE_REVERSAL | NONE | COMPRESSION | SHORT: n=22 avgR=-0.247 WR=36% PnL=-48.68  [DANG CHAN]
-   - NONE | BOS_DOWN | UPTREND | LONG: n=13 avgR=-0.194 WR=54% PnL=-25.25
-   - B_BREAKOUT_RETEST | BOS_UP | BREAKOUT | LONG: n=16 avgR=-0.177 WR=44% PnL=-27.87
-   - NONE | BOS_UP | DOWNTREND | SHORT: n=18 avgR=-0.126 WR=50% PnL=-12.23
**NEN UU TIEN (ky vong duong):**
-   - B_BREAKOUT_RETEST | BOS_DOWN | DOWNTREND | SHORT: n=30 avgR=+0.443 WR=93% PnL=+132.88
-   - NONE | NONE | BREAKDOWN | SHORT: n=7 avgR=+0.415 WR=86% PnL=+29.03
-   - ? | ? | ? | ?: n=84 avgR=+0.383 WR=46% PnL=+71.54
-   - B_BREAKOUT_RETEST | BOS_DOWN | SIDEWAY | SHORT: n=6 avgR=+0.305 WR=83% PnL=+18.40
-   - D_RANGE_REVERSAL | BOS_UP | COMPRESSION | SHORT: n=15 avgR=+0.275 WR=93% PnL=+26.10
-   - NONE | BOS_DOWN | DOWNTREND | SHORT: n=8 avgR=+0.193 WR=75% PnL=+15.47
-   - D_RANGE_REVERSAL | NONE | COMPRESSION | LONG: n=7 avgR=+0.171 WR=71% PnL=+11.96
-   - NONE | BOS_UP | COMPRESSION | LONG: n=11 avgR=+0.132 WR=46% PnL=+14.55

## Ky nang da rut ra (`/evolve`)

| Ky nang | loai | n | avgR | WR | PnL |
|---|---|---|---|---|---|
| uu_tien: ? | ? | ? | ? | uu_tien | 84 | +0.383 | 46% | +71.54 |
| uu_tien: B_BREAKOUT_RETEST / BOS_DOWN / DOWNTREND / SHORT | uu_tien | 30 | +0.443 | 93% | +132.88 |
| uu_tien: COMPRESSION / SHORT | uu_tien | 154 | +0.069 | 66% | +101.77 |
| uu_tien: B_BREAKOUT_RETEST / BOS_DOWN / BREAKDOWN / SHORT | uu_tien | 77 | +0.116 | 62% | +88.11 |
| tranh: DOWNTREND / SHORT | tranh | 117 | -0.058 | 55% | -61.07 |
| tranh: D_RANGE_REVERSAL / COMPRESSION / SHORT | tranh | 22 | -0.247 | 36% | -48.68 |

## To hop dang chan

| To hop | n | avgR | WR | PnL |
|---|---|---|---|---|
| D_RANGE_REVERSAL | NONE | COMPRESSION | SHORT | 22 | -0.247 | 36% | -48.68 |
| B_BREAKOUT_RETEST | BOS_DOWN | COMPRESSION | SHORT | 30 | -0.095 | 57% | -14.69 |
| B_BREAKOUT_RETEST | BOS_UP | COMPRESSION | LONG | 23 | -0.083 | 61% | -18.96 |
| NONE | NONE | DOWNTREND | SHORT | 117 | -0.058 | 55% | -61.07 |

## Ghi chu cua nguoi van hanh

<!-- HUMAN -->
` se KHONG bi ghi de.


## Bài học 22/10 (bổ sung của trợ lý — ngoài khối HUMAN)

**1. "In ra" KHÔNG phải là "báo" (B-028).** `watch_regress` phát hiện kill-switch TRIPPED,
supervisor chết, nhịp tim cũ... rồi chỉ `print` + `exit 1`. Với hệ thống chạy bằng Task
Scheduler (không ai ngồi xem console), **chỉ in ra = im lặng**. Từ nay mọi vấn đề
**tiến trình/an toàn** phải vào `ops_queue` theo **loại** vấn đề (khoá ổn định ⇒ không spam vì
số trong câu đổi mỗi lần), và báo lại mỗi 1h khi vẫn còn lỗi.

**2. Bụi ≠ TRẦN.** `orders_audit` báo "KHÔNG co SL/TP" cho cả vị thế **bụi** (qty < minNotional,
đã ghi `dust_skip.json`) rồi vẫn kết luận "gọn" ⇒ vừa báo động giả, vừa **che mất** vị thế
**TRẦN** (không có gì chặn lỗ). Phải phân biệt **đã biết / không thể bảo vệ** với **thiếu bảo vệ**.

**3. Đo phủ bảo vệ phải ĐỊNH KỲ.** Đo thật 22/10: LIVE `BICO` có **4** lệnh bảo vệ (2 cặp
TRÙNG) — lệnh trùng tích tụ đến khi chạm trần stop-order (`-4045`) thì lệnh bảo vệ mới không
đặt được nữa. Nay task `ATB-WatchRegress` (10 phút/lần) chạy `--check --orders`.

**4. Veto của hội đồng phải được TÔN TRỌNG + ghi lý do.** Hội đồng VETO 0–2 cơ chế tự gỡ
kill-switch sau 12h (lý do: mốc lại peak/start_equity **xoá dấu vết drawdown**; tự gỡ khi chưa
xác nhận nguyên nhân = tái kích hoạt rủi ro). Cách xử lý đúng: **giữ cơ chế trong mã nhưng TẮT**,
ghi `H-20261022-004` kèm lý do, và chống trì trệ bằng đường khác mà hội đồng đã chấp nhận
(cảnh báo tự động khi trip + cổng tạm dừng có hạn + nâng trần ngày).

**5. Đổi tham số rủi ro = đổi `.env` rồi RESTART.** `risk_state.json` **không** ghi đè ngưỡng
trong `.env` (state chỉ lưu ảnh chụp). Đo thật: TESTNET sau restart ghi `max_daily_loss_pct: 6.0`;
LIVE vẫn `2.0` cho tới khi restart (đang chờ hết vị thế).

**6. Đường dẫn TƯƠNG ĐỐI theo cwd = bom hẹn giờ trong Task Scheduler (B-029).** Task
Scheduler không đặt `<WorkingDirectory>` ⇒ cwd = `C:\Windows\System32`. Windows **có sẵn**
`System32\logs` nhưng **không ghi được** (`PermissionError`) ⇒ `ops_queue` ghi cảnh báo thất
bại **trong thinh lặng** (đo thật 24/10: `regress_watch.log` có dòng `VAN DE naked @ LIVE`
nhưng `ops_questions.json` TRỐNG). Bài học kép: (a) mọi file trạng thái phải neo vào **thư mục
dự án**, không theo cwd; (b) **lỗi ghi phải la lên** (stderr + vết trong log), đừng `return False`
rồi thôi. Và phép kiểm "có `logs/`" là chưa đủ để nhận diện instance — phải có **dấu hiệu bot**.

## So lieu

- So lenh da dong doc duoc: **698**
- To hop dieu kien dang theo doi: **30**
- To hop DANG CHAN (du mau + ky vong am): **0**

## Rut kinh nghiem

**NEN TRANH (ky vong am):**
-   - NONE | NONE | SIDEWAY | SHORT: n=11 avgR=-0.368 WR=46% PnL=-40.52
-   - NONE | BOS_DOWN | COMPRESSION | SHORT: n=9 avgR=-0.303 WR=56% PnL=-14.49
-   - NONE | BOS_UP | DOWNTREND | SHORT: n=9 avgR=-0.264 WR=22% PnL=-13.32
-   - B_BREAKOUT_RETEST | BOS_UP | BREAKOUT | LONG: n=11 avgR=-0.257 WR=36% PnL=-27.76
-   - D_RANGE_REVERSAL | NONE | COMPRESSION | SHORT: n=22 avgR=-0.247 WR=36% PnL=-48.68
-   - NONE | BOS_UP | UPTREND | LONG: n=8 avgR=-0.191 WR=38% PnL=-12.34
-   - B_BREAKOUT_RETEST | BOS_DOWN | COMPRESSION | SHORT: n=29 avgR=-0.105 WR=55% PnL=-16.59
-   - NONE | BOS_DOWN | UPTREND | LONG: n=9 avgR=-0.097 WR=56% PnL=-8.70
**NEN UU TIEN (ky vong duong):**
-   - B_BREAKOUT_RETEST | BOS_DOWN | DOWNTREND | SHORT: n=15 avgR=+0.633 WR=93% PnL=+94.93
-   - ? | ? | ? | ?: n=71 avgR=+0.444 WR=45% PnL=+85.42
-   - NONE | BOS_DOWN | DOWNTREND | SHORT: n=5 avgR=+0.339 WR=80% PnL=+16.93
-   - B_BREAKOUT_RETEST | BOS_DOWN | SIDEWAY | SHORT: n=5 avgR=+0.311 WR=80% PnL=+15.61
-   - D_RANGE_REVERSAL | BOS_UP | COMPRESSION | SHORT: n=14 avgR=+0.245 WR=93% PnL=+19.10
-   - D_RANGE_REVERSAL | NONE | COMPRESSION | LONG: n=7 avgR=+0.171 WR=71% PnL=+11.96
-   - NONE | BOS_UP | COMPRESSION | LONG: n=10 avgR=+0.107 WR=40% PnL=+10.71
-   - B_BREAKOUT_RETEST | BOS_UP | UPTREND | LONG: n=5 avgR=+0.091 WR=60% PnL=+4.54

## To hop dang chan

(chua co to hop nao du mau + ky vong am)

## Ghi chu cua nguoi van hanh

<!-- HUMAN -->
### MẪU TP/SL CỦA NGƯỜI VẬN HÀNH (đo từ lệnh thật) — ĐÃ ÁP DỤNG 21/10 THEO YÊU CẦU (hội đồng VETO 1-3)

**Lệnh mẫu (người tự vào, LIVE):** `BICO/USDT:USDT` **LONG 706** @ `0.01703`, đòn bẩy 10×, notional ≈ 12 USDT
(≈30% equity LIVE), lỗ tối đa theo SL ≈ **1.15 USDT = 2.9% equity**.

| Mức | Giá | Cách giá vào | Quy đổi R (R = SL) | KL chốt |
|---|---|---|---|---|
| SL (`closePosition=true`, KHÔNG dời) | 0.0154 | **−9.57%** | −1.00R | 100% |
| TP2 | 0.0217 | **+27.4%** | **+2.86R** | 30% |
| TP1 | 0.0251 | **+47.4%** | **+4.95R** | 50% |
| Runner | — | không TP | — | 20% |

Quy đổi theo ATR tại thời điểm vào: SL = **5.5×ATR(1h) = 14×ATR(15m)**; TP1 = 69×ATR(15m); TP2 = 40×ATR(15m).
Đặc điểm: **SL rất rộng + chốt xa theo bậc + giữ 20% chạy + không dời SL**.

**Vì sao CHƯA áp dụng cho toàn bộ cặp (bằng chứng, không phải ý kiến):**

1. **Mô phỏng trên chính journal của bot** (3.231 lệnh có `mfe_r`, TESTNET): bậc TP của người dùng
   (tương đương 20R/35R của bot) cho **+3.774R** so với **+4.385R** hiện tại ⇒ **−14%**; bậc gần
   (4R/2R) ⇒ **−48%**; (3R/1.5R) ⇒ **−53%**. Lý do: bot đánh khung **15m**, lệnh hiếm khi chạy xa
   (LIVE: MFE p50 = 0.35R, **p90 = 1.25R**) ⇒ đặt TP ở +2.9R/+5R gần như không bao giờ chạm.
2. **Không khả thi trên LIVE ($40 vốn)**: SL 9.57% + risk 0.25% ($0.10) ⇒ notional **$1.04 < 5 USDT**
   (min notional của Binance) ⇒ **không vào được lệnh**. Muốn vào phải nâng risk ≥ **1.2%/lệnh**
   (gấp 4.8×; 2 lệnh thua là trip kill-switch 2%/ngày).
3. **Hội đồng 20/10**: **1 ALLOW / 3 VETO** ⇒ VETO (qwen3.7-plus: TP bất thực tế với MFE p90=1.25R;
   qwen3.8-max + mimo: vi phạm min notional). Phiếu lưu trong journal (`status=COUNCIL`).

**ĐÃ ÁP DỤNG 21/10 (người vận hành yêu cầu "làm đồng thời 2 lựa chọn", sau khi hội đồng VETO 1-3):**
`RISK_PER_TRADE_PCT 1.2` · `MAX_TOTAL_RISK_PCT 1.6` · `SL_ATR_MULT 14` · `TP_ATR_MULT 69` ·
`PARTIAL_AT_R 2.86` · `PARTIAL_PCT 0.3` · `BE_AT_R 0` · `TRAIL_ATR_MULT 0` · `SIZE_TO_MIN_NOTIONAL=true`
(áp dụng **cả TESTNET và LIVE**; backup `.env` giữ tại `*.env.bak-*`).

- `SIZE_TO_MIN_NOTIONAL=true`: khi notional theo risk < 5 USDT (LIVE $40 + SL 9-12%) thì **nâng qty
  lên đúng minNotional** thay vì `SKIP_NOTIONAL` ⇒ mới vào được lệnh (đo: risk 1.2% chỉ 23/40 cặp vào
  được, 1.5% được 29/40; có cờ này thì 40/40). Risk thực tăng nhẹ (trần ≈1.5%).
- `ADOPT_SKIP_SYMBOLS=BICO` (cả 2 instance): bot **không bao giờ** quản lý/dời SL/chốt lệnh tay.
- **HỆ QUẢ PHẢI BIẾT**: risk 1.2%/lệnh nhưng `MAX_DAILY_LOSS_PCT=2.0` ⇒ **2 lệnh thua là trip
  kill-switch** (phải `python risk.py --reset` mới chạy tiếp). Muốn chạy liên tục phải nâng
  `MAX_DAILY_LOSS_PCT` — **quyết định của người vận hành**, chưa làm.
- Về lại cấu hình cũ: `RISK_PER_TRADE_PCT=0.25`, `MAX_TOTAL_RISK_PCT=1.0`, `SL_ATR_MULT=2.0`,
  `TP_ATR_MULT=5.0`, `PARTIAL_AT_R=0.3`, `PARTIAL_PCT=0.5`, `BE_AT_R=1.0`, `TRAIL_ATR_MULT=1.0`,
  `SIZE_TO_MIN_NOTIONAL=false` rồi restart.
**Hạn chế đã biết:** mã hiện tại **luôn kéo SL về hoà vốn** sau khi chốt một phần ⇒ khác mẫu
(người dùng giữ SL cố định). Muốn đúng 100% phải sửa `trade_mgmt` (partial không dời SL).
<!-- /HUMAN -->
