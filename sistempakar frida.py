# -*- coding: utf-8 -*-
"""
SISTEM PAKAR DIAGNOSIS HAMA DAN PENYAKIT TANAMAN KAKAO
Metode inferensi : Forward Chaining
Antarmuka        : Streamlit (web lokal)

Cara menjalankan di Thonny:
  1. Tools > Manage packages, pasang: streamlit, pandas, dan mysql-connector-python
  2. Tutup dulu semua tab peramban dan jendela Streamlit lama (lihat catatan port di bawah).
  3. Buka berkas ini lalu tekan tombol Run (F5). Peramban akan terbuka sendiri.
Cara lain (terminal): streamlit run hamakakaoweb.py

CATATAN PORT: aplikasi dijalankan di port tetap 8501. Bila Thonny menampilkan galat
"Port 8501 is not available", berarti masih ada Streamlit lama (versi lama) yang berjalan.
Hentikan dulu (tombol Stop di Thonny, atau tutup jendela terminal Streamlit, atau
Task Manager > akhiri proses python), lalu Run lagi.
"""
import hmac
import html
import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------
# IDENTITAS (isi sesuai data Anda)
# ----------------------------------------------------------------------
NAMA_PEMBUAT = "Frida Ayu Lestari"
NIM_PEMBUAT = "23010047"
ADMIN_PASSWORD = "admin123"   # kata sandi menu Admin (huruf kecil semua, tanpa spasi; ganti sesuai keinginan)
VERSI = "kakao-v6"   # penanda versi berkas; tampil di tab Database agar mudah memastikan berkas yang berjalan

# Pengaturan MySQL (sesuaikan dengan komputer Anda, mis. XAMPP/Laragon: user root, sandi kosong)
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "sistem_pakar_kakao_frida"

# ----------------------------------------------------------------------
# BASIS PENGETAHUAN
# Kode sumber mengacu ke Daftar Pustaka laporan:
#   [1] Maryani & Daniati (2019), Buku Saku Hama dan Penyakit Tanaman Kakao, Ditjenbun, Kementan
#   [2] Wibawanti dkk. (2025), Buku Pedoman Pengenalan dan Pengendalian OPT Tanaman Penyegar
#       dan Tahunan (Kakao, Kopi, dan Jambu Mete), Pertanian Press
# ----------------------------------------------------------------------
FAKTA = {
    # Buah
    "F1": ("Buah tampak masak lebih awal dengan warna belang kuning-hijau yang tidak merata", "Buah", "[1]"),
    "F2": ("Lubang gerekan kecil pada kulit buah", "Buah", "[1]"),
    "F3": ("Bila buah dibelah, tampak bekas gerekan larva di dalamnya", "Buah", "[1]"),
    "F4": ("Biji kecil, tidak bernas, kehitaman, dan saling melekat (lengket)", "Buah", "[1]"),
    "F5": ("Bercak bekas tusukan berwarna cokelat kehitaman pada kulit buah", "Buah", "[1][2]"),
    "F6": ("Buah muda (pentil) layu, mengering, lalu gugur", "Buah", "[1][2]"),
    "F7": ("Kulit buah retak, berkerut, atau bentuk buah berubah", "Buah", "[1][2]"),
    "F8": ("Busuk basah berwarna cokelat kehitaman dengan batas yang tegas pada buah", "Buah", "[1]"),
    "F9": ("Muncul serbuk putih (spora jamur) pada permukaan buah yang busuk", "Buah", "[1]"),
    "F10": ("Bercak cokelat berlekuk pada buah, lalu buah mengeras, kecil, dan kering", "Buah", "[1]"),
    "F11": ("Bercak cokelat meluas cepat sehingga dalam beberapa hari seluruh buah busuk basah", "Buah", "[1]"),
    # Daun dan pucuk
    "F12": ("Daun berlubang-lubang", "Daun dan pucuk", "[1]"),
    "F13": ("Tanaman atau ranting menjadi gundul (daun habis atau rontok)", "Daun dan pucuk", "[1]"),
    "F14": ("Ulat abu-abu kehijauan (atau hitam bergaris putih) sepanjang sekitar 2,5 cm terlihat pada tanaman", "Daun dan pucuk", "[1]"),
    "F15": ("Kumbang berkulit keras memakan pucuk atau daun muda", "Daun dan pucuk", "[1]"),
    "F16": ("Pucuk layu dan mati, lalu ranting mengering dan meranggas", "Daun dan pucuk", "[1][2]"),
    "F17": ("Daun menguning dengan bercak-bercak hijau, biasanya pada daun kedua atau ketiga dari titik tumbuh", "Daun dan pucuk", "[1][2]"),
    "F18": ("Tiga noktah cokelat kehitaman atau lebih pada bekas dudukan daun; bila ranting dibelah tampak garis cokelat", "Daun dan pucuk", "[1][2]"),
    "F19": ("Benang-benang putih pada bekas dudukan daun atau bekas potongan ranting", "Daun dan pucuk", "[1][2]"),
    "F20": ("Bintik cokelat pada daun muda yang berkembang menjadi bercak berlubang dengan lingkaran kuning (halo)", "Daun dan pucuk", "[1]"),
    "F21": ("Ranting berbentuk seperti kipas dengan ruas yang pendek", "Daun dan pucuk", "[1]"),
    # Batang, cabang, dan akar
    "F22": ("Lubang gerekan pada cabang atau batang disertai kotoran dan bekas gerekan larva", "Batang, cabang, dan akar", "[1][2]"),
    "F23": ("Bagian tanaman di atas lubang gerekan layu, kering, dan mati", "Batang, cabang, dan akar", "[1][2]"),
    "F24": ("Kulit batang atau cabang berwarna gelap kehitaman, membusuk, dan basah", "Batang, cabang, dan akar", "[1]"),
    "F25": ("Bila kulit luar dikupas, jaringan di dalamnya berwarna merah anggur", "Batang, cabang, dan akar", "[1]"),
    "F26": ("Daun menguning, layu, mengering, lalu tanaman mati", "Batang, cabang, dan akar", "[1]"),
    "F27": ("Pada akar atau leher akar terdapat badan buah jamur, kerak cokelat yang mengikat tanah, atau benang putih bercabang", "Batang, cabang, dan akar", "[1]"),
    "F28": ("Akar membusuk, lunak, dan berair", "Batang, cabang, dan akar", "[1]"),
}

KESIMPULAN_ANTARA = {
    "A1": "Ada tanda gerekan pada buah (lubang gerekan atau bekas larva di dalam buah)",
    "A2": "Ada tanda tusukan kepik pada buah (bercak cokelat kehitaman atau kulit buah retak)",
    "A3": "Ada tanda infeksi VSD pada daun atau ranting (bercak hijau pada daun menguning atau noktah pada dudukan daun)",
    "A4": "Ada gangguan pada akar atau leher akar (tanda jamur atau akar membusuk)",
    "A5": "Ada kerusakan daun oleh hama pemakan daun (daun berlubang atau tanaman gundul)",
}

DIAGNOSIS = {
    "K1": {
        "nama": "Penggerek Buah Kakao (PBK)", "latin": "Conopomorpha cramerella", "jenis": "Hama",
        "rekomendasi": [
            "Pangkas pemeliharaan 3-4 kali setahun untuk mengurangi kelembapan dan memasukkan cahaya matahari ke kebun [1].",
            "Panen sering (interval 4-7 hari) diikuti sanitasi: ambil buah terserang dan sisa buah jatuh, kumpulkan serasah, lalu masukkan ke lubang dan tutup tanah [1].",
            "Sarungi buah muda berukuran 8-15 cm dengan kantong plastik; dasar kantong dibiarkan terbuka sebagai ventilasi [1].",
            "Manfaatkan semut hitam sebagai musuh alami dengan memasang sarang buatan dari lipatan daun kelapa di cabang [1][2].",
            "Saat peremajaan, pilih klon toleran PBK dengan kulit buah tanpa atau sedikit alur, mengkilap, licin, dan keras, misalnya Sulawesi 2 dan Sulawesi 3 [1][2].",
            "Insektisida terdaftar hanya pilihan terakhir saat serangan eksplosif; gunakan sesuai anjuran penyuluh [1][2].",
        ]},
    "K2": {
        "nama": "Kepik Penghisap Buah", "latin": "Helopeltis spp.", "jenis": "Hama",
        "rekomendasi": [
            "Sanitasi kebun: kendalikan gulma yang menjadi inang, lalu kumpulkan dan musnahkan buah yang terserang [2].",
            "Pangkas tanaman kakao, buang tunas air (wiwilan), dan atur tanaman penaung karena kepik menyukai tempat yang banyak naungan [1][2].",
            "Manfaatkan semut hitam dan semut merah sebagai predator dengan sarang buatan dari daun kakao kering atau daun kelapa [1][2].",
            "Gunakan jamur Beauveria bassiana atau insektisida nabati (mimba, tembakau, babadotan, sirsak, serai wangi) pada konsentrasi 2,5-5 persen [1][2].",
            "Sarungi buah muda dengan kantong plastik berventilasi [2].",
            "Saat peremajaan, pilih klon tahan Helopeltis seperti ICCRI 01, 02, 03, dan 04 [2].",
            "Insektisida terdaftar hanya pilihan terakhir bila serangan berat, sesuai anjuran penyuluh [1][2].",
        ]},
    "K3": {
        "nama": "Penggerek Cabang dan Batang", "latin": "Zeuzera coffeae", "jenis": "Hama",
        "rekomendasi": [
            "Potong cabang yang terserang pada jarak sekitar 10 cm dari lubang gerekan, lalu musnahkan [1].",
            "Masukkan kawat elastis ke lubang gerekan yang masih aktif (ada larva) [2].",
            "Pasang perangkap lampu pada malam hari karena ngengat dewasa aktif malam dan tertarik cahaya [2].",
            "Semprotkan jamur Beauveria bassiana ke dalam lubang gerekan, lalu tutup lubangnya [1][2].",
            "Insektisida terdaftar hanya pilihan terakhir; konsultasikan dengan penyuluh pertanian [2].",
        ]},
    "K4": {
        "nama": "Ulat Kilan (Ulat Jengkal)", "latin": "Hyposidra talaca", "jenis": "Hama",
        "rekomendasi": [
            "Kumpulkan dan musnahkan larva yang terlihat [1].",
            "Semprot pestisida nabati (ekstrak daun mimba, tembakau, babadotan, atau sirsak) pada konsentrasi 2,5-5 persen [1].",
            "Waspadai serangan pada bibit kakao karena kerugiannya paling besar [1].",
            "Insektisida terdaftar hanya alternatif terakhir saat serangan eksplosif, secara bijaksana dan sesuai anjuran penyuluh [1].",
        ]},
    "K5": {
        "nama": "Kumbang Daun", "latin": "Chrysomelidae", "jenis": "Hama",
        "rekomendasi": [
            "Lakukan pemangkasan rutin dan buang tunas baru (wiwilan) untuk mengurangi bagian tanaman yang menjadi makanan kumbang [1].",
            "Semprot pestisida nabati (ekstrak daun mimba, tembakau, babadotan, atau sirsak) pada konsentrasi 2,5-5 persen [1].",
            "Insektisida terdaftar hanya pilihan terakhir bila serangan berat, sesuai anjuran penyuluh [1].",
        ]},
    "K6": {
        "nama": "Busuk Buah", "latin": "Phytophthora palmivora", "jenis": "Penyakit",
        "rekomendasi": [
            "Sanitasi: petik semua buah busuk saat panen atau pemangkasan; buah yang jatuh dikumpulkan lalu dikubur sedalam minimal 30 cm [1].",
            "Pangkas tanaman kakao dan pohon pelindung untuk mengurangi kelembapan kebun [1].",
            "Semprotkan jamur Trichoderma spp. pada buah yang masih sehat sebagai tindakan pencegahan [1].",
            "Saat peremajaan, tanam klon toleran seperti DRC 16, ICCRI 03, ICCRI 04, atau BL 50 [1].",
        ]},
    "K7": {
        "nama": "Vascular Streak Dieback (VSD)", "latin": "Oncobasidium theobromae", "jenis": "Penyakit",
        "rekomendasi": [
            "Pangkasan sanitasi: potong ranting sakit sampai batas garis cokelat pada xylem, ditambah 30-40 cm di bawahnya [1][2].",
            "Sambung samping atau tanam ulang dengan klon tahan VSD, misalnya Sulawesi 1, DRC 15, Sca 6, atau ICCRI 06 [1][2].",
            "Bongkar tanaman tua yang terserang berat, lalu tanam kembali dengan klon toleran [1].",
            "Di pembenihan, beri atap daun kelapa atau plastik agar spora tidak jatuh ke benih, dan musnahkan benih yang terserang [1][2].",
            "Fungisida terdaftar pada daun muda hanya sebagai tindakan pencegahan, sesuai anjuran penyuluh [1][2].",
        ]},
    "K8": {
        "nama": "Kanker Batang", "latin": "Phytophthora palmivora", "jenis": "Penyakit",
        "rekomendasi": [
            "Kupas kulit batang yang membusuk sampai batas jaringan sehat (berwarna putih), lalu olesi dengan asap cair, arang, atau fungisida terdaftar berbahan aktif tembaga [1].",
            "Bila infeksi sudah melingkari batang, potong atau bongkar tanaman tersebut [1].",
            "Jaga kesehatan tanaman dengan pemupukan dan pemangkasan yang baik agar tanaman tetap kuat [1].",
        ]},
    "K9": {
        "nama": "Antraknosa", "latin": "Colletotrichum gloeosporioides", "jenis": "Penyakit",
        "rekomendasi": [
            "Tanam pohon penaung seperti lamtoro untuk menjaga kelembapan mikroklimat kebun [1].",
            "Sanitasi: petik semua buah busuk dan kubur yang jatuh sedalam minimal 30 cm [1].",
            "Pada serangan berat, beri pemupukan lewat daun sedini mungkin saat tunas mulai pecah [1].",
            "Saat peremajaan, tanam klon toleran seperti DRC 16, ICCRI 03, ICCRI 04, atau BL 50 [1].",
            "Bongkar tanaman yang terinfeksi berat; fungisida terdaftar hanya sebagai pencegahan sesuai anjuran penyuluh [1].",
        ]},
    "K10": {
        "nama": "Penyakit Jamur Akar", "latin": "Ganoderma sp., Phellinus noxius, Rigidoporus microporus", "jenis": "Penyakit",
        "rekomendasi": [
            "Bongkar tanaman yang mati berikut akarnya sampai bersih, kumpulkan akar di lubang bekas bongkaran, lalu musnahkan [1].",
            "Beri belerang sebanyak 300 g pada lubang bekas bongkaran dan biarkan sekitar satu tahun sebelum ditanami kembali [1].",
            "Bongkar juga tanaman lain atau pohon penaung di sekitarnya bila sudah mati atau terinfeksi berat [1].",
            "Aplikasikan jamur Trichoderma pada tanaman di sekitar tanaman yang terserang [1].",
        ]},
}

