#!/bin/bash
set -e

# Tanda tangan mesin, dipakai `register_instance` di bawah.
# Collect system information
HOSTNAME=$(hostname)
MAC_ADDRESS=$(ip link show | awk '/ether/ {print $2}' | head -n 1)
CPU_INFO=$(cat /proc/cpuinfo)
MEMORY_INFO=$(free -h)
DISK_INFO=$(df -h)

# Concatenate information and compute SHA-256 hash
SIGNATURE=$(echo "$HOSTNAME$MAC_ADDRESS$CPU_INFO$MEMORY_INFO$DISK_INFO" | sha256sum | awk '{print $1}')

# Export the variables
export MACHINE_SIGNATURE=$SIGNATURE

# ---------------------------------------------------------------------------
# SATU proses Python untuk seluruh tugas start, bukan tujuh.
#
# KENAPA. Tiap `python manage.py <x>` mem-boot Django dari nol, dan boot itu
# 3,6 detik di server ini. Versi lama memanggilnya ENAM kali berturut-turut,
# jadi hampir seluruh waktu start habis untuk mengimpor Django berulang-ulang
# sebelum gunicorn mau mendengarkan. Diukur dari log start sungguhan:
#
#   wait_for_migrations          10,7 dtk
#   register_instance             9,4 dtk
#   configure_instance            9,1 dtk
#   create_bucket                 8,9 dtk
#   clear_cache + collectstatic  13,7 dtk
#   gunicorn                      2,1 dtk
#   TOTAL 53,9 detik dari container hidup sampai melayani permintaan
#
# Empat dari enam langkah itu bahkan tidak mengerjakan apa pun sesudah boot
# pertama; lognya berbunyi "already registered" dan "already exists". Yang
# dibayar mahal bukan pekerjaannya, melainkan boot Django-nya. `collectstatic`
# juga bukan biang keroknya: ia cuma menyalin 44 berkas.
#
# Diukur di container produksi: satu boot 3,6 detik + seluruh perintah 1,7
# detik = 5,2 detik, menggantikan sekitar 47 detik.
#
# Ini memperpendek jendela 502 saat deploy: selama `api` belum mendengarkan,
# proxy tidak punya tujuan untuk meneruskan permintaan, dan semua orang
# menerima 502.
#
# Seluruh langkah dan URUTANNYA dipertahankan persis, tidak ada yang dilewati.
#
# Aman dirangkai dalam satu proses: keenam perintah sudah diperiksa dan tidak
# satu pun memanggil sys.exit atau os._exit, jadi tidak ada yang memutus proses
# di tengah. Kalau salah satu melempar galat, Python keluar bukan-nol dan
# `set -e` di atas tetap menghentikan container, sama seperti perilaku lama.
# ---------------------------------------------------------------------------
python - <<'PYTHON'
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plane.settings.production")
django.setup()

from django.core.management import call_command

# Urutannya sama persis dengan versi lama, dan itu disengaja: `create_bucket`
# butuh konfigurasi yang dimuat `configure_instance`, dan `collectstatic`
# ditaruh terakhir supaya cache sudah bersih saat manifest ditulis.
call_command("wait_for_db")
call_command("wait_for_migrations")
call_command("register_instance", os.environ["MACHINE_SIGNATURE"])
call_command("configure_instance")
call_command("create_bucket")
call_command("clear_cache")
call_command("collectstatic", interactive=False)
PYTHON

exec gunicorn -w "$GUNICORN_WORKERS" -k uvicorn.workers.UvicornWorker plane.asgi:application --bind 0.0.0.0:"${PORT:-8000}" --max-requests 1200 --max-requests-jitter 1000 --access-logfile -
