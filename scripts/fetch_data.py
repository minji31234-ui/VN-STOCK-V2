#!/usr/bin/env python3
"""Tải nến cổ phiếu Việt Nam bằng thư viện vnstock (chạy trong GitHub Actions),
ghi JSON tĩnh vào _site/data để trang web đọc. Giá tính theo nghìn đồng."""
import json, os, sys, time, datetime as dt
import pandas as pd
from vnstock import Quote
try:
    from vnstock import Listing
except Exception:
    Listing = None

SITE = os.environ.get('SITE_DIR', '_site')
OUT = os.path.join(SITE, 'data')
DELAY = float(os.environ.get('REQ_DELAY', '3.2'))          # giây giữa hai request, tránh bị giới hạn tần suất
SOURCES = [s.strip() for s in os.environ.get('VN_SOURCES', 'KBS,VCI').split(',') if s.strip()]
MAX_MIN = float(os.environ.get('MAX_MINUTES', '100'))      # quá thời gian này thì dừng và ghi phần đã có
FETCH_HOURLY = os.environ.get('FETCH_HOURLY', '1') != '0'
HOUR, DAY = 3600000, 86400000
TZ = 'Asia/Ho_Chi_Minh'
CAP = {'1h': 1000, '1d': 1500, '1w': 800}
IV = {'1h': ['1H', '60m'], '1d': ['1D', 'd'], '1w': ['1W', 'w']}
t0 = time.time()
today = dt.date.today()
START = {'1h': (today - dt.timedelta(days=540)).isoformat(), '1d': '2018-01-01', '1w': '2010-01-01'}

def log(*a):
    print(*a, flush=True)

def group_symbols(x):
    if x is None:
        return []
    if isinstance(x, pd.DataFrame):
        col = next((c for c in x.columns if str(c).lower() in ('symbol', 'ticker', 'code')), x.columns[0])
        x = x[col]
    return [str(s).strip().upper() for s in list(x) if str(s).strip()]

def vn30_live():
    if Listing is None:
        return None
    for src in SOURCES:
        try:
            syms = group_symbols(Listing(source=src).symbols_by_group('VN30'))
            if 25 <= len(syms) <= 35:
                log('VN30 lấy từ', src, len(syms), 'mã')
                return syms
        except Exception as e:
            log('Không lấy được VN30 từ', src, '-', e)
    return None

def universe(wl):
    groups, tags, order = [], {}, []
    for g, v in wl['groups'].items():
        if v == 'auto':
            v = vn30_live() or wl.get('VN30_du_phong', [])
            if not v:
                continue
        v = [s.upper() for s in v]
        groups.append(g)
        for s in v:
            if s not in tags:
                tags[s] = []; order.append(s)
            if g not in tags[s]:
                tags[s].append(g)
    return groups, tags, order

def norm(df, tf):
    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]
    tcol = next((c for c in ('time', 'date', 'datetime') if c in df.columns), df.columns[0])
    ts = pd.to_datetime(df[tcol])
    ts = ts.dt.tz_localize(TZ) if ts.dt.tz is None else ts.dt.tz_convert(TZ)
    rows = {}
    for i in range(len(df)):
        try:
            o, h, l, c = (float(df[k].iloc[i]) for k in ('open', 'high', 'low', 'close'))
            v = float(df['volume'].iloc[i]) if 'volume' in df.columns else 0.0
            t = int(ts.iloc[i].timestamp() * 1000)
        except Exception:
            continue
        if any(x != x for x in (o, h, l, c)):
            continue
        rows[t] = [o, h, l, c, 0.0 if v != v else v]
    bars = sorted(([t] + r for t, r in rows.items()), key=lambda b: b[0])
    if not bars:
        return []
    closes = sorted(b[4] for b in bars)
    if closes[len(closes) // 2] > 1000:           # nguồn trả về đồng -> đổi sang nghìn đồng
        for b in bars:
            for k in (1, 2, 3, 4):
                b[k] /= 1000.0
    out = []
    for b in bars:
        t = b[0]
        d0 = t - ((t + 7 * HOUR) % DAY)           # 00:00 giờ Việt Nam của ngày đó
        if tf == '1h':
            ct = t + HOUR
        elif tf == '1d':
            ct = d0 + 15 * HOUR                   # đóng cửa 15:00
        else:
            wd = ((d0 + 7 * HOUR) // DAY + 3) % 7  # 0 = thứ Hai
            ct = d0 - wd * DAY + 4 * DAY + 15 * HOUR
        out.append([t, round(b[1], 3), round(b[2], 3), round(b[3], 3), round(b[4], 3), int(b[5]), ct])
    return out[-CAP[tf]:]

def hist(sym, tf):
    for src in SOURCES:
        for iv in IV[tf]:
            for attempt in range(2):
                try:
                    df = Quote(symbol=sym, source=src).history(start=START[tf], end=today.isoformat(), interval=iv)
                    time.sleep(DELAY)
                    if df is not None and len(df) >= 30:
                        bars = norm(df, tf)
                        if len(bars) >= 30:
                            return bars
                    break
                except Exception as e:
                    msg = str(e).lower()
                    time.sleep(DELAY)
                    if attempt == 0 and any(k in msg for k in ('429', 'rate', 'limit', 'too many')):
                        log('  bị giới hạn tần suất, chờ 30 giây...')
                        time.sleep(30)
                        continue
                    break
    return None

def save(sym, tf, bars):
    with open(os.path.join(OUT, f'{sym}__{tf}.json'), 'w') as f:
        json.dump(bars, f, separators=(',', ':'))

def main():
    os.makedirs(OUT, exist_ok=True)
    wl = json.load(open('watchlist.json', encoding='utf-8'))
    groups, tags, order = universe(wl)
    log(f'{len(order)} mã trong {len(groups)} nhóm')
    meta, fails = [], []
    for n, sym in enumerate(order, 1):
        if (time.time() - t0) / 60 > MAX_MIN:
            log('Hết thời gian cho phép, dừng sớm.'); fails += order[n - 1:]; break
        d1 = hist(sym, '1d')
        if not d1:
            fails.append(sym); log(f'[{n}/{len(order)}] LỖI {sym}'); continue
        save(sym, '1d', d1)
        have = ['1d']
        w1 = hist(sym, '1w')
        if w1:
            save(sym, '1w', w1); have.append('1w')
        if FETCH_HOURLY:
            h1 = hist(sym, '1h')
            if h1:
                save(sym, '1h', h1); have.append('1h')
        chg = (d1[-1][4] / d1[-2][4] - 1) * 100 if len(d1) > 1 else None
        meta.append({'sym': sym, 'tags': tags[sym], 'chg': chg, 'vol': d1[-1][5] * d1[-1][4], 'price': d1[-1][4], 'tfs': have})
        log(f'[{n}/{len(order)}] ok {sym} {have}')
    if len(meta) < max(5, len(order) // 2):
        sys.exit(f'Chỉ tải được {len(meta)}/{len(order)} mã, không deploy dữ liệu lỗi.')
    meta.sort(key=lambda m: -m['vol'])
    with open(os.path.join(OUT, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump({'updated': int(time.time() * 1000), 'groups': groups, 'symbols': meta, 'failed': fails}, f, ensure_ascii=False, separators=(',', ':'))
    log(f'Xong: {len(meta)} mã, lỗi: {fails}')

if __name__ == '__main__':
    main()
