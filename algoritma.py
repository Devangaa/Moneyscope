import os
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

#function
def cls():
    os.system('cls')

def ambil_data_mata_uang(spreadsheet, kode):
    try:
        sheet = spreadsheet.worksheet(kode)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df["Tanggal"] = pd.to_datetime(df["Tanggal"], dayfirst=True)
        df["Harga Dolar"] = df["Harga Dolar"].astype(float)
        return df
    except Exception as e:
        print(f"Gagal mengambil data untuk {kode}: {e}")
        return None

def pilih_hari_default(hari):
    tanggal_awal = tanggal_akhir - timedelta(days = hari-1)
    df_hari = df[df["Tanggal"] >= tanggal_awal].sort_values("Tanggal")
    harga_hari = df_hari["Harga Dolar"].tolist() 
    return harga_hari

def pilih_hari_custom(tanggal_awal, tanggal_akhir):
    df_hari = df[(df["Tanggal"] >= tanggal_awal) & (df["Tanggal"] <= tanggal_akhir)].sort_values("Tanggal")
    harga_hari = df_hari["Harga Dolar"].tolist() 
    return harga_hari

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

#Fitur no 1
# Tren harga mata uang

def deteksi_tren(data: list, window_size = 3):
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

def fitur_deteksi_tren():
    cls()
    hari = int(input("Jumlah hari (3/7) : "))
    if hari not in [3, 7]:
        print("Pilihan tidak valid. Silakan pilih 3 atau 7.")
    else:
        harga_hari = pilih_hari_default(hari)
        trend = deteksi_tren(harga_hari)
        print(f"Tren harga {mata_uang} dalam {hari} hari terakhir: {trend}")

#Fitur no 2
# Harga mata uang hari ini
def harga_hari_ini():
    cls()
    print(f"Harga {mata_uang} pada {tanggal_akhir.strftime('%d-%m-%Y')}: Rp{df[df['Tanggal'] == tanggal_akhir]['Harga Dolar'].values[0]}")

#Fitur no 3
# Mencari harga mata uang pada tanggal tertentu
def cari_harga_tanggal():
    cls()
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

#Fitur no 4
# Mendeteksi harga ekstrem (tertinggi dan terendah) dalam rentang hari tertentu 

def cari_harga_ekstrim(arr, left, right):
    if left == right:
        return arr[left], arr[left]
    elif right == left + 1:
        if arr[left][1] > arr[right][1]:
            return arr[left], arr[right]
        else:
            return arr[right], arr[left]
    else:
        mid = (left + right) // 2
        max1, min1 = cari_harga_ekstrim(arr, left, mid)
        max2, min2 = cari_harga_ekstrim(arr, mid + 1, right)

        max_harga = max1 if max1[1] >= max2[1] else max2
        min_harga = min1 if min1[1] <= min2[1] else min2

        return max_harga, min_harga

def deteksi_harga_ekstrem():
    cls
    hari = int(input("Cek harga ekstrem dalam berapa hari terakhir? : "))
    tanggal_awal = tanggal_akhir - timedelta(days=hari - 1)
    df_hari = df[df["Tanggal"] >= tanggal_awal].sort_values("Tanggal")

    if df_hari.empty:
        print("Tidak ada data untuk rentang hari tersebut.")
    else:
        harga_list = list(zip(df_hari["Tanggal"], df_hari["Harga Dolar"]))
        max_data, min_data = cari_harga_ekstrim(harga_list, 0, len(harga_list) - 1)

        print(f"Harga TERTINGGI ({mata_uang}): Rp{max_data[1]} pada {max_data[0].strftime('%d-%m-%Y')}")
        print(f"Harga TERENDAH ({mata_uang}) : Rp{min_data[1]} pada {min_data[0].strftime('%d-%m-%Y')}")

#Fitur no 5
# Konversi mata uang

def konversi_rupiah_ke_mata_uang(jumlah_rupiah, kurs):
    return jumlah_rupiah / kurs

def konversi_mata_uang_ke_rupiah(jumlah_mata_uang, kurs):
    return jumlah_mata_uang * kurs

def konversi_mata_uang():
    cls()
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

#Fitur no 6
# Perbandingan mata uang

