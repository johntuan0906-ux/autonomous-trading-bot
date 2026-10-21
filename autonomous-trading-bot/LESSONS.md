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
### MẪU TP/SL CỦA NGƯỜI VẬN HÀNH (đo từ lệnh thật, 20/10) — ĐÃ XEM XÉT, CHƯA ÁP DỤNG

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

**Đã áp dụng (an toàn, không đổi hành vi giao dịch):** `ADOPT_SKIP_SYMBOLS` += `BICO` (bot **không bao giờ**
quản lý/dời SL/chốt lệnh tay của người vận hành); mẫu cấu hình để sẵn trong `.env` (khối
"MẪU TP/SL CỦA NGƯỜI DÙNG", đang comment). Muốn bật: bỏ `#` 6 dòng đó + restart.
**Hạn chế đã biết:** mã hiện tại LUÔN kéo SL về hoà vốn sau khi chốt một phần ⇒ khác người dùng
(giữ SL cố định); muốn đúng 100% phải sửa `trade_mgmt` (partial không dời SL) — chưa làm vì hội đồng VETO.
<!-- /HUMAN -->
