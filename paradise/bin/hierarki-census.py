# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Census hierarki: jenjang, pengawasan, dan dampak kalau aturan penugasan dinyalakan
#
# Jalankan di dalam container API:
#   docker exec -i pradise_plane-api-1 python manage.py shell < paradise/bin/hierarki-census.py
#
# Uji kering (default): tanpa ORG_APPLY   |   Terapkan: ORG_APPLY=1
#
# Menerapkan hanya membaca `paradise/hierarki-organisasi.csv` (lihat bentuknya di
# bawah). Tanpa berkas itu, tidak ada yang ditulis walau ORG_APPLY=1.
# Idempoten: dijalankan dua kali menghasilkan keadaan yang sama.
#
# ## Kenapa census ini ada
#
# Rancangan `.herdr/hierarki-desain.md` §6: pertanyaan yang harus dijawab SEBELUM
# menyalakan aturan penugasan adalah "berapa penugasan yang tiba-tiba butuh
# persetujuan" dan "berapa orang yang tidak punya atasan". Keduanya tidak bisa dijawab
# dengan membaca kode, dan jawabannya berbeda di tiap database.
#
# ## Kenapa `ProjectMember.role = 20` TIDAK dipakai sebagai "atasan"
#
# Diukur 14 Okt 2026: 5 akun NON-SuperAdmin memegang `ProjectMember.role = 20` di
# ~27-31 divisi masing-masing (dibuat 31 Juli oleh skrip, 5 Agustus oleh
# bintang.ramadhan@). Ditambah 12 Super Admin yang memang Admin di semua project,
# `role = 20` menjadi 647 dari 805 baris. Memakainya sebagai atasan akan memberi
# setiap divisi 5 atasan palsu tanpa satu pun error. Karena itu census ini memakai
# tabel `jabatan_organisasi`, dan MELAPORKAN keadaan role 20 sebagai peringatan.

import csv
import os

from django.db import transaction

