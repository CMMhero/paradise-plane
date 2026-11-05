# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pesan langsung antar-karyawan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import models

# Module imports
from .base import BaseModel

# Batas panjang satu pesan. Bukan batas teknis TextField, tapi batas kewarasan:
# tanpa ini satu tempelan berisi seluruh isi spreadsheet masuk ke tabel dan tiap
# pemuatan percakapan ikut menyeretnya.
# KEP-83: batas yang berlaku sekarang CHAT_MESSAGE_MAX_LENGTH di God Mode
# (app/views/chat.py membacanya); angka ini tinggal sebagai bawaannya yang lama.
BATAS_ISI = 5000

# Kanal sistem (3 Nov 2026). Dua kanal per workspace yang diikuti SEMUA anggota,
# plus satu ruang kabar "Paradise" per orang untuk kartu aktivitas. Kunci kabar
# memuat id pemiliknya: `kabar:<user_id>`.
KUNCI_PENGUMUMAN = "pengumuman"
KUNCI_CHANGELOG = "changelog"
AWALAN_KABAR = "kabar:"


class JenisPesan(models.TextChoices):
    """Bentuk sebuah pesan. `teks` = pesan biasa; sisanya kartu yang dirender
    peramban dari `muatan`. `isi` tetap diisi ringkasan teks untuk pencarian,
    email, dan peramban lama yang belum mengenal kartu."""

    TEKS = "teks", "Teks"
    PANGGILAN = "panggilan", "Log panggilan"
    CHANGELOG = "changelog", "Catatan rilis"
    TUGAS = "tugas", "Ditugaskan"
    PROJECT = "project", "Ditambahkan ke project"
    PERSETUJUAN = "persetujuan", "Persetujuan"
    MENTION = "mention", "Disebut"
    KOMENTAR = "komentar", "Komentar"
    PEMBARUAN = "pembaruan", "Pembaruan work item"


class Ruang(BaseModel):
    """Tempat pesan hidup: obrolan berdua, kanal publik, atau kanal privat.

    Model ini menggantikan keputusan lama "tanpa tabel Percakapan". Keputusan itu
    benar selama chat hanya melayani dua orang, dan catatan di PesanLangsung sudah
    memperingatkan bahwa ia tidak akan sanggup menampung kanal. Sekarang saatnya.

    Bentuknya meniru Rocket.Chat: SATU tabel untuk ketiga jenis ruang, dibedakan
    oleh `tipe`. Alternatifnya tabel terpisah untuk DM dan kanal, dan itu berarti
    setiap kueri daftar percakapan, pencarian, dan hitungan belum dibaca ditulis
    dua kali lalu digabung. Satu tabel membuat semuanya jadi satu jalur.
    """

    class Tipe(models.TextChoices):
        DM = "dm", "Pesan Langsung"
        KANAL = "kanal", "Kanal Publik"
        PRIVAT = "privat", "Kanal Privat"

    workspace = models.ForeignKey("db.Workspace", related_name="ruang_obrolan", on_delete=models.CASCADE)
    tipe = models.CharField(max_length=10, choices=Tipe.choices, default=Tipe.DM)
    # Kosong untuk DM: namanya adalah lawan bicaranya, dan itu berbeda tergantung
    # siapa yang melihat. Wajib untuk kanal.
    nama = models.CharField(max_length=80, null=True, blank=True)
    topik = models.CharField(max_length=255, blank=True, default="")

    # Dua id pengguna diurutkan lalu disambung titik dua, hanya untuk DM.
    # Tanpa ini, "cari ruang antara A dan B" berarti dua kali join ke tabel
    # langganan tiap kali orang membuka percakapan. Dengan ini, satu lookup
    # ke indeks unik. Urutan id-nya di-sort supaya A-ke-B dan B-ke-A
    # menghasilkan kunci yang sama persis.
    kunci_dm = models.CharField(max_length=73, null=True, blank=True, unique=True)

    # Disalin dari pesan terakhir supaya daftar percakapan bisa diurutkan tanpa
    # subquery per ruang. Denormalisasi yang disengaja: daftar itu dibuka jauh
    # lebih sering daripada pesan dikirim.
    pesan_terakhir_pada = models.DateTimeField(null=True, blank=True)

    # Ruang milik sistem: tidak bisa ditinggalkan, dihapus, atau diganti nama oleh
    # orang biasa. `kunci_sistem` membedakan perannya (pengumuman, changelog,
    # kabar:<user_id>) dan unik per workspace, jadi pembuatan ulang yang berjalan
    # bersamaan tidak bisa menghasilkan dua kanal Changelog.
    sistem = models.BooleanField(default=False)
    kunci_sistem = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        verbose_name = "Ruang Obrolan"
        verbose_name_plural = "Ruang Obrolan"
        db_table = "chat_rooms"
        ordering = ("-pesan_terakhir_pada",)
        indexes = [
            models.Index(fields=["workspace", "tipe"], name="ruang_ws_tipe_idx"),
            models.Index(fields=["workspace", "pesan_terakhir_pada"], name="ruang_ws_terakhir_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "kunci_sistem"],
                condition=models.Q(kunci_sistem__isnull=False, deleted_at__isnull=True),
                name="ruang_ws_kunci_sistem_unik",
            )
        ]

    def __str__(self):
        return self.nama or f"dm:{self.kunci_dm}"

    @property
    def is_system(self) -> bool:
        """Alias `sistem`, dibaca `chat_kelola.py`."""
        return self.sistem

    @staticmethod
    def buat_kunci_dm(user_a_id, user_b_id) -> str:
        """Kunci DM yang sama untuk arah mana pun."""
        return ":".join(sorted([str(user_a_id), str(user_b_id)]))