# Aturan produksi: (kode, premis, kesimpulan, sumber)
# Premis berbentuk "F1" atau ("AND", ...) atau ("OR", ...), boleh bersarang.
RULES = [
    ("R1", ("OR", "F2", "F3"), "A1", "[1]"),
    ("R2", ("OR", "F5", "F7"), "A2", "[1][2]"),
    ("R3", ("OR", "F17", "F18"), "A3", "[1][2]"),
    ("R4", ("OR", "F27", "F28"), "A4", "[1]"),
    ("R5", ("OR", "F12", "F13"), "A5", "[1]"),
    ("R6", ("AND", "A1", "F1"), "K1", "[1]"),
    ("R7", ("AND", "A1", "F4"), "K1", "[1]"),
    ("R8", ("AND", "F1", "F4"), "K1", "[1]"),
    ("R9", ("AND", "A2", "F6"), "K2", "[1][2]"),
    ("R10", ("AND", "F5", "F16"), "K2", "[1][2]"),
    ("R11", ("AND", "F22", "F23"), "K3", "[1][2]"),
    ("R12", ("AND", "F22", "F16"), "K3", "[1][2]"),
    ("R13", ("AND", "A5", "F14"), "K4", "[1]"),
    ("R14", ("AND", "F14", "F13"), "K4", "[1]"),
    ("R15", ("AND", "A5", "F15"), "K5", "[1]"),
    ("R16", ("AND", "F15", "F16"), "K5", "[1]"),
    ("R17", ("AND", "F8", "F9"), "K6", "[1]"),
    ("R18", ("AND", "F8", "F11"), "K6", "[1]"),
    ("R19", ("AND", "A3", "F19"), "K7", "[1][2]"),
    ("R20", ("AND", "F17", "F18"), "K7", "[1][2]"),
    ("R21", ("AND", "F17", "F13"), "K7", "[1]"),
    ("R22", ("AND", "F24", "F25"), "K8", "[1]"),
    ("R23", ("AND", "F20", "F21"), "K9", "[1]"),
    ("R24", ("AND", "F10", "F20"), "K9", "[1]"),
    ("R25", ("AND", "F20", "F13"), "K9", "[1]"),
    ("R26", ("AND", "A4", "F26"), "K10", "[1]"),
    ("R27", ("AND", "F27", "F28"), "K10", "[1]"),
]

# Skenario pengujian: (nama, fakta masukan, diagnosis diharapkan, aturan terpenuhi yang diharapkan)
SKENARIO = [
    ("Penggerek buah kakao", ["F1", "F2"], ["K1"], ["R1", "R6"]),
    ("Kepik penghisap buah", ["F5", "F6"], ["K2"], ["R2", "R9"]),
    ("Penggerek cabang dan batang", ["F22", "F23"], ["K3"], ["R11"]),
    ("Ulat kilan", ["F12", "F14"], ["K4"], ["R5", "R13"]),
    ("Kumbang daun", ["F12", "F15"], ["K5"], ["R5", "R15"]),
    ("Busuk buah", ["F8", "F9"], ["K6"], ["R17"]),
    ("Vascular Streak Dieback (VSD)", ["F17", "F18", "F19"], ["K7"], ["R3", "R19", "R20"]),
    ("Kanker batang", ["F24", "F25"], ["K8"], ["R22"]),
    ("Antraknosa", ["F20", "F21"], ["K9"], ["R23"]),
    ("Penyakit jamur akar", ["F26", "F27"], ["K10"], ["R4", "R26"]),
    ("Dua OPT sekaligus (PBK dan busuk buah)", ["F1", "F4", "F8", "F9"], ["K1", "K6"], ["R8", "R17"]),
    ("Belum dapat disimpulkan (gejala tunggal)", ["F26"], [], []),
    ("Hanya kesimpulan antara (indikasi akar)", ["F27"], [], ["R4"]),
]

# Kata kunci sederhana untuk membantu pengguna menemukan gejala dari tulisan keluhan
KATA_KUNCI = {
    "belang": ["F1"], "masak": ["F1"], "lubang": ["F2", "F12", "F22"], "berlubang": ["F2", "F12"],
    "gerek": ["F2", "F3", "F22"], "larva": ["F3"], "lengket": ["F4"], "tidak bernas": ["F4"],
    "tusuk": ["F5"], "bercak": ["F5", "F10", "F20"], "layu": ["F6", "F16", "F26"], "pentil": ["F6"],
    "gugur": ["F6"], "retak": ["F7"], "berkerut": ["F7"], "busuk": ["F8", "F24", "F28"],
    "spora": ["F9"], "putih": ["F9", "F19", "F27"], "keras": ["F10"], "kering": ["F10", "F16", "F23"],
    "daun habis": ["F13"], "gundul": ["F13", "F21"], "rontok": ["F13"], "ulat": ["F14"], "jengkal": ["F14"],
    "kilan": ["F14"], "kumbang": ["F15"], "pucuk": ["F16"], "ranting": ["F16", "F21"], "meranggas": ["F16"],
    "menguning": ["F17", "F26"], "kuning": ["F17", "F20"], "noktah": ["F18"], "benang": ["F19"],
    "kipas": ["F21"], "cabang": ["F22", "F23"], "batang": ["F22", "F24"], "kulit": ["F24", "F25"],
    "kehitaman": ["F24"], "merah anggur": ["F25"], "mati": ["F16", "F23", "F26"], "akar": ["F27", "F28"],
    "jamur": ["F9", "F27"], "kerak": ["F27"], "lunak": ["F28"], "berair": ["F28"],
}


# ----------------------------------------------------------------------
# MESIN INFERENSI FORWARD CHAINING
# ----------------------------------------------------------------------
def urut(kode):
    """Kunci pengurutan kode: fakta (F), kesimpulan antara (A), diagnosis (K)."""
    return ({"F": 0, "A": 1, "K": 2}[kode[0]], int(kode[1:]))


def premis_benar(premis, memori):
    if isinstance(premis, str):
        return premis in memori
    operator, *anak = premis
    if operator == "AND":
        return all(premis_benar(p, memori) for p in anak)
    return any(premis_benar(p, memori) for p in anak)


def teks_premis(premis, akar=True):
    if isinstance(premis, str):
        return premis
    operator, *anak = premis
    kata = " DAN " if operator == "AND" else " ATAU "
    isi = kata.join(teks_premis(p, False) for p in anak)
    return isi if akar else "(" + isi + ")"


def kode_dalam_premis(premis):
    if isinstance(premis, str):
        return [premis]
    hasil = []
    for p in premis[1:]:
        hasil += kode_dalam_premis(p)
    return hasil


def nama_kode(kode):
    if kode in FAKTA:
        return FAKTA[kode][0]
    if kode in KESIMPULAN_ANTARA:
        return KESIMPULAN_ANTARA[kode]
    return DIAGNOSIS[kode]["nama"]


def forward_chaining(fakta_awal):
    """Menjalankan Forward Chaining. Mengembalikan memori kerja, diagnosis, dan jejak."""
    memori = set(fakta_awal)
    jejak, penyebab = [], {}
    iterasi = 0
    while True:
        aktif = [r for r in RULES if r[2] not in memori and premis_benar(r[1], memori)]
        jejak.append({
            "iterasi": iterasi,
            "memori": sorted(memori, key=urut),
            "aktif": [r[0] for r in aktif],
            "dipilih": aktif[0][0] if aktif else None,
            "baru": aktif[0][2] if aktif else None,
        })
        if not aktif:
            break
        terpilih = aktif[0]              # urutan kode aturan
        memori.add(terpilih[2])
        penyebab[terpilih[2]] = terpilih
        iterasi += 1
    return {
        "memori": sorted(memori, key=urut),
        "diagnosis": [k for k in sorted(memori, key=urut) if k.startswith("K")],
        "antara": [a for a in sorted(memori, key=urut) if a.startswith("A")],
        "terpenuhi": [r[0] for r in RULES if premis_benar(r[1], memori)],
        "jejak": jejak,
        "penyebab": penyebab,
    }


def alasan(kode, penyebab, kedalaman=0):
    """Menyusun penjelasan bertingkat: kesimpulan <- aturan <- fakta atau kesimpulan antara."""
    if kode not in penyebab:
        return []
    r = penyebab[kode]
    garis = ["    " * kedalaman + f"{kode} ({nama_kode(kode)}) dihasilkan oleh {r[0]}: "
             f"JIKA {teks_premis(r[1])} MAKA {r[2]}"]
    for k in kode_dalam_premis(r[1]):
        if k in penyebab:
            garis += alasan(k, penyebab, kedalaman + 1)
    return garis


def aturan_ke_teks(r):
    return f"JIKA {teks_premis(r[1])} MAKA {r[2]}"


def jalankan_skenario():
    baris = []
    for i, (nama, fakta, k_harap, r_harap) in enumerate(SKENARIO, 1):
        h = forward_chaining(fakta)
        sesuai = h["diagnosis"] == sorted(k_harap, key=urut) and h["terpenuhi"] == sorted(r_harap, key=lambda x: int(x[1:]))
        baris.append({"No": i, "Skenario": nama, "Fakta masukan": ", ".join(fakta),
                      "Aturan terpenuhi": ", ".join(h["terpenuhi"]) or "-",
                      "Hasil diharapkan": ", ".join(k_harap) or "Belum dapat disimpulkan",
                      "Hasil sistem": ", ".join(h["diagnosis"]) or "Belum dapat disimpulkan",
                      "Status": "Sesuai" if sesuai else "Tidak sesuai"})
    return baris


