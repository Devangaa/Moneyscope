from flask import Flask, render_template, request, abort, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import json
import time

app = Flask(__name__)

perbandingan = {
    'USD': {},
    'EUR': {},
    'JPY': {},
    'MYR': {},
    'KRW': {},
    'CNY': {},
    'SGD': {},
    'AUD': {},
    'IDR': {},
}

currencies = [
    {
        'code': 'USD_IDR',
        'name': 'USD/IDR',
        'price_str': 'Rp14,500',
        'price': 14500.00,
        'change': '+150',
        'percent': '+1.05%',
        'change_class': 'text-success',
        'change_icon': '▲',
    },
    {
        'code': 'EUR_IDR',
        'name': 'EUR/IDR',
        'price_str': 'Rp16,900',
        'price': 16900.00,
        'change': '-200',
        'percent': '-1.18%',
        'change_class': 'text-danger',
        'change_icon': '▼',
    },
    {
        'code': 'JPY_IDR',
        'name': 'JPY/IDR',
        'price_str': 'Rp130',
        'price': 130.00,
        'change': '0.00',
        'percent': '0.00%',
        'change_class': 'text-secondary',
        'change_icon': '▬',
    },
    {
        'code': 'MYR_IDR',
        'name': 'MYR/IDR',
        'price_str': 'Rp3,400',
        'price': 3400.00,
        'change': '-50',
        'percent': '-1.45%',
        'change_class': 'text-danger',
        'change_icon': '▼',
    },
    {
        'code': 'KRW_IDR',
        'name': 'KRW/IDR',
        'price_str': 'Rp12',
        'price': 12.00,
        'change': '+1',
        'percent': '+9.09%',
        'change_class': 'text-success',
        'change_icon': '▲',
    },
    {
        'code': 'CNY_IDR',
        'name': 'CNY/IDR',
        'price_str': 'Rp2,200',
        'price': 2200.00,
        'change': '+10',
        'percent': '+0.45%',
        'change_class': 'text-success',
        'change_icon': '▲',
    },
    {
        'code': 'SGD_IDR',
        'name': 'SGD/IDR',
        'price_str': 'Rp11,000',
        'price': 11000.00,
        'change': '-100',
        'percent': '-0.90%',
        'change_class': 'text-danger',
        'change_icon': '▼',
    },
    {
        'code': 'AUD_IDR',
        'name': 'AUD/IDR',
        'price_str': 'Rp11,000',
        'price': 11000.00,
        'change': '-100',
        'percent': '-0.90%',
        'change_class': 'text-danger',
        'change_icon': '▼',
    },
]

# Cache global untuk data Google Sheets
sheet_cache = {}
CACHE_TIMEOUT = 3600  

def ambil_data_sheet(currency_code):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key("1mpPFKqyTTugKHharPyyC0UpbG7p3xRxElNpty4zFZdM")
    sheet = spreadsheet.worksheet(currency_code)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], dayfirst=True)
    df["Harga Dolar"] = df["Harga Dolar"].astype(float)
    # Return dalam format list of dict [{'date': 'YYYY-MM-DD', 'price': ...}, ...]
    return [
        {"date": row["Tanggal"].strftime("%Y-%m-%d"), "price": row["Harga Dolar"]}
        for _, row in df.iterrows()
    ]

def ambil_data_sheet_cached(currency_code):
    now = time.time()
    if currency_code in sheet_cache:
        data, timestamp = sheet_cache[currency_code]
        if now - timestamp < CACHE_TIMEOUT:
            return data
    data = ambil_data_sheet(currency_code)
    sheet_cache[currency_code] = (data, now)
    return data

def deteksi_harga_ekstrim(arr, left, right):
    if left == right:
        return arr[left], arr[left]
    elif right == left + 1:
        if arr[left][1] > arr[right][1]:
            return arr[left], arr[right]
        else:
            return arr[right], arr[left]
    else:
        mid = (left + right) // 2
        max1, min1 = deteksi_harga_ekstrim(arr, left, mid)
        max2, min2 = deteksi_harga_ekstrim(arr, mid + 1, right)

        max_harga = max1 if max1[1] >= max2[1] else max2
        min_harga = min1 if min1[1] <= min2[1] else min2

        return max_harga, min_harga

def deteksi_perubahan_harga_ekstrim(arr, left, right):
    if left == right:
        return arr[left], arr[left]
    elif right == left + 1:
        if arr[left] > arr[right]:
            return arr[left], arr[right]
        else:
            return arr[right], arr[left]
    else:
        mid = (left + right) // 2
        max1, min1 = deteksi_perubahan_harga_ekstrim(arr, left, mid)
        max2, min2 = deteksi_perubahan_harga_ekstrim(arr, mid + 1, right)

        max_harga = max1 if max1 >= max2 else max2
        min_harga = min1 if min1 <= min2 else min2

        return max_harga, min_harga

def deteksi_tren(data, window_size=3):
    trend_count = {"up": 0, "down": 0, "sideways": 0}
    for i in range(len(data) - window_size + 1):
        start = data[i]
        end = data[i + window_size - 1]
        if end > start:
            trend_count["up"] += 1
        elif end < start:
            trend_count["down"] += 1
        else:
            trend_count["sideways"] += 1
    trend_list = list(trend_count.items())
    n = len(trend_list)
    for i in range(n):
        for j in range(0, n - i - 1):
            if trend_list[j][1] < trend_list[j + 1][1]:
                trend_list[j], trend_list[j + 1] = trend_list[j + 1], trend_list[j]
    if trend_list[0][1] == trend_list[1][1]:
        return "Sideways"
    else:
        if trend_list[0][0] == "up":
            return "Uptrend"
        elif trend_list[0][0] == "down":
            return "Downtrend"
        else:
            return "Sideways"

def ambil_hari_ekstrem(history, days):
    if days > len(history):
        days = len(history)
    sub_history = history[-days:]
    harga_list = [(datetime.strptime(item["date"], "%Y-%m-%d"), item["price"]) for item in sub_history]
    max_data, min_data = deteksi_harga_ekstrim(harga_list, 0, len(harga_list)-1)
    return {
        "harga_tertinggi": {"tanggal": max_data[0].strftime("%d-%m-%Y"), "harga": max_data[1]},
        "harga_terendah": {"tanggal": min_data[0].strftime("%d-%m-%Y"), "harga": min_data[1]}
    }

