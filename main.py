from flask import Flask, render_template, request, abort, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import json
import time

app = Flask(__name__)

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
CACHE_TIMEOUT = 600  

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

def get_ekstrim_for_days(history, days):
    if days > len(history):
        days = len(history)
    sub_history = history[-days:]
    harga_list = [(datetime.strptime(item["date"], "%Y-%m-%d"), item["price"]) for item in sub_history]
    max_data, min_data = deteksi_harga_ekstrim(harga_list, 0, len(harga_list)-1)
    return {
        "harga_tertinggi": {"tanggal": max_data[0].strftime("%d-%m-%Y"), "harga": max_data[1]},
        "harga_terendah": {"tanggal": min_data[0].strftime("%d-%m-%Y"), "harga": min_data[1]}
    }

def get_tren_for_days(history, days):
    if days > len(history):
        days = len(history)
    sub_history = history[-days:]
    harga_list = [item["price"] for item in sub_history]
    return deteksi_tren(harga_list)

@app.route('/')
def index():
    update_currencies_from_sheet()
    return render_template("index.html", currencies=currencies)

# Data dummy perbandingan untuk tabel perbandingan antar mata uang
perbandingan_dummy = {
    'USD': {
        'Rata-rata Perubahan (%)': '0.85',
        'Tren Dominan': 'Uptrend',
        'Kenaikan Max(%)': '2.10',
        'Penurunan Max(%)': '-1.50',
        'Volatilitas(%)': '0.95',
        'Jumlah Hari Naik': '8',
        'Jumlah Hari Turun': '6',
        'Durasi Tren Naik Terpanjang': '3',
        'Durasi Tren Turun Terpanjang': '2',
        'Persentase Hari Untung(%)': '57.1'
    },
    'EUR': {
        'Rata-rata Perubahan (%)': '0.60',
        'Tren Dominan': 'Sideways',
        'Kenaikan Max(%)': '1.80',
        'Penurunan Max(%)': '-1.20',
        'Volatilitas(%)': '0.80',
        'Jumlah Hari Naik': '7',
        'Jumlah Hari Turun': '7',
        'Durasi Tren Naik Terpanjang': '2',
        'Durasi Tren Turun Terpanjang': '2',
        'Persentase Hari Untung(%)': '50.0'
    },
    'SGD': {
        'Rata-rata Perubahan (%)': '0.72',
        'Tren Dominan': 'Downtrend',
        'Kenaikan Max(%)': '1.50',
        'Penurunan Max(%)': '-2.00',
        'Volatilitas(%)': '1.10',
        'Jumlah Hari Naik': '6',
        'Jumlah Hari Turun': '8',
        'Durasi Tren Naik Terpanjang': '2',
        'Durasi Tren Turun Terpanjang': '3',
        'Persentase Hari Untung(%)': '42.9'
    },
    'AUD': {
        'Rata-rata Perubahan (%)': '0.55',
        'Tren Dominan': 'Sideways',
        'Kenaikan Max(%)': '1.20',
        'Penurunan Max(%)': '-1.10',
        'Volatilitas(%)': '0.75',
        'Jumlah Hari Naik': '6',
        'Jumlah Hari Turun': '8',
        'Durasi Tren Naik Terpanjang': '2',
        'Durasi Tren Turun Terpanjang': '3',
        'Persentase Hari Untung(%)': '42.9'
    }
}

def format_tanggal_indonesia(date_obj):
    bulan_id = [
        'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
        'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
    ]
    hari = date_obj.day
    bulan = bulan_id[date_obj.month - 1]
    tahun = date_obj.year
    return f"{hari} {bulan} {tahun}"

def update_currencies_from_sheet():
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
        if not sheet_code:
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