# ----------------------------------------------------------------------
# LOGIKA PENDUKUNG: dugaan, penjelasan, dan tips yang menyesuaikan keluhan
# ----------------------------------------------------------------------
def bersih(teks):
    """Hapus penanda sumber seperti [1][2] agar teks lebih enak dibaca pengguna."""
    return re.sub(r"\s*(\[\d\])+", "", teks)


def fakta_terkait(kode):
    """Semua gejala (F) yang berperan pada suatu kesimpulan, termasuk lewat kesimpulan antara."""
    hasil = set()
    for r in RULES:
        if r[2] == kode:
            for k in kode_dalam_premis(r[1]):
                hasil |= {k} if k.startswith("F") else fakta_terkait(k)
    return hasil


def dugaan(fakta, maks=3):
    """Kemungkinan terdekat saat belum ada diagnosis pasti (kecocokan sebagian)."""
    pilih, hasil = set(fakta), []
    for k in DIAGNOSIS:
        rel = fakta_terkait(k)
        cocok = pilih & rel
        if cocok:
            hasil.append({"kode": k, "skor": len(cocok) / len(rel),
                          "cocok": sorted(cocok, key=urut), "cek": sorted(rel - pilih, key=urut)})
    hasil.sort(key=lambda d: (-d["skor"], urut(d["kode"])))
    return hasil[:maks]


def teks_premis_nama(premis, akar=True):
    if isinstance(premis, str):
        return nama_kode(premis)
    operator, *anak = premis
    kata = " dan " if operator == "AND" else " atau "
    isi = kata.join(teks_premis_nama(p, False) for p in anak)
    return isi if akar else "(" + isi + ")"


def petunjuk_kata_kunci(teks):
    t = teks.lower()
    kode = set()
    for kata, daftar in KATA_KUNCI.items():
        if kata in t:
            kode.update(daftar)
    if "gugur" in t and "daun" in t and "buah" not in t and "pentil" not in t:
        kode.discard("F6")
        kode.add("F13")
    return sorted(kode, key=urut)


# Tips: (ikon, judul, isi, kode gejala/diagnosis yang terkait). Disarikan dari rekomendasi basis pengetahuan.
TIPS = [
    ("✂️", "Pangkas rutin", "Pangkas tanaman kakao dan pohon penaungnya secara berkala (3-4 kali setahun) agar kebun tidak terlalu lembap dan cahaya matahari masuk. Buang juga tunas air (wiwilan).", {"K1", "K2", "K5", "K6", "F1", "F2", "F5", "F8", "F9", "F12"}),
    ("🧹", "Sanitasi kebun", "Petik buah yang terserang, kumpulkan buah dan serasah yang jatuh, lalu kubur dalam lubang (minimal 30 cm) agar tidak menjadi sumber penularan.", {"K1", "K2", "K6", "K9", "F2", "F3", "F8", "F9", "F10", "F11"}),
    ("🗓️", "Panen sering", "Panen dengan jarak 4-7 hari sekali dan segera belah buahnya di tempat penampungan. Cara ini memutus siklus hidup penggerek buah kakao.", {"K1", "F1", "F2", "F3", "F4"}),
    ("🛍️", "Sarungi buah muda", "Bungkus buah muda berukuran sekitar 8-15 cm dengan kantong plastik. Biarkan dasar kantong terbuka sebagai ventilasi agar buah tidak terlalu lembap.", {"K1", "K2", "F1", "F2", "F5", "F6", "F7"}),
    ("🐜", "Manfaatkan semut hitam", "Gantung sarang buatan dari lipatan daun kelapa atau daun kakao kering di cabang. Semut hitam membantu menekan penggerek buah dan kepik penghisap buah.", {"K1", "K2", "F2", "F5", "F6"}),
    ("🍃", "Pestisida nabati", "Ekstrak daun mimba, tembakau, babadotan, atau sirsak pada konsentrasi 2,5-5 persen dapat dipakai untuk kepik, ulat kilan, dan kumbang daun sebelum memakai bahan kimia.", {"K2", "K4", "K5", "F5", "F12", "F14", "F15", "F16"}),
    ("🐛", "Kumpulkan ulat", "Kumpulkan dan musnahkan ulat kilan yang terlihat, terutama di pembibitan karena bibit paling rugi bila diserang.", {"K4", "F12", "F13", "F14"}),
    ("🪓", "Potong bagian yang digerek", "Potong cabang yang digerek sekitar 10 cm dari lubang gerekan lalu musnahkan. Pasang perangkap lampu malam untuk ngengat dewasa.", {"K3", "F22", "F23"}),
    ("🌳", "Pilih klon tahan", "Saat peremajaan atau sambung samping, pilih klon yang toleran terhadap OPT di kebun Anda, misalnya Sulawesi 1, Sulawesi 2, DRC 15, DRC 16, atau ICCRI 03 dan 04.", {"K1", "K2", "K6", "K7", "K9", "F17", "F18", "F19"}),
    ("🔪", "Pangkasan sanitasi VSD", "Potong ranting yang sakit sampai batas garis cokelat pada jaringan xylem, ditambah 30-40 cm di bawahnya, lalu musnahkan.", {"K7", "F17", "F18", "F19"}),
    ("🧴", "Rawat luka kanker batang", "Kupas kulit yang busuk sampai jaringan sehat berwarna putih, lalu olesi asap cair, arang, atau fungisida berizin sesuai anjuran penyuluh.", {"K8", "F24", "F25"}),
    ("🌿", "Trichoderma untuk pencegahan", "Jamur antagonis Trichoderma dapat disemprotkan pada buah sehat (busuk buah) atau diaplikasikan di sekitar tanaman yang terkena jamur akar.", {"K6", "K10", "F8", "F9", "F26", "F27"}),
    ("🌱", "Bongkar tanaman terkena jamur akar", "Bongkar tanaman yang mati beserta akarnya sampai bersih, beri belerang di lubang bekas, dan tunggu sekitar satu tahun sebelum menanam lagi.", {"K10", "F26", "F27", "F28"}),
]

TIPS_UMUM = [
    ("🔎", "Pantau berkala", "Periksa buah, bagian bawah daun, batang, dan akar secara rutin. Gejala yang ketahuan sejak awal lebih mudah dikendalikan."),
    ("🛡️", "Pestisida seperlunya", "Dahulukan cara budidaya dan pengendali hayati atau nabati. Bahan kimia jadi pilihan terakhir dan sesuai anjuran penyuluh."),
    ("📝", "Catat kondisi kebun", "Catat tanggal, bagian kebun, dan gejala yang muncul. Catatan ini membantu penyuluh memastikan penyebabnya."),
    ("🤝", "Tanya penyuluh", "Bila gejala meluas atau tidak jelas, minta pemeriksaan penyuluh pertanian atau petugas pengamat hama dan penyakit setempat."),
]


def kode_pengguna(teks_tambahan=""):
    """Kumpulan kode gejala dan diagnosis yang relevan bagi pengguna, dari konsultasi dan tulisan keluhan."""
    kode = set(petunjuk_kata_kunci(teks_tambahan))
    h = st.session_state.get("hasil")
    if h:
        kode |= set(h["fakta"]) | set(h["hasil"]["diagnosis"]) | set(petunjuk_kata_kunci(h["keluhan"]))
        if not h["hasil"]["diagnosis"]:
            kode |= {d["kode"] for d in dugaan(h["fakta"])}
    return kode


def tips_relevan(kode):
    hasil = []
    for ikon, judul_tip, isi, tag in TIPS:
        irisan = tag & kode
        skor = sum(2 if c.startswith("K") else 1 for c in irisan)
        if skor:
            hasil.append((skor, ikon, judul_tip, isi, irisan))
    hasil.sort(key=lambda x: -x[0])
    return hasil


# ----------------------------------------------------------------------
# PENYIMPANAN DATA KONSULTASI (MySQL, dengan cadangan CSV bila MySQL belum siap)
# Database dan tabel dibuat otomatis saat aplikasi dibuka.
# ----------------------------------------------------------------------
KOLOM = ["waktu", "nama", "kelurahan", "keluhan", "gejala", "diagnosis"]
BERKAS_INI = os.path.abspath(__file__) if "__file__" in globals() else "(tidak diketahui)"
FOLDER = os.path.dirname(BERKAS_INI) if "__file__" in globals() else "."
BERKAS_CADANGAN = os.path.join(FOLDER, "cadangan_pakar_kakao_baru.csv")
SQL_TABEL = ("CREATE TABLE IF NOT EXISTS konsultasi (id INT AUTO_INCREMENT PRIMARY KEY, waktu DATETIME NOT NULL, "
             "nama VARCHAR(100) NOT NULL, kelurahan VARCHAR(100) NOT NULL, keluhan TEXT, gejala TEXT, diagnosis TEXT)")
SQL_SIMPAN = "INSERT INTO konsultasi (waktu, nama, kelurahan, keluhan, gejala, diagnosis) VALUES (%s, %s, %s, %s, %s, %s)"


def db_sambung(dengan_db=True):
    import mysql.connector  # pasang lewat: Tools > Manage packages > mysql-connector-python
    cfg = dict(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, connection_timeout=3)
    if dengan_db:
        cfg["database"] = DB_NAME
    return mysql.connector.connect(**cfg)


def db_siapkan():
    kon = db_sambung(False)
    try:
        cur = kon.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4")
        cur.execute(f"USE `{DB_NAME}`")
        cur.execute(SQL_TABEL)
        # Lengkapi kolom bila tabel konsultasi berasal dari versi lama (mis. database sistem_pakar yang diganti nama)
        for kol, tipe in (("kelurahan", "VARCHAR(100) NOT NULL DEFAULT ''"), ("keluhan", "TEXT")):
            cur.execute("SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='konsultasi' AND COLUMN_NAME=%s", (DB_NAME, kol))
            if cur.fetchone()[0] == 0:
                cur.execute(f"ALTER TABLE konsultasi ADD COLUMN {kol} {tipe}")
        kon.commit()
    finally:
        kon.close()


def db_daftar():
    """Daftar semua database di server MySQL (selain database bawaan sistem)."""
    kon = db_sambung(False)
    try:
        cur = kon.cursor()
        cur.execute("SHOW DATABASES")
        semua = [b[0] for b in cur.fetchall()]
    finally:
        kon.close()
    bawaan = {"information_schema", "mysql", "performance_schema", "sys", "phpmyadmin", "test"}
    return [d for d in semua if d.lower() not in bawaan]


def simpan_konsultasi(data):
    """Simpan ke MySQL. Bila gagal, simpan ke CSV cadangan agar data tidak hilang. Mengembalikan (tempat, galat)."""
    try:
        db_siapkan()
        kon = db_sambung()
        try:
            kon.cursor().execute(SQL_SIMPAN, tuple(data[k] for k in KOLOM))
            kon.commit()
        finally:
            kon.close()
        return "MySQL", ""
    except Exception as e:
        ada = os.path.exists(BERKAS_CADANGAN)
        pd.DataFrame([data], columns=KOLOM).to_csv(BERKAS_CADANGAN, mode="a", header=not ada, index=False, encoding="utf-8-sig")
        return "CSV", str(e)


def baca_konsultasi():
    """Baca data konsultasi (terbaru di atas). Mengembalikan (tabel, sumber, galat)."""
    try:
        db_siapkan()   # pastikan database dan tabel yang aktif (DB_NAME) sudah ada
        kon = db_sambung()
        try:
            cur = kon.cursor()
            cur.execute("SELECT id, waktu, nama, kelurahan, keluhan, gejala, diagnosis FROM konsultasi ORDER BY id DESC")
            tabel = pd.DataFrame(cur.fetchall(), columns=["id"] + KOLOM)
        finally:
            kon.close()
        return tabel, "MySQL", ""
    except Exception as e:
        if os.path.exists(BERKAS_CADANGAN):
            tabel = pd.read_csv(BERKAS_CADANGAN, encoding="utf-8-sig").fillna("").iloc[::-1].reset_index(drop=True)
        else:
            tabel = pd.DataFrame(columns=KOLOM)
        return tabel, "CSV", str(e)