def ambil_hari_tren(history, days):
    if days > len(history):
        days = len(history)
    sub_history = history[-days:]
    harga_list = [item["price"] for item in sub_history]
    return deteksi_tren(harga_list)

def format_tanggal_indonesia(date_obj):
    bulan_id = [
        'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
        'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
    ]
    hari = date_obj.day
    bulan = bulan_id[date_obj.month - 1]
    tahun = date_obj.year
    return f"{hari} {bulan} {tahun}"

def persentase_perubahan(data:list, left, right):
    if left == right:
        return []
    
    mid = (left + right) // 2
    perubahan_kiri = persentase_perubahan(data, left, mid)
    perubahan_kanan = persentase_perubahan(data, mid + 1, right)

    data_perubahan = []
    if mid + 1 <= right:
        perubahan = [((data[mid + 1] - data[mid]) / data[mid]) * 100]
        data_perubahan = perubahan

    return perubahan_kiri + data_perubahan + perubahan_kanan

def volatilitas(data:list):
    perubahan = persentase_perubahan(data, 0, len(data) - 1)
    avg = sum(perubahan) / len(perubahan)
    deviasi = deviasi_kuadrat(perubahan, 0, len(perubahan) - 1, avg)
    std_deviasi = (deviasi / len(perubahan)) ** 0.5
    return std_deviasi * (252 ** 0.5)


def deviasi_kuadrat(data: list, left, right, ratarata):
    if left == right:
        return (data[left] - ratarata) ** 2
    
    mid = (left + right) // 2
    kiri = deviasi_kuadrat(data, left, mid, ratarata)
    kanan = deviasi_kuadrat(data, mid + 1, right, ratarata)

    return kiri + kanan

def hari_naik_turun(data: list):
    naik = 0
    turun = 0
    for i in range(1, len(data)):
        if data[i] > data[i - 1]:
            naik += 1
        elif data[i] < data[i - 1]:
            turun += 1
    return naik, turun

def streak_naik_turun(data: list):
    streak_naik = 0
    streak_turun = 0
    max_streak_naik = 0
    max_streak_turun = 0

    for i in range(1, len(data)):
        if data[i] > data[i - 1]:
            streak_naik += 1
            streak_turun = 0
        elif data[i] < data[i - 1]:
            streak_turun += 1
            streak_naik = 0
        else:
            streak_naik = 0
            streak_turun = 0

        max_streak_naik = max(max_streak_naik, streak_naik)
        max_streak_turun = max(max_streak_turun, streak_turun)

    return max_streak_naik, max_streak_turun

def sharpe_ratio(expected_return, suku_bunga, volatil):
    if volatil == 0:
        return 0
    return (expected_return - suku_bunga) / volatil

def interest_rate_difference(suku_bunga, suku_bunga_idr):
    return suku_bunga - suku_bunga_idr

def top_potensi():
    items = [(kode, data.get('potensi', 0)) for kode, data in perbandingan.items() if kode != 'IDR']
    n = len(items)

    for i in range(n):
        for j in range(0, n - i - 1):
            if items[j][1] < items[j + 1][1]:
                items[j], items[j + 1] = items[j + 1], items[j]
    return [kode for kode, _ in items[:3]]

#UPDATE DATA
def update_data():
    update_detail_dari_sheet()
    update_perbandingan_dari_sheet()
    update_skba()
    update_potensi()
    print("Data terupdate")

def update_potensi():
    suku_bunga_idr = perbandingan['IDR']['skba']

    for kode, data in perbandingan.items():
        if kode == 'IDR':
            continue

        expected_return = data.get('Rata-rata Perubahan (%)', 0) / 100
        volatil = data.get('Volatilitas(%)', 0) / 100
        suku_bunga = data.get('skba', 0) / 100
        sharperatio = sharpe_ratio(expected_return, suku_bunga, volatil)
        ird = interest_rate_difference(suku_bunga, suku_bunga_idr)

        potensi = ((expected_return * 0.35) + (volatil * 0.25) + (sharperatio * 0.25) + (ird * 0.15)) * 100

        data['potensi'] = round(potensi, 2)

def update_skba():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key("1mpPFKqyTTugKHharPyyC0UpbG7p3xRxElNpty4zFZdM")
    sheet = spreadsheet.worksheet("SKBA")

    data = sheet.get_all_records()
    skba_map = {row['mata uang']: float(row['suku bunga']) for row in data}
    for kode in perbandingan:
        perbandingan[kode]['skba'] = skba_map[kode]

def update_detail_dari_sheet():
    code_map = {
        'USD_IDR': 'USD',
        'EUR_IDR': 'EUR',
        'JPY_IDR': 'JPY',
        'MYR_IDR': 'MYR',
        'KRW_IDR': 'KRW',
        'CNY_IDR': 'CNY',
        'SGD_IDR': 'SGD',
        'AUD_IDR': 'AUD',
    }
    for c in currencies:
        sheet_code = code_map.get(c['code'])
        if not sheet_code or sheet_code == 'IDR':
            continue
        history = ambil_data_sheet_cached(sheet_code)
        if len(history) < 2:
            continue

        last = history[-1]
        prev = history[-2]
        price = last['price']
        price_str = f"Rp{int(price):,}".replace(",", ".")
        change_val = price - prev['price']
        if change_val == 0:
            change = "0.00"
        else:
            change = f"{change_val:+.2f}" if abs(change_val) < 1 else f"{change_val:+.0f}"
        percent_val = (change_val / prev['price']) * 100 if prev['price'] != 0 else 0
        percent = f"{percent_val:+.2f}%"
        if change_val > 0:
            change_class = 'text-success'
            change_icon = '▲'
        elif change_val < 0:
            change_class = 'text-danger'
            change_icon = '▼'
        else:
            change_class = 'text-secondary'
            change_icon = '▬'

        c['price'] = price
        c['price_str'] = price_str
        c['change'] = change
        c['percent'] = percent
        c['change_class'] = change_class
        c['change_icon'] = change_icon