class Langganan(BaseModel):
    """Hubungan satu orang dengan satu ruang: sudah dibaca sampai mana, dan maunya
    diberi tahu seperti apa.

    Inilah bagian yang membuat kanal mungkin, dan yang paling mudah salah
    dirancang. Menandai terbaca PER PESAN seperti yang dipakai DM sekarang berarti
    satu baris untuk tiap anggota dikali tiap pesan. Untuk kanal berisi 20 orang,
    seribu pesan menjadi dua puluh ribu baris yang tidak menyimpan satu fakta pun
    yang tidak bisa diturunkan dari satu cap waktu.

    Jadi di sini yang disimpan cuma `dibaca_sampai`. Jumlah belum dibaca adalah
    hitungan pesan yang lebih baru dari cap itu dan bukan kiriman sendiri.

    `PesanLangsung.dibaca_pada` TETAP ADA dan tidak digantikan, tapi maknanya kini
    sempit: tanda terima untuk DM, supaya pengirim tahu pesannya sudah dibaca.
    Kanal sengaja tidak punya itu. Tidak ada yang mau membaca "dibaca oleh 14 dari
    20 orang", dan biayanya persis ledakan baris yang baru saja dihindari.
    """

    class Notifikasi(models.TextChoices):
        SEMUA = "semua", "Semua pesan"
        MENTION = "mention", "Hanya kalau disebut"
        MATI = "mati", "Bisukan"

    ruang = models.ForeignKey("db.Ruang", related_name="langganan", on_delete=models.CASCADE)
    user = models.ForeignKey("db.User", related_name="langganan_ruang", on_delete=models.CASCADE)
    dibaca_sampai = models.DateTimeField(null=True, blank=True)
    notifikasi = models.CharField(max_length=10, choices=Notifikasi.choices, default=Notifikasi.SEMUA)
    disematkan = models.BooleanField(default=False)

    class Meta:
        # `deleted_at` ikut kunci supaya orang yang keluar kanal lalu bergabung
        # lagi tidak menabrak baris lamanya yang sudah dihapus lunak.
        unique_together = ["ruang", "user", "deleted_at"]
        verbose_name = "Langganan Ruang"
        verbose_name_plural = "Langganan Ruang"
        db_table = "chat_subscriptions"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "ruang"], name="langganan_user_ruang_idx"),
        ]

    def __str__(self):
        return f"{self.user_id} @ {self.ruang_id}"