def sinkronkan_cadangan():
    """Kirim isi CSV cadangan ke MySQL, lalu ganti namanya agar tidak terkirim dua kali."""
    tabel = pd.read_csv(BERKAS_CADANGAN, encoding="utf-8-sig").fillna("")
    db_siapkan()
    kon = db_sambung()
    try:
        cur = kon.cursor()
        for _, b in tabel.iterrows():
            cur.execute(SQL_SIMPAN, tuple(str(b[k]) for k in KOLOM))
        kon.commit()
    finally:
        kon.close()
    os.replace(BERKAS_CADANGAN, BERKAS_CADANGAN + "." + datetime.now().strftime("%Y%m%d%H%M%S") + ".terkirim")
    return len(tabel)


def db_ganti_kata(lama, baru):
    """Ganti kata (mis. kopi -> kakao) pada kolom keluhan, gejala, dan diagnosis. Mengembalikan jumlah perubahan."""
    kon = db_sambung()
    total = 0
    try:
        cur = kon.cursor()
        for kolom in ("keluhan", "gejala", "diagnosis"):
            for a, b in ((lama, baru), (lama.capitalize(), baru.capitalize())):
                cur.execute(f"UPDATE konsultasi SET {kolom} = REPLACE({kolom}, %s, %s) WHERE {kolom} LIKE %s",
                            (a, b, "%" + a + "%"))
                total += cur.rowcount
        kon.commit()
    finally:
        kon.close()
    return total


def db_hapus(daftar_id):
    """Hapus konsultasi berdasarkan id. Mengembalikan jumlah baris yang terhapus."""
    if not daftar_id:
        return 0
    kon = db_sambung()
    try:
        cur = kon.cursor()
        cur.execute("DELETE FROM konsultasi WHERE id IN (" + ",".join(["%s"] * len(daftar_id)) + ")",
                    tuple(int(i) for i in daftar_id))
        n = cur.rowcount
        kon.commit()
    finally:
        kon.close()
    return n


def db_kosongkan():
    """Hapus semua data konsultasi dan mulai ID dari 1 lagi."""
    kon = db_sambung()
    try:
        kon.cursor().execute("TRUNCATE TABLE konsultasi")
        kon.commit()
    finally:
        kon.close()


def ringkas_diagnosis(hasil, fakta):
    if hasil["diagnosis"]:
        return ", ".join(DIAGNOSIS[k]["nama"] for k in hasil["diagnosis"])
    kira = [DIAGNOSIS[d["kode"]]["nama"] for d in dugaan(fakta)]
    return "Belum dapat disimpulkan" + (" (dugaan: " + ", ".join(kira) + ")" if kira else "")