def mata_uang_2(mata_uang, hari):
    sheet2 = spreadsheet.worksheet(mata_uang)

    data2 = sheet2.get_all_records()
    df2 = pd.DataFrame(data2)
    df2["Tanggal"] = pd.to_datetime(df2["Tanggal"], dayfirst=True)
    df2["Tanggal"] = df2["Tanggal"].dt.date
    df2["Harga Dolar"] = df2["Harga Dolar"].astype(float)
    tanggal_akhir = df2["Tanggal"].max()

    tanggal_awal = tanggal_akhir - timedelta(days = hari-1)
    df2_hari = df2[df2["Tanggal"] >= tanggal_awal].sort_values("Tanggal")
    harga_hari = df2_hari["Harga Dolar"].tolist() 
    return harga_hari

def naik_turun_max(data):
    list_harga = persentase_perubahan(data, 0, len(data) - 1)
    atas = max(list_harga)
    bawah = min(list_harga)
    return atas, bawah



def persentase_perubahan(data: list, left, right):
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

def avg_persentase_perubahan(data: list):
    total = sum(data) / len(data)
    return total

def std_deviasi(data: list, left, right, ratarata):
    if left == right:
        return (data[left] - ratarata) ** 2
    
    mid = (left + right) // 2
    kiri = std_deviasi(data, left, mid, ratarata)
    kanan = std_deviasi(data, mid + 1, right, ratarata)

    return kiri + kanan

def volatilitas(data: list):
    list_perubahan = persentase_perubahan(data, 0, len(data) - 1)
    rata_perubahan = avg_persentase_perubahan(list_perubahan)
    jumlah_deviasi = std_deviasi(list_perubahan, 0, len(list_perubahan) - 1, rata_perubahan)
    return (jumlah_deviasi / len(list_perubahan)) ** 0.5

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

def persentase_hari_untung(data: list):
    total_hari = len(data)
    hari_naik, hari_turun = hari_naik_turun(data)
    
    if total_hari == 0:
        return 0
    
    persentase_naik = (hari_naik / total_hari) * 100
    return persentase_naik

def bandingkan_mata_uang(uang):
    cls()
    
    list_uang = ["USD", "EUR", "JPY", "MYR", "KRW", "CNY", "SGD"]
    list_uang.remove(uang)
    list_uang_jadi = "/".join(list_uang)
    uang_pembanding = input(f"Masukkan mata uang yang ingin dibandingkan ({list_uang_jadi}): ").upper()
    if uang_pembanding not in list_uang:
        print("Mata uang tidak valid. Silakan pilih dari daftar yang tersedia.")
        return
    hari = int(input("Cek perbandingan dalam berapa hari terakhir? : "))
    
    list1, list2 = pilih_hari_default(hari), mata_uang_2(uang_pembanding,hari)
    rata1, rata2 = avg_persentase_perubahan(persentase_perubahan(list1, 0, len(list1) - 1)), avg_persentase_perubahan(persentase_perubahan(list2, 0, len(list2) - 1))
    tren1, tren_prediksi = deteksi_tren(list1), deteksi_tren(list2)
    naik1, turun1 = naik_turun_max(list1)
    naik2, turun2 = naik_turun_max(list2)
    volatilitas1 = volatilitas(list1)
    volatilitas2 = volatilitas(list2)
    atas1, bawah1 = hari_naik_turun(list1)
    atas2, bawah2 = hari_naik_turun(list2)
    streakn1, streakt1 = streak_naik_turun(list1)
    streakn2, streakt2 = streak_naik_turun(list2)
    persentase_untung1, persentase_untung2 = persentase_hari_untung(list1), persentase_hari_untung(list2)

    cls()
    print(f"Perbandingan {mata_uang} dan {uang_pembanding} dalam {hari} hari terakhir:\n")
    print("-" * 60)
    print(f"{'Aspek':<30} | {mata_uang:^10} | {uang_pembanding:^10}")
    print("-" * 60)
    print(f"{'Rata-rata perubahan (%)':<30} | {rata1:^10.2f} | {rata2:^10.2f}")
    print(f"{'Tren dominan':<30} | {tren1:^10} | {tren_prediksi:^10}")
    print(f"{'Kenaikan max (%)':<30} | {naik1:^10.2f} | {naik2:^10.2f}")
    print(f"{'Penurunan max (%)':<30} | {turun1:^10.2f} | {turun2:^10.2f}")
    print(f"{'Volatilitas':<30} | {volatilitas1:^10.2f} | {volatilitas2:^10.2f}")
    print(f"{'Jumlah hari naik':<30} | {atas1:^10} | {atas2:^10}")
    print(f"{'Jumlah hari turun':<30} | {bawah1:^10} | {bawah2:^10}")
    print(f"{'Durasi tren naik terpanjang':<30} | {streakn1:^10} | {streakn2:^10}")
    print(f"{'Durasi tren turun terpanjang':<30} | {streakt1:^10} | {streakt2:^10}")
    print(f"{'Persentase hari untung (%)':<30} | {persentase_untung1:^10.2f} | {persentase_untung2:^10.2f}")