class PesanLangsung(BaseModel):
    """Satu pesan di dalam satu Ruang.

    Versi pertama model ini sengaja tidak punya tabel Percakapan, karena untuk
    obrolan berdua percakapan bisa diturunkan sepenuhnya dari pasangan
    pengirim-penerima. Catatan lamanya juga sudah memperingatkan bahwa model itu
    tidak akan sanggup menampung kanal. Peringatan itu terbukti, dan sejak
    migrasi 0136 tempatnya adalah `Ruang`.

    Nama kelasnya sengaja TIDAK diganti jadi `Pesan`. Mengganti nama model
    berarti mengganti nama tabel, dan `direct_messages` sudah dirujuk oleh
    migrasi lama, tugas email, penjaga lampiran, serta indeks yang ditulis
    tangan. Nama yang sedikit meleset jauh lebih murah daripada migrasi
    penggantian nama pada tabel yang sedang dipakai orang.

    `penerima` dan `dibaca_pada` hanya berarti untuk DM. Untuk kanal keduanya
    kosong, dan yang menggantikannya adalah `Langganan.dibaca_sampai`.
    """

    workspace = models.ForeignKey("db.Workspace", related_name="pesan_langsung", on_delete=models.CASCADE)
    # Tempat pesan ini tinggal. Boleh kosong HANYA selama migrasi 0136 berjalan;
    # sesudah backfill setiap baris punya ruang, dan penulis baru wajib mengisinya.
    ruang = models.ForeignKey(
        "db.Ruang", related_name="pesan", on_delete=models.CASCADE, null=True, blank=True
    )
    # Kosong = dikirim sistem ("Paradise"): catatan rilis dan kartu kabar. Bukan
    # akun bot sungguhan, karena akun bot ikut muncul di daftar anggota, dan
    # penyaringan akun bot di setiap daftar adalah tempat yang mudah terlewat.
    pengirim = models.ForeignKey(
        "db.User", related_name="pesan_terkirim", on_delete=models.CASCADE, null=True, blank=True
    )
    # Kosong untuk pesan kanal: penerimanya adalah seluruh anggota ruang, dan itu
    # sudah tercatat di Langganan. Tetap diisi untuk DM karena tanda terima,
    # email pemberitahuan, dan penjaga lampiran semuanya bersandar padanya.
    penerima = models.ForeignKey(
        "db.User", related_name="pesan_diterima", on_delete=models.CASCADE, null=True, blank=True
    )
    isi = models.TextField()
    # Kartu: `jenis` memilih cara merender, `muatan` membawa datanya. Lihat
    # `JenisPesan`. Kartu tidak bisa disunting lewat endpoint pesan.
    jenis = models.CharField(max_length=20, choices=JenisPesan.choices, default=JenisPesan.TEKS)
    muatan = models.JSONField(default=dict, blank=True)
    # Tanda terima, dan HANYA berarti untuk DM. Lihat alasannya di Langganan.
    dibaca_pada = models.DateTimeField(null=True, blank=True)
    # Diisi saat pesan ini sudah pernah masuk email pemberitahuan. Ditaruh di
    # pesan, bukan di penerima, karena inilah yang membuat email tidak pernah
    # mengulang isi yang sama: penanda per-orang akan kehilangan jejak pesan
    # mana yang sudah diberitahukan begitu ada pesan baru menyusul.
    dinotifikasi_pada = models.DateTimeField(null=True, blank=True)
    # Diisi saat pesan disunting. Waktunya disimpan, bukan sekadar bendera:
    # penerima berhak tahu bahwa yang dibacanya bukan lagi kalimat yang
    # dikirim semula, dan kapan berubahnya.
    disunting_pada = models.DateTimeField(null=True, blank=True)
    # Pesan yang sedang dibalas. SET_NULL, bukan CASCADE: menghapus pesan yang
    # dikutip tidak boleh ikut menghapus balasannya, karena balasan itu milik
    # orang lain dan sering justru bagian yang penting.
    balasan_ke = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="balasan"
    )
    # Sematan (migrasi 0167). Dua kolom di pesan, bukan tabel sendiri: sematan
    # berlaku untuk SELURUH ruang, bukan per orang, jadi satu pesan paling banyak
    # punya satu sematan. Tabel terpisah cuma menambah join tanpa menyimpan fakta
    # yang tidak muat di sini. `disematkan_oleh` SET_NULL supaya akun yang dihapus
    # permanen tidak ikut melepas sematan yang masih dipakai orang lain.
    disematkan_pada = models.DateTimeField(null=True, blank=True)
    disematkan_oleh = models.ForeignKey(
        "db.User", related_name="pesan_disematkan", on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = "Pesan Langsung"
        verbose_name_plural = "Pesan Langsung"
        db_table = "direct_messages"
        ordering = ("-created_at",)
        # Nama indeks ditulis eksplisit. Kalau dikosongkan Django menurunkannya
        # dari hash, dan migrasi yang ditulis tangan akan selalu meleset satu
        # RenameIndex dari keadaan model. Itu persis yang terjadi di 0131.
        indexes = [
            models.Index(fields=["workspace", "pengirim", "penerima"], name="dm_ws_pengirim_penerima_idx"),
            models.Index(fields=["penerima", "dibaca_pada"], name="dm_penerima_dibaca_idx"),
            # Memuat isi satu ruang urut waktu, dan menghitung belum dibaca
            # sesudah `dibaca_sampai`. Keduanya dilayani indeks yang sama.
            models.Index(fields=["ruang", "created_at"], name="dm_ruang_created_idx"),
            # Daftar sematan satu ruang. Parsial: hampir semua pesan tidak
            # disematkan, jadi indeks penuh cuma memboroskan tulis tiap pesan.
            models.Index(
                fields=["ruang", "disematkan_pada"],
                name="dm_ruang_disematkan_idx",
                condition=models.Q(disematkan_pada__isnull=False),
            ),
        ]

    def save(self, *args, **kwargs):
        """Tolak pesan baru yang tidak punya ruang.

        Kolomnya nullable karena migrasi 0136 harus bisa menambahkannya ke tabel
        yang sudah berisi, bukan karena pesan tanpa ruang itu sah. Pesan yatim
        tidak akan muncul di percakapan mana pun, dan tidak menimbulkan error di
        mana pun: percakapannya sekadar tampak kosong bagi pemiliknya. Itu bentuk
        kegagalan yang paling mahal ditemukan, jadi ditutup di sini, di satu
        tempat yang dilewati semua penulis.
        """
        if self._state.adding and self.ruang_id is None:
            raise ValueError("PesanLangsung wajib punya ruang. Pakai _ruang_dm() atau ruang kanal.")
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pengirim_id} -> {self.penerima_id}"


