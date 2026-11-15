# BAI HOC TU JOURNAL (tu dong)

> Sinh boi `python tools/learn_review.py`. Nguong chan: xem `logs/lessons.json`.
> Muc do NGUOI viet nam trong 2 marker `

<!-- AUTO:LESSONS -->

## Bài học tự sinh (đừng sửa tay — chạy `python tools\lessons_wiki.py --write`)

Nguồn: `C:\Users\User\.vscode\Projects\autonomous-trading-bot\logs\journal.jsonl` · khóa = `strategy + setup_type + market_regime + direction` · ngưỡng mẫu n ≥ 8 · sắp theo `avg_r` tăng dần.

| Khóa (strategy · setup · regime · hướng) | n | thắng | avg R | PnL | trích dẫn |
|---|---|---|---|---|---|
| B_BREAKOUT_RETEST | BOS_UP | UPTREND | LONG (!) | 8 | 37.5% | -0.736 | -22.33 | ts=1791659590, ts=1791715301, ts=1791836740 |
| A_TREND_PULLBACK | NONE | COMPRESSION | SHORT (!) | 14 | 42.9% | -0.519 | -35.96 | ts=1790241246, ts=1791895772, ts=1791941462 |
| B_BREAKOUT_RETEST | BOS_UP | BREAKOUT | LONG (!) | 16 | 31.2% | -0.427 | -67.80 | ts=1791172737, ts=1791192600, ts=1791703530 |
| NONE | BOS_DOWN | UPTREND | LONG (!) | 15 | 53.3% | -0.233 | -36.16 | ts=1790944473, ts=1791171483, ts=1791209887 |
| D_RANGE_REVERSAL | BOS_UP | COMPRESSION | SHORT (!) | 16 | 50.0% | -0.230 | -25.99 | ts=1790234668, ts=1790242256, ts=1790247753 |
| D_RANGE_REVERSAL | NONE | COMPRESSION | SHORT (!) | 23 | 52.2% | -0.193 | -42.81 | ts=1790235075, ts=1790678431, ts=1790859967 |
| NONE | BOS_UP | UPTREND | LONG (!) | 17 | 47.1% | -0.167 | -22.89 | ts=1790860024, ts=1790944746, ts=1791207439 |
| NONE | BOS_DOWN | DOWNTREND | SHORT (!) | 15 | 53.3% | -0.154 | -15.09 | ts=1791483918, ts=1791483918, ts=1791822472 |
| NONE | NONE | UPTREND | LONG (!) | 79 | 57.0% | -0.124 | -59.07 | ts=1790163248, ts=1790163442, ts=1790679289 |
| NONE | BOS_DOWN | COMPRESSION | LONG (!) | 15 | 60.0% | -0.108 | -14.25 | ts=1790942445, ts=1790950155, ts=1790950634 |
| NONE | NONE | DOWNTREND | LONG (!) | 8 | 62.5% | -0.089 | -7.09 | ts=1790305214, ts=1791744554, ts=1791782456 |
| A_TREND_PULLBACK | NONE | DOWNTREND | SHORT (!) | 13 | 30.8% | -0.076 | -10.69 | ts=1790262914, ts=1790328557, ts=1792407163 |
| NONE | BOS_UP | DOWNTREND | SHORT (!) | 23 | 60.9% | -0.058 | -15.58 | ts=1790292546, ts=1790672545, ts=1791480340 |
| NONE | NONE | COMPRESSION | LONG (!) | 129 | 59.7% | -0.014 | +9.47 | ts=1790868713, ts=1790872757, ts=1790930989 |
| NONE | BOS_UP | COMPRESSION | SHORT (!) | 21 | 71.4% | -0.007 | -0.35 | ts=1790861108, ts=1790935903, ts=1791177991 |
| NONE | NONE | UPTREND | SHORT | 9 | 66.7% | +0.005 | +1.29 | ts=1791830821, ts=1791890678, ts=1791918198 |
| NONE | NONE | BREAKDOWN | SHORT | 9 | 66.7% | +0.025 | -0.96 | ts=1791842018, ts=1791849801, ts=1791850443 |
| NONE | NONE | DOWNTREND | SHORT | 115 | 67.0% | +0.029 | +6.36 | ts=1790254886, ts=1790255830, ts=1790283974 |
| B_BREAKOUT_RETEST | BOS_DOWN | COMPRESSION | SHORT | 27 | 70.4% | +0.082 | +8.06 | ts=1790244695, ts=1790246692, ts=1790251768 |
| B_BREAKOUT_RETEST | BOS_DOWN | BREAKDOWN | LONG | 17 | 35.3% | +0.090 | -35.62 | ts=1791209952, ts=1791209952, ts=1791672167 |
| B_BREAKOUT_RETEST | BOS_UP | COMPRESSION | LONG | 18 | 77.8% | +0.103 | +18.41 | ts=1790875371, ts=1790938154, ts=1790940554 |
| NONE | NONE | COMPRESSION | SHORT | 194 | 66.0% | +0.104 | +30.72 | ts=1790235075, ts=1790235538, ts=1790240549 |
| NONE | BOS_UP | COMPRESSION | LONG | 10 | 70.0% | +0.209 | +20.96 | ts=1790929940, ts=1790938286, ts=1790950567 |
| B_BREAKOUT_RETEST | BOS_DOWN | DOWNTREND | SHORT | 35 | 85.7% | +0.267 | +85.76 | ts=1790255830, ts=1791465270, ts=1791465573 |
| B_BREAKOUT_RETEST | BOS_DOWN | BREAKDOWN | SHORT | 93 | 68.8% | +0.315 | +254.65 | ts=1790247218, ts=1791210909, ts=1791452680 |
| NONE | NONE | BREAKOUT | LONG | 9 | 66.7% | +0.338 | +2.72 | ts=1790670756, ts=1790675507, ts=1790935934 |
| NONE | NONE | SIDEWAY | LONG | 8 | 62.5% | +0.345 | +31.78 | ts=1791859390, ts=1791970339, ts=1791970954 |
| NONE | NONE | SIDEWAY | SHORT | 20 | 75.0% | +0.416 | +92.77 | ts=1791478900, ts=1791478941, ts=1791824867 |
| NONE | BOS_DOWN | COMPRESSION | SHORT | 20 | 75.0% | +0.466 | +26.88 | ts=1790950647, ts=1791205436, ts=1791459655 |
| ? | ? | ? | LONG | 1187 | 19.4% | +0.994 | -2342.30 | ts=1791654635, ts=1791660863, ts=1791662067 |
| ? | ? | ? | SHORT | 1237 | 73.5% | +2.868 | +1220.32 | ts=1791517281, ts=1791524196, ts=1791525385 |

```json
{
 "? | ? | ? | LONG": {
  "avg_r": 0.994,
  "n": 1187,
  "pnl": -2342.3,
  "refs": [
   "ts=1791654635",
   "ts=1791660863",
   "ts=1791662067"
  ],
  "winrate": 19.4,
  "wins": 230
 },
 "? | ? | ? | SHORT": {
  "avg_r": 2.868,
  "n": 1237,
  "pnl": 1220.32,
  "refs": [
   "ts=1791517281",
   "ts=1791524196",
   "ts=1791525385"
  ],
  "winrate": 73.5,
  "wins": 909
 },
 "A_TREND_PULLBACK | NONE | COMPRESSION | SHORT": {
  "avg_r": -0.519,
  "n": 14,
  "pnl": -35.96,
  "refs": [
   "ts=1790241246",
   "ts=1791895772",
   "ts=1791941462"
  ],
  "winrate": 42.9,
  "wins": 6
 },
 "A_TREND_PULLBACK | NONE | DOWNTREND | SHORT": {
  "avg_r": -0.076,
  "n": 13,
  "pnl": -10.69,
  "refs": [
   "ts=1790262914",
   "ts=1790328557",
   "ts=1792407163"
  ],
  "winrate": 30.8,
  "wins": 4
 },
 "B_BREAKOUT_RETEST | BOS_DOWN | BREAKDOWN | LONG": {
  "avg_r": 0.09,
  "n": 17,
  "pnl": -35.62,
  "refs": [
   "ts=1791209952",
   "ts=1791209952",
   "ts=1791672167"
  ],
  "winrate": 35.3,
  "wins": 6
 },
 "B_BREAKOUT_RETEST | BOS_DOWN | BREAKDOWN | SHORT": {
  "avg_r": 0.315,
  "n": 93,
  "pnl": 254.65,
  "refs": [
   "ts=1790247218",
   "ts=1791210909",
   "ts=1791452680"
  ],
  "winrate": 68.8,
  "wins": 64
 },
 "B_BREAKOUT_RETEST | BOS_DOWN | COMPRESSION | SHORT": {
  "avg_r": 0.082,
  "n": 27,
  "pnl": 8.06,
  "refs": [
   "ts=1790244695",
   "ts=1790246692",
   "ts=1790251768"
  ],
  "winrate": 70.4,
  "wins": 19
 },
 "B_BREAKOUT_RETEST | BOS_DOWN | DOWNTREND | SHORT": {
  "avg_r": 0.267,
  "n": 35,
  "pnl": 85.76,
  "refs": [
   "ts=1790255830",
   "ts=1791465270",
   "ts=1791465573"
  ],
  "winrate": 85.7,
  "wins": 30
 },
 "B_BREAKOUT_RETEST | BOS_UP | BREAKOUT | LONG": {
  "avg_r": -0.427,
  "n": 16,
  "pnl": -67.8,
  "refs": [
   "ts=1791172737",
   "ts=1791192600",
   "ts=1791703530"
  ],
  "winrate": 31.2,
  "wins": 5
 },
 "B_BREAKOUT_RETEST | BOS_UP | COMPRESSION | LONG": {
  "avg_r": 0.103,
  "n": 18,
  "pnl": 18.41,
  "refs": [
   "ts=1790875371",
   "ts=1790938154",
   "ts=1790940554"
  ],
  "winrate": 77.8,
  "wins": 14
 },
 "B_BREAKOUT_RETEST | BOS_UP | UPTREND | LONG": {
  "avg_r": -0.736,
  "n": 8,
  "pnl": -22.33,
  "refs": [
   "ts=1791659590",
   "ts=1791715301",
   "ts=1791836740"
  ],
  "winrate": 37.5,
  "wins": 3
 },
 "D_RANGE_REVERSAL | BOS_UP | COMPRESSION | SHORT": {
  "avg_r": -0.23,
  "n": 16,
  "pnl": -25.99,
  "refs": [
   "ts=1790234668",
   "ts=1790242256",
   "ts=1790247753"
  ],
  "winrate": 50.0,
  "wins": 8
 },
 "D_RANGE_REVERSAL | NONE | COMPRESSION | SHORT": {
  "avg_r": -0.193,
  "n": 23,
  "pnl": -42.81,
  "refs": [
   "ts=1790235075",
   "ts=1790678431",
   "ts=1790859967"
  ],
  "winrate": 52.2,
  "wins": 12
 },
 "NONE | BOS_DOWN | COMPRESSION | LONG": {
  "avg_r": -0.108,
  "n": 15,
  "pnl": -14.25,
  "refs": [
   "ts=1790942445",
   "ts=1790950155",
   "ts=1790950634"
  ],
  "winrate": 60.0,
  "wins": 9
 },
 "NONE | BOS_DOWN | COMPRESSION | SHORT": {
  "avg_r": 0.466,
  "n": 20,
  "pnl": 26.88,
  "refs": [
   "ts=1790950647",
   "ts=1791205436",
   "ts=1791459655"
  ],
  "winrate": 75.0,
  "wins": 15
 },
 "NONE | BOS_DOWN | DOWNTREND | SHORT": {
  "avg_r": -0.154,
  "n": 15,
  "pnl": -15.09,
  "refs": [
   "ts=1791483918",
   "ts=1791483918",
   "ts=1791822472"
  ],
  "winrate": 53.3,
  "wins": 8
 },
 "NONE | BOS_DOWN | UPTREND | LONG": {
  "avg_r": -0.233,
  "n": 15,
  "pnl": -36.16,
  "refs": [
   "ts=1790944473",
   "ts=1791171483",
   "ts=1791209887"
  ],
  "winrate": 53.3,
  "wins": 8
 },
 "NONE | BOS_UP | COMPRESSION | LONG": {
  "avg_r": 0.209,
  "n": 10,
  "pnl": 20.96,
  "refs": [
   "ts=1790929940",
   "ts=1790938286",
   "ts=1790950567"
  ],
  "winrate": 70.0,
  "wins": 7
 },
 "NONE | BOS_UP | COMPRESSION | SHORT": {
  "avg_r": -0.007,
  "n": 21,
  "pnl": -0.35,
  "refs": [
   "ts=1790861108",
   "ts=1790935903",
   "ts=1791177991"
  ],
  "winrate": 71.4,
  "wins": 15
 },
 "NONE | BOS_UP | DOWNTREND | SHORT": {
  "avg_r": -0.058,
  "n": 23,
  "pnl": -15.58,
  "refs": [
   "ts=1790292546",
   "ts=1790672545",
   "ts=1791480340"
  ],
  "winrate": 60.9,
  "wins": 14
 },
 "NONE | BOS_UP | UPTREND | LONG": {
  "avg_r": -0.167,
  "n": 17,
  "pnl": -22.89,
  "refs": [
   "ts=1790860024",
   "ts=1790944746",
   "ts=1791207439"
  ],
  "winrate": 47.1,
  "wins": 8
 },
 "NONE | NONE | BREAKDOWN | SHORT": {
  "avg_r": 0.025,
  "n": 9,
  "pnl": -0.96,
  "refs": [
   "ts=1791842018",
   "ts=1791849801",
   "ts=1791850443"
  ],
  "winrate": 66.7,
  "wins": 6
 },
 "NONE | NONE | BREAKOUT | LONG": {
  "avg_r": 0.338,
  "n": 9,
  "pnl": 2.72,
  "refs": [
   "ts=1790670756",
   "ts=1790675507",
   "ts=1790935934"
  ],
  "winrate": 66.7,
  "wins": 6
 },
 "NONE | NONE | COMPRESSION | LONG": {
  "avg_r": -0.014,
  "n": 129,
  "pnl": 9.47,
  "refs": [
   "ts=1790868713",
   "ts=1790872757",
   "ts=1790930989"
  ],
  "winrate": 59.7,
  "wins": 77
 },
 "NONE | NONE | COMPRESSION | SHORT": {
  "avg_r": 0.104,
  "n": 194,
  "pnl": 30.72,
  "refs": [
   "ts=1790235075",
   "ts=1790235538",
   "ts=1790240549"
  ],
  "winrate": 66.0,
  "wins": 128
 },
 "NONE | NONE | DOWNTREND | LONG": {
  "avg_r": -0.089,
  "n": 8,
  "pnl": -7.09,
  "refs": [
   "ts=1790305214",
   "ts=1791744554",
   "ts=1791782456"
  ],
  "winrate": 62.5,
  "wins": 5
 },
 "NONE | NONE | DOWNTREND | SHORT": {
  "avg_r": 0.029,
  "n": 115,
  "pnl": 6.36,
  "refs": [
   "ts=1790254886",
   "ts=1790255830",
   "ts=1790283974"
  ],
  "winrate": 67.0,
  "wins": 77
 },
 "NONE | NONE | SIDEWAY | LONG": {
  "avg_r": 0.345,
  "n": 8,
  "pnl": 31.78,
  "refs": [
   "ts=1791859390",
   "ts=1791970339",
   "ts=1791970954"
  ],
  "winrate": 62.5,
  "wins": 5
 },
 "NONE | NONE | SIDEWAY | SHORT": {
  "avg_r": 0.416,
  "n": 20,
  "pnl": 92.77,
  "refs": [
   "ts=1791478900",
   "ts=1791478941",
   "ts=1791824867"
  ],
  "winrate": 75.0,
  "wins": 15
 },
 "NONE | NONE | UPTREND | LONG": {
  "avg_r": -0.124,
  "n": 79,
  "pnl": -59.07,
  "refs": [
   "ts=1790163248",
   "ts=1790163442",
   "ts=1790679289"
  ],
  "winrate": 57.0,
  "wins": 45
 },
 "NONE | NONE | UPTREND | SHORT": {
  "avg_r": 0.005,
  "n": 9,
  "pnl": 1.29,
  "refs": [
   "ts=1791830821",
   "ts=1791890678",
   "ts=1791918198"
  ],
  "winrate": 66.7,
  "wins": 6
 }
}
```
<!-- /AUTO:LESSONS -->

<!-- HUMAN -->` se KHONG bi ghi de.

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