#Fitur no 7
# Perbandingan rentang waktu berbeda
def bandingkan_rentang_waktu():
    cls()
    awal1, batas1 = input("Masukkan tanggal awal dan batas pertama (dd-mm-yyyy, dd-mm-yyyy): ").split(", ")
    try:
        awal1 = datetime.strptime(awal1, "%d-%m-%Y").date()
        batas1 = datetime.strptime(batas1, "%d-%m-%Y").date()
    except ValueError:
        print("Format tanggal tidak valid. Gunakan format dd-mm-yyyy.")
        return
    awal2, batas2 = input("Masukkan tanggal awal dan batas kedua (dd-mm-yyyy, dd-mm-yyyy): ").split(", ")
    try:
        awal2 = datetime.strptime(awal2, "%d-%m-%Y").date()
        batas2 = datetime.strptime(batas2, "%d-%m-%Y").date()

        if awal1 > batas1 or awal2 > batas2:
            print("Tanggal awal tidak boleh lebih besar dari tanggal batas.")
            return
    except ValueError:
        print("Format tanggal tidak valid. Gunakan format dd-mm-yyyy.")
        return
    
    list1, list2 = pilih_hari_custom(awal1, batas1), pilih_hari_custom(awal2, batas2)
    rata1, rata2 = avg_persentase_perubahan(persentase_perubahan(list1, 0, len(list1) - 1)), avg_persentase_perubahan(persentase_perubahan(list2, 0, len(list2) - 1))
    tren1, tren_prediksi = deteksi_tren(list1), deteksi_tren(list2)
    naik1, turun1 = naik_turun_max(list1)
    naik2, turun2 = naik_turun_max(list2)
    volatilitas1 = volatilitas(list1)
    volatilitas2 = volatilitas(list2)
    atas1, bawah1 = hari_naik_turun(list1)
    atas2, bawah2 = hari_naik_turun(list2)
    streakn1, streakt1 = streak_naik_turun(list1)
    streakn2, streakt2 = streak_naik_turun(list2)
    persentase_untung1, persentase_untung2 = persentase_hari_untung(list1), persentase_hari_untung(list2)

    cls()
    print(f"Perbandingan {mata_uang} dalam rentang waktu {awal1.strftime('%d-%m-%Y')} s/d {batas1.strftime('%d-%m-%Y')} dengan {awal2.strftime('%d-%m-%Y')} s/d {batas2.strftime('%d-%m-%Y')}:\n")
    print("-" * 60)
    print(f"{'Aspek':<30} | {'Rentang 1':^10} | {'Rentang 2':^10}")
    print("-" * 60)
    print(f"{'Rata-rata perubahan (%)':<30} | {rata1:^10.2f} | {rata2:^10.2f}")
    print(f"{'Tren dominan':<30} | {tren1:^10} | {tren_prediksi:^10}")
    print(f"{'Kenaikan max (%)':<30} | {naik1:^10.2f} | {naik2:^10.2f}")
    print(f"{'Penurunan max (%)':<30} | {turun1:^10.2f} | {turun2:^10.2f}")
    print(f"{'Volatilitas':<30} | {volatilitas1:^10.2f} | {volatilitas2:^10.2f}")
    print(f"{'Jumlah hari naik':<30} | {atas1:^10} | {atas2:^10}")
    print(f"{'Jumlah hari turun':<30} | {bawah1:^10} | {bawah2:^10}")
    print(f"{'Durasi tren naik terpanjang':<30} | {streakn1:^10} | {streakn2:^10}")
    print(f"{'Durasi tren turun terpanjang':<30} | {streakt1:^10} | {streakt2:^10}")
    print(f"{'Persentase hari untung (%)':<30} | {persentase_untung1:^10.2f} | {persentase_untung2:^10.2f}")

#Fitur no 8
# Prediksi arah tren sederhana berdasarkan 3, 5, dan 7 hari terakhir