def update_perbandingan_dari_sheet():
    code_map = {
        'USD_IDR': 'USD',
        'EUR_IDR': 'EUR',
        'JPY_IDR': 'JPY',
        'MYR_IDR': 'MYR',
        'KRW_IDR': 'KRW',
        'CNY_IDR': 'CNY',
        'SGD_IDR': 'SGD',
        'AUD_IDR': 'AUD',
    }
    for c in currencies:
        sheet_code = code_map.get(c['code'])
        if not sheet_code or sheet_code == 'IDR':
            continue
        history = ambil_data_sheet_cached(sheet_code)
        if len(history) < 2:
            continue
        days = 365
        if days > len(history):
            days = len(history)
        sub_history = history[-days:]
        harga_list = [item["price"] for item in sub_history]
        rata_rata_perubahan = sum(persentase_perubahan(harga_list, 0, len(harga_list) - 1)) / (len(harga_list) - 1) if len(harga_list) > 1 else 0
        tren = deteksi_tren(harga_list)
        kenaikan_max, penurunan_max = deteksi_perubahan_harga_ekstrim(persentase_perubahan(harga_list, 0, len(harga_list)-1), 0, len(harga_list)-2)
        volatil = volatilitas(harga_list)
        hari_naik, hari_turun = hari_naik_turun(harga_list)
        streak_naik, streak_turun = streak_naik_turun(harga_list)
        persentase_untung = (hari_naik / (hari_naik + hari_turun)) * 100 if (hari_naik + hari_turun) > 0 else 0
        perbandingan[sheet_code] = {
            'Rata-rata Perubahan (%)': round(rata_rata_perubahan, 2),
            'Tren Dominan': tren,
            'Kenaikan Max(%)': round(kenaikan_max, 2),
            'Penurunan Max(%)': round(penurunan_max, 2),
            'Volatilitas(%)': round(volatil, 2),
            'Jumlah Hari Naik': hari_naik,
            'Jumlah Hari Turun': hari_turun,
            'Durasi Tren Naik Terpanjang': streak_naik,
            'Durasi Tren Turun Terpanjang': streak_turun,
            'Persentase Hari Untung(%)': round(persentase_untung, 2)
        }

#APP ROUTE
@app.route('/')
def index():
    update_data()
    return render_template("index.html", currencies=currencies)

@app.route('/potensi')
def potensi():
    update_data()

    potensi_terbaik = top_potensi()
    print(potensi_terbaik)
    satu = ambil_data_sheet_cached(potensi_terbaik[0])
    dua = ambil_data_sheet_cached(potensi_terbaik[1])
    tiga = ambil_data_sheet_cached(potensi_terbaik[2])
    return render_template('potensi.html', 
    perbandingan=perbandingan,
    potensi_terbaik=potensi_terbaik,
    pertama=satu,
    kedua=dua,
    ketiga=tiga
    )

@app.route('/tentang')
def tentang():
    update_data()
    return render_template('tentang.html')

@app.route('/usd')
def usd():
    update_data()
    history = ambil_data_sheet_cached('USD')
    len_data = len(history)
    currency = next((c for c in currencies if c['code'] == 'USD_IDR'), None)
    if not currency:
        abort(404)

    change = currency['change']
    is_up = change.startswith('+')
    is_down = change.startswith('-')

    # Generate data_chart dari history, label: DD-MM-YYYY
    data_chart = {
        "labels": [datetime.strptime(item["date"], "%Y-%m-%d").strftime("%d-%m-%Y") for item in history],
        "values": [item["price"] for item in history]
    }

    ekstrim_7 = ambil_hari_ekstrem(history, 7)
    ekstrim_14 = ambil_hari_ekstrem(history, 14)
    ekstrim_1b = ambil_hari_ekstrem(history, 30)
    ekstrim_3b = ambil_hari_ekstrem(history, 90)
    ekstrim_6b = ambil_hari_ekstrem(history, 180)
    ekstrim_1t = ambil_hari_ekstrem(history, 365)
    ekstrim_5t = ambil_hari_ekstrem(history, 1825) 
    ekstrim_all = ambil_hari_ekstrem(history, len_data)
    ekstrim_json = json.dumps({
        7: {'tertinggi': ekstrim_7['harga_tertinggi'], 'terendah': ekstrim_7['harga_terendah']},
        14: {'tertinggi': ekstrim_14['harga_tertinggi'], 'terendah': ekstrim_14['harga_terendah']},
        30: {'tertinggi': ekstrim_1b['harga_tertinggi'], 'terendah': ekstrim_1b['harga_terendah']},
        90: {'tertinggi': ekstrim_3b['harga_tertinggi'], 'terendah': ekstrim_3b['harga_terendah']},
        180: {'tertinggi': ekstrim_6b['harga_tertinggi'], 'terendah': ekstrim_6b['harga_terendah']},
        365: {'tertinggi': ekstrim_1t['harga_tertinggi'], 'terendah': ekstrim_1t['harga_terendah']},
        1825: {'tertinggi': ekstrim_5t['harga_tertinggi'], 'terendah': ekstrim_5t['harga_terendah']},
        'all': {'tertinggi': ekstrim_all['harga_tertinggi'], 'terendah': ekstrim_all['harga_terendah']}
    })

    tren_dict = {
        '7': ambil_hari_tren(history, 7),
        '14': ambil_hari_tren(history, 14),
        '30': ambil_hari_tren(history, 30),
        '90': ambil_hari_tren(history, 90),
        '180': ambil_hari_tren(history, 180),
        '365': ambil_hari_tren(history, 365),
        '1825': ambil_hari_tren(history, 1825),
        'all': ambil_hari_tren(history, len_data)
    }

    return render_template(
        'mata_uang/usd.html',
        currency=currency,
        is_up=is_up,
        is_down=is_down,
        update_date=format_tanggal_indonesia(datetime.now()),
        currencies=currencies,
        data_chart=data_chart,
        harga_tertinggi_7=ekstrim_7["harga_tertinggi"],
        harga_terendah_7=ekstrim_7["harga_terendah"],
        harga_tertinggi_14=ekstrim_14["harga_tertinggi"],
        harga_terendah_14=ekstrim_14["harga_terendah"],
        harga_tertinggi_1b=ekstrim_1b["harga_tertinggi"],
        harga_terendah_1b=ekstrim_1b["harga_terendah"],
        harga_tertinggi_3b=ekstrim_3b["harga_tertinggi"],
        harga_terendah_3b=ekstrim_3b["harga_terendah"],
        harga_tertinggi_6b=ekstrim_6b["harga_tertinggi"],
        harga_terendah_6b=ekstrim_6b["harga_terendah"],
        harga_tertinggi_1t=ekstrim_1t["harga_tertinggi"],
        harga_terendah_1t=ekstrim_1t["harga_terendah"],
        harga_tertinggi_5t=ekstrim_5t["harga_tertinggi"],
        harga_terendah_5t=ekstrim_5t["harga_terendah"],
        harga_tertinggi_all=ekstrim_all["harga_tertinggi"],
        harga_terendah_all=ekstrim_all["harga_terendah"],
        ekstrim_json=ekstrim_json,
        tren_dict=tren_dict,
        history=history,
        perbandingan=perbandingan
    )

