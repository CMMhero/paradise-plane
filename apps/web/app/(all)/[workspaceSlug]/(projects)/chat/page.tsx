/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { observer } from "mobx-react";
import { useParams, useSearchParams } from "react-router";
import useSWR, { mutate } from "swr";
import {
  ChevronLeft,
  ChevronUp,
  Paperclip,
  Settings2,
  Upload,
  Pencil,
  Search,
  Send,
  SmilePlus,
  X,
  Hash,
  Lock,
  Plus,
  Compass,
  Phone,
  Video,
} from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { stringToEmoji } from "@plane/propel/emoji-icon-picker";
import { EmojiReactionPicker } from "@plane/propel/emoji-reaction";
import { EmptyStateCompact } from "@plane/propel/empty-state";
import { Button } from "@plane/propel/button";
import { IconButton } from "@plane/propel/icon-button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Avatar, Input } from "@plane/ui";
import { cn, getFileURL, getNumberCount, renderFormattedDate, renderFormattedTime } from "@plane/utils";
// components
import { CountChip } from "@/components/common/count-chip";
import { PageHead } from "@/components/core/page-title";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useKonfirmasi } from "@/hooks/use-konfirmasi";
import { useParadiseLimits } from "@/hooks/use-paradise-limits";
import { SaklarSuara } from "@/components/notifikasi/saklar-suara";
import { useSuaraNotifikasi } from "@/hooks/use-suara-notifikasi";
import { useUser } from "@/hooks/store/user";
import { useInstance } from "@/hooks/store/use-instance";
// services
import {
  ChatService,
  KUNCI_BELUM_DIBACA,
  type THasilCari,
  type TPercakapan,
  type TPesan,
} from "@/services/chat.service";
// local imports
import { susunBaris } from "./baris";
import { useObrolanLangsung } from "./langsung";
import { usePanggilanWorkspace } from "./penyedia-panggilan";
import { Gelembung } from "./gelembung";
import { KutipanBalasan } from "./kutipan-balasan";
import { DaftarSebut, useSebutan } from "./pemilih-sebut";
import type { TCalonSebut } from "./pemilih-sebut";
import { DialogBuatKanal, DialogJelajahKanal } from "./kanal-dialog";
import { DialogSetelanKanal } from "./kanal-setelan";
import { ukuranTerbaca } from "./lampiran";
import { berkasDariTempel, seretBerkas, useUnggahLampiran } from "./unggah-lampiran";
import { DenganKehadiran, StatusKehadiranTeks, TitikKehadiran } from "@/components/chat/titik-kehadiran";
import { MemberProfileTrigger } from "@/components/member-profile";
import { usePetaKehadiran } from "@/hooks/use-kehadiran";
import { urutkanMenurutKehadiran } from "@/lib/kehadiran";

const chatService = new ChatService();

// Selang tarik-ulang. Percakapan yang sedang dibuka diperiksa lebih sering
// daripada daftarnya, karena di situlah orang menunggu balasan.
// ponytail: angka tetap, bukan backoff. Naikkan kalau server terasa berat.
const SELANG_PESAN = 5000;
// Dipakai saat soket real-time hidup. Bukan dimatikan, cuma dijarangkan:
// satu penarikan tiap setengah menit cukup untuk menambal siaran yang
// terlewat saat soket sempat putus dan menyambung lagi.
const SELANG_PESAN_CADANGAN = 30000;
const SELANG_DAFTAR = 15000;
const TINGGI_TULIS_MAKS = 160;
/** Berapa lama sesudah aksi di tab ini gema soketnya dianggap milik aksi itu. */
const JENDELA_GEMA_MS = 3000;
/** Dipanggil penangan aksi pesan, di luar render; lihat `onPerubahan`. */
const tandaiAksiLokal = (ref: { current: number }): void => {
  ref.current = Date.now();
};

/** Id elemen DOM satu baris pesan, sasaran lompatan dari kutipan balasan. */
const idElemenPesan = (pesanId: string) => `pesan-${pesanId}`;
/** Paling banyak halaman riwayat yang dimuat untuk mencari pesan asli kutipan. */
const BATAS_HALAMAN_LOMPAT = 10;
const LAMA_SOROT_MS = 1600;

type TBarisDaftar = { id: string; terakhir: TPercakapan | undefined };

/** Jam untuk pesan hari ini, tanggal untuk yang lebih lama.
 *
 * Bukan calculateTimeAgo: hasilnya berbahasa Inggris di UI berbahasa Indonesia,
 * dan "less than a minute ago" cukup panjang untuk mendesak nama orang sampai
 * terpotong jadi "Um...". */
const waktuRingkas = (waktu: string): string => {
  const tanggal = new Date(waktu);
  const hariIni = new Date().toDateString() === tanggal.toDateString();
  return (hariIni ? renderFormattedTime(waktu) : renderFormattedDate(waktu, "dd MMM")) ?? "";
};