**7. Cảnh báo phải ra khỏi CÁI MÁY (Telegram 2 chiều).** Hệ thống đã có Telegram 1 chiều
(OPEN/CLOSE/KILL + báo cáo), nhưng cảnh báo vận hành thì nằm im trong file ⇒ phải có người mở
máy xem. Nay `tools/telegram_bridge.py` đẩy **câu hỏi đang chờ** ra Telegram (nhắc lại sau 6h nếu
còn treo) và **nhận lệnh vào** (`/status /health /list /ask /answer`, cộng `/dedupe /reset /restart`
khi được cho phép). Nguyên tắc giữ nguyên: **lệnh ghi mặc định TẮT**, chỉ nghe chat_id trong `.env`,
argv cố định (không `shell=True`), mọi lệnh có vết trong log.

**8. Veto vì TÀI NGUYÊN là veto hợp lệ — nhưng phải ghi ĐIỀU KIỆN MỞ LẠI.** Hội đồng bác Kronos
0–4 (máy CPU-only đang chia tài nguyên cho llamafile; chưa có bằng chứng vượt ATR). Điều cần làm
không phải là "bỏ qua repo đó", mà là: ghi sổ **rejected + điều kiện mở lại** (có GPU, hoặc có
giả thuyết đo được), và **rút ra phần dùng được ngay** (đo chất lượng proxy ATR bằng MAE/MFE thật,
backtest phải tính phí/slippage, sinh dữ liệu tổng hợp để stress-test harness) — phần này **0 đồng,
0 dependency**.