# ----------------------------------------------------------------------
# TAMPILAN (STREAMLIT)
# Palet segar: teal, amber, jingga-koral, dengan aksen ungu-pink pada banner.
# ----------------------------------------------------------------------
M_BERANDA = "🏠 Beranda"
M_KONSUL = "🩺 Konsultasi"
M_HASIL = "📋 Hasil Diagnosis"
M_TIPS = "💡 Tips Perawatan"
M_TENTANG = "👥 Tentang Kami"
M_ADMIN = "🔐 Admin"
MENU_PUBLIK = [M_BERANDA, M_KONSUL, M_HASIL, M_TIPS, M_TENTANG, M_ADMIN]
IKON_DIAG = {"K1": "🐛", "K2": "🪲", "K3": "🪵", "K4": "🐛", "K5": "🪲", "K6": "🍫", "K7": "🍂", "K8": "🌳", "K9": "🍃", "K10": "🍄"}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
.stApp { color-scheme: light; font-family: 'Plus Jakarta Sans', sans-serif; background-attachment: fixed;
  background: radial-gradient(circle at 5% 0%, #99f6e4 0%, rgba(201,238,187,0) 40%), radial-gradient(circle at 100% 6%, #fed7aa 0%, rgba(255,215,161,0) 40%), linear-gradient(160deg, #f0fdfa 0%, #ecfeff 55%, #fff1e6 100%); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] { display: none !important; }
[data-testid="stMainBlockContainer"], .block-container { max-width: 1120px !important; margin-left: auto !important; margin-right: auto !important; padding-top: 1.4rem; }
[data-testid="stMain"] [data-testid="stMarkdownContainer"] :is(p, li, span, b, strong, i, em, div, td, th) { color: #1e293b; }
[data-testid="stMain"] :is(label, summary, [data-testid="stCaptionContainer"]) { color: #1e293b; }
[data-testid="stMain"] :is(h1, h2, h3, h4) { color: #0f172a !important; font-family: 'Fraunces', Georgia, serif; }
[data-testid="stMain"] [data-testid="stHeading"] h3, [data-testid="stMain"] [data-testid="stMarkdownContainer"] > h3 { position: relative; padding-left: 16px; margin-top: .6rem; }
[data-testid="stMain"] [data-testid="stHeading"] h3::before, [data-testid="stMain"] [data-testid="stMarkdownContainer"] > h3::before { content: ""; position: absolute; left: 0; top: .22em; bottom: .22em; width: 6px; border-radius: 6px; background: linear-gradient(#0d9488, #fbbf24); }
[data-testid="stMain"] input, [data-testid="stMain"] textarea { color: #0f172a !important; background: #ffffff !important; }
[data-testid="stMain"] [data-baseweb="input"], [data-testid="stMain"] [data-baseweb="textarea"], [data-testid="stMain"] [data-baseweb="select"] > div { border-radius: 14px; border-color: #a7d3cc; background: #ffffff; }
[data-testid="stMain"] [data-baseweb="select"] * { color: #0f172a; }
[data-testid="stMain"] button[data-baseweb="tab"] p { color: #0f766e !important; font-weight: 800; }
[data-testid="stMain"] button[data-baseweb="tab"][aria-selected="true"] p { color: #0f766e !important; }
[data-testid="stMain"] [data-baseweb="tab-highlight"] { background: #0d9488; }
[data-testid="stMain"] [data-testid="stCheckbox"] { background: rgba(255,255,255,.85); border: 1px solid #cfe7e3; border-radius: 14px; padding: 8px 14px; margin-bottom: 8px; transition: all .15s; }
[data-testid="stMain"] [data-testid="stCheckbox"]:hover { background: #fff; border-color: #0d9488; transform: translateX(3px); }
[data-testid="stMain"] [data-testid="stExpander"], [data-testid="stMain"] [data-testid="stForm"] { background: rgba(255,255,255,.78); border-radius: 18px; border: 1px solid #cfe7e3; }
[data-testid="stMain"] [data-testid="stMetric"] { background: linear-gradient(145deg, #fff, #e0f7f4); border: 1px solid #cfe7e3; border-radius: 18px; padding: 12px 16px; box-shadow: 0 6px 16px rgba(15,118,110,.12); }
[data-testid="stMain"] [data-testid="stMetric"] * { color: #1e293b !important; }

[data-testid="stMain"] :is(.stButton, [data-testid="stFormSubmitButton"], [data-testid="stDownloadButton"]) > button { width: 100%; display: flex; align-items: center; justify-content: center; text-align: center; background: #ffffff; border: 2px solid #5eead4; border-radius: 999px; padding: .6rem 1.4rem; transition: all .2s; }
[data-testid="stMain"] :is(.stButton, [data-testid="stFormSubmitButton"], [data-testid="stDownloadButton"]) > button p { color: #0f766e; font-weight: 800; margin: 0; text-align: center; }
[data-testid="stMain"] :is(.stButton, [data-testid="stFormSubmitButton"], [data-testid="stDownloadButton"]) > button:hover { background: #fff; border-color: #0d9488; transform: translateY(-2px); box-shadow: 0 8px 18px rgba(15,118,110,.22); }
[data-testid="stMain"] [data-testid="stBaseButton-primary"], [data-testid="stMain"] [data-testid="stBaseButton-primaryFormSubmit"], [data-testid="stMain"] button[kind="primary"],
[data-testid="stMain"] [data-testid="stBaseButton-primary"]:hover, [data-testid="stMain"] [data-testid="stBaseButton-primaryFormSubmit"]:hover, [data-testid="stMain"] button[kind="primary"]:hover { background: linear-gradient(90deg, #fbbf24, #f97316); border: 0; box-shadow: 0 8px 20px rgba(249,115,22,.45); }
[data-testid="stMain"] [data-testid="stBaseButton-primary"] p, [data-testid="stMain"] [data-testid="stBaseButton-primaryFormSubmit"] p, [data-testid="stMain"] button[kind="primary"] p { color: #3b1d00; }

[data-testid="stMain"] [class*="st-key-nav_"] .stButton > button { padding: .5rem .3rem; background: rgba(255,255,255,.85); border: 1.5px solid #cfe7e3; box-shadow: none; }
[data-testid="stMain"] [class*="st-key-nav_"] .stButton > button p { font-size: .93rem; white-space: nowrap; color: #115e59; }
[data-testid="stMain"] [class*="st-key-nav_"] .stButton > button:hover { background: #fff; border-color: #0d9488; }
[data-testid="stMain"] [class*="st-key-nav_"] [data-testid="stBaseButton-primary"], [data-testid="stMain"] [class*="st-key-nav_"] [data-testid="stBaseButton-primary"]:hover { background: linear-gradient(90deg, #0f766e, #14b8a6); border-color: transparent; box-shadow: 0 6px 16px rgba(13,148,136,.45); }
[data-testid="stMain"] [class*="st-key-nav_"] [data-testid="stBaseButton-primary"] p { color: #fff; }
[data-testid="stHorizontalBlock"]:has([class*="st-key-nav_"]) { gap: .5rem; background: rgba(255,255,255,.7); border: 1px solid #cfe7e3; border-radius: 999px; padding: 8px 12px; margin-bottom: 18px; box-shadow: 0 8px 22px rgba(15,118,110,.14); }

[data-testid="stMain"] [data-testid="stRadio"] [role="radiogroup"] { gap: .5rem; flex-wrap: wrap; }
[data-testid="stMain"] [data-testid="stRadio"] label { background: rgba(255,255,255,.85); border: 1.5px solid #cfe7e3; border-radius: 999px; padding: 6px 16px; margin: 0; cursor: pointer; transition: all .15s; }
[data-testid="stMain"] [data-testid="stRadio"] label:hover { background: #fff; border-color: #0d9488; }
[data-testid="stMain"] [data-testid="stRadio"] label:has(input:checked) { background: linear-gradient(90deg, #0f766e, #14b8a6); border-color: transparent; }
[data-testid="stMain"] [data-testid="stRadio"] label:has(input:checked) * { color: #fff !important; }
[data-testid="stMain"] [data-testid="stRadio"] label > div:first-child { display: none; }

.brand { display: flex; justify-content: center; align-items: center; gap: 14px; margin: 2px 0 14px; }
.brand .logo { width: 58px; height: 58px; border-radius: 50%; background: linear-gradient(135deg, #14b8a6, #fbbf24); display: flex; align-items: center; justify-content: center; font-size: 1.9rem; box-shadow: 0 6px 16px rgba(13,148,136,.4); animation: ayun 4s ease-in-out infinite; }
.brand .nm { font-family: 'Fraunces', Georgia, serif; font-weight: 800; font-size: 1.6rem; line-height: 1.1; }
.brand .sb { font-size: .8rem; }
.kaki { text-align: center; margin: 22px 0 6px; font-size: .72rem; }

.stApp .hero { position: relative; overflow: hidden; border-radius: 30px; min-height: 470px; padding: 54px 46px 190px; margin-bottom: 20px;
  background: linear-gradient(115deg, #134e4a, #0d9488, #5eead4, #fcd34d, #f97316, #0d9488, #134e4a); background-size: 320% 320%; animation: geser 16s ease infinite;
  box-shadow: 0 18px 40px rgba(13,148,136,.38); }
.stApp .hero::before { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, rgba(10,45,30,.62), rgba(10,45,30,0) 68%); z-index: 1; }
.stApp .hero .teks { position: relative; z-index: 4; max-width: 54%; }
.stApp .hero h1 { color: #fff !important; font-size: 2.75rem; line-height: 1.15; margin: 0 0 14px 0; text-shadow: 0 2px 10px rgba(0,0,0,.4); }
.stApp .hero p { color: #fff4dc !important; font-size: 1.1rem; margin: 0 0 18px 0; text-shadow: 0 1px 6px rgba(0,0,0,.4); }
.stApp .hero .pil { display: inline-block; padding: 5px 14px; margin: 0 8px 6px 0; border-radius: 999px; background: rgba(255,255,255,.22); border: 1px solid rgba(255,255,255,.55); color: #fff !important; font-weight: 800; font-size: .86rem; }
.hero .matahari { position: absolute; right: 17%; top: 7%; width: 200px; height: 200px; border-radius: 50%; z-index: 1;
  background: radial-gradient(circle, #fffbe0 0%, #ffe27a 36%, rgba(255,190,90,0) 70%); animation: denyut 5s ease-in-out infinite; }
.hero .awan { position: absolute; z-index: 1; height: 26px; width: 110px; border-radius: 999px; background: rgba(255,255,255,.85); animation: lintas 46s linear infinite; }
.hero .awan::before, .hero .awan::after { content: ""; position: absolute; background: rgba(255,255,255,.85); border-radius: 50%; }
.hero .awan::before { width: 46px; height: 46px; left: 16px; top: -22px; }
.hero .awan::after { width: 34px; height: 34px; left: 56px; top: -14px; }
.hero .cangkir { position: absolute; right: 7%; bottom: 112px; width: 270px; z-index: 3; filter: drop-shadow(0 10px 12px rgba(0,0,0,.35)); }
.hero .kebun { position: absolute; left: 0; bottom: 0; width: 100%; height: 195px; z-index: 2; display: block; }
.biji { position: absolute; z-index: 1; width: var(--u); height: calc(var(--u) * 1.45); border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
  background: radial-gradient(circle at 35% 30%, #c99a6b, #6b4128 60%, #3a2214); opacity: .8; animation: melayang 7s ease-in-out infinite; }
.biji::after { content: ""; position: absolute; left: 46%; top: 8%; width: 2px; height: 84%; background: #2a170c; border-radius: 2px; transform: rotate(12deg); }
.hero .uap { fill: none; stroke: #fff; stroke-opacity: .8; stroke-width: 5; stroke-linecap: round; animation: uap 3.4s ease-in-out infinite; }
.hero .uap2 { animation-delay: -1.1s; }
.hero .uap3 { animation-delay: -2.2s; }
@keyframes geser { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
@keyframes denyut { 0%, 100% { transform: scale(1); opacity: .9; } 50% { transform: scale(1.12); opacity: 1; } }
@keyframes melayang { 0%, 100% { transform: translateY(0) rotate(-12deg); } 50% { transform: translateY(-22px) rotate(18deg); } }
@keyframes uap { 0% { opacity: 0; transform: translateY(16px); } 40% { opacity: .85; } 100% { opacity: 0; transform: translateY(-20px); } }
@keyframes lintas { from { left: -20%; } to { left: 110%; } }
@keyframes ayun { 0%, 100% { transform: rotate(-6deg); } 50% { transform: rotate(6deg); } }
@keyframes naik { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@media (max-width: 820px) { .stApp .hero .teks { max-width: 100%; } .hero .cangkir, .hero .matahari { display: none; } .stApp .hero h1 { font-size: 2rem; } }
@media (prefers-reduced-motion: reduce) { .stApp .hero, .biji, .hero .uap, .hero .matahari, .hero .awan, .stApp .banner, .brand .logo, .kartu, .hasil { animation: none; } }

.stApp .banner { position: relative; overflow: hidden; display: flex; align-items: center; gap: 18px; border-radius: 24px; padding: 22px 28px; margin-bottom: 18px;
  background: linear-gradient(115deg, #134e4a, #0f766e, #6366f1, #ec4899); background-size: 260% 260%; animation: geser 20s ease infinite; box-shadow: 0 10px 24px rgba(13,148,136,.3); }
.stApp .banner .bola { flex: 0 0 62px; height: 62px; border-radius: 20px; background: rgba(255,255,255,.88); display: flex; align-items: center; justify-content: center; font-size: 2rem; box-shadow: 0 6px 14px rgba(0,0,0,.2); }
.stApp .banner h2 { color: #fff !important; margin: 0 0 2px 0; padding: 0; text-shadow: 0 2px 8px rgba(0,0,0,.35); }
.stApp .banner p { color: #fff4dc !important; margin: 0; text-shadow: 0 1px 6px rgba(0,0,0,.35); }

.kartu { border-radius: 22px; padding: 18px 22px 20px; box-shadow: 0 8px 22px rgba(15,118,110,.16); border: 1px solid rgba(15,118,110,.14); height: 100%; transition: transform .2s, box-shadow .2s; animation: naik .6s ease both; }
.kartu:hover { transform: translateY(-5px); box-shadow: 0 16px 30px rgba(15,118,110,.26); }
.kartu.p1 { background: linear-gradient(145deg, #ccfbf1, #99f6e4); }
.kartu.p2 { background: linear-gradient(145deg, #fef3c7, #fde68a); }
.kartu.p3 { background: linear-gradient(145deg, #ffe4e6, #fecdd3); }
.kartu.p4 { background: linear-gradient(145deg, #ede9fe, #ddd6fe); }
.kartu .ik { width: 48px; height: 48px; border-radius: 15px; background: rgba(255,255,255,.85); display: flex; align-items: center; justify-content: center; font-size: 1.55rem; margin-bottom: 10px; box-shadow: 0 4px 10px rgba(15,118,110,.18); }
.kartu h4 { margin: 0 0 6px 0; }
.kartu p { margin: 0 0 6px 0; }
.hasil { background: linear-gradient(135deg, #ffffff 0%, #ccfbf1 100%); border-left: 8px solid #0d9488; border-radius: 18px; padding: 18px 22px; margin: 14px 0 8px; box-shadow: 0 8px 22px rgba(15,118,110,.16); animation: naik .5s ease both; }
.hasil h3 { margin: 0; padding: 0; }
.stApp .lencana { display: inline-block; padding: 3px 12px; border-radius: 999px; background: linear-gradient(90deg, #0f766e, #14b8a6); color: #fff !important; font-size: .8rem; margin-left: 8px; font-weight: 800; }
.kotak { border-radius: 16px; padding: 12px 16px; margin: 10px 0; border: 1px solid; }
.kotak.info { background: #ccfbf1; border-color: #5eead4; }
.kotak.sukses { background: #bbf7d0; border-color: #4ade80; }
.kotak.waspada { background: #fef3c7; border-color: #fcd34d; }
.rekom { display: flex; gap: 12px; align-items: flex-start; background: rgba(255,255,255,.92); border-radius: 14px; padding: 10px 14px; margin: 8px 0; border: 1px solid #cfe7e3; }
.stApp .rekom .c { flex: 0 0 26px; height: 26px; border-radius: 50%; background: #0d9488; color: #fff !important; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: .8rem; }
.langkah { display: flex; gap: 14px; align-items: flex-start; }
.stApp .langkah .no { flex: 0 0 42px; height: 42px; border-radius: 50%; background: linear-gradient(135deg, #0d9488, #fbbf24); color: #fff !important; font-weight: 800; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(15,118,110,.3); }
.stApp .dev { display: flex; gap: 22px; align-items: center; border-radius: 26px; padding: 26px 30px; margin: 6px 0 16px; background: linear-gradient(120deg, #134e4a, #0d9488, #f59e0b); box-shadow: 0 14px 30px rgba(13,148,136,.35); }
.stApp .dev .avatar { flex: 0 0 80px; height: 80px; border-radius: 50%; background: linear-gradient(135deg, #fde68a, #fbbf24); display: flex; align-items: center; justify-content: center; font-size: 2.3rem; font-weight: 800; font-family: 'Fraunces', Georgia, serif; color: #1e293b !important; box-shadow: 0 6px 16px rgba(0,0,0,.3); }
.stApp .dev h3 { color: #fff !important; margin: 0 0 4px 0; padding: 0; }
.stApp .dev p { color: #fff4dc !important; margin: 0; }
/* ===== Percantik tambahan ===== */
.brand .nm { background: linear-gradient(90deg, #0f766e, #f97316); -webkit-background-clip: text; background-clip: text; color: transparent !important; }
.brand .sb { color: #475569 !important; }
.stApp .hero { box-shadow: 0 24px 50px rgba(13,148,136,.35), 0 0 0 1px rgba(255,255,255,.25) inset; }
.stApp .hero h1 { letter-spacing: -.5px; }
.stApp .hero .pil { backdrop-filter: blur(6px); background: rgba(255,255,255,.2); }
.stApp .banner { box-shadow: 0 14px 30px rgba(99,102,241,.28); }
.kartu { backdrop-filter: blur(4px); border: 1px solid rgba(255,255,255,.7); }
.kartu h4 { color: #0f172a; font-weight: 800; }
.kartu:hover { transform: translateY(-6px) scale(1.01); }
.hasil { border-left-width: 8px; border-image: linear-gradient(#0d9488, #f97316) 1; border-radius: 0; }
.rekom { box-shadow: 0 3px 10px rgba(15,118,110,.08); transition: transform .15s; }
.rekom:hover { transform: translateX(4px); }
.stApp .rekom .c { background: linear-gradient(135deg, #0d9488, #14b8a6); }
.kotak { box-shadow: 0 3px 10px rgba(15,23,42,.05); }
[data-testid="stMain"] [data-testid="stDataFrame"] { border-radius: 16px; overflow: hidden; border: 1px solid #cfe7e3; box-shadow: 0 6px 16px rgba(15,118,110,.1); }
[data-testid="stMain"] [data-testid="stMetric"] { border-left: 5px solid #0d9488; }
[data-testid="stMain"] [data-testid="stMetricValue"] { font-family: 'Fraunces', Georgia, serif; font-size: 1.25rem !important; }
[data-testid="stMain"] [data-testid="stMetricLabel"] p { font-size: .78rem !important; }
[data-testid="stMain"] [data-baseweb="input"]:focus-within, [data-testid="stMain"] [data-baseweb="textarea"]:focus-within { border-color: #0d9488; box-shadow: 0 0 0 3px rgba(13,148,136,.2); }
.kaki { display: block; width: fit-content; margin: 22px auto 6px; padding: 3px 12px; font-size: .6rem !important; opacity: .8; border-radius: 999px; background: rgba(255,255,255,.75); border: 1px solid #cfe7e3; color: #475569 !important; box-shadow: 0 4px 12px rgba(15,118,110,.1); }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: linear-gradient(#14b8a6, #fbbf24); border-radius: 10px; }
</style>
"""


def svg_kebun():
    """Perbukitan kebun kakao: bukit berlapis, deretan pohon, buah kakao kuning-oranye."""
    semak = ""
    for y, rx, ry, warna, geser in [(114, 15, 11, "#2c7d49", 0), (162, 19, 14, "#17583a", 22)]:
        for x in range(10 + geser, 1200, 44):
            semak += f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{warna}"/>'
            if (x // 22 + y) % 2 == 0:
                semak += (f'<ellipse cx="{x - 5}" cy="{y - 2}" rx="2.6" ry="4.2" fill="#f2a62e"/>'
                          f'<ellipse cx="{x + 6}" cy="{y + 3}" rx="2.6" ry="4.2" fill="#e8892b"/>')
    return ('<svg class="kebun" viewBox="0 0 1200 200" preserveAspectRatio="xMidYMax slice" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 90 C200 40 400 70 600 55 C800 40 1000 75 1200 50 L1200 200 L0 200Z" fill="#d8803f"/>'
            '<path d="M0 125 C250 85 450 115 700 95 C900 80 1050 110 1200 90 L1200 200 L0 200Z" fill="#46a05a"/>'
            '<path d="M0 160 C300 135 600 170 900 150 C1050 140 1150 155 1200 148 L1200 200 L0 200Z" fill="#23704a"/>'
            + semak + '<rect x="0" y="190" width="1200" height="10" fill="#6b3f24"/></svg>')


def svg_cangkir():
    return ('<svg class="cangkir" viewBox="0 0 260 240" xmlns="http://www.w3.org/2000/svg">'
            '<ellipse cx="120" cy="214" rx="108" ry="14" fill="#1d0f0a" opacity=".35"/>'
            '<ellipse cx="120" cy="198" rx="104" ry="18" fill="#f6e3c6"/>'
            '<ellipse cx="120" cy="192" rx="80" ry="12" fill="#fff4e0"/>'
            '<path d="M44 98 H196 C196 160 176 194 120 194 C64 194 44 160 44 98Z" fill="#fff4e0"/>'
            '<path d="M196 112 C238 108 238 170 186 170" fill="none" stroke="#fff4e0" stroke-width="13" stroke-linecap="round"/>'
            '<ellipse cx="120" cy="98" rx="76" ry="14" fill="#3b1c10"/>'
            '<ellipse cx="120" cy="100" rx="60" ry="9" fill="#8a4a28"/>'
            '<path class="uap uap1" d="M92 82 C80 62 104 50 92 28"/>'
            '<path class="uap uap2" d="M122 80 C110 58 134 46 122 22"/>'
            '<path class="uap uap3" d="M152 82 C140 62 164 50 152 30"/></svg>')


def biji_melayang(pos=None):
    pos = pos or [(5, 14, 24, 0), (17, 62, 16, -3), (34, 18, 20, -1), (48, 66, 14, -5),
                  (62, 10, 22, -2), (76, 56, 18, -4), (90, 16, 26, -6), (95, 66, 14, -2)]
    return "".join(f'<span class="biji" style="left:{x}%;top:{y}%;--u:{u}px;animation-delay:{d}s"></span>'
                   for x, y, u, d in pos)


def awan():
    return "".join(f'<div class="awan" style="top:{t}%;animation-delay:{d}s;transform:scale({s})"></div>'
                   for t, d, s in [(10, 0, 1), (28, -18, .7), (18, -32, .85)])


def kartu(ikon, judul_kartu, isi, ekstra="", warna=1):
    return (f'<div class="kartu p{warna}"><div class="ik">{ikon}</div><h4>{judul_kartu}</h4>'
            f'<p>{isi}</p>{ekstra}</div>')


def banner(ikon, judul_halaman, sub=""):
    st.markdown(f'<div class="banner">{biji_melayang([(78, 20, 16, 0), (88, 55, 12, -3), (94, 15, 20, -5)])}'
                f'<div class="bola">{ikon}</div><div><h2>{judul_halaman}</h2><p>{sub}</p></div></div>',
                unsafe_allow_html=True)


def kotak(jenis, isi):
    st.markdown(f'<div class="kotak {jenis}">{isi}</div>', unsafe_allow_html=True)


def rekom(daftar):
    for item in daftar:
        st.markdown(f'<div class="rekom"><div class="c">✓</div><div>{html.escape(bersih(item))}</div></div>', unsafe_allow_html=True)


def baris_kartu(daftar_html, per_baris=3):
    for i in range(0, len(daftar_html), per_baris):
        kolom = st.columns(per_baris)
        for kol, isi in zip(kolom, daftar_html[i:i + per_baris]):
            kol.markdown(isi, unsafe_allow_html=True)
        st.write("")


def pilih_bagian(daftar, key):
    """Pilihan bagian berbentuk tombol bulat (pengganti st.tabs). Tetap terpilih saat halaman dimuat ulang."""
    if st.session_state.get(key) not in daftar:
        st.session_state[key] = daftar[0]
    return st.radio("Bagian", daftar, key=key, horizontal=True, label_visibility="collapsed")


def tombol_tengah(label, **kw):
    _, tengah, _ = st.columns([1, 1.3, 1])
    return tengah.button(label, **kw)


# ----------------------------------------------------------------------
# STATE DAN NAVIGASI
# ----------------------------------------------------------------------
def pindah(menu):
    st.session_state.menu = menu


def siapkan():
    st.session_state.hasil = None
    st.session_state.in_nama = ""
    st.session_state.in_kelurahan = ""
    st.session_state.in_keluhan = ""
    for k in FAKTA:
        st.session_state[f"chk_{k}"] = False


def reset_konsultasi():
    siapkan()
    st.session_state.menu = M_KONSUL


def ubah_jawaban():
    h = st.session_state.hasil
    st.session_state.in_nama = h["nama"]
    st.session_state.in_kelurahan = h["kelurahan"]
    st.session_state.in_keluhan = h["keluhan"]
    for k in FAKTA:
        st.session_state[f"chk_{k}"] = k in h["fakta"]
    st.session_state.menu = M_KONSUL


def isi_dari_keluhan():
    for k in petunjuk_kata_kunci(st.session_state.get("in_keluhan", "")):
        st.session_state[f"chk_{k}"] = True


def keluar_admin():
    st.session_state.admin = False


# ----------------------------------------------------------------------
# HALAMAN
# ----------------------------------------------------------------------
def halaman_beranda():
    st.markdown(
        '<div class="hero">' + awan() + biji_melayang() + '<div class="matahari"></div>' + svg_cangkir() + svg_kebun() +
        '<div class="teks"><h1>Kebun kakao sehat dimulai dari gejala yang tampak</h1>'
        "<p>Ceritakan keluhan tanaman kakao Anda. Sistem pakar menebak hama atau penyakitnya, "
        "lalu memberi saran penanganan yang bisa langsung dicoba.</p>"
        f'<span class="pil">🍫 {len(FAKTA)} gejala</span><span class="pil">🐛 {len(DIAGNOSIS)} hama dan penyakit</span>'
        f'<span class="pil">📜 {len(RULES)} aturan pakar</span></div></div>', unsafe_allow_html=True)
    tombol_tengah("Mulai konsultasi ➜", type="primary", on_click=pindah, args=(M_KONSUL,), key="cta_mulai")
    st.write("")
    baris_kartu([
        kartu("🌱", "Mudah digunakan", "Tulis keluhan dengan kata-kata Anda sendiri, lalu centang gejala yang terlihat. Tidak perlu istilah teknis.", warna=1),
        kartu("🎯", "Hasil langsung", "Sistem menyebutkan kemungkinan hama atau penyakit beserta saran penanganan awalnya.", warna=2),
        kartu("📖", "Berbasis sumber", "Pengetahuan disusun dari buku saku dan buku pedoman resmi Direktorat Jenderal Perkebunan, Kementerian Pertanian.", warna=3),
    ])
    st.subheader("Cara kerja")
    baris_kartu([
        f'<div class="kartu p{w} langkah"><div class="no">{no}</div><div><b>{jd}</b><br>{tx}</div></div>'
        for w, (no, jd, tx) in enumerate([(1, "Ceritakan keluhan", "Isi nama, kelurahan, dan tuliskan kondisi kebun yang Anda lihat."),
                                          (2, "Pilih gejala", "Centang gejala pada buah, daun, batang, atau akar yang paling mirip."),
                                          (3, "Baca hasilnya", "Lihat kemungkinan penyakit, saran penanganan, dan tips perawatan yang cocok.")], 1)])
    st.subheader("Hama dan penyakit yang dikenali")
    baris_kartu([kartu(IKON_DIAG[k], d["nama"], f'<i>{d["latin"]}</i>',
                       f'<span class="lencana" style="margin-left:0">{d["jenis"]}</span>', warna=1 if d["jenis"] == "Hama" else 3)
                 for k, d in DIAGNOSIS.items()], 4)
    kotak("waspada", "⚠️ Hasil sistem adalah <b>diagnosis awal</b> dan tidak menggantikan pemeriksaan penyuluh pertanian "
                     "atau petugas pengamat hama dan penyakit. Gunakan pestisida hanya sesuai anjuran pada label dan petugas.")


def halaman_konsultasi():
    banner("🩺", "Konsultasi Kebun Kakao", "Ceritakan keluhan Anda, lalu pilih gejala yang paling mendekati.")
    kotak("waspada", "Amati tanaman dengan aman. Jangan menyentuh atau menyemprotkan bahan kimia tanpa perlindungan dan petunjuk petugas.")
    k1, k2 = st.columns(2)
    k1.text_input("Nama Anda", key="in_nama", placeholder="Contoh: Budi Santoso")
    k2.text_input("Kelurahan / Desa", key="in_kelurahan", placeholder="Contoh: Yosomulyo")
    st.text_area("Apa yang Anda keluhkan pada kebun kakao Anda?", key="in_keluhan", height=110,
                 placeholder="Contoh: Buah kakao saya berlubang kecil, masaknya belang, dan bijinya lengket.")
    petunjuk = petunjuk_kata_kunci(st.session_state.get("in_keluhan", ""))
    if petunjuk:
        kotak("info", f"✨ Dari keluhan Anda, sistem mengenali <b>{len(petunjuk)} kemungkinan gejala</b>. "
                      "Klik tombol di bawah untuk mencentangnya otomatis, lalu periksa kembali daftarnya.")
        tombol_tengah("✨ Centang gejala dari keluhan saya", on_click=isi_dari_keluhan, key="btn_otomatis")

    st.markdown("### Pilih gejala yang paling mendekati kondisi tanaman Anda")
    st.caption("Boleh lebih dari satu. Makin lengkap gejalanya, makin tepat hasilnya.")
    grup = ["Buah", "Daun dan pucuk", "Batang, cabang, dan akar"]
    tabs = st.tabs(["🍫 Buah", "🍃 Daun dan pucuk", "🌿 Batang, cabang, dan akar"])
    for tab, g in zip(tabs, grup):
        with tab:
            for kode, (nama, kelompok, _) in FAKTA.items():
                if kelompok == g:
                    st.checkbox(nama, key=f"chk_{kode}")

    terpilih = [k for k in FAKTA if st.session_state.get(f"chk_{k}")]
    st.markdown(f"**{len(terpilih)} gejala dipilih**")
    if tombol_tengah("🔍 Diagnosis sekarang", type="primary", key="btn_diagnosis"):
        nama = st.session_state.in_nama.strip()
        kelurahan = st.session_state.in_kelurahan.strip()
        otomatis = False
        if not terpilih and petunjuk:
            terpilih, otomatis = petunjuk, True
        galat = []
        if not re.fullmatch(r"[A-Za-z][A-Za-z .'\-]{1,49}", nama):
            galat.append("Nama wajib diisi (2 sampai 50 karakter, hanya huruf, spasi, titik, apostrof, atau tanda hubung).")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .,'/\-]{1,59}", kelurahan):
            galat.append("Kelurahan atau desa wajib diisi (2 sampai 60 karakter).")
        if not terpilih:
            galat.append("Pilih minimal satu gejala, atau tuliskan keluhan yang menggambarkan kondisi tanaman.")
        for g in galat:
            st.error(g)
        if not galat:
            hasil = forward_chaining(terpilih)
            simpan_konsultasi({"waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "nama": nama, "kelurahan": kelurahan,
                               "keluhan": st.session_state.in_keluhan.strip(),
                               "gejala": "; ".join(FAKTA[k][0] for k in terpilih),
                               "diagnosis": ringkas_diagnosis(hasil, terpilih)})
            st.session_state.hasil = {"nama": nama, "kelurahan": kelurahan, "keluhan": st.session_state.in_keluhan,
                                      "fakta": terpilih, "otomatis": otomatis, "hasil": hasil}
            st.session_state.menu = M_HASIL
            st.rerun()


def halaman_hasil():
    banner("📋", "Hasil Diagnosis", "Kemungkinan hama atau penyakit beserta saran penanganannya.")
    h = st.session_state.hasil
    if not h:
        st.markdown(kartu("🌾", "Belum ada hasil", "Lakukan konsultasi terlebih dahulu. Setelah keluhan dan gejala diisi, hasil diagnosis muncul di halaman ini.", warna=2), unsafe_allow_html=True)
        st.write("")
        tombol_tengah("Mulai konsultasi ➜", type="primary", on_click=pindah, args=(M_KONSUL,), key="cta_kosong")
        return
    r = h["hasil"]
    st.markdown(f"### Hasil untuk {h['nama']} ({h['kelurahan']})")
    if h["keluhan"].strip():
        kotak("info", "<b>Keluhan Anda:</b> " + html.escape(h["keluhan"].strip()))
    if h.get("otomatis"):
        kotak("info", "Anda belum mencentang gejala, jadi sistem memakai gejala yang dikenali dari keluhan Anda. Daftarnya ada di bagian penjelasan.")

    if r["diagnosis"]:
        kotak("sukses", f"✅ Ditemukan <b>{len(r['diagnosis'])} kemungkinan</b> hama atau penyakit pada tanaman Anda.")
        for k in r["diagnosis"]:
            d = DIAGNOSIS[k]
            st.markdown(f'<div class="hasil"><h3>{IKON_DIAG[k]} {d["nama"]} <span class="lencana">{d["jenis"]}</span></h3>'
                        f'<i>{d["latin"]}</i></div>', unsafe_allow_html=True)
            st.markdown("**Saran penanganan awal**")
            rekom(d["rekomendasi"])
    else:
        kotak("waspada", "Belum ada diagnosis yang pasti. Setiap hama atau penyakit dikenali dari beberapa gejala yang muncul bersamaan, "
                         "sedangkan gejala yang dipilih baru sebagian. Berikut kemungkinan terdekat berdasarkan gejala Anda.")
        kira = dugaan(h["fakta"])
        for d in kira:
            info = DIAGNOSIS[d["kode"]]
            st.markdown(f'<div class="hasil"><h3>{IKON_DIAG[d["kode"]]} {info["nama"]} <span class="lencana">Kemungkinan</span></h3>'
                        f'<i>{info["latin"]}</i></div>', unsafe_allow_html=True)
            st.markdown("**Gejala Anda yang cocok:** " + "; ".join(FAKTA[k][0] for k in d["cocok"]))
            if d["cek"]:
                st.markdown("**Periksa juga:** " + "; ".join(FAKTA[k][0] for k in d["cek"][:3]))
            with st.expander("Saran penanganan awal"):
                rekom(info["rekomendasi"])
        if not kira:
            st.write("Tambahkan gejala lain yang terlihat pada buah, daun, batang, atau akar.")
        if r["antara"]:
            st.markdown("**Indikasi awal:** " + "; ".join(KESIMPULAN_ANTARA[a] for a in r["antara"]))

    with st.expander("🔍 Mengapa hasilnya begini?"):
        st.markdown("**Gejala yang dipakai sistem**")
        for k in h["fakta"]:
            st.markdown(f"- {FAKTA[k][0]}")
        for k in r["diagnosis"]:
            st.markdown(f"**{DIAGNOSIS[k]['nama']}** disimpulkan karena terdeteksi: {teks_premis_nama(r['penyebab'][k][1])}.")

    if st.session_state.get("admin"):
        with st.expander("🛠️ Detail teknis Forward Chaining (admin)"):
            for k in r["diagnosis"]:
                st.code("\n".join(alasan(k, r["penyebab"])), language="text")
            st.dataframe(pd.DataFrame([{"Aturan": x[0], "Isi aturan": aturan_ke_teks(x)} for x in RULES if x[0] in r["terpenuhi"]]), hide_index=True, width="stretch")
            st.dataframe(pd.DataFrame([{"Iterasi": j["iterasi"], "Memori kerja": ", ".join(j["memori"]),
                                        "Aturan aktif": ", ".join(j["aktif"]) or "-", "Aturan dipilih": j["dipilih"] or "-",
                                        "Fakta baru": j["baru"] or "-"} for j in r["jejak"]]), hide_index=True, width="stretch")

    st.write("")
    c1, c2, c3 = st.columns(3)
    c1.button("✏️ Ubah jawaban", on_click=ubah_jawaban, key="btn_ubah")
    c2.button("🔄 Konsultasi ulang", on_click=reset_konsultasi, key="btn_ulang")
    c3.button("💡 Tips untuk saya", type="primary", on_click=pindah, args=(M_TIPS,), key="btn_tips")


def kartu_tips(ikon, judul_tip, isi, irisan, warna):
    nama = [DIAGNOSIS[c]["nama"] for c in sorted(irisan, key=urut) if c.startswith("K")]
    label = "Cocok untuk: " + ", ".join(nama) if nama else "Cocok dengan gejala Anda"
    return kartu(ikon, judul_tip, isi, f'<span class="lencana" style="margin-left:0">{label}</span>', warna)


def halaman_tips():
    banner("💡", "Tips Perawatan", "Saran perawatan yang menyesuaikan dengan keluhan dan gejala Anda.")
    h = st.session_state.get("hasil")
    if h:
        nama = [DIAGNOSIS[k]["nama"] for k in h["hasil"]["diagnosis"]] or [DIAGNOSIS[d["kode"]]["nama"] for d in dugaan(h["fakta"])]
        kotak("info", "Berdasarkan konsultasi terakhir Anda" + (": <b>" + ", ".join(nama) + "</b>." if nama else "."))
    st.text_area("Ingin tips untuk keluhan lain? Tuliskan di sini", key="in_tips", height=90,
                 placeholder="Contoh: Buah kakao saya berlubang dan bijinya lengket")
    tombol_tengah("💡 Cari tips yang cocok", type="primary", key="btn_cari")
    kode = kode_pengguna(st.session_state.get("in_tips", ""))
    st.markdown("### Tips untuk keluhan Anda")
    if not kode:
        kotak("waspada", "Belum ada keluhan yang bisa dicocokkan. Lakukan konsultasi, atau tulis keluhan di kotak di atas. Tips umum ada di bawah.")
    else:
        cocok = tips_relevan(kode)
        if cocok:
            baris_kartu([kartu_tips(i, j, t, ir, n % 4 + 1) for n, (_, i, j, t, ir) in enumerate(cocok[:6])])
        else:
            kotak("waspada", "Belum ada tips khusus untuk kata-kata tersebut. Coba tuliskan gejalanya, misalnya daun gugur, buah berlubang, atau akar membusuk.")
    st.markdown("### Tips umum untuk semua kebun")
    baris_kartu([kartu(i, j, t, warna=n % 4 + 1) for n, (i, j, t) in enumerate(TIPS_UMUM)], 4)
    st.caption("Disarikan dari Maryani dan Daniati (2019) serta Wibawanti dkk. (2025). Tidak menggantikan pemeriksaan penyuluh pertanian.")


def halaman_tentang():
    banner("👥", "Tentang Kami", "Mengenal sistem pakar kakao dan pengembangnya.")
    baris_kartu([
        kartu("🍫", "Untuk apa sistem ini?", "Membantu pekebun kakao mengenali hama atau penyakit tanaman dari gejala yang terlihat, tanpa harus menunggu petugas datang.", warna=1),
        kartu("🧠", "Bagaimana cara kerjanya?", "Pengetahuan pakar ditulis sebagai aturan JIKA-MAKA. Sistem mencocokkan gejala Anda dengan aturan itu secara bertahap (Forward Chaining) sampai muncul kesimpulan.", warna=2),
        kartu("📖", "Dari mana pengetahuannya?", "Dari Buku Saku Hama dan Penyakit Tanaman Kakao (Maryani dan Daniati, Ditjenbun, 2019) dan Buku Pedoman Pengenalan dan Pengendalian OPT Tanaman Penyegar dan Tahunan (Wibawanti dkk., Pertanian Press, 2025).", warna=3),
    ])
    st.subheader("Yang bisa Anda lakukan")
    baris_kartu([
        kartu("🩺", "Konsultasi", "Tulis keluhan dan pilih gejala yang mendekati kondisi tanaman.", warna=4),
        kartu("📋", "Lihat diagnosis", "Dapatkan kemungkinan hama atau penyakit beserta saran penanganan awal.", warna=1),
        kartu("💡", "Ikuti tips", "Baca tips perawatan yang disesuaikan dengan keluhan Anda.", warna=2),
    ])
    st.subheader("Pengembang")
    st.markdown(f'<div class="dev"><div class="avatar">{html.escape(NAMA_PEMBUAT[:1])}</div><div>'
                f"<h3>{html.escape(NAMA_PEMBUAT)}</h3><p>NIM {html.escape(NIM_PEMBUAT)}</p>"
                "<p>S1 Teknik Informatika</p></div></div>", unsafe_allow_html=True)
    kotak("waspada", f"Batasan: sistem mencakup {len(DIAGNOSIS)} hama dan penyakit, memakai jawaban Ya atau Tidak tanpa tingkat keyakinan, "
                     "dan hasilnya berupa diagnosis awal yang tidak menggantikan pemeriksaan penyuluh pertanian.")


# ----------------------------------------------------------------------
# PANEL ADMIN
# ----------------------------------------------------------------------
def status_sumber(sumber, galat):
    if sumber == "MySQL":
        kotak("sukses", f"✅ Terhubung ke MySQL (database <b>{html.escape(DB_NAME)}</b>).")
    else:
        petunjuk = "Buka tab Database untuk mengecek koneksi."
        if "10061" in galat or "2003" in galat:
            petunjuk = "MySQL belum menyala. Buka XAMPP Control Panel lalu klik Start pada baris MySQL, kemudian muat ulang halaman ini."
        elif "1045" in galat:
            petunjuk = "Kata sandi MySQL salah. Samakan DB_USER dan DB_PASSWORD di bagian atas berkas dengan akun MySQL Anda."
        elif "No module named" in galat:
            petunjuk = "Pustaka belum terpasang. Di Thonny buka Tools > Manage packages, lalu pasang mysql-connector-python."
        kotak("waspada", "MySQL belum terhubung, jadi yang tampil adalah data cadangan di komputer ini. " + html.escape(petunjuk) +
                         "<br><small>Penyebab: " + html.escape(galat) + "</small>")


def isi_dashboard(tabel, sumber, galat):
    status_sumber(sumber, galat)
    if tabel.empty:
        kotak("info", "Belum ada data konsultasi. Dashboard terisi setelah pengguna menekan Diagnosis sekarang.")
        return
    t = tabel.copy()
    t["waktu"] = pd.to_datetime(t["waktu"], errors="coerce")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total konsultasi", len(t))
    m2.metric("Pengguna berbeda", int(t["nama"].astype(str).str.strip().str.lower().nunique()))
    m3.metric("Kelurahan berbeda", int(t["kelurahan"].astype(str).str.strip().str.lower().nunique()))
    m4.metric("Konsultasi hari ini", int((t["waktu"].dt.date == datetime.now().date()).sum()))
    st.write("")
    hitung = {}
    for teks in t["diagnosis"].astype(str):
        for nama in (["Belum dapat disimpulkan"] if teks.startswith("Belum") else teks.split(", ")):
            hitung[nama] = hitung.get(nama, 0) + 1
    k1, k2 = st.columns(2)
    with k1:
        st.markdown("### Diagnosis terbanyak")
        st.bar_chart(pd.Series(hitung).sort_values(ascending=False), color="#f97316", horizontal=True)
    with k2:
        st.markdown("### Konsultasi per kelurahan")
        st.bar_chart(t["kelurahan"].astype(str).str.strip().value_counts(), color="#0d9488", horizontal=True)
    per_hari = t.dropna(subset=["waktu"]).groupby(t["waktu"].dt.date).size()
    if len(per_hari):
        per_hari.index = [str(d) for d in per_hari.index]
        st.markdown("### Konsultasi per hari")
        st.bar_chart(per_hari, color="#6366f1")
    st.markdown("### Konsultasi terbaru")
    terbaru = t.head(10).copy()
    terbaru["waktu"] = terbaru["waktu"].dt.strftime("%d-%m-%Y %H:%M")
    st.dataframe(terbaru[["waktu", "nama", "kelurahan", "keluhan", "diagnosis"]].rename(columns={
        "waktu": "Waktu", "nama": "Nama", "kelurahan": "Kelurahan", "keluhan": "Keluhan", "diagnosis": "Diagnosis"}),
        hide_index=True, width="stretch")


def kosongkan_semua(sumber):
    """Hapus semua data konsultasi (MySQL) dan berkas cadangan CSV bila ada."""
    if sumber == "MySQL":
        db_kosongkan()
    if os.path.exists(BERKAS_CADANGAN):
        os.remove(BERKAS_CADANGAN)


def kelola_data(tabel, sumber):
    """Alat bantu admin: kosongkan semua data, ganti kata, atau hapus data terpilih."""
    kotak("waspada", "Ingin memulai dari nol? Tombol di bawah menghapus <b>semua</b> data konsultasi lama "
                     "(termasuk berkas cadangan CSV) dan tidak bisa dibatalkan.")
    yakin2 = st.checkbox("Saya yakin ingin menghapus SEMUA data konsultasi", key="yakin_semua")
    if tombol_tengah("🧹 Kosongkan semua data konsultasi", key="btn_kosong"):
        if not yakin2:
            st.error("Centang dulu kotak keyakinan di atas.")
        else:
            try:
                kosongkan_semua(sumber)
                st.session_state.yakin_semua = False
                st.session_state.pesan_admin = "✅ Semua data konsultasi lama sudah dikosongkan. Data baru akan tercatat dari konsultasi berikutnya."
                st.rerun()
            except Exception as e:
                st.error("Gagal mengosongkan: " + str(e))
    if sumber != "MySQL":
        return
    with st.expander("🛠️ Ganti kata atau hapus data tertentu"):
        st.markdown("**Ganti kata pada data lama**")
        c1, c2 = st.columns(2)
        lama = c1.text_input("Kata yang diganti", value="", key="kata_lama")
        baru = c2.text_input("Diganti menjadi", value="", key="kata_baru")
        if st.button("🔁 Ganti kata pada semua data", key="btn_ganti"):
            if not lama.strip():
                st.error("Kata yang diganti tidak boleh kosong.")
            else:
                try:
                    n = db_ganti_kata(lama.strip(), baru.strip())
                    st.session_state.pesan_admin = f"✅ Selesai. {n} perubahan dilakukan: kata '{lama.strip()}' diganti '{baru.strip()}'."
                    st.rerun()
                except Exception as e:
                    st.error("Gagal mengganti: " + str(e))
        st.markdown("**Hapus data terpilih**")
        opsi = {int(r["id"]): f'#{r["id"]} | {r["waktu"]} | {r["nama"]} | {str(r["keluhan"])[:45]}' for _, r in tabel.iterrows()}
        pilih = st.multiselect("Pilih data yang dihapus", list(opsi), format_func=lambda i: opsi[i], key="hapus_id")
        yakin = st.checkbox("Saya yakin ingin menghapus data terpilih", key="yakin_hapus")
        if st.button("🗑️ Hapus data terpilih", key="btn_hapus"):
            if not pilih:
                st.error("Pilih minimal satu data.")
            elif not yakin:
                st.error("Centang dulu kotak keyakinan.")
            else:
                try:
                    st.session_state.pesan_admin = f"✅ {db_hapus(pilih)} data berhasil dihapus."
                    st.session_state.hapus_id = []
                    st.session_state.yakin_hapus = False
                    st.rerun()
                except Exception as e:
                    st.error("Gagal menghapus: " + str(e))


def isi_data_konsultasi(tabel, sumber, galat):
    status_sumber(sumber, galat)
    st.caption(f"Menampilkan semua konsultasi pengguna: {len(tabel)} data.")
    if tabel.empty:
        kotak("info", "Belum ada data konsultasi. Data muncul di sini setelah pengguna menekan Diagnosis sekarang.")
        return
    kelola_data(tabel, sumber)
    pilihan = ["Semua"] + sorted(tabel["kelurahan"].astype(str).unique())
    pilih = st.selectbox("Filter kelurahan", pilihan, key="flt_kel")
    tampil = tabel if pilih == "Semua" else tabel[tabel["kelurahan"].astype(str) == pilih]
    tampil = tampil.rename(columns={"id": "ID", "waktu": "Waktu", "nama": "Nama", "kelurahan": "Kelurahan",
                                    "keluhan": "Keluhan", "gejala": "Gejala", "diagnosis": "Diagnosis"})
    st.dataframe(tampil, hide_index=True, width="stretch")
    _, tengah, _ = st.columns([1, 1.3, 1])
    tengah.download_button("⬇️ Unduh data (CSV)", tampil.to_csv(index=False).encode("utf-8-sig"),
                           file_name="data_konsultasi.csv", mime="text/csv", key="unduh_csv")


def isi_basis():
    bagian = pilih_bagian(["Fakta", "Kesimpulan", "Aturan", "Sumber"], "basis_bagian")
    st.write("")
    if bagian == "Fakta":
        st.dataframe(pd.DataFrame([{"Kode": k, "Gejala": v[0], "Kelompok": v[1], "Domain nilai": "Ya / Tidak", "Sumber": v[2]}
                                   for k, v in FAKTA.items()]), hide_index=True, width="stretch")
    elif bagian == "Kesimpulan":
        st.markdown("**Kesimpulan antara**")
        st.dataframe(pd.DataFrame([{"Kode": k, "Kesimpulan antara": v} for k, v in KESIMPULAN_ANTARA.items()]), hide_index=True, width="stretch")
        st.markdown("**Diagnosis akhir**")
        st.dataframe(pd.DataFrame([{"Kode": k, "Diagnosis": v["nama"], "Penyebab": v["latin"], "Jenis": v["jenis"]}
                                   for k, v in DIAGNOSIS.items()]), hide_index=True, width="stretch")
    elif bagian == "Aturan":
        st.dataframe(pd.DataFrame([{"Kode": r[0], "Premis (JIKA)": teks_premis(r[1]), "Kesimpulan (MAKA)": r[2], "Sumber": r[3]}
                                   for r in RULES]), hide_index=True, width="stretch")
    else:
        st.markdown(
            "- [1] Y. Maryani dan C. Daniati, *Buku Saku Hama dan Penyakit Tanaman Kakao*. Jakarta: Direktorat Perlindungan "
            "Perkebunan, Ditjen Perkebunan, Kementerian Pertanian, 2019.\n"
            "- [2] R. Wibawanti dkk., *Buku Pedoman Pengenalan dan Pengendalian OPT Tanaman Penyegar dan Tahunan "
            "(Kakao, Kopi, dan Jambu Mete)*. Bogor: Pertanian Press, 2025.")


def isi_pengujian():
    st.write("Setiap skenario dijalankan dengan mesin inferensi yang sama seperti pada konsultasi, "
             "lalu dibandingkan dengan hasil yang diharapkan dari basis pengetahuan.")
    baris = jalankan_skenario()
    st.dataframe(pd.DataFrame(baris), hide_index=True, width="stretch")
    sesuai = sum(1 for b in baris if b["Status"] == "Sesuai")
    st.metric("Tingkat kesesuaian", f"{sesuai / len(baris) * 100:.1f}%", f"{sesuai} dari {len(baris)} skenario sesuai")


def isi_database():
    st.markdown("**Status koneksi MySQL**")
    m1, m2, m3 = st.columns(3)
    m1.metric("Server", f"{DB_HOST}:{DB_PORT}")
    m2.metric("Pengguna", DB_USER)
    m3.metric("Database", DB_NAME)
    c1, c2 = st.columns(2)
    if c1.button("🔌 Tes koneksi MySQL", key="btn_tes"):
        try:
            db_siapkan()
            kotak("sukses", f"✅ Terhubung. Database <b>{html.escape(DB_NAME)}</b> dan tabel konsultasi siap dipakai.")
        except Exception as e:
            kotak("waspada", "Belum bisa terhubung: " + html.escape(str(e)))
    if os.path.exists(BERKAS_CADANGAN):
        if c2.button("📤 Kirim data cadangan ke MySQL", key="btn_sinkron"):
            try:
                kotak("sukses", f"✅ {sinkronkan_cadangan()} data cadangan berhasil dikirim ke MySQL.")
            except Exception as e:
                kotak("waspada", "Gagal mengirim: " + html.escape(str(e)))
    else:
        c2.caption("Tidak ada data cadangan yang menunggu dikirim.")


def halaman_admin():
    banner("🔐", "Panel Admin", "Data pengguna, basis pengetahuan, pengujian, dan pengaturan database.")
    if not st.session_state.get("admin"):
        _, tengah, _ = st.columns([1, 1.6, 1])
        with tengah:
            with st.form("form_admin"):
                st.markdown("#### Masuk sebagai admin")
                sandi = st.text_input("Kata sandi", type="password", placeholder="Masukkan kata sandi admin")
                masuk = st.form_submit_button("Masuk", type="primary")
            if masuk:
                if hmac.compare_digest(sandi.strip().encode("utf-8"), ADMIN_PASSWORD.encode("utf-8")):
                    st.session_state.admin = True
                    st.rerun()
                else:
                    st.error("Kata sandi salah. Coba lagi.")
        return
    kotak("sukses", f"Anda masuk sebagai admin. Database aktif: <b>{html.escape(DB_NAME)}</b> (versi {html.escape(VERSI)}).")
    pesan = st.session_state.pop("pesan_admin", None)
    if pesan:
        kotak("sukses", html.escape(pesan))
    tabel, sumber, galat = baca_konsultasi()
    bagian = pilih_bagian(["📊 Dashboard", "👤 Data Konsultasi", "📚 Basis Pengetahuan", "🧪 Pengujian", "🗄️ Database"], "admin_bagian")
    st.write("")
    if bagian.endswith("Dashboard"):
        isi_dashboard(tabel, sumber, galat)
    elif bagian.endswith("Data Konsultasi"):
        isi_data_konsultasi(tabel, sumber, galat)
    elif bagian.endswith("Basis Pengetahuan"):
        isi_basis()
    elif bagian.endswith("Pengujian"):
        isi_pengujian()
    else:
        isi_database()
    st.write("")
    tombol_tengah("🚪 Keluar dari admin", on_click=keluar_admin, key="btn_keluar")


HALAMAN = {M_BERANDA: halaman_beranda, M_KONSUL: halaman_konsultasi, M_HASIL: halaman_hasil,
           M_TIPS: halaman_tips, M_TENTANG: halaman_tentang, M_ADMIN: halaman_admin}


def main():
    st.set_page_config(page_title="Sistem Pakar Kakao", page_icon="🍫", layout="wide",
                       initial_sidebar_state="collapsed")
    st.markdown(re.sub(r"\n\s*\n", "\n", CSS), unsafe_allow_html=True)
    if "hasil" not in st.session_state:
        siapkan()
    if "menu" not in st.session_state:
        st.session_state.menu = M_BERANDA
    if st.session_state.menu not in MENU_PUBLIK:
        st.session_state.menu = M_BERANDA

    st.markdown('<div class="brand"><div class="logo">🍫</div><div><div class="nm">Sistem Pakar Kakao</div>'
                '<div class="sb">Diagnosis awal hama dan penyakit tanaman kakao</div></div></div>', unsafe_allow_html=True)
    for kol, (i, m) in zip(st.columns(len(MENU_PUBLIK)), enumerate(MENU_PUBLIK)):
        kol.button(m, key=f"nav_{i}", on_click=pindah, args=(m,),
                   type="primary" if st.session_state.menu == m else "secondary")

    HALAMAN[st.session_state.menu]()

    st.markdown(f'<div class="kaki">🍫 Sistem Pakar Kakao · dikembangkan oleh {html.escape(NAMA_PEMBUAT)}</div>', unsafe_allow_html=True)


def dijalankan_oleh_streamlit():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        try:
            return get_script_run_ctx(suppress_warning=True) is not None
        except TypeError:
            return get_script_run_ctx() is not None
    except Exception:
        return False


if dijalankan_oleh_streamlit():
    main()
elif __name__ == "__main__":
    # Dijalankan lewat tombol Run di Thonny: buka aplikasi di peramban lewat Streamlit.
    # Port dikunci 8501. Bila sudah dipakai Streamlit lama, Streamlit menampilkan galat (bukan diam-diam
    # pindah ke port lain), sehingga Anda tahu harus menghentikan proses lama dulu.
    import subprocess
    import sys
    # Thonny kadang menjalankan kode tanpa __file__ (berkas belum disimpan). Cari lokasi berkas dengan cadangan.
    lokasi = globals().get("__file__") or (sys.argv[0] if sys.argv and sys.argv[0].endswith(".py") else "")
    if not lokasi or not os.path.exists(lokasi):
        lokasi = os.path.join(os.getcwd(), "hamakakao.py")
    if not os.path.exists(lokasi):
        raise SystemExit("Simpan dulu berkas ini (File > Save as, mis. hamakakao.py), lalu tekan Run lagi.")
    subprocess.run([sys.executable, "-m", "streamlit", "run", lokasi,
                    "--server.port", "8501",
                    "--theme.base", "light", "--theme.primaryColor", "#0d9488",
                    "--theme.backgroundColor", "#f0fdfa", "--theme.secondaryBackgroundColor", "#ecfeff",
                    "--theme.textColor", "#1e293b"])