def prediksi_tren_multi_window(df, windows=[3,5,7]):
    hasil_tren = []

    for harga in windows:
        harga_hari = pilih_hari_default(harga)  
        tren = deteksi_tren(harga_hari)  
        hasil_tren.append(tren)

    hitung = {"Uptrend":0, "Downtrend":0, "Sideways":0}
    for t in hasil_tren:
        hitung[t] += 1

    max_jumlah = max(hitung.values())
    tren_terbanyak = [k for k, v in hitung.items() if v == max_jumlah]

    if len(tren_terbanyak) == 1:
        return tren_terbanyak[0]
    else:
        return "Sideways"
        
def prediksi_tren():
    cls()
    tren_prediksi = prediksi_tren_multi_window(df)
    print(f"Prediksi tren harga {mata_uang} berdasarkan 3, 5, dan 7 hari terakhir: {tren_prediksi}")

#Fitur no 9
# Fungsi untuk menghitung potensi investasi
def potensi_investasi():
    cls()
    data = pilih_hari_default(365)
    expected_return = avg_persentase_perubahan(persentase_perubahan(data, 0, len(data) - 1))
    volatil = volatilitas(data)
    
    sheet2 = spreadsheet.worksheet("SKBA")
    data2 = sheet2.get_all_records()
    df2 = pd.DataFrame(data2)
    df2["suku bunga"] = df2["suku bunga"].astype(float)

    suku_bunga = (df2[df2["mata uang"] == mata_uang]["suku bunga"].values[0])/100
    sharperatio = sharpe_ratio(expected_return, suku_bunga, volatil)
    ird = interest_rate_difference(suku_bunga)

    potensi = ((expected_return * 0.35) + (volatil * 0.25) + (sharperatio * 0.25) + (ird * 0.15)) * 100
    print(f"Potensi investasi untuk {mata_uang} dalam 1 tahun terakhir: {potensi:.2f}%")

def sharpe_ratio(expected_return, suku_bunga, volatil):
    if volatil == 0:
        return 0
    return (expected_return - suku_bunga) / volatil

def interest_rate_difference(suku_bunga):
    sheet3 = spreadsheet.worksheet("SKBA")
    data3 = sheet3.get_all_records()
    df3 = pd.DataFrame(data3)
    df3["suku bunga"] = df3["suku bunga"].astype(float)

    suku_idr = df3[df3["mata uang"] == "IDR"]["suku bunga"].values[0] / 100
    return suku_bunga - suku_idr 

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

data_default = sheet.get_all_records()
df = pd.DataFrame(data_default)
df["Tanggal"] = pd.to_datetime(df["Tanggal"], dayfirst=True)
df["Tanggal"] = df["Tanggal"].dt.date
df["Harga Dolar"] = df["Harga Dolar"].astype(float)
tanggal_akhir = df["Tanggal"].max()

#kode
cls()

print(f"Ingin cek apa? \n1: Tren \n2: Harga {mata_uang} \n3: Cari Tanggal \n4: Deteksi Harga Ekstrem \n5: Konversi Mata Uang \n6: Perbandingan Mata Uang \n7: Perbandingan Rentang Waktu Berbeda  \n8: Prediksi Arah Trend Sederhana \n9: Potensi Investasi \n=====================================")
pilihan = int(input("Masukkan pilihan (1/2/3/4/5/6/7/8/9) : "))

if pilihan == 1:
    fitur_deteksi_tren()
    akhir = input("\nTekan Enter untuk keluar...")

elif pilihan == 2:
    harga_hari_ini()
    akhir = input("\nTekan Enter untuk keluar...")

elif pilihan == 3:
    cari_harga_tanggal()
    akhir = input("\nTekan Enter untuk keluar...")

elif pilihan == 4:
    deteksi_harga_ekstrem()
    akhir = input("\nTekan Enter untuk keluar...")

elif pilihan == 5:
    konversi_mata_uang()
    akhir = input("\nTekan Enter untuk keluar...")

elif pilihan == 6:
    bandingkan_mata_uang(mata_uang)
    akhir = input("\nTekan Enter untuk keluar...")

elif pilihan == 7:
    bandingkan_rentang_waktu()
    akhir = input("\nTekan Enter untuk keluar...")

elif pilihan == 8:
    prediksi_tren()
    akhir = input("\nTekan Enter untuk keluar...")

elif pilihan == 9:
    potensi_investasi()
    akhir = input("\nTekan Enter untuk keluar...")

else:    
    print("Pilihan tidak valid.")
    akhir = input("\nTekan Enter untuk keluar...")