function ChatPage() {
  const { workspaceSlug } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const dengan = searchParams.get("dengan");
  // Kanal memakai `?ruang=`, DM tetap `?dengan=`. Dua parameter, bukan satu,
  // supaya tautan percakapan yang sudah beredar tidak berubah artinya.
  const ruangParam = searchParams.get("ruang");
  const adalahKanal = Boolean(ruangParam);
  // store hooks
  const { data: currentUser } = useUser();
  const petaKehadiran = usePetaKehadiran();
  const { config: instanceConfig } = useInstance();
  const batasHapusJam = instanceConfig?.paradise_chat_delete_window_hours;
  const {
    workspace: { workspaceMemberIds, getWorkspaceMemberDetails },
  } = useMember();
  const { t, currentLocale } = useTranslation();
  // states
  const [cari, setCari] = useState("");
  // Kotak cari dipakai untuk dua hal: menyaring nama (langsung, tanpa server)
  // dan mencari isi pesan (Enter atau tombol "Isi"). Dipisah begitu supaya
  // mengetik nama tidak memanggil server tiap huruf.
  const [hasilCari, setHasilCari] = useState<THasilCari[] | null>(null);
  const [mencari, setMencari] = useState(false);
  const [draf, setDraf] = useState("");
  const [mengirim, setMengirim] = useState(false);
  const [emojiTerbuka, setEmojiTerbuka] = useState(false);
  const [setelanTerbuka, setSetelanTerbuka] = useState(false);
  /** Berkas sedang diseret di atas percakapan: tampilkan area lepas. */
  const [diseret, setDiseret] = useState(false);
  const [membalas, setMembalas] = useState<TPesan | null>(null);
  const [menyunting, setMenyunting] = useState<TPesan | null>(null);
  const [lama, setLama] = useState<TPesan[]>([]);
  const [memuatLama, setMemuatLama] = useState(false);
  const [habis, setHabis] = useState(false);
  /** Pesan asli yang sedang dicari sesudah kutipan balasan diklik. */
  const [lompatKe, setLompatKe] = useState<string | null>(null);
  /** Baris yang baru dilompati, disorot sebentar supaya mata langsung menemukannya. */
  const [disorot, setDisorot] = useState<string | null>(null);
  const sisaHalamanLompat = useRef(0);
  const [buatTerbuka, setBuatTerbuka] = useState(false);
  const [jelajah, setJelajah] = useState(false);
  const berkasRef = useRef<HTMLInputElement>(null);
  const akhirRef = useRef<HTMLDivElement>(null);
  const { bunyikan } = useSuaraNotifikasi();
  const pesanTerakhirRef = useRef<string | null>(null);
  /** Waktu aksi pesan terakhir dari tab ini; lihat `onPerubahan`. */
  const aksiLokalRef = useRef(0);
  const { minta, dialog: dialogKonfirmasi } = useKonfirmasi();
  const tulisRef = useRef<HTMLTextAreaElement>(null);
  // Panggilan hidup di lapisan workspace (penyedia-panggilan.tsx) supaya
  // bertahan saat pindah halaman; halaman ini cuma memakainya.
  const panggilan = usePanggilanWorkspace();

  const slug = workspaceSlug?.toString();

  const { data: percakapan, mutate: muatPercakapan } = useSWR(
    slug ? `CHAT_PERCAKAPAN_${slug}` : null,
    slug ? () => chatService.getPercakapan(slug) : null,
    { refreshInterval: SELANG_DAFTAR }
  );

  const { data: daftarKanal, mutate: muatKanal } = useSWR(
    slug ? `CHAT_KANAL_${slug}` : null,
    slug ? () => chatService.getDaftarRuang(slug) : null,
    { refreshInterval: SELANG_DAFTAR }
  );

  // Ruang yang sedang dibuka. Untuk kanal langsung dari URL; untuk DM dicari
  // dari daftar percakapan. DM yang belum pernah berisi pesan belum punya
  // ruang, dan itu wajar: soketnya menyusul begitu pesan pertama terkirim.
  const ruangSaatIni = ruangParam ?? (percakapan ?? []).find((p) => p.lawan_bicara === dengan)?.id ?? null;
  /** Ada percakapan yang sedang dibuka.
   *
   * Di layar sempit ini yang menentukan panel mana yang tampil: daftar ATAU
   * percakapan, tidak pernah keduanya. Sebelumnya keduanya dipaksa berdampingan,
   * dan karena daftarnya dipatok `w-80 shrink-0` alias 320px yang menolak
   * menyusut, di HP 375px sisa untuk percakapan tinggal 55px. Tangkapan layar
   * HP dari user 19 Agt memperlihatkannya: potongan teks terjepit di pinggir
   * kanan layar itu adalah seluruh kolom percakapan. */
  const adaPercakapanTerbuka = Boolean(dengan || ruangParam);

  const kunciIsi = slug && (ruangParam || dengan) ? `CHAT_ISI_${slug}_${ruangParam ?? dengan}` : null;

  // Sengaja memakai `mutate` global, bukan handle dari useSWR di bawah: hook ini
  // harus berdiri SEBELUM SWR isi percakapan supaya `tersambung` bisa dipakai
  // menentukan seberapa sering penarikan cadangan berjalan.
  const { tersambung, kirimSinyal } = useObrolanLangsung({
    slug,
    ruangId: ruangSaatIni,
    onPerubahan: (kejadian) => {
      // Gema aksi tab ini sendiri: penangan aksinya sudah menarik ulang, jadi
      // menarik lagi di sini menggandakan tiap request (dan tiap tarik pesan
      // juga menandai dibaca di server). Dibatasi jendela waktu, BUKAN cuma
      // `oleh === saya`, supaya aksi dari perangkat lain milik orang yang sama
      // tetap muncul seketika di tab ini.
      const gemaSendiri =
        !!kejadian.oleh && kejadian.oleh === currentUser?.id && Date.now() - aksiLokalRef.current < JENDELA_GEMA_MS;
      if (gemaSendiri) return;
      if (kunciIsi) void mutate(kunciIsi);
      void mutate(`CHAT_PERCAKAPAN_${slug}`);
      void mutate(KUNCI_BELUM_DIBACA);
      // Nama/topik/anggota kanal berubah (chat_kelola.py menyiarkan "ruang"/"anggota").
      if (kejadian.tipe === "ruang" || kejadian.tipe === "anggota") {
        void mutate(`CHAT_KANAL_${slug}`);
        if (ruangSaatIni) {
          void mutate(`CHAT_DETAIL_RUANG_${ruangSaatIni}`);
          void mutate(`CHAT_ANGGOTA_RUANG_${ruangSaatIni}`);
        }
      }
    },
    // Soket ruang tinggal membawa ajakan konferensi kanal. Sinyal DM pindah ke
    // soket kehadiran, dan `pergi` sengaja TIDAK lagi menutup panggilan: lawan
    // yang sekadar pindah percakapan dulu ikut memutus panggilan yang sedang jalan.
    onSinyal: (_dari, muatan) => panggilan.terimaSinyalRuang(ruangSaatIni, muatan),
  });

  // Satu SWR untuk dua jenis percakapan. Kuncinya dibedakan supaya berpindah
  // dari kanal ke DM tidak menampilkan sisa pesan sebelumnya sekejap.
  const { data: pesan, mutate: muatPesan } = useSWR(
    slug && (ruangParam || dengan) ? `CHAT_ISI_${slug}_${ruangParam ?? dengan}` : null,
    slug && ruangParam
      ? () => chatService.getPesanRuang(slug, ruangParam)
      : slug && dengan
        ? () => chatService.getPesan(slug, dengan)
        : null,
    // Soket hidup = pesan sudah datang seketika, jadi penarikan tinggal jadi
    // jaring pengaman. TIDAK dimatikan sama sekali: kalau soketnya putus tanpa
    // sempat menyambung lagi, ini satu-satunya yang menyelamatkan percakapan.
    { refreshInterval: tersambung ? SELANG_PESAN_CADANGAN : SELANG_PESAN }
  );

  // Sebutan @: hanya orang di percakapan ini. Kanal memakai kunci SWR yang
  // sama dengan panel anggota (kanal-setelan), jadi tidak menambah permintaan.
  const { data: anggotaRuang } = useSWR(
    slug && ruangParam ? `CHAT_ANGGOTA_RUANG_${ruangParam}` : null,
    slug && ruangParam ? () => chatService.getAnggotaRuang(slug, ruangParam) : null
  );
  const calonSebut: TCalonSebut[] = useMemo(() => {
    const ids = ruangParam ? (anggotaRuang ?? []) : dengan ? [dengan] : [];
    return ids
      .filter((id) => id !== currentUser?.id)
      .flatMap((id) => {
        const anggota = getWorkspaceMemberDetails(id)?.member;
        return anggota?.display_name ? [{ id, nama: anggota.display_name, avatar: anggota.avatar_url }] : [];
      });
  }, [ruangParam, anggotaRuang, dengan, currentUser?.id, getWorkspaceMemberDetails]);
  const sebutan = useSebutan({ calon: calonSebut, draf, setDraf, tulisRef });

  // Ganti lawan bicara = buang riwayat lama yang sudah dimuat, kalau tidak
  // pesan orang sebelumnya ikut menempel di atas percakapan berikutnya.
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- reset per-conversation state when the conversation changes
    setLama([]);
    setHabis(false);
    setMembalas(null);
    setMenyunting(null);
    setLompatKe(null);
    // oxlint-disable-next-line react/exhaustive-effect-dependencies -- deps are the reset triggers, not read in the body
  }, [dengan, ruangParam]);

  // Berbunyi saat pesan MASUK baru tiba di percakapan yang sedang terbuka.
  // Lencana sidebar tidak bisa mengurus ini: membuka percakapan menandainya
  // terbaca, jadi angkanya tidak pernah naik dan bunyinya tidak pernah keluar.
  //
  // Penanda dikunci PER PERCAKAPAN. Dulu cuma id pesan terakhir, jadi berpindah
  // ke percakapan yang sudah ada di cache SWR (tanpa jeda `undefined`) terbaca
  // sebagai "pesan baru": id-nya beda dan pengirimnya bukan saya. Kanal sistem
  // paling sering kena karena pengirimnya selalu kosong, jadi tiap kali dibuka
  // berbunyi. Pembanding sekarang hanya pesan di percakapan yang SAMA.
  useEffect(() => {
    const daftar = pesan ?? [];
    const terakhir = daftar[daftar.length - 1];
    const sebelumnya = pesanTerakhirRef.current;
    if (!terakhir || !kunciIsi) {
      pesanTerakhirRef.current = null;
      return;
    }
    const penanda = `${kunciIsi}|${terakhir.id}`;
    const percakapanSama = sebelumnya?.startsWith(`${kunciIsi}|`) ?? false;
    if (percakapanSama && sebelumnya !== penanda && terakhir.pengirim !== currentUser?.id) bunyikan("pesan");
    pesanTerakhirRef.current = penanda;
  }, [pesan, kunciIsi, currentUser?.id, bunyikan]);

  // Selalu tampilkan pesan terbaru saat percakapan bertambah atau berganti.
  useEffect(() => {
    akhirRef.current?.scrollIntoView({ block: "end" });
    // Memuat percakapan berarti menandainya terbaca di server, jadi lencana di
    // sidebar sudah basi sejak detik itu. Disegarkan di sini supaya angkanya
    // turun seketika, bukan pada tarikan 30 detik berikutnya.
    void mutate(KUNCI_BELUM_DIBACA);
    // oxlint-disable-next-line react/exhaustive-effect-dependencies -- dengan/ruangParam re-scroll on conversation switch
  }, [pesan?.length, dengan, ruangParam]);

  const daftar: TBarisDaftar[] = useMemo(() => {
    // Hanya baris DM yang masuk daftar orang. Sejak kanal ikut dikirim endpoint
    // yang sama, `lawan_bicara` bisa kosong, dan kanal yang menyelinap ke sini
    // akan tampil sebagai "Anggota" tanpa nama.
    const barisDM = (percakapan ?? []).filter((baris): baris is TPercakapan & { lawan_bicara: string } =>
      Boolean(baris.lawan_bicara)
    );
    const peta = new Map(barisDM.map((baris) => [baris.lawan_bicara, baris]));
    const kunciCari = cari.trim().toLowerCase();
    const kandidat = (workspaceMemberIds ?? []).filter((id) => {
      // Diri sendiri disaring di sini lalu disisipkan paling atas di bawah,
      // sebagai ruang catatan pribadi.
      if (id === currentUser?.id) return false;
      if (!kunciCari) return true;
      const nama = getWorkspaceMemberDetails(id)?.member?.display_name ?? "";
      return nama.toLowerCase().includes(kunciCari);
    });
    // Tidak ada pengurutan di sini sama sekali. Server sudah mengirim percakapan
    // terbaru lebih dulu, dan store sudah mengurutkan anggota menurut nama, jadi
    // menyambung dua daftar yang masing-masing sudah urut sudah cukup.
    const cocok = new Set(kandidat);
    const namaDari = (id: string) => getWorkspaceMemberDetails(id)?.member?.display_name ?? "";
    // Online dulu, lalu away, lalu offline; dalam satu kelompok menurut nama.
    const urut = urutkanMenurutKehadiran(
      [
        ...barisDM.map((baris) => baris.lawan_bicara).filter((id) => cocok.has(id)),
        ...kandidat.filter((id) => !peta.has(id)),
      ],
      petaKehadiran,
      namaDari
    );
    // Catatan untuk diri sendiri selalu paling atas, seperti "Saved messages":
    // ia tempat yang dicari dengan sengaja, bukan percakapan yang tenggelam.
    const namaSaya = (currentUser?.display_name ?? "").toLowerCase();
    const diriSendiri = currentUser?.id && (!kunciCari || namaSaya.includes(kunciCari)) ? [currentUser.id] : [];
    return [...diriSendiri, ...urut].map((id) => ({ id, terakhir: peta.get(id) }));
    // oxlint-disable-next-line react/preserve-manual-memoization -- narrower deps are intentional to avoid recomputing on unrelated user fields
  }, [
    percakapan,
    workspaceMemberIds,
    currentUser?.id,
    currentUser?.display_name,
    cari,
    getWorkspaceMemberDetails,
    petaKehadiran,
  ]);

  const semuaPesan = useMemo(() => [...lama, ...(pesan ?? [])], [lama, pesan]);
  const barisPesan = useMemo(
    // oxlint-disable-next-line react/purity -- current date is needed to group messages by day
    () => susunBaris(semuaPesan, currentUser?.id, new Date(), currentLocale),
    [semuaPesan, currentUser?.id, currentLocale]
  );

  const lawanBicara = dengan ? getWorkspaceMemberDetails(dengan)?.member : undefined;

  const aturTinggiTulis = () => {
    const el = tulisRef.current;
    if (!el) return;
    // Tinggi dinolkan dulu; tanpa itu scrollHeight ikut tinggi lama dan kotaknya
    // tumbuh terus tapi tidak pernah menyusut lagi.
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, TINGGI_TULIS_MAKS)}px`;
  };

  const batasParadise = useParadiseLimits();
  // Tombol klip, tempel, dan seret semuanya lewat `tambahLampiran`: batas
  // jumlah/ukuran dan kemajuan unggah ada di unggah-lampiran.ts.
  const {
    siap: lampiran,
    naik: sedangNaik,
    mengunggah,
    tambah: tambahLampiran,
    buang: buangLampiran,
    kosongkan: kosongkanLampiran,
    maksJumlah: maksLampiran,
  } = useUnggahLampiran({
    slug,
    onTolak: (tolak, maks) => {
      const terlaluBesar = tolak.filter((x) => x.jenis === "terlalu-besar");
      setToast({
        type: TOAST_TYPE.ERROR,
        title:
          terlaluBesar.length > 0
            ? t("chatux_kelola_ui.file_too_large", { name: terlaluBesar[0].nama, size: Math.round(maks / 1024 / 1024) })
            : t("chatux_kelola_ui.too_many_files", { count: maksLampiran }),
      });
    },
    onGagal: (gagal, total, pesanServer) =>
      setToast({
        type: TOAST_TYPE.ERROR,
        title: gagal === total ? t("chat_ui.upload_failed_all") : t("chat_ui.upload_failed_some", { count: gagal }),
        message: pesanServer ?? t("chat_ui.upload_failed_hint"),
      }),
  });

  const unggah = async (berkas: FileList | File[] | null) => {
    if (berkasRef.current) berkasRef.current.value = "";
    await tambahLampiran(berkas);
  };

  /** Lepas berkas di area percakapan. Hanya aktif saat ada percakapan terbuka. */
  const aturSeret = {
    onDragEnter: (e: React.DragEvent) => {
      if (!seretBerkas(e.dataTransfer)) return;
      e.preventDefault();
      setDiseret(true);
    },
    onDragOver: (e: React.DragEvent) => {
      if (!seretBerkas(e.dataTransfer)) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = "copy";
    },
    onDragLeave: (e: React.DragEvent) => {
      // Masuk ke anak elemen juga memicu dragleave; hanya keluar sungguhan yang dihitung.
      if (e.currentTarget.contains(e.relatedTarget as Node | null)) return;
      setDiseret(false);
    },
    onDrop: (e: React.DragEvent) => {
      if (!seretBerkas(e.dataTransfer)) return;
      e.preventDefault();
      setDiseret(false);
      void unggah(e.dataTransfer.files);
    },
  };

  const cariIsiPesan = async () => {
    const q = cari.trim();
    if (!slug || q.length < 3) {
      setToast({ type: TOAST_TYPE.ERROR, title: t("chat_ui.search_min_chars") });
      return;
    }
    setMencari(true);
    try {
      setHasilCari(await chatService.cariPesan(slug, q));
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("chat_ui.search_failed"),
        message: (galat as { error?: string })?.error ?? t("chat_ui.try_again_shortly"),
      });
    } finally {
      setMencari(false);
    }
  };

  const muatLama = async () => {
    const tertua = semuaPesan[0];
    if (!slug || (!dengan && !ruangParam) || !tertua || memuatLama) return;
    setMemuatLama(true);
    try {
      const hasil = ruangParam
        ? await chatService.getPesanLamaRuang(slug, ruangParam, tertua.created_at)
        : await chatService.getPesanLama(slug, dengan as string, tertua.created_at);
      if (hasil.length === 0) setHabis(true);
      else setLama((sebelumnya) => [...hasil, ...sebelumnya]);
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: t("chat_ui.load_older_failed") });
    } finally {
      setMemuatLama(false);
    }
  };

  const lompatKePesan = (pesanId: string) => {
    sisaHalamanLompat.current = BATAS_HALAMAN_LOMPAT;
    setLompatKe(pesanId);
  };

  // Cari pesan asli kutipan. Kalau belum termuat, tarik riwayat lama satu
  // halaman per putaran sampai ketemu, server bilang habis, atau batas halaman
  // tercapai. Efek ini jalan lagi tiap riwayat bertambah atau pemuatan selesai,
  // jadi pemuatan yang gagal juga ikut mengurangi jatah, tidak berulang selamanya.
  // Efek ini memang menyinkronkan dengan DOM (elemen sasaran baru ada sesudah
  // render), dan pemicunya riwayat yang termuat, bukan muatLama/t yang dibuat
  // ulang tiap render.
  /* oxlint-disable react/set-state-in-effect, react/exhaustive-effect-dependencies, react-hooks/exhaustive-deps */
  useEffect(() => {
    if (!lompatKe) return;
    const el = document.getElementById(idElemenPesan(lompatKe));
    if (el) {
      el.scrollIntoView({ block: "center", behavior: "smooth" });
      setDisorot(lompatKe);
      setLompatKe(null);
      return;
    }
    if (memuatLama) return;
    if (habis || sisaHalamanLompat.current <= 0) {
      setToast({ type: TOAST_TYPE.INFO, title: t("chat_ui.original_not_found") });
      setLompatKe(null);
      return;
    }
    sisaHalamanLompat.current -= 1;
    void muatLama();
  }, [lompatKe, semuaPesan.length, memuatLama, habis]);
  /* oxlint-enable react/set-state-in-effect, react/exhaustive-effect-dependencies, react-hooks/exhaustive-deps */

  useEffect(() => {
    if (!disorot) return;
    const jeda = setTimeout(() => setDisorot(null), LAMA_SOROT_MS);
    return () => clearTimeout(jeda);
  }, [disorot]);

  const simpanSuntingan = async () => {
    const isi = draf.trim();
    if (!slug || !menyunting || !isi) return;
    tandaiAksiLokal(aksiLokalRef);
    setMengirim(true);
    try {
      await chatService.suntingPesan(slug, menyunting.id, isi);
      setMenyunting(null);
      setDraf("");
      await Promise.all([muatPesan(), muatPercakapan()]);
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("chat_ui.edit_failed"),
        message: (galat as { error?: string })?.error ?? t("chat_ui.try_again_shortly"),
      });
    } finally {
      setMengirim(false);
    }
  };

  const hapus = async (p: TPesan) => {
    if (!slug) return;
    tandaiAksiLokal(aksiLokalRef);
    try {
      await chatService.hapusPesan(slug, p.id);
      // Riwayat lama disimpan terpisah dari SWR, jadi ikut dijadikan batu nisan
      // (pesan tetap di tempatnya, isinya diganti "Pesan dihapus").
      setLama((sebelumnya) =>
        sebelumnya.map((x) =>
          x.id === p.id ? { ...x, dihapus: true, isi: "", lampiran: [], reaksi: [], balasan_ke: null } : x
        )
      );
      await Promise.all([muatPesan(), muatPercakapan()]);
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("chat_ui.delete_failed"),
        message: (galat as { error?: string })?.error ?? t("chat_ui.try_again_shortly"),
      });
    }
  };

  const reaksi = async (p: TPesan, emoji: string) => {
    if (!slug) return;
    tandaiAksiLokal(aksiLokalRef);
    try {
      await chatService.toggleReaksi(slug, p.id, emoji);
      await muatPesan();
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: t("chat_ui.react_failed") });
    }
  };

  const kirim = async () => {
    const isi = draf.trim();
    // Boleh mengirim tanpa teks asal ada lampiran.
    if ((!isi && lampiran.length === 0) || !slug || (!dengan && !ruangParam) || mengirim || mengunggah) return;
    setMengirim(true);
    tandaiAksiLokal(aksiLokalRef);
    try {
      const berkas = lampiran.map((l) => l.id);
      const sebut = sebutan.idUntukKirim(isi);
      if (ruangParam) await chatService.kirimPesanRuang(slug, ruangParam, isi, berkas, membalas?.id, sebut);
      else await chatService.kirimPesan(slug, dengan as string, isi, berkas, membalas?.id, sebut);
      setDraf("");
      sebutan.reset();
      kosongkanLampiran();
      setMembalas(null);
      if (tulisRef.current) tulisRef.current.style.height = "auto";
      await Promise.all([muatPesan(), muatPercakapan()]);
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("chat_ui.send_failed"),
        message: (galat as { error?: string })?.error ?? t("chat_ui.try_again_shortly"),
      });
    } finally {
      setMengirim(false);
    }
  };

  const kanalAktif = (daftarKanal ?? []).find((r) => r.id === ruangParam);
  /** Konferensi di kanal yang sedang dibuka. Tidak berlaku di DM. */
  const mulaiKonferensi = (video: boolean) => {
    if (!ruangParam) return;
    void panggilan.mulaiKonferensi({
      ruang: ruangParam,
      nama: kanalAktif?.nama ?? t("chat_ui.channel"),
      video,
      kirimSinyalRuang: kirimSinyal,
    });
  };
  const telepon = (video: boolean) => {
    if (dengan) void panggilan.panggil(dengan, ruangSaatIni, video);
  };
  // Ajakan konferensi hanya berlaku untuk kanal tempat ia diterima; berpindah
  // percakapan atau meninggalkan halaman ini membuangnya.
  const { lupakanKonferensi } = panggilan;
  useEffect(() => {
    if (!ruangSaatIni) return undefined;
    return lupakanKonferensi;
  }, [ruangSaatIni, lupakanKonferensi]);
  // Kanal sistem yang hanya dibaca (Announcements, Changelog, Paradise) tidak
  // bisa ditelepon; kanal divisi/departemen bisa, karena isinya orang sungguhan.
  const kanalTanpaPanggilan = !!kanalAktif?.sistem && !/^(divisi|departemen):/.test(kanalAktif.kunci_sistem ?? "");
  const kanalDiikuti = (daftarKanal ?? []).filter((r) => r.ikut);
  const kanalBelumDiikuti = (daftarKanal ?? []).filter((r) => !r.ikut);

  const buatKanal = async (nama: string, privat: boolean): Promise<boolean> => {
    if (!slug) return false;
    try {
      const dibuat = await chatService.buatRuang(slug, nama, privat ? "privat" : "kanal");
      setBuatTerbuka(false);
      await Promise.all([muatKanal(), muatPercakapan()]);
      setSearchParams({ ruang: dibuat.id });
      return true;
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("chat_ui.channel_create_failed"),
        message: (galat as { error?: string })?.error ?? t("chat_ui.try_again_shortly"),
      });
      return false;
    }
  };

  const gabung = async (ruangId: string) => {
    if (!slug) return;
    try {
      await chatService.gabungRuang(slug, ruangId);
      await Promise.all([muatKanal(), muatPercakapan()]);
      setJelajah(false);
      setSearchParams({ ruang: ruangId });
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("chat_ui.join_failed"),
        message: (galat as { error?: string })?.error ?? t("chat_ui.try_again_shortly"),
      });
    }
  };

  // Keluar kanal pindah ke DialogSetelanKanal (kanal-setelan.tsx).

  if (!slug) return <></>;

  return (
    <div className="flex h-full w-full">
      <PageHead title={t("chat_nav")} />

      {/* Daftar orang */}
      {/* Lebar penuh di layar sempit, 320px sejak lg. `lg` (1024px) sengaja sama
          dengan ambang `isLayarSempit` di usePlatformOS, supaya sidebar aplikasi
          dan panel obrolan berpindah mode pada titik yang sama persis. */}
      <aside
        className={cn(
          "flex w-full shrink-0 flex-col border-r border-subtle lg:w-80",
          adaPercakapanTerbuka && "hidden lg:flex"
        )}
      >
        <div className="flex items-center gap-2 border-b border-subtle p-3">
          <div className="flex flex-1 items-center gap-2 search-field border border-subtle px-2.5 py-1.5 focus-within:border-accent-strong">
            <Search className="size-3.5 shrink-0 text-tertiary" />
            <Input
              type="text"
              mode="true-transparent"
              value={cari}
              onChange={(e) => {
                setCari(e.target.value);
                // Mengetik ulang membatalkan hasil lama, kalau tidak daftar
                // hasil bertahan padahal kata kuncinya sudah berubah.
                if (hasilCari) setHasilCari(null);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") void cariIsiPesan();
                if (e.key === "Escape") {
                  setCari("");
                  setHasilCari(null);
                }
              }}
              placeholder={t("chat_ui.search_placeholder")}
              aria-label={t("chat_ui.search_label")}
              className="w-full p-0 text-primary placeholder:text-placeholder"
            />
            {cari.trim().length >= 3 ? (
              <button
                type="button"
                onClick={() => void cariIsiPesan()}
                disabled={mencari}
                aria-label={t("chat_ui.search_messages")}
                title={t("chat_ui.search_messages")}
                className="shrink-0 rounded-button px-1.5 py-0.5 text-12 font-medium text-accent-primary hover:bg-layer-1 disabled:opacity-50"
              >
                {mencari ? "…" : t("chat_ui.search_content_short")}
              </button>
            ) : null}
          </div>
          <SaklarSuara />
        </div>
        <div className="flex-1 overflow-y-auto">
          {/* Kanal ditaruh di ATAS daftar orang. Kanal jumlahnya sedikit dan
              dibuka berulang kali; daftar orang panjang dan sebagian besar
              tidak pernah disentuh. */}
          {!hasilCari ? (
            <div className="border-b border-subtle pb-1">
              <div className="flex items-center justify-between px-3 pt-2.5 pb-1">
                <p className="text-12 font-semibold tracking-wide text-tertiary uppercase">{t("chat_ui.channels")}</p>
                <div className="flex items-center gap-0.5">
                  <IconButton
                    type="button"
                    onClick={() => setJelajah(true)}
                    title={t("chat_ui.browse_channels")}
                    variant="ghost"
                    size="sm"
                    icon={Compass}
                  />
                  <IconButton
                    type="button"
                    onClick={() => setBuatTerbuka(true)}
                    title={t("chat_ui.create_channel")}
                    variant="ghost"
                    size="sm"
                    icon={Plus}
                  />
                </div>
              </div>
              {kanalDiikuti.length === 0 ? (
                <p className="px-3 pb-1.5 text-12 text-tertiary">{t("chat_ui.no_channels_joined")}</p>
              ) : (
                kanalDiikuti.map((r) => {
                  const adaBaru = r.belum_dibaca > 0;
                  return (
                    <button
                      key={r.id}
                      type="button"
                      onClick={() => setSearchParams({ ruang: r.id })}
                      className={`flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-layer-1 ${
                        r.id === ruangParam ? "bg-layer-1-selected" : ""
                      }`}
                    >
                      {r.tipe === "privat" ? (
                        <Lock className="size-3.5 shrink-0 text-tertiary" />
                      ) : (
                        <Hash className="size-3.5 shrink-0 text-tertiary" />
                      )}
                      <span
                        className={`min-w-0 flex-1 truncate text-13 text-primary ${
                          adaBaru ? "font-semibold" : "font-regular"
                        }`}
                      >
                        {r.nama}
                      </span>
                      {r.sistem ? (
                        <span className="shrink-0 rounded-control bg-layer-3 px-1.5 py-px text-11 font-medium text-tertiary">
                          {/* Kanal divisi/departemen diberi label unitnya, bukan "System":
                              isinya obrolan orang, cuma anggotanya yang diatur God Mode. */}
                          {r.kunci_sistem?.startsWith("divisi:")
                            ? t("chatkartu_ui.org_division")
                            : r.kunci_sistem?.startsWith("departemen:")
                              ? t("chatkartu_ui.org_department")
                              : t("chatkartu_ui.system_badge")}
                        </span>
                      ) : null}
                      {adaBaru ? <CountChip count={getNumberCount(r.belum_dibaca)} className="shrink-0" /> : null}
                    </button>
                  );
                })
              )}
            </div>
          ) : null}
          {hasilCari ? (
            <div>
              <div className="flex items-center justify-between px-3 py-2">
                <p className="text-12 font-medium text-secondary">
                  {hasilCari.length > 0 ? t("chat_ui.messages_found", { count: hasilCari.length }) : ""}
                </p>
                <button
                  type="button"
                  onClick={() => setHasilCari(null)}
                  className="text-12 text-tertiary hover:text-primary"
                >
                  {t("close")}
                </button>
              </div>
              {hasilCari.length === 0 ? (
                <EmptyStateCompact
                  assetKey="search"
                  title={t("chat_ui.no_matching_messages")}
                  assetClassName="size-16"
                  rootClassName="px-page-x py-8"
                />
              ) : null}
              {hasilCari.map((h) => {
                // Pesan kanal tidak punya lawan bicara. Judulnya diambil dari
                // nama kanal, dan membukanya lewat id ruang.
                const anggota = h.lawan_bicara ? getWorkspaceMemberDetails(h.lawan_bicara)?.member : undefined;
                const kanal = (daftarKanal ?? []).find((r) => r.id === h.ruang);
                const judul = anggota?.display_name ?? kanal?.nama ?? t("chat_ui.conversation");
                return (
                  <button
                    key={h.id}
                    type="button"
                    onClick={() => {
                      setSearchParams(h.lawan_bicara ? { dengan: h.lawan_bicara } : { ruang: h.ruang });
                      setHasilCari(null);
                      setCari("");
                    }}
                    className="flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left hover:bg-layer-1"
                  >
                    <span className="flex w-full items-center justify-between gap-2 text-12">
                      <span className="truncate font-medium text-primary">{judul}</span>
                      <span className="shrink-0 text-tertiary">{waktuRingkas(h.created_at)}</span>
                    </span>
                    <span className="line-clamp-2 text-12 text-secondary">
                      {h.dari_saya ? t("chat_ui.you_prefix") : ""}
                      {h.isi}
                    </span>
                  </button>
                );
              })}
            </div>
          ) : daftar.length === 0 ? (
            // Kosong tanpa kata kunci berarti memang belum ada anggota lain,
            // bukan hasil pencarian. "Tidak ada yang cocok" di situ menyesatkan.
            <EmptyStateCompact
              assetKey={cari.trim() ? "search" : "members"}
              title={cari.trim() ? t("chat_ui.no_matching_people") : t("chat_ui.no_teammates")}
              assetClassName="size-16"
              rootClassName="px-page-x py-8"
            />
          ) : (
            daftar.map(({ id, terakhir }) => {
              const anggota = getWorkspaceMemberDetails(id)?.member;
              const terpilih = id === dengan;
              const adaBaru = (terakhir?.belum_dibaca ?? 0) > 0;
              const diriSendiri = id === currentUser?.id;
              const nama = anggota?.display_name ?? t("chat_ui.member");
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => setSearchParams({ dengan: id })}
                  className={`flex w-full items-center gap-2.5 px-3 py-2.5 text-left hover:bg-layer-1 ${
                    terpilih ? "bg-layer-1-selected" : ""
                  }`}
                >
                  <DenganKehadiran userId={id}>
                    <Avatar
                      name={anggota?.display_name}
                      src={getFileURL(anggota?.avatar_url ?? "")}
                      size={32}
                      shape="circle"
                    />
                  </DenganKehadiran>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      {/* Belum dibaca ditandai tebal, bukan cuma lencana. Angka
                          saja mudah terlewat saat menyapu daftar dengan mata. */}
                      <p className={`truncate text-13 text-primary ${adaBaru ? "font-semibold" : "font-medium"}`}>
                        {diriSendiri ? `${nama} (${t("chat_ui.you")})` : nama}
                      </p>
                      {terakhir ? (
                        <span className={`shrink-0 text-12 ${adaBaru ? "text-accent-primary" : "text-tertiary"}`}>
                          {waktuRingkas(terakhir.created_at)}
                        </span>
                      ) : null}
                    </div>
                    <div className="mt-0.5 flex items-center justify-between gap-2">
                      <p className={`truncate text-12 ${adaBaru ? "font-medium text-secondary" : "text-tertiary"}`}>
                        {terakhir
                          ? `${terakhir.dari_saya && !diriSendiri ? t("chat_ui.you_prefix") : ""}${terakhir.isi || t("chat_ui.sent_attachment")}`
                          : diriSendiri
                            ? t("chat_ui.notes_to_self")
                            : t("chat_ui.no_messages")}
                      </p>
                      {adaBaru ? (
                        <CountChip count={getNumberCount(terakhir?.belum_dibaca ?? 0)} className="shrink-0" />
                      ) : null}
                    </div>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </aside>

      {/* Percakapan */}
      {/* Kebalikannya: di layar sempit, panel ini hanya muncul kalau ada yang
          dibuka. Keadaan kosong "Pilih orang di sebelah kiri" tidak masuk akal
          di HP, karena di situ tidak ada "sebelah kiri". */}
      <section
        className={cn("relative flex min-w-0 flex-1 flex-col", !adaPercakapanTerbuka && "hidden lg:flex")}
        {...(adaPercakapanTerbuka ? aturSeret : {})}
      >
        {/* Area lepas: muncul hanya saat berkas diseret di atas percakapan. */}
        {diseret && adaPercakapanTerbuka ? (
          <div
            aria-hidden
            className="pointer-events-none absolute inset-2 z-20 grid place-items-center rounded-card border-2 border-dashed border-accent-strong bg-surface-1/90"
          >
            <p className="flex items-center gap-2 text-14 font-medium text-accent-primary">
              <Upload className="size-5" />
              {t("chatux_kelola_ui.drop_to_attach")}
            </p>
          </div>
        ) : null}
        {!dengan && !ruangParam ? (
          // Sama dengan Intake: panel detail yang kosong memakai empty state
          // bawaan, bukan teks kecil di tengah layar kosong.
          <EmptyStateCompact
            assetKey="members"
            title={t("chat_ui.no_conversation_open")}
            description={t("chat_ui.pick_someone")}
            assetClassName="size-20"
            rootClassName="px-page-x"
            actions={[
              { label: t("chat_ui.create_channel"), variant: "primary", onClick: () => setBuatTerbuka(true) },
              { label: t("chat_ui.browse_channels"), variant: "secondary", onClick: () => setJelajah(true) },
            ]}
          />
        ) : (
          <>
            <div className="flex items-center gap-2.5 border-b border-subtle px-4 py-2.5">
              {/* Satu-satunya jalan kembali ke daftar di layar sempit, karena di
                  situ daftarnya memang tidak terlihat. Disembunyikan sejak lg,
                  di mana kedua panel tampil berdampingan dan tombol ini justru
                  membingungkan. `size-9` supaya nyaman disentuh jari. */}
              <button
                type="button"
                onClick={() => setSearchParams({})}
                className="-ml-1.5 grid size-9 shrink-0 place-items-center rounded-button text-secondary hover:bg-layer-1 hover:text-primary lg:hidden"
                aria-label={t("chat_ui.back_to_list")}
              >
                <ChevronLeft className="size-5" />
              </button>
              {adalahKanal ? (
                <>
                  {kanalAktif?.tipe === "privat" ? (
                    <Lock className="size-4 text-tertiary" />
                  ) : (
                    <Hash className="size-4 text-tertiary" />
                  )}
                  <p className="min-w-0 truncate text-13 font-medium text-primary">
                    {kanalAktif?.nama ?? t("chat_ui.channel")}
                  </p>
                  {kanalAktif?.topik ? (
                    <p className="hidden min-w-0 truncate text-12 text-tertiary sm:block">{kanalAktif.topik}</p>
                  ) : null}
                  {/* Panggilan kanal = konferensi. Tidak berdering ke satu orang;
                      undangannya disiarkan ke anggota yang sedang membuka kanal
                      ini, lalu mereka memutuskan sendiri mau gabung atau tidak.
                      Meneleponkan dering ke belasan orang sekaligus akan jadi
                      gangguan, bukan fitur. */}
                  <div className="ml-auto flex items-center gap-1">
                    <IconButton
                      type="button"
                      onClick={() => mulaiKonferensi(false)}
                      disabled={!tersambung || panggilan.status !== "diam" || kanalTanpaPanggilan}
                      title={tersambung ? t("chat_ui.start_channel_voice") : t("chat_ui.realtime_down")}
                      aria-label={t("chat_ui.channel_voice_call")}
                      variant="ghost"
                      size="lg"
                      icon={Phone}
                    />
                    <IconButton
                      type="button"
                      onClick={() => mulaiKonferensi(true)}
                      disabled={!tersambung || panggilan.status !== "diam" || kanalTanpaPanggilan}
                      title={tersambung ? t("chat_ui.start_channel_video") : t("chat_ui.realtime_down")}
                      aria-label={t("chat_ui.channel_video_call")}
                      variant="ghost"
                      size="lg"
                      icon={Video}
                    />
                    {/* Setelan kanal: anggota, undang, ubah nama/topik, keluar,
                        hapus. Keluar pindah ke sini; kanal sistem tidak punya
                        tombol keluar di dalamnya. */}
                    <IconButton
                      type="button"
                      onClick={() => setSetelanTerbuka(true)}
                      title={t("chatux_kelola_ui.channel_settings")}
                      aria-label={t("chatux_kelola_ui.channel_settings")}
                      variant="ghost"
                      size="lg"
                      icon={Settings2}
                    />
                  </div>
                </>
              ) : (
                <>
                  <MemberProfileTrigger userId={dengan} className="shrink-0">
                    <DenganKehadiran userId={dengan}>
                      <Avatar
                        name={lawanBicara?.display_name}
                        src={getFileURL(lawanBicara?.avatar_url ?? "")}
                        size={32}
                        shape="circle"
                      />
                    </DenganKehadiran>
                  </MemberProfileTrigger>
                  <div className="min-w-0">
                    <p className="truncate text-13 font-medium text-primary">
                      <MemberProfileTrigger userId={dengan}>
                        <span className="truncate hover:underline">
                          {lawanBicara?.display_name ?? t("chat_ui.member")}
                        </span>
                      </MemberProfileTrigger>
                    </p>
                    {dengan !== currentUser?.id ? (
                      <p className="flex items-center gap-1 text-12 text-tertiary">
                        <TitikKehadiran userId={dengan} className="size-2" />
                        <StatusKehadiranTeks userId={dengan} />
                      </p>
                    ) : null}
                  </div>
                  {dengan === currentUser?.id ? (
                    <p className="truncate text-12 text-tertiary">{t("chat_ui.notes_to_self")}</p>
                  ) : null}
                  {/* Panggilan hanya untuk DM. Untuk kanal butuh SFU, dan itu
                      pekerjaan lain. Tombolnya mati kalau soket kehadiran putus,
                      karena tanpa jalur sinyal panggilan tidak akan tersambung
                      dan yang menekan cuma menunggu tanpa tahu sebabnya.
                      Tidak ada tombol sama sekali di catatan diri sendiri:
                      menelepon diri sendiri cuma berdering tanpa ujung. */}
                  <div className={cn("ml-auto flex items-center gap-1", dengan === currentUser?.id && "hidden")}>
                    <IconButton
                      type="button"
                      onClick={() => telepon(false)}
                      disabled={!panggilan.siap || panggilan.status !== "diam"}
                      title={panggilan.siap ? t("chat_ui.voice_call") : t("chat_ui.realtime_down")}
                      aria-label={t("chat_ui.voice_call")}
                      variant="ghost"
                      size="lg"
                      icon={Phone}
                    />
                    <IconButton
                      type="button"
                      onClick={() => telepon(true)}
                      disabled={!panggilan.siap || panggilan.status !== "diam"}
                      title={panggilan.siap ? t("chat_ui.video_call") : t("chat_ui.realtime_down")}
                      aria-label={t("chat_ui.video_call")}
                      variant="ghost"
                      size="lg"
                      icon={Video}
                    />
                  </div>
                </>
              )}
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-3">
              {/* Tombol riwayat hanya muncul kalau memang ada kemungkinan ada
                  yang lebih lama, dan menghilang setelah server bilang habis. */}
              {barisPesan.length > 0 && !habis ? (
                <div className="mb-2 flex justify-center">
                  <Button
                    variant="secondary"
                    size="base"
                    prependIcon={<ChevronUp />}
                    onClick={() => void muatLama()}
                    disabled={memuatLama}
                  >
                    {memuatLama ? t("chat_ui.loading") : t("chat_ui.load_older")}
                  </Button>
                </div>
              ) : null}

              {barisPesan.length === 0 ? (
                <EmptyStateCompact
                  assetKey="inbox"
                  title={t("chat_ui.no_messages")}
                  description={t("chat_ui.empty_thread")}
                  assetClassName="size-20"
                />
              ) : (
                <div className="flex flex-col">
                  {barisPesan.map((baris) => {
                    if (baris.jenis === "tanggal")
                      return (
                        <div key={baris.kunci} className="my-3 flex items-center justify-center">
                          <span className="rounded-control bg-layer-3 px-2.5 py-1 text-12 font-medium text-secondary">
                            {baris.relatif === "hari-ini"
                              ? t("chat_ui.today")
                              : baris.relatif === "kemarin"
                                ? t("chat_ui.yesterday")
                                : baris.label}
                          </span>
                        </div>
                      );

                    if (baris.jenis === "belum-dibaca")
                      return (
                        <div key={baris.kunci} className="my-3 flex items-center gap-2">
                          <div className="h-px flex-1 bg-accent-primary/40" />
                          <span className="text-12 font-medium text-accent-primary">
                            {t("chat_ui.unread_messages")}
                          </span>
                          <div className="h-px flex-1 bg-accent-primary/40" />
                        </div>
                      );

                    const { pesan: p, dariSaya, awalKelompok, akhirKelompok } = baris;
                    // Di kanal tiap pesan bisa dari orang lain, jadi avatarnya
                    // dari pengirim pesan itu, bukan dari lawan bicara DM.
                    const pengirim = p.pengirim ? getWorkspaceMemberDetails(p.pengirim)?.member : undefined;
                    return (
                      <div
                        key={baris.kunci}
                        id={idElemenPesan(p.id)}
                        className={`flex scroll-my-16 items-end gap-2 rounded-item transition-colors duration-700 ${
                          awalKelompok ? "mt-2" : "mt-0.5"
                        } ${dariSaya ? "justify-end" : "justify-start"} ${disorot === p.id ? "bg-accent-subtle" : ""}`}
                      >
                        {!dariSaya ? (
                          <div className="w-7 shrink-0">
                            {awalKelompok && p.pengirim ? (
                              <MemberProfileTrigger userId={p.pengirim}>
                                <Avatar
                                  name={pengirim?.display_name}
                                  src={getFileURL(pengirim?.avatar_url ?? "")}
                                  size={28}
                                  shape="circle"
                                />
                              </MemberProfileTrigger>
                            ) : null}
                          </div>
                        ) : null}
                        <Gelembung
                          pesan={p}
                          dariSaya={dariSaya}
                          awalKelompok={awalKelompok}
                          akhirKelompok={akhirKelompok}
                          sayaId={currentUser?.id}
                          namaOrang={(id) =>
                            id === currentUser?.id
                              ? t("chat_ui.you")
                              : (getWorkspaceMemberDetails(id)?.member?.display_name ?? t("chat_ui.member"))
                          }
                          namaSebutan={(id) =>
                            id === currentUser?.id
                              ? (currentUser?.display_name ?? "")
                              : (getWorkspaceMemberDetails(id)?.member?.display_name ?? "")
                          }
                          onBukaKutipan={lompatKePesan}
                          onBalas={(pesanIni) => {
                            setMenyunting(null);
                            setMembalas(pesanIni);
                            tulisRef.current?.focus();
                          }}
                          onSunting={(pesanIni) => {
                            setMembalas(null);
                            setMenyunting(pesanIni);
                            setDraf(pesanIni.isi);
                            tulisRef.current?.focus();
                          }}
                          onHapus={(pesanIni) =>
                            minta(
                              { judul: t("chat_ui.confirm_delete_title"), isi: t("chat_ui.confirm_delete_body") },
                              () => hapus(pesanIni)
                            )
                          }
                          batasHapusJam={batasHapusJam}
                          onReaksi={(pesanIni, emoji) => void reaksi(pesanIni, emoji)}
                          onTelepon={(video) => {
                            if (adalahKanal) mulaiKonferensi(video);
                            else telepon(video);
                          }}
                        />
                      </div>
                    );
                  })}
                </div>
              )}
              <div ref={akhirRef} />
            </div>

            {/* Kanal sistem yang hanya bisa dibaca: Changelog, ruang kabar
                "Paradise", dan Announcements bagi yang bukan admin. Server tetap
                menolak 403; kolom tulis cuma disembunyikan supaya tidak menipu. */}
            {kanalAktif?.boleh_kirim === false ? (
              <p className="border-t border-subtle p-3 text-center text-12 text-tertiary">
                {kanalAktif.kunci_sistem === "pengumuman"
                  ? t("chatkartu_ui.announcements_admin_only")
                  : t("chatkartu_ui.read_only")}
              </p>
            ) : null}
            <div
              className={`flex flex-col gap-2 border-t border-subtle p-3 ${kanalAktif?.boleh_kirim === false ? "hidden" : ""}`}
            >
              {membalas && !menyunting ? (
                <KutipanBalasan
                  nama={
                    membalas.pengirim && membalas.pengirim === currentUser?.id
                      ? t("chat_ui.you")
                      : ((membalas.pengirim
                          ? getWorkspaceMemberDetails(membalas.pengirim)?.member?.display_name
                          : null) ?? t("chat_ui.member"))
                  }
                  isi={membalas.dihapus ? t("chat_ui.message_deleted") : membalas.isi || t("chat_ui.attachment")}
                  miring={!!membalas.dihapus}
                  labelBatal={t("cancel")}
                  onBatal={() => setMembalas(null)}
                />
              ) : null}
              {menyunting ? (
                <div className="flex items-start gap-2 rounded-item border-l-2 border-accent-strong bg-layer-1 px-2.5 py-1.5">
                  <div className="min-w-0 flex-1">
                    <p className="flex items-center gap-1 text-12 font-medium text-accent-primary">
                      <Pencil className="size-3" />
                      {t("chat_ui.editing_message")}
                    </p>
                    <p className="truncate text-12 text-tertiary">{menyunting.isi || t("chat_ui.attachment")}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      // Batal menyunting mengembalikan kotak tulis ke kosong,
                      // bukan meninggalkan teks lama yang lalu terkirim sebagai
                      // pesan baru tanpa disadari.
                      if (menyunting) setDraf("");
                      setMenyunting(null);
                      setMembalas(null);
                    }}
                    aria-label={t("cancel")}
                    className="-m-1.5 rounded-button p-1.5 text-tertiary hover:text-primary"
                  >
                    <X className="size-3.5" />
                  </button>
                </div>
              ) : null}
              {lampiran.length > 0 || mengunggah ? (
                <div className="flex flex-wrap items-center gap-2">
                  {lampiran.map((l) => (
                    <span
                      key={l.id}
                      className="flex items-center gap-1.5 rounded-control border border-subtle px-2 py-1 text-12 text-secondary"
                    >
                      <span className="max-w-40 truncate">{l.nama}</span>
                      <span className="text-tertiary">{ukuranTerbaca(l.ukuran)}</span>
                      <button
                        type="button"
                        data-sentuh-lega
                        onClick={() => buangLampiran(l.id)}
                        aria-label={t("chat_ui.remove_named", { name: l.nama })}
                        className="-m-1.5 rounded-button p-1.5 text-tertiary hover:text-primary"
                      >
                        <X className="size-3" />
                      </button>
                    </span>
                  ))}
                  {/* Berkas yang masih naik: nama + kemajuan. Tidak bisa dibatalkan
                      di tengah jalan; sesudah selesai ia jadi chip biasa yang bisa dibuang. */}
                  {sedangNaik.map((n) => (
                    <span
                      key={n.kunci}
                      className="relative flex items-center gap-1.5 overflow-hidden rounded-control border border-subtle px-2 py-1 text-12 text-tertiary"
                    >
                      <span
                        aria-hidden
                        className="absolute inset-y-0 left-0 bg-accent-primary/10 transition-[width]"
                        style={{ width: `${n.persen}%` }}
                      />
                      <span className="relative max-w-40 truncate">{n.nama}</span>
                      <span className="relative tabular-nums">{n.persen}%</span>
                      <progress
                        className="sr-only"
                        max={100}
                        value={n.persen}
                        aria-label={t("chatux_kelola_ui.uploading_named", { name: n.nama })}
                      />
                    </span>
                  ))}
                </div>
              ) : null}
              <div className="flex items-end gap-2">
                <input ref={berkasRef} type="file" multiple hidden onChange={(e) => void unggah(e.target.files)} />
                <IconButton
                  type="button"
                  onClick={() => berkasRef.current?.click()}
                  disabled={mengunggah}
                  aria-label={t("chat_ui.attach_file")}
                  variant="ghost"
                  size="xl"
                  icon={Paperclip}
                />
                <EmojiReactionPicker
                  isOpen={emojiTerbuka}
                  handleToggle={setEmojiTerbuka}
                  placement="top-start"
                  onChange={(emoji) => {
                    // Picker memberi kode desimal, bukan karakternya. Tanpa
                    // stringToEmoji yang masuk ke pesan adalah angka.
                    setDraf((sebelumnya) => `${sebelumnya}${stringToEmoji(emoji)}`);
                    setEmojiTerbuka(false);
                    tulisRef.current?.focus();
                  }}
                  label={
                    <span
                      className="flex size-9 items-center justify-center rounded-button text-secondary hover:bg-layer-transparent-hover"
                      aria-label={t("chat_ui.insert_emoji")}
                    >
                      <SmilePlus className="size-4" />
                    </span>
                  }
                />
                <div className="relative min-w-0 flex-1">
                  {sebutan.terbuka ? (
                    <DaftarSebut
                      cocok={sebutan.cocok}
                      sorot={sebutan.sorot}
                      onSorot={sebutan.setSorot}
                      onPilih={sebutan.pilih}
                    />
                  ) : null}
                  <textarea
                    ref={tulisRef}
                    maxLength={batasParadise.chat_message_max_length}
                    value={draf}
                    onChange={(e) => {
                      setDraf(e.target.value);
                      sebutan.onChange(e);
                      aturTinggiTulis();
                    }}
                    onClick={(e) => sebutan.onKursor(e.currentTarget.value, e.currentTarget.selectionStart ?? 0)}
                    onBlur={() => sebutan.onKursor("", 0)}
                    onPaste={(e) => {
                      // Tempel gambar/berkas = lampiran. Tempelan teks biasa
                      // dibiarkan jalan seperti biasa.
                      const berkas = berkasDariTempel(e.clipboardData);
                      if (berkas.length === 0) return;
                      e.preventDefault();
                      void unggah(berkas);
                    }}
                    onKeyDown={(e) => {
                      // Pemilih sebutan yang terbuka menang atas Enter/Escape.
                      if (sebutan.onKeyDown(e)) return;
                      // Enter mengirim, Shift+Enter ganti baris. Kebiasaan yang
                      // sudah dibawa orang dari aplikasi obrolan lain.
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        void (menyunting ? simpanSuntingan() : kirim());
                      }
                      // Escape membatalkan balas atau sunting. Tanpa ini, satu
                      // satunya jalan keluar adalah mengklik tanda silang kecil.
                      if (e.key === "Escape" && (menyunting || membalas)) {
                        if (menyunting) setDraf("");
                        setMenyunting(null);
                        setMembalas(null);
                      }
                    }}
                    rows={1}
                    placeholder={t("chat_ui.write_message")}
                    aria-label={t("chat_ui.write_message")}
                    className="block min-h-9 w-full resize-none rounded-field border border-subtle bg-transparent px-3 py-2 text-13 text-primary outline-none placeholder:text-placeholder focus:border-accent-strong"
                  />
                </div>
                <IconButton
                  variant="primary"
                  size="xl"
                  icon={Send}
                  onClick={() => void (menyunting ? simpanSuntingan() : kirim())}
                  disabled={
                    mengirim ||
                    mengunggah ||
                    (menyunting ? draf.trim().length === 0 : draf.trim().length === 0 && lampiran.length === 0)
                  }
                  aria-label={t("chat_ui.send_message")}
                />
              </div>
            </div>
          </>
        )}
      </section>

      {dialogKonfirmasi}

      {/* Ajakan gabung, bukan dering. Muncul untuk yang sedang membuka ruang
          saat orang lain memulai panggilan di sana. */}
      {panggilan.konferensiBerjalan &&
      panggilan.konferensiBerjalan.ruang === ruangSaatIni &&
      panggilan.status === "diam" ? (
        <div className="fixed bottom-6 left-1/2 z-30 flex -translate-x-1/2 items-center gap-3 rounded-control border border-subtle bg-layer-3 px-4 py-2">
          <span className="text-13 text-primary">{t("chat_ui.call_in_progress")}</span>
          <Button
            variant="primary"
            size="base"
            onClick={() => mulaiKonferensi(panggilan.konferensiBerjalan?.video ?? false)}
          >
            {t("chat_ui.join")}
          </Button>
        </div>
      ) : null}

      {/* Layar panggilan dirender PenyediaPanggilan di lapisan workspace. */}

      <DialogBuatKanal isOpen={buatTerbuka} onClose={() => setBuatTerbuka(false)} onBuat={buatKanal} />
      <DialogSetelanKanal
        isOpen={setelanTerbuka && adalahKanal}
        onClose={() => setSetelanTerbuka(false)}
        slug={slug}
        ruangId={ruangParam}
        onPergi={() => {
          void Promise.all([muatKanal(), muatPercakapan()]);
          setSearchParams({});
        }}
        onBerubah={() => void Promise.all([muatKanal(), muatPercakapan()])}
      />
      <DialogJelajahKanal
        isOpen={jelajah}
        onClose={() => setJelajah(false)}
        kanal={kanalBelumDiikuti}
        onGabung={(ruangId) => void gabung(ruangId)}
      />
    </div>
  );
}

export default observer(ChatPage);
