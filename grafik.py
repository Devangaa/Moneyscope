import os
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

#function
def cls():
    os.system('cls')

def deteksi_tren_sliding_window(data: list, window_size = 3):
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

def pilih_hari_tren(hari):
    tanggal_awal = tanggal_akhir - timedelta(days = hari-1)
    df_hari = df[df["Tanggal"] >= tanggal_awal].sort_values("Tanggal")
    harga_hari = df_hari["Harga Dolar"].tolist() 
 
 
def cari_tanggal(data, target_tanggal):
    left = 0
    right = len(data) - 1
    target_tanggal = target_tanggal.date()

    while left <= right:
        mid = (left + right) // 2
        mid_date = data[mid]["Tanggal"].date()
        
        if mid_date == target_tanggal:
            return data[mid]
        elif mid_date < target_tanggal:
            left = mid + 1
        else:
            right = mid - 1
    
    return None 

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

def konversi_rupiah_ke_mata_uang(jumlah_rupiah, kurs):
    return jumlah_rupiah / kurs

def konversi_mata_uang_ke_rupiah(jumlah_mata_uang, kurs):
    return jumlah_mata_uang * kurs

#batas function

#setup google sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

#ambil data dari sheet
cls()

spreadsheet = client.open_by_key("1mpPFKqyTTugKHharPyyC0UpbG7p3xRxElNpty4zFZdM")

mata_uang = input("Pilih mata uang (USD/EUR/JPY/MYR/KRW/CNY/SGD): ").upper()

try:
    sheet = spreadsheet.worksheet(mata_uang)
except:
    print("Sheet tidak ditemukan untuk mata uang:", mata_uang)
    exit()

data = sheet.get_all_records()
df = pd.DataFrame(data)
df["Tanggal"] = pd.to_datetime(df["Tanggal"], dayfirst=True)
df["Harga Dolar"] = df["Harga Dolar"].astype(float)
tanggal_akhir = df["Tanggal"].max()

#kode
cls()

print(f"Ingin cek apa? (1: Tren, 2: Harga {mata_uang}, 3: Cari Tanggal, 4: Deteksi Harga Ekstrem (Tertinggi dan Terendah), 5: Konversi Mata Uang)")
pilihan = int(input("Masukkan pilihan (1/2/3/4/5) : "))
if pilihan == 1:
    hari = int(input("Jumlah hari (3/7) : "))
    if hari not in [3, 7]:
        print("Pilihan tidak valid. Silakan pilih 3 atau 7.")
    else:
        harga_hari = pilih_hari_tren(hari)
        trend = deteksi_tren_sliding_window(harga_hari)
        print(f"Tren harga {mata_uang} dalam {hari} hari terakhir: {trend}")
elif pilihan == 2:
    print(f"Harga {mata_uang} pada {tanggal_akhir.strftime('%d-%m-%Y')}: Rp{df[df['Tanggal'] == tanggal_akhir]['Harga Dolar'].values[0]}")
elif pilihan == 3:
    tanggal_input = input("Masukkan tanggal (dd-mm-yyyy): ")
    try:
        target_tanggal = datetime.strptime(tanggal_input, "%d-%m-%Y")
        
        data_records = df.to_dict('records')
        
        for row in data_records:
            row['Tanggal'] = pd.to_datetime(row['Tanggal'], dayfirst=True).to_pydatetime()

        data_tanggal = cari_tanggal(data_records, target_tanggal)
        
        if data_tanggal:
            harga = data_tanggal['Harga Dolar']
            print(f"Harga {mata_uang} pada {target_tanggal.strftime('%d-%m-%Y')}: Rp{harga}")
        else:
            print("Tanggal tidak ditemukan dalam data.")
    except ValueError:
        print("Format tanggal tidak valid. Gunakan format dd-mm-yyyy.")
elif pilihan == 4:
    hari = int(input("Cek harga ekstrem dalam berapa hari terakhir? : "))
    tanggal_awal = tanggal_akhir - timedelta(days=hari - 1)
    df_hari = df[df["Tanggal"] >= tanggal_awal].sort_values("Tanggal")

    if df_hari.empty:
        print("Tidak ada data untuk rentang hari tersebut.")
    else:
        harga_list = list(zip(df_hari["Tanggal"], df_hari["Harga Dolar"]))
        max_data, min_data = deteksi_harga_ekstrim(harga_list, 0, len(harga_list) - 1)

        print(f"Harga TERTINGGI ({mata_uang}): Rp{max_data[1]} pada {max_data[0].strftime('%d-%m-%Y')}")
        print(f"Harga TERENDAH ({mata_uang}) : Rp{min_data[1]} pada {min_data[0].strftime('%d-%m-%Y')}")
elif pilihan == 5:
    print("Konversi:")
    print(f"1. Rupiah ke {mata_uang}")
    print(f"2. {mata_uang} ke Rupiah")
    arah = input("Pilih arah konversi (1/2): ")

    kurs_terbaru = df[df["Tanggal"] == tanggal_akhir]["Harga Dolar"].values[0]

    if arah == "1":
        try:
            jumlah = float(input("Masukkan jumlah dalam Rupiah: "))
            hasil = konversi_rupiah_ke_mata_uang(jumlah, kurs_terbaru)
            print(f"Rp{jumlah:,.2f} = {hasil:,.2f} {mata_uang} (kurs {tanggal_akhir.strftime('%d-%m-%Y')})")
        except:
            print("Input tidak valid.")
    elif arah == "2":
        try:
            jumlah = float(input(f"Masukkan jumlah dalam {mata_uang}: "))
            hasil = konversi_mata_uang_ke_rupiah(jumlah, kurs_terbaru)
            print(f"{jumlah:,.2f} {mata_uang} = Rp{hasil:,.2f} (kurs {tanggal_akhir.strftime('%d-%m-%Y')})")
        except:
            print("Input tidak valid.")
    else:
        print("Pilihan arah tidak valid.")