@app.route('/eur')
def eur():
    update_data()
    history = ambil_data_sheet_cached('EUR')
    len_data = len(history)
    currency = next((c for c in currencies if c['code'] == 'EUR_IDR'), None)
    if not currency:
        abort(404)

    change = currency['change']
    is_up = change.startswith('+')
    is_down = change.startswith('-')

    # Data chart EUR/IDR (dummy: gunakan history sama, bisa diganti jika ada data EUR)
    data_chart = {
        "labels": [datetime.strptime(item["date"], "%Y-%m-%d").strftime("%d-%m-%Y") for item in history],
        "values": [item["price"] for item in history]
    }

    
    ekstrim_7 = ambil_hari_ekstrem(history, 7)
    ekstrim_14 = ambil_hari_ekstrem(history, 14)
    ekstrim_1b = ambil_hari_ekstrem(history, 30)
    ekstrim_3b = ambil_hari_ekstrem(history, 90)
    ekstrim_6b = ambil_hari_ekstrem(history, 180)
    ekstrim_1t = ambil_hari_ekstrem(history, 365)
    ekstrim_5t = ambil_hari_ekstrem(history, 1825) 
    ekstrim_all = ambil_hari_ekstrem(history, len_data)
    ekstrim_json = json.dumps({
        7: {'tertinggi': ekstrim_7['harga_tertinggi'], 'terendah': ekstrim_7['harga_terendah']},
        14: {'tertinggi': ekstrim_14['harga_tertinggi'], 'terendah': ekstrim_14['harga_terendah']},
        30: {'tertinggi': ekstrim_1b['harga_tertinggi'], 'terendah': ekstrim_1b['harga_terendah']},
        90: {'tertinggi': ekstrim_3b['harga_tertinggi'], 'terendah': ekstrim_3b['harga_terendah']},
        180: {'tertinggi': ekstrim_6b['harga_tertinggi'], 'terendah': ekstrim_6b['harga_terendah']},
        365: {'tertinggi': ekstrim_1t['harga_tertinggi'], 'terendah': ekstrim_1t['harga_terendah']},
        1825: {'tertinggi': ekstrim_5t['harga_tertinggi'], 'terendah': ekstrim_5t['harga_terendah']},
        'all': {'tertinggi': ekstrim_all['harga_tertinggi'], 'terendah': ekstrim_all['harga_terendah']}
    })

    tren_dict = {
        '7': ambil_hari_tren(history, 7),
        '14': ambil_hari_tren(history, 14),
        '30': ambil_hari_tren(history, 30),
        '90': ambil_hari_tren(history, 90),
        '180': ambil_hari_tren(history, 180),
        '365': ambil_hari_tren(history, 365),
        '1825': ambil_hari_tren(history, 1825),
        'all': ambil_hari_tren(history, len_data)
    }

    return render_template(
        'mata_uang/eur.html',
        currency=currency,
        is_up=is_up,
        is_down=is_down,
        update_date=format_tanggal_indonesia(datetime.now()),
        currencies=currencies,
        data_chart=data_chart,
        harga_tertinggi_7=ekstrim_7["harga_tertinggi"],
        harga_terendah_7=ekstrim_7["harga_terendah"],
        harga_tertinggi_14=ekstrim_14["harga_tertinggi"],
        harga_terendah_14=ekstrim_14["harga_terendah"],
        harga_tertinggi_1b=ekstrim_1b["harga_tertinggi"],
        harga_terendah_1b=ekstrim_1b["harga_terendah"],
        harga_tertinggi_3b=ekstrim_3b["harga_tertinggi"],
        harga_terendah_3b=ekstrim_3b["harga_terendah"],
        harga_tertinggi_6b=ekstrim_6b["harga_tertinggi"],
        harga_terendah_6b=ekstrim_6b["harga_terendah"],
        harga_tertinggi_1t=ekstrim_1t["harga_tertinggi"],
        harga_terendah_1t=ekstrim_1t["harga_terendah"],
        harga_tertinggi_5t=ekstrim_5t["harga_tertinggi"],
        harga_terendah_5t=ekstrim_5t["harga_terendah"],
        harga_tertinggi_all=ekstrim_all["harga_tertinggi"],
        harga_terendah_all=ekstrim_all["harga_terendah"],
        ekstrim_json=ekstrim_json,
        tren_dict=tren_dict,
        history=history,
        perbandingan=perbandingan
    )

