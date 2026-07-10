# app.py

import streamlit as st
import pandas as pd
import re
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ==================================================
# KONFIGURASI GOOGLE SHEETS
# ==================================================
SHEET_NAME = "Database_Warning_Juanda"
WORKSHEET_NAME = "warning"
SERVICE_ACCOUNT_FILE = "credentials.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)

client = gspread.authorize(creds)
spreadsheet = client.open(SHEET_NAME)
sheet = spreadsheet.worksheet(WORKSHEET_NAME)

# ==================================================
# FUNGSI WAKTU DDHHMM
# ==================================================
def decode_warning_time(kode_waktu, bulan, tahun):
    hari = int(kode_waktu[:2])
    jam = int(kode_waktu[2:4])
    menit = int(kode_waktu[4:6])

    return datetime(tahun, bulan, hari, jam, menit)


# ==================================================
# FUNGSI PARSE AERODROME WARNING
# ==================================================
def parse_ad_warning(sandi, bulan, tahun):
    teks = sandi.upper().replace("=", "").strip()

    hasil = {
        "ICAO": "",
        "Jenis_Warning": "Aerodrome Warning",
        "Nomor_Warning": "",
        "Waktu_Terbit": "",
        "Valid_Dari": "",
        "Valid_Sampai": "",
        "Fenomena": "",
        "Intensitas": "",
        "Wind_Speed": "",
        "Wind_Max": "",
        "Area": "",
        "Status_Observasi": "",
        "Waktu_Observasi": "",
        "Sandi_Asli": sandi
    }

    tokens = teks.split()

    if tokens:
        hasil["ICAO"] = tokens[0]

    nomor = re.search(r"AD\s+WRNG\s+(\d+)", teks)
    if nomor:
        hasil["Nomor_Warning"] = nomor.group(1)

    valid = re.search(r"VALID\s+(\d{6})/(\d{6})", teks)
    if valid:
        hasil["Valid_Dari"] = decode_warning_time(valid.group(1), bulan, tahun)
        hasil["Valid_Sampai"] = decode_warning_time(valid.group(2), bulan, tahun)

    if "HVY" in tokens:
        hasil["Intensitas"] = "Heavy / Lebat"
    elif "MOD" in tokens:
        hasil["Intensitas"] = "Moderate / Sedang"
    elif "LIGHT" in tokens or "LGT" in tokens:
        hasil["Intensitas"] = "Light / Ringan"

    fenomena = []
    if "TSRA" in tokens:
        fenomena.append("Thunderstorm with Rain / Badai petir disertai hujan")
    if "TS" in tokens:
        fenomena.append("Thunderstorm / Badai petir")
    if "RA" in tokens:
        fenomena.append("Rain / Hujan")
    if "BR" in tokens:
        fenomena.append("Mist / Kabut tipis")
    if "HZ" in tokens or "HAZE" in tokens:
        fenomena.append("Haze / Udara kabur")
    if "L" in tokens:
        fenomena.append("Lightning / Petir/Kilat")

    hasil["Fenomena"] = "; ".join(fenomena)

    wspd = re.search(r"WSPD\s+(\d+)KT", teks)
    if wspd:
        hasil["Wind_Speed"] = f"{wspd.group(1)} KT"

    maxspd = re.search(r"MAX\s+(\d+)", teks)
    if maxspd:
        hasil["Wind_Max"] = f"{maxspd.group(1)} KT"

    return hasil


# ==================================================
# FUNGSI PARSE WIND SHEAR WARNING
# ==================================================
def parse_ws_warning(sandi, bulan, tahun):
    teks = sandi.upper().replace("=", "").strip()

    hasil = {
        "ICAO": "",
        "Jenis_Warning": "Wind Shear Warning",
        "Nomor_Warning": "",
        "Waktu_Terbit": "",
        "Valid_Dari": "",
        "Valid_Sampai": "",
        "Fenomena": "Wind Shear",
        "Intensitas": "",
        "Wind_Speed": "",
        "Wind_Max": "",
        "Area": "",
        "Status_Observasi": "",
        "Waktu_Observasi": "",
        "Arah_Angin_Surface": "",
        "Kecepatan_Angin_Surface": "",
        "Arah_Angin_100ft": "",
        "Kecepatan_Angin_100ft": "",
        "Sandi_Asli": sandi
    }

    tokens = teks.split()

    if tokens:
        hasil["ICAO"] = tokens[0]

    nomor = re.search(r"WS\s+WRNG\s+(\d+)", teks)
    if nomor:
        hasil["Nomor_Warning"] = nomor.group(1)

    waktu_terbit = re.search(r"WS\s+WRNG\s+\d+\s+(\d{6})", teks)
    if waktu_terbit:
        hasil["Waktu_Terbit"] = decode_warning_time(waktu_terbit.group(1), bulan, tahun)
        hasil["Valid_Dari"] = decode_warning_time(waktu_terbit.group(1), bulan, tahun)

    valid_tl = re.search(r"VALID\s+TL\s+(\d{6})", teks)
    if valid_tl:
        hasil["Valid_Sampai"] = decode_warning_time(valid_tl.group(1), bulan, tahun)

    area = re.search(r"WS\s+(ALL\s+RWY|RWY\s+\d+)", teks)
    if area:
        hasil["Area"] = area.group(1)

    obs = re.search(r"OBS\s+AT\s+(\d{4})", teks)
    if obs:
        hasil["Status_Observasi"] = "Observed"
        hasil["Waktu_Observasi"] = obs.group(1)

    sfc = re.search(r"SFC\s+WIND:\s*(\d{3})/(\d{2})KT", teks)
    if sfc:
        hasil["Arah_Angin_Surface"] = sfc.group(1)
        hasil["Kecepatan_Angin_Surface"] = f"{sfc.group(2)} KT"

    wind_100ft = re.search(r"100FT[-\s]?WIND:\s*(\d{3})/(\d{2})KT", teks)
    if wind_100ft:
        hasil["Arah_Angin_100ft"] = wind_100ft.group(1)
        hasil["Kecepatan_Angin_100ft"] = f"{wind_100ft.group(2)} KT"

    return hasil