class ReaksiPesan(BaseModel):
    """Satu reaksi emoji dari satu orang pada satu pesan.

    Tabel sendiri, bukan kolom JSON di pesan: reaksi ditambah dan dibuang oleh
    orang yang BERBEDA dari pemilik pesan, dan dua orang bisa bereaksi pada
    detik yang sama. Kolom JSON membuat keduanya saling menimpa, dan yang kalah
    hilang tanpa jejak.
    """

    pesan = models.ForeignKey("db.PesanLangsung", related_name="reaksi", on_delete=models.CASCADE)
    user = models.ForeignKey("db.User", related_name="reaksi_pesan", on_delete=models.CASCADE)
    # Disimpan sebagai karakter emoji, bukan kode desimal: yang membacanya cuma
    # UI, dan menyimpan kode berarti tiap pembaca harus tahu cara mengubahnya
    # kembali.
    emoji = models.CharField(max_length=32)

    class Meta:
        # Satu orang, satu emoji, satu pesan. Tanpa kunci ini, klik ganda
        # membuat reaksi kembar yang tidak bisa dibatalkan dari UI.
        unique_together = ["pesan", "user", "emoji", "deleted_at"]
        verbose_name = "Reaksi Pesan"
        verbose_name_plural = "Reaksi Pesan"
        db_table = "direct_message_reactions"
        ordering = ("created_at",)
        indexes = [models.Index(fields=["pesan"], name="dm_reaksi_pesan_idx")]

    def __str__(self):
        return f"{self.user_id} {self.emoji} {self.pesan_id}"