@app.route('/jpy')
def jpy():
    update_data()
    history = ambil_data_sheet_cached('JPY')
    len_data = len(history)
    currency = next((c for c in currencies if c['code'] == 'JPY_IDR'), None)
    if not currency:
        abort(404)

    change = currency['change']
    is_up = change.startswith('+')
    is_down = change.startswith('-')

    # Data chart EUR/IDR (dummy: gunakan history sama, bisa diganti jika ada data EUR)
    data_chart = {
        "labels": [datetime.strptime(item["date"], "%Y-%m-%d").strftime("%d-%m-%Y") for item in history],
        "values": [item["price"] for item in history]
    }

    
    ekstrim_7 = ambil_hari_ekstrem(history, 7)
    ekstrim_14 = ambil_hari_ekstrem(history, 14)
    ekstrim_1b = ambil_hari_ekstrem(history, 30)
    ekstrim_3b = ambil_hari_ekstrem(history, 90)
    ekstrim_6b = ambil_hari_ekstrem(history, 180)
    ekstrim_1t = ambil_hari_ekstrem(history, 365)
    ekstrim_5t = ambil_hari_ekstrem(history, 1825) 
    ekstrim_all = ambil_hari_ekstrem(history, len_data)
    ekstrim_json = json.dumps({
        7: {'tertinggi': ekstrim_7['harga_tertinggi'], 'terendah': ekstrim_7['harga_terendah']},
        14: {'tertinggi': ekstrim_14['harga_tertinggi'], 'terendah': ekstrim_14['harga_terendah']},
        30: {'tertinggi': ekstrim_1b['harga_tertinggi'], 'terendah': ekstrim_1b['harga_terendah']},
        90: {'tertinggi': ekstrim_3b['harga_tertinggi'], 'terendah': ekstrim_3b['harga_terendah']},
        180: {'tertinggi': ekstrim_6b['harga_tertinggi'], 'terendah': ekstrim_6b['harga_terendah']},
        365: {'tertinggi': ekstrim_1t['harga_tertinggi'], 'terendah': ekstrim_1t['harga_terendah']},
        1825: {'tertinggi': ekstrim_5t['harga_tertinggi'], 'terendah': ekstrim_5t['harga_terendah']},
        'all': {'tertinggi': ekstrim_all['harga_tertinggi'], 'terendah': ekstrim_all['harga_terendah']}
    })

    tren_dict = {
        '7': ambil_hari_tren(history, 7),
        '14': ambil_hari_tren(history, 14),
        '30': ambil_hari_tren(history, 30),
        '90': ambil_hari_tren(history, 90),
        '180': ambil_hari_tren(history, 180),
        '365': ambil_hari_tren(history, 365),
        '1825': ambil_hari_tren(history, 1825),
        'all': ambil_hari_tren(history, len_data)
    }

    return render_template(
        'mata_uang/jpy.html',
        currency=currency,
        is_up=is_up,
        is_down=is_down,
        update_date=format_tanggal_indonesia(datetime.now()),
        currencies=currencies,
        data_chart=data_chart,
        harga_tertinggi_7=ekstrim_7["harga_tertinggi"],
        harga_terendah_7=ekstrim_7["harga_terendah"],
        harga_tertinggi_14=ekstrim_14["harga_tertinggi"],
        harga_terendah_14=ekstrim_14["harga_terendah"],
        harga_tertinggi_1b=ekstrim_1b["harga_tertinggi"],
        harga_terendah_1b=ekstrim_1b["harga_terendah"],
        harga_tertinggi_3b=ekstrim_3b["harga_tertinggi"],
        harga_terendah_3b=ekstrim_3b["harga_terendah"],
        harga_tertinggi_6b=ekstrim_6b["harga_tertinggi"],
        harga_terendah_6b=ekstrim_6b["harga_terendah"],
        harga_tertinggi_1t=ekstrim_1t["harga_tertinggi"],
        harga_terendah_1t=ekstrim_1t["harga_terendah"],
        harga_tertinggi_5t=ekstrim_5t["harga_tertinggi"],
        harga_terendah_5t=ekstrim_5t["harga_terendah"],
        harga_tertinggi_all=ekstrim_all["harga_tertinggi"],
        harga_terendah_all=ekstrim_all["harga_terendah"],
        tren_dict=tren_dict,
        ekstrim_json=ekstrim_json,
        history=history,
        perbandingan=perbandingan
    )

@app.route('/myr')
def myr():
    update_data()
    history = ambil_data_sheet_cached('MYR')
    len_data = len(history)
    currency = next((c for c in currencies if c['code'] == 'MYR_IDR'), None)
    if not currency:
        abort(404)

    change = currency['change']
    is_up = change.startswith('+')
    is_down = change.startswith('-')

    # Data chart EUR/IDR (dummy: gunakan history sama, bisa diganti jika ada data EUR)
    data_chart = {
        "labels": [datetime.strptime(item["date"], "%Y-%m-%d").strftime("%d-%m-%Y") for item in history],
        "values": [item["price"] for item in history]
    }

    
    ekstrim_7 = ambil_hari_ekstrem(history, 7)
    ekstrim_14 = ambil_hari_ekstrem(history, 14)
    ekstrim_1b = ambil_hari_ekstrem(history, 30)
    ekstrim_3b = ambil_hari_ekstrem(history, 90)
    ekstrim_6b = ambil_hari_ekstrem(history, 180)
    ekstrim_1t = ambil_hari_ekstrem(history, 365)
    ekstrim_5t = ambil_hari_ekstrem(history, 1825) 
    ekstrim_all = ambil_hari_ekstrem(history, len_data)
    ekstrim_json = json.dumps({
        7: {'tertinggi': ekstrim_7['harga_tertinggi'], 'terendah': ekstrim_7['harga_terendah']},
        14: {'tertinggi': ekstrim_14['harga_tertinggi'], 'terendah': ekstrim_14['harga_terendah']},
        30: {'tertinggi': ekstrim_1b['harga_tertinggi'], 'terendah': ekstrim_1b['harga_terendah']},
        90: {'tertinggi': ekstrim_3b['harga_tertinggi'], 'terendah': ekstrim_3b['harga_terendah']},
        180: {'tertinggi': ekstrim_6b['harga_tertinggi'], 'terendah': ekstrim_6b['harga_terendah']},
        365: {'tertinggi': ekstrim_1t['harga_tertinggi'], 'terendah': ekstrim_1t['harga_terendah']},
        1825: {'tertinggi': ekstrim_5t['harga_tertinggi'], 'terendah': ekstrim_5t['harga_terendah']},
        'all': {'tertinggi': ekstrim_all['harga_tertinggi'], 'terendah': ekstrim_all['harga_terendah']}
    })

    tren_dict = {
        '7': ambil_hari_tren(history, 7),
        '14': ambil_hari_tren(history, 14),
        '30': ambil_hari_tren(history, 30),
        '90': ambil_hari_tren(history, 90),
        '180': ambil_hari_tren(history, 180),
        '365': ambil_hari_tren(history, 365),
        '1825': ambil_hari_tren(history, 1825),
        'all': ambil_hari_tren(history, len_data)
    }

    return render_template(
        'mata_uang/myr.html',
        currency=currency,
        is_up=is_up,
        is_down=is_down,
        update_date=format_tanggal_indonesia(datetime.now()),
        currencies=currencies,
        data_chart=data_chart,
        harga_tertinggi_7=ekstrim_7["harga_tertinggi"],
        harga_terendah_7=ekstrim_7["harga_terendah"],
        harga_tertinggi_14=ekstrim_14["harga_tertinggi"],
        harga_terendah_14=ekstrim_14["harga_terendah"],
        harga_tertinggi_1b=ekstrim_1b["harga_tertinggi"],
        harga_terendah_1b=ekstrim_1b["harga_terendah"],
        harga_tertinggi_3b=ekstrim_3b["harga_tertinggi"],
        harga_terendah_3b=ekstrim_3b["harga_terendah"],
        harga_tertinggi_6b=ekstrim_6b["harga_tertinggi"],
        harga_terendah_6b=ekstrim_6b["harga_terendah"],
        harga_tertinggi_1t=ekstrim_1t["harga_tertinggi"],
        harga_terendah_1t=ekstrim_1t["harga_terendah"],
        harga_tertinggi_5t=ekstrim_5t["harga_tertinggi"],
        harga_terendah_5t=ekstrim_5t["harga_terendah"],
        harga_tertinggi_all=ekstrim_all["harga_tertinggi"],
        harga_terendah_all=ekstrim_all["harga_terendah"],
        tren_dict=tren_dict,
        ekstrim_json=ekstrim_json,
        history=history,
        perbandingan=perbandingan
    )