**9. Bằng chứng phải ĐỦ MẠNH, không chỉ "có số".** Tôi đo được hình học SL/TP hiện tại là tệ nhất
trong 7 biến thể (PF 0.20) và đề nghị đổi — hội đồng **VETO 0–4** với lý do đúng: **n=31 quá nhỏ**,
chưa có bằng chứng live, và mẫu đó do **người vận hành** chọn. Bài học: (a) *p-value không có thì
"PF thấp" chưa phải bằng chứng*; (b) veto vì **thiếu mẫu** khác veto vì **sai nguyên tắc** — cả hai
đều phải ghi kèm **điều kiện mở lại cụ thể** (≥100 lệnh/arm…); (c) muốn đổi tham số mà **người vận
hành đã chọn** thì cần chính họ đồng ý, dù số liệu nói gì.

**10. Đo cái RẺ trước cái ĐẮT.** Trước khi cài PyTorch + model 25–100M, một probe 200 dòng
(`tools/atr_quality_probe.py`) đã trả lời được câu hỏi cốt lõi: ATR(15m) trung vị **0.580%** trong
khi biên độ thuận thật chỉ **0.23%** (mfe/ATR = 0.37) và chi phí ăn **40–50%** biên độ thuận trung
vị. ⇒ Vấn đề nằm ở **hình học SL/TP + chi phí**, không phải ở chỗ thiếu model dự báo.