@app.route('/usd')
def usd():
    update_currencies_from_sheet()
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

    ekstrim_7 = get_ekstrim_for_days(history, 7)
    ekstrim_14 = get_ekstrim_for_days(history, 14)
    ekstrim_1b = get_ekstrim_for_days(history, 30)
    ekstrim_3b = get_ekstrim_for_days(history, 90)
    ekstrim_6b = get_ekstrim_for_days(history, 180)
    ekstrim_1t = get_ekstrim_for_days(history, 365)
    ekstrim_5t = get_ekstrim_for_days(history, 1825) 
    ekstrim_all = get_ekstrim_for_days(history, len_data)
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
        '7': get_tren_for_days(history, 7),
        '14': get_tren_for_days(history, 14),
        '30': get_tren_for_days(history, 30),
        '90': get_tren_for_days(history, 90),
        '180': get_tren_for_days(history, 180),
        '365': get_tren_for_days(history, 365),
        '1825': get_tren_for_days(history, 1825),
        'all': get_tren_for_days(history, len_data)
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
        perbandingan_dummy=perbandingan_dummy
    )

@app.route('/eur')
def eur():
    update_currencies_from_sheet()
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

    
    ekstrim_7 = get_ekstrim_for_days(history, 7)
    ekstrim_14 = get_ekstrim_for_days(history, 14)
    ekstrim_1b = get_ekstrim_for_days(history, 30)
    ekstrim_3b = get_ekstrim_for_days(history, 90)
    ekstrim_6b = get_ekstrim_for_days(history, 180)
    ekstrim_1t = get_ekstrim_for_days(history, 365)
    ekstrim_5t = get_ekstrim_for_days(history, 1825) 
    ekstrim_all = get_ekstrim_for_days(history, len_data)
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
        '7': get_tren_for_days(history, 7),
        '14': get_tren_for_days(history, 14),
        '30': get_tren_for_days(history, 30),
        '90': get_tren_for_days(history, 90),
        '180': get_tren_for_days(history, 180),
        '365': get_tren_for_days(history, 365),
        '1825': get_tren_for_days(history, 1825),
        'all': get_tren_for_days(history, len_data)
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
        perbandingan_dummy=perbandingan_dummy
    )

@app.route('/jpy')
def jpy():
    update_currencies_from_sheet()
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

    
    ekstrim_7 = get_ekstrim_for_days(history, 7)
    ekstrim_14 = get_ekstrim_for_days(history, 14)
    ekstrim_1b = get_ekstrim_for_days(history, 30)
    ekstrim_3b = get_ekstrim_for_days(history, 90)
    ekstrim_6b = get_ekstrim_for_days(history, 180)
    ekstrim_1t = get_ekstrim_for_days(history, 365)
    ekstrim_5t = get_ekstrim_for_days(history, 1825) 
    ekstrim_all = get_ekstrim_for_days(history, len_data)
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
        '7': get_tren_for_days(history, 7),
        '14': get_tren_for_days(history, 14),
        '30': get_tren_for_days(history, 30),
        '90': get_tren_for_days(history, 90),
        '180': get_tren_for_days(history, 180),
        '365': get_tren_for_days(history, 365),
        '1825': get_tren_for_days(history, 1825),
        'all': get_tren_for_days(history, len_data)
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
        perbandingan_dummy=perbandingan_dummy
    )

@app.route('/myr')
def myr():
    update_currencies_from_sheet()
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

    
    ekstrim_7 = get_ekstrim_for_days(history, 7)
    ekstrim_14 = get_ekstrim_for_days(history, 14)
    ekstrim_1b = get_ekstrim_for_days(history, 30)
    ekstrim_3b = get_ekstrim_for_days(history, 90)
    ekstrim_6b = get_ekstrim_for_days(history, 180)
    ekstrim_1t = get_ekstrim_for_days(history, 365)
    ekstrim_5t = get_ekstrim_for_days(history, 1825) 
    ekstrim_all = get_ekstrim_for_days(history, len_data)
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
        '7': get_tren_for_days(history, 7),
        '14': get_tren_for_days(history, 14),
        '30': get_tren_for_days(history, 30),
        '90': get_tren_for_days(history, 90),
        '180': get_tren_for_days(history, 180),
        '365': get_tren_for_days(history, 365),
        '1825': get_tren_for_days(history, 1825),
        'all': get_tren_for_days(history, len_data)
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
        perbandingan_dummy=perbandingan_dummy
    )