@app.route('/krw')
def krw():
    update_data()
    history = ambil_data_sheet_cached('KRW')
    len_data = len(history)
    currency = next((c for c in currencies if c['code'] == 'KRW_IDR'), None)
    if not currency:
        abort(404)

    change = currency['change']
    is_up = change.startswith('+')
    is_down = change.startswith('-')

    # Data chart EUR/IDR (dummy: gunakan history sama, bisa diganti jika ada data EUR)
    data_chart = {
        "labels": [datetime.strptime(item["date"], "%Y-%m-%d").strftime("%d-%m-%Y") for item in history],
        "values": [item["price"] for item in history]
    }

    
    ekstrim_7 = ambil_hari_ekstrem(history, 7)
    ekstrim_14 = ambil_hari_ekstrem(history, 14)
    ekstrim_1b = ambil_hari_ekstrem(history, 30)
    ekstrim_3b = ambil_hari_ekstrem(history, 90)
    ekstrim_6b = ambil_hari_ekstrem(history, 180)
    ekstrim_1t = ambil_hari_ekstrem(history, 365)
    ekstrim_5t = ambil_hari_ekstrem(history, 1825) 
    ekstrim_all = ambil_hari_ekstrem(history, len_data)
    ekstrim_json = json.dumps({
        7: {'tertinggi': ekstrim_7['harga_tertinggi'], 'terendah': ekstrim_7['harga_terendah']},
        14: {'tertinggi': ekstrim_14['harga_tertinggi'], 'terendah': ekstrim_14['harga_terendah']},
        30: {'tertinggi': ekstrim_1b['harga_tertinggi'], 'terendah': ekstrim_1b['harga_terendah']},
        90: {'tertinggi': ekstrim_3b['harga_tertinggi'], 'terendah': ekstrim_3b['harga_terendah']},
        180: {'tertinggi': ekstrim_6b['harga_tertinggi'], 'terendah': ekstrim_6b['harga_terendah']},
        365: {'tertinggi': ekstrim_1t['harga_tertinggi'], 'terendah': ekstrim_1t['harga_terendah']},
        1825: {'tertinggi': ekstrim_5t['harga_tertinggi'], 'terendah': ekstrim_5t['harga_terendah']},
        'all': {'tertinggi': ekstrim_all['harga_tertinggi'], 'terendah': ekstrim_all['harga_terendah']}
    })

    tren_dict = {
        '7': ambil_hari_tren(history, 7),
        '14': ambil_hari_tren(history, 14),
        '30': ambil_hari_tren(history, 30),
        '90': ambil_hari_tren(history, 90),
        '180': ambil_hari_tren(history, 180),
        '365': ambil_hari_tren(history, 365),
        '1825': ambil_hari_tren(history, 1825),
        'all': ambil_hari_tren(history, len_data)
    }

    return render_template(
        'mata_uang/krw.html',
        currency=currency,
        is_up=is_up,
        is_down=is_down,
        update_date=format_tanggal_indonesia(datetime.now()),
        currencies=currencies,
        data_chart=data_chart,
        harga_tertinggi_7=ekstrim_7["harga_tertinggi"],
        harga_terendah_7=ekstrim_7["harga_terendah"],
        harga_tertinggi_14=ekstrim_14["harga_tertinggi"],
        harga_terendah_14=ekstrim_14["harga_terendah"],
        harga_tertinggi_1b=ekstrim_1b["harga_tertinggi"],
        harga_terendah_1b=ekstrim_1b["harga_terendah"],
        harga_tertinggi_3b=ekstrim_3b["harga_tertinggi"],
        harga_terendah_3b=ekstrim_3b["harga_terendah"],
        harga_tertinggi_6b=ekstrim_6b["harga_tertinggi"],
        harga_terendah_6b=ekstrim_6b["harga_terendah"],
        harga_tertinggi_1t=ekstrim_1t["harga_tertinggi"],
        harga_terendah_1t=ekstrim_1t["harga_terendah"],
        harga_tertinggi_5t=ekstrim_5t["harga_tertinggi"],
        harga_terendah_5t=ekstrim_5t["harga_terendah"],
        harga_tertinggi_all=ekstrim_all["harga_tertinggi"],
        harga_terendah_all=ekstrim_all["harga_terendah"],
        tren_dict=tren_dict,
        ekstrim_json=ekstrim_json,
        history=history,
        perbandingan=perbandingan
    )