**11. Đừng tin MỘT đường equity — hãy bootstrap.** `tools/stress_harness.py` lấy phân phối R thật
rồi mô phỏng 3000 đường: LIVE có **P(kết thúc âm)=13%**, drawdown p90 **13.7R (~16.4% equity)**, và
**P(chạm trần ngày) 16% với trần 2% → 0.3% với trần 6%** ⇒ quyết định nâng trần của hội đồng nay
được **kiểm chứng bằng xác suất**, không chỉ bằng "11/15 ngày lỗ >2%".

**12. Edge mỏng thì CHI PHÍ là kẻ thù số một.** Trên LIVE E(R)=0.085R/lệnh; thêm **0.05R** chi
phí/lệnh ⇒ P(âm) 13%→**35%**; thêm 0.10R ⇒ **62%**. Vì vậy thứ tự ưu tiên đúng là: (1) giảm chi phí
(phí/slippage/không overtrade), (2) hình học SL/TP, (3) mới tới model dự báo. Ghi kèm **giới hạn**:
bootstrap giả định lệnh độc lập — regime xấu làm nhiều lệnh hỏng liên tiếp nên số thực có thể xấu
hơn ⇒ công cụ để **so sánh phương án**, không phải để "chứng minh an toàn".

**13. Veto có LÝ DO CỤ THỂ thì phải trả lời bằng DỮ LIỆU, không phải bằng lời.** Hội đồng VETO
đổi hình học SL/TP với lý do *"n=31 quá nhỏ"*. Việc đúng đắn không phải là tranh luận lại, mà là
**chạy đúng phép đo mà lý do đó đòi**: backtest **10 cặp × 60 ngày** ⇒ n tăng 5–18 lần
(162 / 305 / 558) và xu hướng đơn điệu (SL hẹp ⇒ PF cao). Kết quả: **cùng hội đồng, cùng câu hỏi,
10:14 = 4 VETO → 13:45 = 4 ALLOW (chọn B = 6×ATR/12×ATR)** ⇒ đã thi hành trên cả 2 instance.
Bài học: *một veto tốt là một yêu cầu bổ sung dữ liệu, không phải một bức tường* — và cơ chế chỉ
đáng tin khi nó **đổi ý khi dữ liệu đổi**.

**14. Thu hẹp SL không chỉ "chặt lỗ hơn" — nó đổi CẢ cấu trúc chi phí.** Với risk/lệnh cố định,
`notional = risk / khoảng_cách_SL` ⇒ SL hẹp 2.4× thì **notional tăng 2.4×** và **chi phí quy ra R
tăng 2.4×** (0.017R → 0.040R). Đồng thời số lệnh tăng ~1.9× (học nhanh hơn) và TP trở nên thực tế
hơn (14/69 cần ~40% giá — trong khi MFE trung vị chỉ **0.37×ATR** ⇒ TP bất khả thi). Muốn đổi hình
học thì phải nhìn **cả 4 thứ**: khoảng cách SL, chi phí theo R, số mẫu, và khả năng chạm TP.

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