from plane.db.models import (
    IssueAssignee,
    JabatanOrganisasi,
    PengawasanDivisi,
    Project,
    ProjectMember,
    TINGKAT_CHOICES,
    TINGKAT_MEMBER,
    TINGKAT_NAMA,
    TINGKAT_SUPERVISOR,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.utils.hierarki import BUTUH_PERSETUJUAN, TANPA_ATASAN, periksa_penugasan

APPLY = os.environ.get("ORG_APPLY") == "1"
CSV_JALUR = os.path.join("paradise", "hierarki-organisasi.csv")

# Akun uji yang pernah dibuat di workspace produksi. Disaring dari hitungan "88
# karyawan" saja, bukan dari daftar mentahnya.
AKUN_UJI = {"tester@paradiseperkasa.com"}

# Nama jenjang yang boleh ditulis di CSV. Menerima angka maupun kata.
NAMA_KE_TINGKAT = {}
for _nilai, _nama in TINGKAT_CHOICES:
    NAMA_KE_TINGKAT[str(_nilai)] = _nilai
    NAMA_KE_TINGKAT[_nama.lower()] = _nilai

# Angka 20/15/5 milik `ROLE` project, dan 20 di sana berarti "Admin divisi" -- bukan
# "Supervisor". Kalau seseorang menulis 15 di CSV dengan harapan "Member" ala project,
# ia akan mendapat jenjang yang salah. Jadi 15/5 ditolak dengan pesan yang menjelaskan,
# bukan diam-diam dibulatkan.
TINGKAT_SALAH_KAPAL = {15: "15 adalah ROLE project (Member), bukan jenjang. Pakai 10 untuk member.",
                       5: "5 adalah ROLE project (Guest). Jenjang terendah adalah 10 (member)."}

ws = Workspace.objects.filter(slug=os.environ.get("HIERARKI_WORKSPACE", "pt-paradise-perkasa")).first()
if ws is None:
    print(f"! Workspace tidak ditemukan: {os.environ.get('HIERARKI_WORKSPACE', 'pt-paradise-perkasa')}")
    raise SystemExit(1)

print("=" * 78)
print("CENSUS HIERARKI   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print(f"workspace: {ws.slug}")
print("=" * 78)

anggota = list(
    WorkspaceMember.objects.filter(workspace=ws, is_active=True).select_related("member").order_by("member__email")
)
proyek = {p.id: p for p in Project.objects.filter(workspace=ws, deleted_at__isnull=True)}
peta = dict(JabatanOrganisasi.objects.filter(workspace=ws).values_list("member_id", "tingkat"))
pengawasan = {}
for pid, uid in PengawasanDivisi.objects.filter(workspace=ws).values_list("project_id", "member_id"):
    pengawasan.setdefault(uid, set()).add(pid)

divisi_orang = {}
for uid, pid in ProjectMember.objects.filter(workspace=ws, is_active=True).values_list("member_id", "project_id"):
    if pid in proyek:
        divisi_orang.setdefault(uid, set()).add(pid)

uid_email = {wm.member_id: wm.member.email for wm in anggota}
uid_nama = {wm.member_id: wm.member.display_name for wm in anggota}

# --------------------------------------------------------------------------
# 1) Keadaan jenjang
# --------------------------------------------------------------------------
print("\n1) KEADAAN JENJANG")
print("-" * 78)
punya = [u for u in uid_email if u in peta]
belum = [u for u in uid_email if u not in peta]
print(f"   anggota workspace aktif          : {len(uid_email)}")
print(f"   sudah punya jenjang              : {len(punya)}")
print(f"   BELUM diisi                      : {len(belum)}")
for uid in sorted(punya, key=lambda u: -peta[u]):
    sumber = JabatanOrganisasi.objects.filter(workspace=ws, member_id=uid).values_list("sumber", flat=True).first()
    print(f"     {uid_email[uid]:<45} {TINGKAT_NAMA.get(peta[uid], peta[uid]):<12} ({sumber})")
if belum:
    print("   yang belum diisi (maks 15 ditampilkan):")
    for uid in sorted(belum, key=lambda u: uid_email[u])[:15]:
        print(f"     {uid_email[uid]}")

# --------------------------------------------------------------------------
# 2) Siapa yang tidak punya atasan
# --------------------------------------------------------------------------
print("\n2) ORANG YANG TIDAK PUNYA ATASAN (dihitung dari JENJANG, bukan dari role project)")
print("-" * 78)
tertinggi_per_divisi = {}
for uid, tingkat in peta.items():
    for pid in divisi_orang.get(uid, set()):
        sekarang = tertinggi_per_divisi.get(pid)
        if sekarang is None or tingkat > sekarang[1]:
            tertinggi_per_divisi[pid] = (uid, tingkat)

tanpa_atasan = []
for uid in uid_email:
    tingkat = peta.get(uid)
    punya_atasan = False
    for pid in divisi_orang.get(uid, set()):
        t = tertinggi_per_divisi.get(pid)
        if t and t[0] != uid and tingkat is not None and t[1] > tingkat:
            punya_atasan = True
            break
    if not punya_atasan:
        tanpa_atasan.append(uid)

tanpa_atasan_uji = [u for u in tanpa_atasan if uid_email[u] not in AKUN_UJI]
print(f"   tanpa atasan                     : {len(tanpa_atasan)} dari {len(uid_email)}")
print(f"   tanpa atasan (tanpa akun uji)    : {len(tanpa_atasan_uji)} dari {len(uid_email) - len(AKUN_UJI & set(uid_email))}")
print("   -> selama belum ada jenjang yang diisi, angka ini SAMA dengan jumlah anggota.")
print("      Itu jawaban yang benar (kekosongan data), bukan kerusakan.")

# --------------------------------------------------------------------------
# 3) Dampak pada penugasan yang SUDAH ADA
# --------------------------------------------------------------------------
print("\n3) DAMPAK PADA PENUGASAN YANG SUDAH ADA")
print("-" * 78)
penugasan = (
    IssueAssignee.objects.filter(project__workspace=ws, project__deleted_at__isnull=True)
    .select_related("issue", "assignee", "created_by")
)
n_total = n_butuh = n_tanpa = n_tolak = n_serah = 0
n_dinilai = 0
# Batas aman: `periksa_penugasan()` sengaja memakai implementasi yang SAMA dengan
# gerbangnya (satu keputusan, bukan dua). Ongkosnya beberapa query per penugasan.
# Di produksi penugasan hidup cuma belasan; di DB berisi data dummy bisa puluhan ribu,
# dan census tidak boleh menggantung karena itu.
BATAS_NILAI = 5000
per_project = {}
for a in penugasan:
    n_total += 1
    if a.assignee_id == a.created_by_id:
        n_serah += 1
    if n_dinilai >= BATAS_NILAI:
        continue
    n_dinilai += 1
    putusan = periksa_penugasan(a.project_id, [a.assignee_id], actor=a.created_by, abaikan_katup=True)
    kunci = proyek[a.project_id].identifier if a.project_id in proyek else str(a.project_id)
    if putusan is None:
        continue
    if putusan == BUTUH_PERSETUJUAN:
        n_butuh += 1
    elif putusan == TANPA_ATASAN:
        n_tanpa += 1
    else:
        n_tolak += 1
    per_project.setdefault(kunci, {"butuh": 0, "tanpa": 0, "tolak": 0})
    per_project[kunci]["butuh" if putusan == BUTUH_PERSETUJUAN else ("tanpa" if putusan == TANPA_ATASAN else "tolak")] += 1

print(f"   penugasan hidup                  : {n_total}")
print(f"   untuk diri sendiri               : {n_serah}")
print(f"   dinilai (batas {BATAS_NILAI})          : {n_dinilai}")
print(f"   -> butuh persetujuan             : {n_butuh}")
print(f"   -> tanpa atasan (tidak bisa disetujui apa pun) : {n_tanpa}")
print(f"   -> ditolak oleh aturan           : {n_tolak}")
for kunci, v in sorted(per_project.items()):
    print(f"      {kunci:<8} butuh={v['butuh']} tanpa_atasan={v['tanpa']} ditolak={v['tolak']}")
print("   CATATAN: hitungan ini memakai `abaikan_katup=True`, yaitu jawaban atas")
print("   'kalau katupnya dinyalakan'. Hari ini katupnya MATI, jadi tidak ada yang ditolak.")

# --------------------------------------------------------------------------
# 4) Peringatan: role 20 di banyak divisi
# --------------------------------------------------------------------------
print("\n4) PERINGATAN: baris role=20 (=Admin divisi) di BANYAK divisi")
print("-" * 78)
role20 = {}
for uid, pid in ProjectMember.objects.filter(workspace=ws, is_active=True, role=20).values_list(
    "member_id", "project_id"
):
    if pid in proyek:
        role20.setdefault(uid, set()).add(pid)
for uid, divs in sorted(role20.items(), key=lambda x: -len(x[1])):
    if len(divs) < 5:
        continue
    print(f"   {uid_email.get(uid, uid):<45} {len(divs)} divisi")
print("   Ini BUKAN data hierarki. Ia ada di sini supaya tidak ada yang memakai")
print("   `ProjectMember.role = 20` sebagai proksi 'atasan' -- hasilnya 5 atasan palsu")
print("   di setiap divisi, tanpa error. Lihat .herdr/hierarki-desain.md paragraf 1.3.")

# --------------------------------------------------------------------------
# 5) Terapkan (hanya kalau diminta DAN berkasnya ada)
# --------------------------------------------------------------------------
print("\n5) PENERAPAN")
print("-" * 78)
if not os.path.exists(CSV_JALUR):
    print(f"   berkas {CSV_JALUR} tidak ada -> tidak ada yang ditulis.")
    print("   Bentuknya: kolom `email,tingkat,sumber,catatan`; tingkat = direktur|manager|")
    print("   supervisor|member atau 40|30|20|10. Baris `email,tingkat` sudah cukup.")
    print("   TIDAK ADA baris = jenjang belum diisi (BUKAN member) -- itu disengaja.")
else:
    baris = []
    with open(CSV_JALUR, newline="", encoding="utf-8") as f:
        for i, r in enumerate(csv.DictReader(f), start=2):
            email = (r.get("email") or "").strip().lower()
            mentah = (r.get("tingkat") or "").strip().lower()
            if not email or email.startswith("#"):
                continue
            if mentah not in NAMA_KE_TINGKAT:
                print(f"   ! baris {i}: tingkat '{mentah}' tidak dikenal, dilewati")
                continue
            nilai = NAMA_KE_TINGKAT[mentah]
            if nilai in TINGKAT_SALAH_KAPAL:
                print(f"   ! baris {i}: {TINGKAT_SALAH_KAPAL[nilai]} Dilewati.")
                continue
            baris.append((email, nilai, (r.get("sumber") or "manual").strip(), (r.get("catatan") or "").strip()))

    users = {u.email.lower(): u for u in User.objects.filter(is_active=True, is_bot=False)}
    n_baru = n_ubah = n_lewat = 0
    with transaction.atomic():
        for email, tingkat, sumber, catatan in baris:
            u = users.get(email)
            if u is None:
                print(f"   ! user tidak ada: {email}")
                n_lewat += 1
                continue
            lama = peta.get(u.id)
            if lama == tingkat:
                n_lewat += 1
                continue
            n_baru += 1 if lama is None else 0
            n_ubah += 1 if lama is not None else 0
            print(f"   {'+' if lama is None else '~'} {email:<45} {lama} -> {tingkat} ({sumber})")
            if APPLY:
                # `all_objects` + hidupkan kembali, BUKAN `get_or_create` dengan manager
                # bawaan: jebakan A21 -- manager bawaan menyaring baris ber-deleted_at,
                # jadi `get_or_create` akan membuat baris BARU dan menabrak constraint
                # unik. (Dijalankan di dalam blok yang sama dengan peringatan ini karena
                # itu satu-satunya cara jebakan itu tidak terulang.)
                obj = JabatanOrganisasi.all_objects.filter(workspace=ws, member=u).first()
                if obj is None:
                    JabatanOrganisasi.objects.create(
                        workspace=ws, member=u, tingkat=tingkat, sumber=sumber, catatan=catatan
                    )
                else:
                    obj.deleted_at = None
                    obj.tingkat = tingkat
                    obj.sumber = sumber
                    obj.catatan = catatan
                    obj.save(update_fields=["deleted_at", "tingkat", "sumber", "catatan"])
        if not APPLY:
            print("\n   UJI KERING, transaksi dibatalkan, tidak ada yang ditulis.")
            transaction.set_rollback(True)
    print(f"   baru={n_baru} diubah={n_ubah} dilewati={n_lewat}")

print("\nSelesai.")