@app.route('/cny')
def cny():
    update_data()
    history = ambil_data_sheet_cached('CNY')
    len_data = len(history)
    currency = next((c for c in currencies if c['code'] == 'CNY_IDR'), None)
    if not currency:
        abort(404)

    change = currency['change']
    is_up = change.startswith('+')
    is_down = change.startswith('-')

    # Data chart EUR/IDR (dummy: gunakan history sama, bisa diganti jika ada data EUR)
    data_chart = {
        "labels": [datetime.strptime(item["date"], "%Y-%m-%d").strftime("%d-%m-%Y") for item in history],
        "values": [item["price"] for item in history]
    }

    
    ekstrim_7 = ambil_hari_ekstrem(history, 7)
    ekstrim_14 = ambil_hari_ekstrem(history, 14)
    ekstrim_1b = ambil_hari_ekstrem(history, 30)
    ekstrim_3b = ambil_hari_ekstrem(history, 90)
    ekstrim_6b = ambil_hari_ekstrem(history, 180)
    ekstrim_1t = ambil_hari_ekstrem(history, 365)
    ekstrim_5t = ambil_hari_ekstrem(history, 1825) 
    ekstrim_all = ambil_hari_ekstrem(history, len_data)
    ekstrim_json = json.dumps({
        7: {'tertinggi': ekstrim_7['harga_tertinggi'], 'terendah': ekstrim_7['harga_terendah']},
        14: {'tertinggi': ekstrim_14['harga_tertinggi'], 'terendah': ekstrim_14['harga_terendah']},
        30: {'tertinggi': ekstrim_1b['harga_tertinggi'], 'terendah': ekstrim_1b['harga_terendah']},
        90: {'tertinggi': ekstrim_3b['harga_tertinggi'], 'terendah': ekstrim_3b['harga_terendah']},
        180: {'tertinggi': ekstrim_6b['harga_tertinggi'], 'terendah': ekstrim_6b['harga_terendah']},
        365: {'tertinggi': ekstrim_1t['harga_tertinggi'], 'terendah': ekstrim_1t['harga_terendah']},
        1825: {'tertinggi': ekstrim_5t['harga_tertinggi'], 'terendah': ekstrim_5t['harga_terendah']},
        'all': {'tertinggi': ekstrim_all['harga_tertinggi'], 'terendah': ekstrim_all['harga_terendah']}
    })

    tren_dict = {
        '7': ambil_hari_tren(history, 7),
        '14': ambil_hari_tren(history, 14),
        '30': ambil_hari_tren(history, 30),
        '90': ambil_hari_tren(history, 90),
        '180': ambil_hari_tren(history, 180),
        '365': ambil_hari_tren(history, 365),
        '1825': ambil_hari_tren(history, 1825),
        'all': ambil_hari_tren(history, len_data)
    }

    return render_template(
        'mata_uang/cny.html',
        currency=currency,
        is_up=is_up,
        is_down=is_down,
        update_date=format_tanggal_indonesia(datetime.now()),
        currencies=currencies,
        data_chart=data_chart,
        harga_tertinggi_7=ekstrim_7["harga_tertinggi"],
        harga_terendah_7=ekstrim_7["harga_terendah"],
        harga_tertinggi_14=ekstrim_14["harga_tertinggi"],
        harga_terendah_14=ekstrim_14["harga_terendah"],
        harga_tertinggi_1b=ekstrim_1b["harga_tertinggi"],
        harga_terendah_1b=ekstrim_1b["harga_terendah"],
        harga_tertinggi_3b=ekstrim_3b["harga_tertinggi"],
        harga_terendah_3b=ekstrim_3b["harga_terendah"],
        harga_tertinggi_6b=ekstrim_6b["harga_tertinggi"],
        harga_terendah_6b=ekstrim_6b["harga_terendah"],
        harga_tertinggi_1t=ekstrim_1t["harga_tertinggi"],
        harga_terendah_1t=ekstrim_1t["harga_terendah"],
        harga_tertinggi_5t=ekstrim_5t["harga_tertinggi"],
        harga_terendah_5t=ekstrim_5t["harga_terendah"],
        harga_tertinggi_all=ekstrim_all["harga_tertinggi"],
        harga_terendah_all=ekstrim_all["harga_terendah"],
        ekstrim_json=ekstrim_json,
        tren_dict=tren_dict,
        history=history,
        perbandingan=perbandingan
    )

@app.route('/sgd')
def sgd():
    update_data()
    history = ambil_data_sheet_cached('SGD')
    len_data = len(history)
    currency = next((c for c in currencies if c['code'] == 'SGD_IDR'), None)
    if not currency:
        abort(404)

    change = currency['change']
    is_up = change.startswith('+')
    is_down = change.startswith('-')

    # Data chart EUR/IDR (dummy: gunakan history sama, bisa diganti jika ada data EUR)
    data_chart = {
        "labels": [datetime.strptime(item["date"], "%Y-%m-%d").strftime("%d-%m-%Y") for item in history],
        "values": [item["price"] for item in history]
    }

    ekstrim_7 = ambil_hari_ekstrem(history, 7)
    ekstrim_14 = ambil_hari_ekstrem(history, 14)
    ekstrim_1b = ambil_hari_ekstrem(history, 30)
    ekstrim_3b = ambil_hari_ekstrem(history, 90)
    ekstrim_6b = ambil_hari_ekstrem(history, 180)
    ekstrim_1t = ambil_hari_ekstrem(history, 365)
    ekstrim_5t = ambil_hari_ekstrem(history, 1825) 
    ekstrim_all = ambil_hari_ekstrem(history, len_data)
    ekstrim_json = json.dumps({
        7: {'tertinggi': ekstrim_7['harga_tertinggi'], 'terendah': ekstrim_7['harga_terendah']},
        14: {'tertinggi': ekstrim_14['harga_tertinggi'], 'terendah': ekstrim_14['harga_terendah']},
        30: {'tertinggi': ekstrim_1b['harga_tertinggi'], 'terendah': ekstrim_1b['harga_terendah']},
        90: {'tertinggi': ekstrim_3b['harga_tertinggi'], 'terendah': ekstrim_3b['harga_terendah']},
        180: {'tertinggi': ekstrim_6b['harga_tertinggi'], 'terendah': ekstrim_6b['harga_terendah']},
        365: {'tertinggi': ekstrim_1t['harga_tertinggi'], 'terendah': ekstrim_1t['harga_terendah']},
        1825: {'tertinggi': ekstrim_5t['harga_tertinggi'], 'terendah': ekstrim_5t['harga_terendah']},
        'all': {'tertinggi': ekstrim_all['harga_tertinggi'], 'terendah': ekstrim_all['harga_terendah']}
    })

    tren_dict = {
        '7': ambil_hari_tren(history, 7),
        '14': ambil_hari_tren(history, 14),
        '30': ambil_hari_tren(history, 30),
        '90': ambil_hari_tren(history, 90),
        '180': ambil_hari_tren(history, 180),
        '365': ambil_hari_tren(history, 365),
        '1825': ambil_hari_tren(history, 1825),
        'all': ambil_hari_tren(history, len_data)
    }

    return render_template(
        'mata_uang/sgd.html',
        currency=currency,
        is_up=is_up,
        is_down=is_down,
        update_date=format_tanggal_indonesia(datetime.now()),
        currencies=currencies,
        data_chart=data_chart,
        harga_tertinggi_7=ekstrim_7["harga_tertinggi"],
        harga_terendah_7=ekstrim_7["harga_terendah"],
        harga_tertinggi_14=ekstrim_14["harga_tertinggi"],
        harga_terendah_14=ekstrim_14["harga_terendah"],
        harga_tertinggi_1b=ekstrim_1b["harga_tertinggi"],
        harga_terendah_1b=ekstrim_1b["harga_terendah"],
        harga_tertinggi_3b=ekstrim_3b["harga_tertinggi"],
        harga_terendah_3b=ekstrim_3b["harga_terendah"],
        harga_tertinggi_6b=ekstrim_6b["harga_tertinggi"],
        harga_terendah_6b=ekstrim_6b["harga_terendah"],
        harga_tertinggi_1t=ekstrim_1t["harga_tertinggi"],
        harga_terendah_1t=ekstrim_1t["harga_terendah"],
        harga_tertinggi_5t=ekstrim_5t["harga_tertinggi"],
        harga_terendah_5t=ekstrim_5t["harga_terendah"],
        harga_tertinggi_all=ekstrim_all["harga_tertinggi"],
        harga_terendah_all=ekstrim_all["harga_terendah"],
        tren_dict=tren_dict,
        ekstrim_json=ekstrim_json,
        history=history,
        perbandingan=perbandingan
    )