@app.route('/krw')
def krw():
    update_currencies_from_sheet()
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

    
    ekstrim_7 = get_ekstrim_for_days(history, 7)
    ekstrim_14 = get_ekstrim_for_days(history, 14)
    ekstrim_1b = get_ekstrim_for_days(history, 30)
    ekstrim_3b = get_ekstrim_for_days(history, 90)
    ekstrim_6b = get_ekstrim_for_days(history, 180)
    ekstrim_1t = get_ekstrim_for_days(history, 365)
    ekstrim_5t = get_ekstrim_for_days(history, 1825) 
    ekstrim_all = get_ekstrim_for_days(history, len_data)
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
        '7': get_tren_for_days(history, 7),
        '14': get_tren_for_days(history, 14),
        '30': get_tren_for_days(history, 30),
        '90': get_tren_for_days(history, 90),
        '180': get_tren_for_days(history, 180),
        '365': get_tren_for_days(history, 365),
        '1825': get_tren_for_days(history, 1825),
        'all': get_tren_for_days(history, len_data)
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
        perbandingan_dummy=perbandingan_dummy
    )

@app.route('/cny')
def cny():
    update_currencies_from_sheet()
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

    
    ekstrim_7 = get_ekstrim_for_days(history, 7)
    ekstrim_14 = get_ekstrim_for_days(history, 14)
    ekstrim_1b = get_ekstrim_for_days(history, 30)
    ekstrim_3b = get_ekstrim_for_days(history, 90)
    ekstrim_6b = get_ekstrim_for_days(history, 180)
    ekstrim_1t = get_ekstrim_for_days(history, 365)
    ekstrim_5t = get_ekstrim_for_days(history, 1825) 
    ekstrim_all = get_ekstrim_for_days(history, len_data)
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
        '7': get_tren_for_days(history, 7),
        '14': get_tren_for_days(history, 14),
        '30': get_tren_for_days(history, 30),
        '90': get_tren_for_days(history, 90),
        '180': get_tren_for_days(history, 180),
        '365': get_tren_for_days(history, 365),
        '1825': get_tren_for_days(history, 1825),
        'all': get_tren_for_days(history, len_data)
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
        tren_dict=tren_dict,
        ekstrim_json=ekstrim_json,
        history=history,
        perbandingan_dummy=perbandingan_dummy
    )

@app.route('/sgd')
def sgd():
    update_currencies_from_sheet()
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

    ekstrim_7 = get_ekstrim_for_days(history, 7)
    ekstrim_14 = get_ekstrim_for_days(history, 14)
    ekstrim_1b = get_ekstrim_for_days(history, 30)
    ekstrim_3b = get_ekstrim_for_days(history, 90)
    ekstrim_6b = get_ekstrim_for_days(history, 180)
    ekstrim_1t = get_ekstrim_for_days(history, 365)
    ekstrim_5t = get_ekstrim_for_days(history, 1825) 
    ekstrim_all = get_ekstrim_for_days(history, len_data)
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
        '7': get_tren_for_days(history, 7),
        '14': get_tren_for_days(history, 14),
        '30': get_tren_for_days(history, 30),
        '90': get_tren_for_days(history, 90),
        '180': get_tren_for_days(history, 180),
        '365': get_tren_for_days(history, 365),
        '1825': get_tren_for_days(history, 1825),
        'all': get_tren_for_days(history, len_data)
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
        perbandingan_dummy=perbandingan_dummy
    )

@app.route('/aud')
def aud():
    update_currencies_from_sheet()
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

    ekstrim_7 = get_ekstrim_for_days(history, 7)
    ekstrim_14 = get_ekstrim_for_days(history, 14)
    ekstrim_1b = get_ekstrim_for_days(history, 30)
    ekstrim_3b = get_ekstrim_for_days(history, 90)
    ekstrim_6b = get_ekstrim_for_days(history, 180)
    ekstrim_1t = get_ekstrim_for_days(history, 365)
    ekstrim_5t = get_ekstrim_for_days(history, 1825) 
    ekstrim_all = get_ekstrim_for_days(history, len_data)
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
        '7': get_tren_for_days(history, 7),
        '14': get_tren_for_days(history, 14),
        '30': get_tren_for_days(history, 30),
        '90': get_tren_for_days(history, 90),
        '180': get_tren_for_days(history, 180),
        '365': get_tren_for_days(history, 365),
        '1825': get_tren_for_days(history, 1825),
        'all': get_tren_for_days(history, len_data)
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
        perbandingan_dummy=perbandingan_dummy
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