# ==================================================
# FUNGSI DETEKSI JENIS WARNING
# ==================================================
def parse_warning(sandi, bulan, tahun):
    teks = sandi.upper()

    if "AD WRNG" in teks:
        return parse_ad_warning(sandi, bulan, tahun)

    elif "WS WRNG" in teks:
        return parse_ws_warning(sandi, bulan, tahun)

    else:
        return None


# ==================================================
# SIMPAN KE GOOGLE SHEETS
# ==================================================
def simpan_ke_sheets(data):
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        data.get("ICAO", ""),
        data.get("Jenis_Warning", ""),
        data.get("Nomor_Warning", ""),
        str(data.get("Waktu_Terbit", "")),
        str(data.get("Valid_Dari", "")),
        str(data.get("Valid_Sampai", "")),
        data.get("Fenomena", ""),
        data.get("Intensitas", ""),
        data.get("Wind_Speed", ""),
        data.get("Wind_Max", ""),
        data.get("Area", ""),
        data.get("Status_Observasi", ""),
        data.get("Waktu_Observasi", ""),
        data.get("Arah_Angin_Surface", ""),
        data.get("Kecepatan_Angin_Surface", ""),
        data.get("Arah_Angin_100ft", ""),
        data.get("Kecepatan_Angin_100ft", ""),
        data.get("Sandi_Asli", ""),
        data.get("Petugas", "")
    ])


# ==================================================
# STREAMLIT APP
# ==================================================
st.set_page_config(
    page_title="Input Warning Juanda",
    layout="wide"
)

st.title("⚠️ Form Input Sandi *Aerodrome Warning* & *Wind Shear Warning*")
st.write("Input sandi warning, sistem akan menerjemahkan otomatis dan menyimpan ke Google Sheets.")

with st.form("form_warning"):
    col1, col2 = st.columns(2)

    with col1:
        bulan = st.selectbox(
            "Bulan",
            list(range(1, 13)),
            format_func=lambda x: [
                "Januari", "Februari", "Maret", "April", "Mei", "Juni",
                "Juli", "Agustus", "September", "Oktober", "November", "Desember"
            ][x-1]
        )

        tahun = st.number_input(
            "Tahun",
            min_value=2020,
            max_value=2100,
            value=2025,
            step=1
        )

    with col2:
        petugas = st.text_input("Nama *Forecaster/Inputter*")

    sandi = st.text_area(
        "Masukkan Sandi *Warning*",
        height=120,
        placeholder=(
            "Contoh AD:\n"
            "WARR AD WRNG 1 VALID 040500/040600 HVY TSRA WSPD 10KT MAX 30 FCST=\n\n"
            "Contoh WS:\n"
            "WARR WS WRNG 1 040616 VALID TL 040640 WS ALL RWY OBS AT 0610 SFC WIND: 200/09KT 100FT-WIND: 150/20KT="
        )
    )

    submit = st.form_submit_button("Terjemahkan & Simpan")

if submit:
    if not sandi.strip():
        st.warning("Sandi *warning* belum diisi.")
    else:
        hasil = parse_warning(sandi, bulan, int(tahun))

        if hasil is None:
            st.error("Jenis *warning* tidak terdeteksi. Pastikan sandi mengandung 'AD WRNG' atau 'WS WRNG'.")
        else:
            hasil["*Forecaster/Inputter*"] = petugas

            simpan_ke_sheets(hasil)

            st.success("Data berhasil diterjemahkan dan disimpan ke Google Sheets.")

            st.subheader("Hasil Terjemahan")
            st.json({k: str(v) for k, v in hasil.items()})


# ==================================================
# RIWAYAT DATA
# ==================================================
st.divider()
st.subheader("📋 Riwayat Data *Warning*")

try:
    data = sheet.get_all_records(
                expected_headers=[
                    "Timestamp",
                    "ICAO",
                    "Jenis_Warning",
                    "Nomor_Warning",
                    "Waktu_Terbit",
                    "Valid_Dari",
                    "Valid_Sampai",
                    "Area",
                    "Status_Observasi",
                    "Waktu_Observasi",
                    "Arah_Angin_Surface",
                    "Kecepatan_Angin_Surface",
                    "Arah_Angin_100ft",
                    "Kecepatan_Angin_100ft",
                    "Sandi_Asli",
                    "Petugas"
                ]
    )       
    df_db = pd.DataFrame(data[1:], columns=data[0])

    if df_db.empty:
        st.info("Belum ada data tersimpan.")
    else:
        st.dataframe(df_db, use_container_width=True)

        csv = df_db.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Data CSV",
            data=csv,
            file_name="database_warning_juanda.csv",
            mime="text/csv"
        )

except Exception as e:
    st.error(f"Gagal membaca Google Sheets: {e}")