@app.route('/aud')
def aud():
    update_data()
    history = ambil_data_sheet_cached('AUD')
    len_data = len(history)
    currency = next((c for c in currencies if c['code'] == 'AUD_IDR'), None)
    if not currency:
        abort(404)

    change = currency['change']
    is_up = change.startswith('+')
    is_down = change.startswith('-')

    # Data chart EUR/IDR (dummy: gunakan history sama, bisa diganti jika ada data EUR)
    data_chart = {
        "labels": [datetime.strptime(item["date"], "%Y-%m-%d").strftime("%d-%m-%Y") for item in history],
        "values": [item["price"] for item in history]
    }

    ekstrim_7 = ambil_hari_ekstrem(history, 7)
    ekstrim_14 = ambil_hari_ekstrem(history, 14)
    ekstrim_1b = ambil_hari_ekstrem(history, 30)
    ekstrim_3b = ambil_hari_ekstrem(history, 90)
    ekstrim_6b = ambil_hari_ekstrem(history, 180)
    ekstrim_1t = ambil_hari_ekstrem(history, 365)
    ekstrim_5t = ambil_hari_ekstrem(history, 1825) 
    ekstrim_all = ambil_hari_ekstrem(history, len_data)
    ekstrim_json = json.dumps({
        7: {'tertinggi': ekstrim_7['harga_tertinggi'], 'terendah': ekstrim_7['harga_terendah']},
        14: {'tertinggi': ekstrim_14['harga_tertinggi'], 'terendah': ekstrim_14['harga_terendah']},
        30: {'tertinggi': ekstrim_1b['harga_tertinggi'], 'terendah': ekstrim_1b['harga_terendah']},
        90: {'tertinggi': ekstrim_3b['harga_tertinggi'], 'terendah': ekstrim_3b['harga_terendah']},
        180: {'tertinggi': ekstrim_6b['harga_tertinggi'], 'terendah': ekstrim_6b['harga_terendah']},
        365: {'tertinggi': ekstrim_1t['harga_tertinggi'], 'terendah': ekstrim_1t['harga_terendah']},
        1825: {'tertinggi': ekstrim_5t['harga_tertinggi'], 'terendah': ekstrim_5t['harga_terendah']},
        'all': {'tertinggi': ekstrim_all['harga_tertinggi'], 'terendah': ekstrim_all['harga_terendah']}
    })

    tren_dict = {
        '7': ambil_hari_tren(history, 7),
        '14': ambil_hari_tren(history, 14),
        '30': ambil_hari_tren(history, 30),
        '90': ambil_hari_tren(history, 90),
        '180': ambil_hari_tren(history, 180),
        '365': ambil_hari_tren(history, 365),
        '1825': ambil_hari_tren(history, 1825),
        'all': ambil_hari_tren(history, len_data)
    }

    return render_template(
        'mata_uang/aud.html',
        currency=currency,
        is_up=is_up,
        is_down=is_down,
        update_date=format_tanggal_indonesia(datetime.now()),
        currencies=currencies,
        data_chart=data_chart,
        harga_tertinggi_7=ekstrim_7["harga_tertinggi"],
        harga_terendah_7=ekstrim_7["harga_terendah"],
        harga_tertinggi_14=ekstrim_14["harga_tertinggi"],
        harga_terendah_14=ekstrim_14["harga_terendah"],
        harga_tertinggi_1b=ekstrim_1b["harga_tertinggi"],
        harga_terendah_1b=ekstrim_1b["harga_terendah"],
        harga_tertinggi_3b=ekstrim_3b["harga_tertinggi"],
        harga_terendah_3b=ekstrim_3b["harga_terendah"],
        harga_tertinggi_6b=ekstrim_6b["harga_tertinggi"],
        harga_terendah_6b=ekstrim_6b["harga_terendah"],
        harga_tertinggi_1t=ekstrim_1t["harga_tertinggi"],
        harga_terendah_1t=ekstrim_1t["harga_terendah"],
        harga_tertinggi_5t=ekstrim_5t["harga_tertinggi"],
        harga_terendah_5t=ekstrim_5t["harga_terendah"],
        harga_tertinggi_all=ekstrim_all["harga_tertinggi"],
        harga_terendah_all=ekstrim_all["harga_terendah"],
        tren_dict=tren_dict,
        ekstrim_json=ekstrim_json,
        history=history,
        perbandingan=perbandingan
    )

@app.route('/chart_data/<currency>/<range>')
def chart_data(currency, range):
    # Map range ke (jumlah_hari, interval_sampling)
    range_map = {
        '7': (7, 1),
        '14': (14, 1),
        '1bulan': (30, 1),
        '3bulan': (90, 3),
        '6bulan': (180, 5),
        '1tahun': (365, 8),
        '5tahun': (1825, 26),
        'all': (None, 30)
    }
    if range not in range_map:
        return jsonify({'error': 'Invalid range'}), 400
    days, interval = range_map[range]
    history = ambil_data_sheet_cached(currency.upper())
    if not history:
        return jsonify({'error': 'No data'}), 404
    # Ambil data sesuai rentang hari
    if days:
        history = history[-days:]
    # Sampling interval
    sampled = history[::interval]
    # Pastikan data terakhir selalu ikut
    if sampled and sampled[-1]['date'] != history[-1]['date']:
        sampled.append(history[-1])
    labels = [item['date'] for item in sampled]
    values = [item['price'] for item in sampled]
    return jsonify({'labels': labels, 'values': values})

if __name__ == '__main__':
    app.run(debug=True)
