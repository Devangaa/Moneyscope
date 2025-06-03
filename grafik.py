import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

#setup google sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

#ambil data dari sheet
sheet = client.open_by_key("13-0ZzKKOKq7NPwnCON4plSgNnrwECCS-MYDSKyfVpFc").sheet1
data = sheet.get_all_records()
df = pd.DataFrame(data)
df["Tanggal"] = pd.to_datetime(df["Tanggal"], dayfirst=True)
df["Harga Dolar"] = df["Harga Dolar"].astype(float)
tanggal_akhir = df["Tanggal"].max()

#kode
def deteksi_tren_sliding_window(data: list, window_size: int = 3) -> str:
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

    sorted_trend = sorted(trend_count.items(), key=lambda x: x[1], reverse=True)
    if sorted_trend[0][1] == sorted_trend[1][1]:
        return "Sideways"
    else:
        if sorted_trend[0][0] == "up":
            return "Uptrend"
        elif sorted_trend[0][0] == "down":
            return "Downtrend"
        else:
            return "Sideways"

tanggal_awal = tanggal_akhir - timedelta(days = 6)
df_3hari = df[df["Tanggal"] >= tanggal_awal].sort_values("Tanggal")
harga_3hari = df_3hari["Harga Dolar"].tolist() 

print(deteksi_tren_sliding_window(harga_3hari))