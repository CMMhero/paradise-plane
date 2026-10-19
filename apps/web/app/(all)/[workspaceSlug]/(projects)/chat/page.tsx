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
  CornerUpLeft,
  MessageSquare,
  Paperclip,
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
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Avatar } from "@plane/ui";
import { cn, getFileURL, renderFormattedDate, renderFormattedTime } from "@plane/utils";
// components
import { PageHead } from "@/components/core/page-title";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { SaklarSuara } from "@/components/notifikasi/saklar-suara";
import { useSuaraNotifikasi } from "@/hooks/use-suara-notifikasi";
import { useUser } from "@/hooks/store/user";
// services
import { EFileAssetType } from "@plane/types";
import { FileService } from "@/services/file.service";
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
import { usePanggilan } from "./panggilan";
import { PanggilanLayar } from "./panggilan-layar";
import { Gelembung } from "./gelembung";
import { ukuranTerbaca } from "./lampiran";

const chatService = new ChatService();
const fileService = new FileService();

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
  const {
    workspace: { workspaceMemberIds, getWorkspaceMemberDetails },
  } = useMember();
  const { t } = useTranslation();
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
  const [lampiran, setLampiran] = useState<{ id: string; nama: string; ukuran: number }[]>([]);
  const [membalas, setMembalas] = useState<TPesan | null>(null);
  const [menyunting, setMenyunting] = useState<TPesan | null>(null);
  const [lama, setLama] = useState<TPesan[]>([]);
  const [memuatLama, setMemuatLama] = useState(false);
  const [habis, setHabis] = useState(false);
  const [mengunggah, setMengunggah] = useState(false);
  const [buatTerbuka, setBuatTerbuka] = useState(false);
  const [namaKanal, setNamaKanal] = useState("");
  const [kanalPrivat, setKanalPrivat] = useState(false);
  const [membuat, setMembuat] = useState(false);
  const [jelajah, setJelajah] = useState(false);
  const berkasRef = useRef<HTMLInputElement>(null);
  const akhirRef = useRef<HTMLDivElement>(null);
  const { bunyikan } = useSuaraNotifikasi();
  const pesanTerakhirRef = useRef<string | null>(null);
  const tulisRef = useRef<HTMLTextAreaElement>(null);
  const namaKanalRef = useRef<HTMLInputElement>(null);
  const panggilanRef = useRef<ReturnType<typeof usePanggilan> | null>(null);

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
    onPerubahan: () => {
      if (kunciIsi) void mutate(kunciIsi);
      void mutate(`CHAT_PERCAKAPAN_${slug}`);
      void mutate(KUNCI_BELUM_DIBACA);
    },
    onSinyal: (dari, muatan) => void panggilanRef.current?.terimaSinyal(dari, muatan),
    onPergi: (dari) => panggilanRef.current?.lawanPergi(dari),
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

  // Ganti lawan bicara = buang riwayat lama yang sudah dimuat, kalau tidak
  // pesan orang sebelumnya ikut menempel di atas percakapan berikutnya.
  useEffect(() => {
    setLama([]);
    setHabis(false);
    setMembalas(null);
    setMenyunting(null);
  }, [dengan, ruangParam]);

  // Berbunyi saat pesan MASUK baru tiba di percakapan yang sedang terbuka.
  // Lencana sidebar tidak bisa mengurus ini: membuka percakapan menandainya
  // terbaca, jadi angkanya tidak pernah naik dan bunyinya tidak pernah keluar.
  useEffect(() => {
    const daftar = pesan ?? [];
    const terakhir = daftar[daftar.length - 1];
    if (!terakhir) {
      pesanTerakhirRef.current = null;
      return;
    }
    const berganti = pesanTerakhirRef.current !== null && pesanTerakhirRef.current !== terakhir.id;
    if (berganti && terakhir.pengirim !== currentUser?.id) bunyikan("pesan");
    pesanTerakhirRef.current = terakhir.id;
  }, [pesan, currentUser?.id, bunyikan]);

  // Selalu tampilkan pesan terbaru saat percakapan bertambah atau berganti.
  useEffect(() => {
    akhirRef.current?.scrollIntoView({ block: "end" });
    // Memuat percakapan berarti menandainya terbaca di server, jadi lencana di
    // sidebar sudah basi sejak detik itu. Disegarkan di sini supaya angkanya
    // turun seketika, bukan pada tarikan 30 detik berikutnya.
    void mutate(KUNCI_BELUM_DIBACA);
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
      if (id === currentUser?.id) return false;
      if (!kunciCari) return true;
      const nama = getWorkspaceMemberDetails(id)?.member?.display_name ?? "";
      return nama.toLowerCase().includes(kunciCari);
    });
    // Tidak ada pengurutan di sini sama sekali. Server sudah mengirim percakapan
    // terbaru lebih dulu, dan store sudah mengurutkan anggota menurut nama, jadi
    // menyambung dua daftar yang masing-masing sudah urut sudah cukup.
    const cocok = new Set(kandidat);
    const adaPesan = barisDM.map((baris) => baris.lawan_bicara).filter((id) => cocok.has(id));
    const belumPernah = kandidat.filter((id) => !peta.has(id));
    return [...adaPesan, ...belumPernah].map((id) => ({ id, terakhir: peta.get(id) }));
  }, [percakapan, workspaceMemberIds, currentUser?.id, cari, getWorkspaceMemberDetails]);

  const semuaPesan = useMemo(() => [...lama, ...(pesan ?? [])], [lama, pesan]);
  const barisPesan = useMemo(() => susunBaris(semuaPesan, currentUser?.id), [semuaPesan, currentUser?.id]);

  const lawanBicara = dengan ? getWorkspaceMemberDetails(dengan)?.member : undefined;

  const aturTinggiTulis = () => {
    const el = tulisRef.current;
    if (!el) return;
    // Tinggi dinolkan dulu; tanpa itu scrollHeight ikut tinggi lama dan kotaknya
    // tumbuh terus tapi tidak pernah menyusut lagi.
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, TINGGI_TULIS_MAKS)}px`;
  };

  const unggah = async (berkas: FileList | null) => {
    if (!berkas || berkas.length === 0 || !slug) return;
    setMengunggah(true);
    // allSettled, bukan all: satu berkas yang ditolak server tidak boleh
    // membuang berkas lain yang sudah berhasil naik.
    const hasil = await Promise.allSettled(
      Array.from(berkas).map(async (f) => {
        // entity_identifier dikosongkan: pesannya belum ada saat berkas
        // diunggah. Server yang menempelkannya ke pesan begitu terkirim, dan
        // hanya menerima berkas yang diunggah orang yang sama.
        const res = await fileService.uploadWorkspaceAsset(
          slug,
          { entity_identifier: "", entity_type: EFileAssetType.CHAT_ATTACHMENT },
          f
        );
        return { id: res.asset_id, nama: f.name, ukuran: f.size };
      })
    );

    const berhasil = hasil.filter((h) => h.status === "fulfilled").map((h) => h.value);
    if (berhasil.length > 0) setLampiran((sebelumnya) => [...sebelumnya, ...berhasil]);

    const gagal = hasil.length - berhasil.length;
    if (gagal > 0)
      setToast({
        type: TOAST_TYPE.ERROR,
        title: gagal === hasil.length ? "Berkas gagal diunggah" : `${gagal} berkas gagal diunggah`,
        message: "Ukurannya mungkin melebihi batas, atau tipenya tidak diizinkan.",
      });

    setMengunggah(false);
    if (berkasRef.current) berkasRef.current.value = "";
  };

  const cariIsiPesan = async () => {
    const q = cari.trim();
    if (!slug || q.length < 3) {
      setToast({ type: TOAST_TYPE.ERROR, title: "Kata kunci minimal 3 huruf" });
      return;
    }
    setMencari(true);
    try {
      setHasilCari(await chatService.cariPesan(slug, q));
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Pencarian gagal",
        message: (galat as { error?: string })?.error ?? "Coba lagi sebentar.",
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
      setToast({ type: TOAST_TYPE.ERROR, title: "Gagal memuat pesan lama" });
    } finally {
      setMemuatLama(false);
    }
  };

  const simpanSuntingan = async () => {
    const isi = draf.trim();
    if (!slug || !menyunting || !isi) return;
    setMengirim(true);
    try {
      await chatService.suntingPesan(slug, menyunting.id, isi);
      setMenyunting(null);
      setDraf("");
      await Promise.all([muatPesan(), muatPercakapan()]);
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Gagal menyunting",
        message: (galat as { error?: string })?.error ?? "Coba lagi sebentar.",
      });
    } finally {
      setMengirim(false);
    }
  };

  const hapus = async (p: TPesan) => {
    if (!slug) return;
    try {
      await chatService.hapusPesan(slug, p.id);
      // Riwayat lama disimpan terpisah dari SWR, jadi harus ikut dibersihkan.
      setLama((sebelumnya) => sebelumnya.filter((x) => x.id !== p.id));
      await Promise.all([muatPesan(), muatPercakapan()]);
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Gagal menghapus",
        message: (galat as { error?: string })?.error ?? "Coba lagi sebentar.",
      });
    }
  };

  const reaksi = async (p: TPesan, emoji: string) => {
    if (!slug) return;
    try {
      await chatService.toggleReaksi(slug, p.id, emoji);
      await muatPesan();
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Gagal memberi reaksi" });
    }
  };

  const kirim = async () => {
    const isi = draf.trim();
    // Boleh mengirim tanpa teks asal ada lampiran.
    if ((!isi && lampiran.length === 0) || !slug || (!dengan && !ruangParam) || mengirim || mengunggah) return;
    setMengirim(true);
    try {
      const berkas = lampiran.map((l) => l.id);
      if (ruangParam) await chatService.kirimPesanRuang(slug, ruangParam, isi, berkas, membalas?.id);
      else await chatService.kirimPesan(slug, dengan as string, isi, berkas, membalas?.id);
      setDraf("");
      setLampiran([]);
      setMembalas(null);
      if (tulisRef.current) tulisRef.current.style.height = "auto";
      await Promise.all([muatPesan(), muatPercakapan()]);
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Pesan gagal terkirim",
        message: (galat as { error?: string })?.error ?? "Coba lagi sebentar.",
      });
    } finally {
      setMengirim(false);
    }
  };

  // Fokus masuk ke dialog begitu ia terbuka. Tanpa ini, pembaca layar tetap
  // berada di tombol pemanggil dan isi dialog seolah tidak pernah muncul.
  useEffect(() => {
    if (buatTerbuka) namaKanalRef.current?.focus();
  }, [buatTerbuka]);

  const panggilan = usePanggilan({
    slug,
    ruangId: ruangSaatIni,
    kirimSinyal,
    onGagal: (pesanGalat) => setToast({ type: TOAST_TYPE.ERROR, title: "Panggilan gagal", message: pesanGalat }),
  });
  // Soket dibuat lebih dulu daripada hook panggilan, jadi callback-nya tidak
  // bisa menunjuk `panggilan` secara langsung. Ref ini yang menjembatani.
  panggilanRef.current = panggilan;

  const kanalAktif = (daftarKanal ?? []).find((r) => r.id === ruangParam);
  const kanalDiikuti = (daftarKanal ?? []).filter((r) => r.ikut);
  const kanalBelumDiikuti = (daftarKanal ?? []).filter((r) => !r.ikut);

  const buatKanal = async () => {
    const nama = namaKanal.trim();
    if (!slug || !nama || membuat) return;
    setMembuat(true);
    try {
      const dibuat = await chatService.buatRuang(slug, nama, kanalPrivat ? "privat" : "kanal");
      setNamaKanal("");
      setKanalPrivat(false);
      setBuatTerbuka(false);
      await Promise.all([muatKanal(), muatPercakapan()]);
      setSearchParams({ ruang: dibuat.id });
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Kanal gagal dibuat",
        message: (galat as { error?: string })?.error ?? "Coba lagi sebentar.",
      });
    } finally {
      setMembuat(false);
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
        title: "Gagal bergabung",
        message: (galat as { error?: string })?.error ?? "Coba lagi sebentar.",
      });
    }
  };

  const keluar = async (ruangId: string) => {
    if (!slug) return;
    try {
      await chatService.keluarRuang(slug, ruangId);
      await Promise.all([muatKanal(), muatPercakapan()]);
      setSearchParams({});
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Gagal keluar kanal",
        message: (galat as { error?: string })?.error ?? "Coba lagi sebentar.",
      });
    }
  };

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
          <div className="focus-within:border-accent-primary flex flex-1 items-center gap-2 rounded-md border border-subtle px-2.5 py-1.5">
            <Search className="size-3.5 shrink-0 text-tertiary" />
            <input
              type="text"
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
              placeholder="Cari orang, Enter untuk cari isi pesan"
              aria-label="Cari orang atau isi pesan"
              className="text-sm w-full bg-transparent text-primary outline-none placeholder:text-placeholder"
            />
            {cari.trim().length >= 3 ? (
              <button
                type="button"
                onClick={() => void cariIsiPesan()}
                disabled={mencari}
                aria-label="Cari isi pesan"
                title="Cari isi pesan"
                className="text-xs shrink-0 rounded px-1.5 py-0.5 font-medium text-accent-primary hover:bg-layer-1 disabled:opacity-50"
              >
                {mencari ? "…" : "Isi"}
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
                <p className="text-xs font-semibold tracking-wide text-tertiary uppercase">Kanal</p>
                <div className="flex items-center gap-0.5">
                  <button
                    type="button"
                    onClick={() => setJelajah(true)}
                    title="Jelajahi kanal"
                    className="flex size-6 items-center justify-center rounded text-tertiary hover:bg-layer-1 hover:text-secondary"
                  >
                    <Compass className="size-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setBuatTerbuka(true)}
                    title="Buat kanal"
                    className="flex size-6 items-center justify-center rounded text-tertiary hover:bg-layer-1 hover:text-secondary"
                  >
                    <Plus className="size-3.5" />
                  </button>
                </div>
              </div>
              {kanalDiikuti.length === 0 ? (
                <p className="text-xs px-3 pb-1.5 text-tertiary">Belum ikut kanal mana pun.</p>
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
                        className={`text-sm min-w-0 flex-1 truncate text-primary ${
                          adaBaru ? "font-semibold" : "font-normal"
                        }`}
                      >
                        {r.nama}
                      </span>
                      {adaBaru ? (
                        <span className="text-xs shrink-0 rounded-full bg-accent-primary px-1.5 font-medium text-white">
                          {r.belum_dibaca}
                        </span>
                      ) : null}
                    </button>
                  );
                })
              )}
            </div>
          ) : null}
          {hasilCari ? (
            <div>
              <div className="flex items-center justify-between px-3 py-2">
                <p className="text-xs font-medium text-secondary">
                  {hasilCari.length === 0 ? "Tidak ada pesan yang cocok" : `${hasilCari.length} pesan ditemukan`}
                </p>
                <button
                  type="button"
                  onClick={() => setHasilCari(null)}
                  className="text-xs text-tertiary hover:text-primary"
                >
                  Tutup
                </button>
              </div>
              {hasilCari.map((h) => {
                // Pesan kanal tidak punya lawan bicara. Judulnya diambil dari
                // nama kanal, dan membukanya lewat id ruang.
                const anggota = h.lawan_bicara ? getWorkspaceMemberDetails(h.lawan_bicara)?.member : undefined;
                const kanal = (daftarKanal ?? []).find((r) => r.id === h.ruang);
                const judul = anggota?.display_name ?? kanal?.nama ?? "Percakapan";
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
                    <span className="text-xs flex w-full items-center justify-between gap-2">
                      <span className="truncate font-medium text-primary">{judul}</span>
                      <span className="shrink-0 text-tertiary">{waktuRingkas(h.created_at)}</span>
                    </span>
                    <span className="text-xs line-clamp-2 text-secondary">
                      {h.dari_saya ? "Kamu: " : ""}
                      {h.isi}
                    </span>
                  </button>
                );
              })}
            </div>
          ) : daftar.length === 0 ? (
            <p className="text-sm p-3 text-tertiary">Tidak ada orang yang cocok.</p>
          ) : (
            daftar.map(({ id, terakhir }) => {
              const anggota = getWorkspaceMemberDetails(id)?.member;
              const terpilih = id === dengan;
              const adaBaru = (terakhir?.belum_dibaca ?? 0) > 0;
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => setSearchParams({ dengan: id })}
                  className={`flex w-full items-center gap-2.5 px-3 py-2.5 text-left hover:bg-layer-1 ${
                    terpilih ? "bg-layer-1-selected" : ""
                  }`}
                >
                  <Avatar
                    name={anggota?.display_name}
                    src={getFileURL(anggota?.avatar_url ?? "")}
                    size={32}
                    shape="circle"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      {/* Belum dibaca ditandai tebal, bukan cuma lencana. Angka
                          saja mudah terlewat saat menyapu daftar dengan mata. */}
                      <p className={`text-sm truncate text-primary ${adaBaru ? "font-semibold" : "font-medium"}`}>
                        {anggota?.display_name ?? "Anggota"}
                      </p>
                      {terakhir ? (
                        <span className={`text-xs shrink-0 ${adaBaru ? "text-accent-primary" : "text-tertiary"}`}>
                          {waktuRingkas(terakhir.created_at)}
                        </span>
                      ) : null}
                    </div>
                    <div className="mt-0.5 flex items-center justify-between gap-2">
                      <p className={`text-xs truncate ${adaBaru ? "font-medium text-secondary" : "text-tertiary"}`}>
                        {terakhir
                          ? `${terakhir.dari_saya ? "Kamu: " : ""}${terakhir.isi || "mengirim lampiran"}`
                          : "Belum ada pesan"}
                      </p>
                      {adaBaru ? (
                        <span className="text-xs shrink-0 rounded-full bg-accent-primary px-1.5 font-medium text-white">
                          {terakhir?.belum_dibaca}
                        </span>
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
      <section className={cn("flex min-w-0 flex-1 flex-col", !adaPercakapanTerbuka && "hidden lg:flex")}>
        {!dengan && !ruangParam ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-tertiary">
            <MessageSquare className="size-10" strokeWidth={1.25} />
            <div className="text-center">
              <p className="text-sm font-medium text-secondary">Belum ada percakapan yang dibuka</p>
              <p className="text-xs mt-1">Pilih orang di sebelah kiri untuk mulai mengobrol.</p>
            </div>
          </div>
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
                className="-ml-1.5 grid size-9 shrink-0 place-items-center rounded-sm text-secondary hover:bg-layer-1 hover:text-primary lg:hidden"
                aria-label="Kembali ke daftar percakapan"
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
                  <p className="text-sm font-medium text-primary">{kanalAktif?.nama ?? "Kanal"}</p>
                  {kanalAktif?.topik ? <p className="text-xs truncate text-tertiary">{kanalAktif.topik}</p> : null}
                  {/* Panggilan kanal = konferensi. Tidak berdering ke satu orang;
                      undangannya disiarkan ke anggota yang sedang membuka kanal
                      ini, lalu mereka memutuskan sendiri mau gabung atau tidak.
                      Meneleponkan dering ke belasan orang sekaligus akan jadi
                      gangguan, bukan fitur. */}
                  <div className="ml-auto flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => void panggilan.mulaiKonferensi(false)}
                      disabled={!tersambung || panggilan.status !== "diam"}
                      title={tersambung ? "Mulai panggilan suara di kanal" : "Sambungan real-time sedang putus"}
                      aria-label="Panggilan suara kanal"
                      className="flex size-8 items-center justify-center rounded-md text-tertiary hover:bg-layer-1 hover:text-secondary disabled:opacity-40"
                    >
                      <Phone className="size-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => void panggilan.mulaiKonferensi(true)}
                      disabled={!tersambung || panggilan.status !== "diam"}
                      title={tersambung ? "Mulai panggilan video di kanal" : "Sambungan real-time sedang putus"}
                      aria-label="Panggilan video kanal"
                      className="flex size-8 items-center justify-center rounded-md text-tertiary hover:bg-layer-1 hover:text-secondary disabled:opacity-40"
                    >
                      <Video className="size-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => keluar(ruangParam as string)}
                      className="text-xs rounded-md px-2 py-1 text-tertiary hover:bg-layer-1 hover:text-secondary"
                    >
                      Keluar kanal
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <Avatar
                    name={lawanBicara?.display_name}
                    src={getFileURL(lawanBicara?.avatar_url ?? "")}
                    size={32}
                    shape="circle"
                  />
                  <p className="text-sm font-medium text-primary">{lawanBicara?.display_name ?? "Anggota"}</p>
                  {/* Panggilan hanya untuk DM. Untuk kanal butuh SFU, dan itu
                      pekerjaan lain. Tombolnya mati kalau soket sedang putus,
                      karena tanpa jalur sinyal panggilan tidak akan tersambung
                      dan yang menekan cuma menunggu tanpa tahu sebabnya. */}
                  <div className="ml-auto flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => dengan && void panggilan.panggil(dengan, false)}
                      disabled={!tersambung || panggilan.status !== "diam"}
                      title={tersambung ? "Panggilan suara" : "Sambungan real-time sedang putus"}
                      aria-label="Panggilan suara"
                      className="flex size-8 items-center justify-center rounded-md text-tertiary hover:bg-layer-1 hover:text-secondary disabled:opacity-40"
                    >
                      <Phone className="size-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => dengan && void panggilan.panggil(dengan, true)}
                      disabled={!tersambung || panggilan.status !== "diam"}
                      title={tersambung ? "Panggilan video" : "Sambungan real-time sedang putus"}
                      aria-label="Panggilan video"
                      className="flex size-8 items-center justify-center rounded-md text-tertiary hover:bg-layer-1 hover:text-secondary disabled:opacity-40"
                    >
                      <Video className="size-4" />
                    </button>
                  </div>
                </>
              )}
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-3">
              {/* Tombol riwayat hanya muncul kalau memang ada kemungkinan ada
                  yang lebih lama, dan menghilang setelah server bilang habis. */}
              {barisPesan.length > 0 && !habis ? (
                <div className="mb-2 flex justify-center">
                  <button
                    type="button"
                    onClick={() => void muatLama()}
                    disabled={memuatLama}
                    className="text-xs flex items-center gap-1.5 rounded-full border border-subtle px-3 py-1 text-secondary hover:bg-layer-1 disabled:opacity-50"
                  >
                    <ChevronUp className="size-3.5" />
                    {memuatLama ? "Memuat…" : "Muat pesan lama"}
                  </button>
                </div>
              ) : null}

              {barisPesan.length === 0 ? (
                <p className="text-sm text-tertiary">Belum ada pesan. Mulai dari sini.</p>
              ) : (
                <div className="flex flex-col">
                  {barisPesan.map((baris) => {
                    if (baris.jenis === "tanggal")
                      return (
                        <div key={baris.kunci} className="my-3 flex items-center justify-center">
                          <span className="text-xs rounded-full bg-layer-3 px-2.5 py-1 font-medium text-secondary">
                            {baris.label}
                          </span>
                        </div>
                      );

                    if (baris.jenis === "belum-dibaca")
                      return (
                        <div key={baris.kunci} className="my-3 flex items-center gap-2">
                          <div className="h-px flex-1 bg-accent-primary/40" />
                          <span className="text-xs font-medium text-accent-primary">Pesan belum dibaca</span>
                          <div className="h-px flex-1 bg-accent-primary/40" />
                        </div>
                      );

                    const { pesan: p, dariSaya, awalKelompok, akhirKelompok } = baris;
                    return (
                      <div
                        key={baris.kunci}
                        className={`flex items-end gap-2 ${awalKelompok ? "mt-2" : "mt-0.5"} ${
                          dariSaya ? "justify-end" : "justify-start"
                        }`}
                      >
                        {!dariSaya ? (
                          <div className="w-7 shrink-0">
                            {awalKelompok ? (
                              <Avatar
                                name={lawanBicara?.display_name}
                                src={getFileURL(lawanBicara?.avatar_url ?? "")}
                                size={28}
                                shape="circle"
                              />
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
                              ? "Kamu"
                              : (getWorkspaceMemberDetails(id)?.member?.display_name ?? "Anggota")
                          }
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
                          onHapus={(pesanIni) => void hapus(pesanIni)}
                          onReaksi={(pesanIni, emoji) => void reaksi(pesanIni, emoji)}
                        />
                      </div>
                    );
                  })}
                </div>
              )}
              <div ref={akhirRef} />
            </div>

            <div className="flex flex-col gap-2 border-t border-subtle p-3">
              {membalas || menyunting ? (
                <div className="border-accent-primary flex items-start gap-2 rounded-md border-l-2 bg-layer-1 px-2.5 py-1.5">
                  <div className="min-w-0 flex-1">
                    <p className="text-xs flex items-center gap-1 font-medium text-accent-primary">
                      {menyunting ? <Pencil className="size-3" /> : <CornerUpLeft className="size-3" />}
                      {menyunting ? "Menyunting pesan" : `Membalas ${lawanBicara?.display_name ?? "pesan"}`}
                    </p>
                    <p className="text-xs truncate text-tertiary">{(menyunting ?? membalas)?.isi || "lampiran"}</p>
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
                    aria-label="Batal"
                    className="text-tertiary hover:text-primary"
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
                      className="text-xs flex items-center gap-1.5 rounded-md border border-subtle px-2 py-1 text-secondary"
                    >
                      <span className="max-w-40 truncate">{l.nama}</span>
                      <span className="text-tertiary">{ukuranTerbaca(l.ukuran)}</span>
                      <button
                        type="button"
                        onClick={() => setLampiran((s2) => s2.filter((x) => x.id !== l.id))}
                        aria-label={`Buang ${l.nama}`}
                        className="text-tertiary hover:text-primary"
                      >
                        <X className="size-3" />
                      </button>
                    </span>
                  ))}
                  {mengunggah ? <span className="text-xs text-tertiary">Mengunggah…</span> : null}
                </div>
              ) : null}
              <div className="flex items-end gap-2">
                <input ref={berkasRef} type="file" multiple hidden onChange={(e) => void unggah(e.target.files)} />
                <button
                  type="button"
                  onClick={() => berkasRef.current?.click()}
                  disabled={mengunggah}
                  aria-label="Lampirkan berkas"
                  className="flex size-9 items-center justify-center rounded-md text-tertiary hover:bg-layer-1 hover:text-secondary disabled:opacity-40"
                >
                  <Paperclip className="size-4" />
                </button>
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
                      className="flex size-9 items-center justify-center rounded-md text-tertiary hover:bg-layer-1 hover:text-secondary"
                      aria-label="Sisipkan emoji"
                    >
                      <SmilePlus className="size-4" />
                    </span>
                  }
                />
                <textarea
                  ref={tulisRef}
                  value={draf}
                  onChange={(e) => {
                    setDraf(e.target.value);
                    aturTinggiTulis();
                  }}
                  onKeyDown={(e) => {
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
                  placeholder="Tulis pesan"
                  aria-label="Tulis pesan"
                  className="text-sm focus:border-accent-primary min-h-9 flex-1 resize-none rounded-md border border-subtle bg-transparent px-3 py-2 text-primary outline-none placeholder:text-placeholder"
                />
                <button
                  type="button"
                  onClick={() => void (menyunting ? simpanSuntingan() : kirim())}
                  disabled={
                    mengirim ||
                    mengunggah ||
                    (menyunting ? draf.trim().length === 0 : draf.trim().length === 0 && lampiran.length === 0)
                  }
                  aria-label="Kirim pesan"
                  className="flex size-9 items-center justify-center rounded-md bg-accent-primary text-white disabled:opacity-40"
                >
                  <Send className="size-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </section>

      {/* Ajakan gabung, bukan dering. Muncul untuk yang sedang membuka ruang
          saat orang lain memulai panggilan di sana. */}
      {panggilan.konferensiBerjalan && panggilan.status === "diam" ? (
        <div className="shadow-lg fixed bottom-6 left-1/2 z-30 flex -translate-x-1/2 items-center gap-3 rounded-full border border-subtle bg-layer-3 px-4 py-2">
          <span className="text-sm text-primary">Ada panggilan berlangsung di sini</span>
          <button
            type="button"
            onClick={() => void panggilan.mulaiKonferensi(panggilan.pakaiVideo)}
            className="text-xs rounded-full bg-accent-primary px-3 py-1.5 font-medium text-white"
          >
            Gabung
          </button>
        </div>
      ) : null}

      <PanggilanLayar
        status={panggilan.status}
        koneksi={panggilan.koneksi}
        judul={
          adalahKanal
            ? (kanalAktif?.nama ?? "Kanal")
            : ((panggilan.lawan ? getWorkspaceMemberDetails(panggilan.lawan)?.member?.display_name : undefined) ??
              "Anggota")
        }
        pakaiVideo={panggilan.pakaiVideo}
        mikMati={panggilan.mikMati}
        kameraMati={panggilan.kameraMati}
        streamLokal={panggilan.streamLokal}
        pesertaJauh={panggilan.pesertaJauh}
        byteMasuk={panggilan.byteMasuk}
        onAngkat={() => void panggilan.angkat()}
        onTutup={panggilan.tutup}
        onSetelMik={panggilan.setelMik}
        onSetelKamera={panggilan.setelKamera}
      />

      {/* Buat kanal */}
      {buatTerbuka ? (
        <div className="fixed inset-0 z-30 flex items-center justify-center bg-black/40 p-4">
          <div className="shadow-lg w-full max-w-sm rounded-lg border border-subtle bg-layer-3 p-4">
            <p className="text-sm font-semibold text-primary">Kanal baru</p>
            <input
              ref={namaKanalRef}
              type="text"
              value={namaKanal}
              onChange={(e) => setNamaKanal(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void buatKanal();
                if (e.key === "Escape") setBuatTerbuka(false);
              }}
              maxLength={80}
              placeholder="nama-kanal"
              className="text-sm focus:border-accent-primary mt-3 w-full rounded-md border border-subtle bg-layer-1 px-2.5 py-1.5 text-primary outline-none"
            />
            <label className="text-xs mt-3 flex cursor-pointer items-center gap-2 text-secondary">
              <input type="checkbox" checked={kanalPrivat} onChange={(e) => setKanalPrivat(e.target.checked)} />
              Kanal privat, hanya yang diundang bisa melihat
            </label>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setBuatTerbuka(false)}
                className="text-xs rounded-md px-3 py-1.5 text-secondary hover:bg-layer-1"
              >
                Batal
              </button>
              <button
                type="button"
                onClick={() => void buatKanal()}
                disabled={!namaKanal.trim() || membuat}
                className="text-xs rounded-md bg-accent-primary px-3 py-1.5 font-medium text-white disabled:opacity-50"
              >
                {membuat ? "Membuat..." : "Buat"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Jelajahi kanal publik yang belum diikuti */}
      {jelajah ? (
        <div className="fixed inset-0 z-30 flex items-center justify-center bg-black/40 p-4">
          <div className="shadow-lg flex max-h-[70vh] w-full max-w-sm flex-col rounded-lg border border-subtle bg-layer-3 p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-primary">Kanal yang bisa diikuti</p>
              <button
                type="button"
                onClick={() => setJelajah(false)}
                className="text-xs text-tertiary hover:text-primary"
              >
                Tutup
              </button>
            </div>
            <div className="mt-3 flex-1 overflow-y-auto">
              {kanalBelumDiikuti.length === 0 ? (
                <p className="text-xs text-tertiary">Tidak ada kanal lain untuk saat ini.</p>
              ) : (
                kanalBelumDiikuti.map((r) => (
                  <div key={r.id} className="flex items-center gap-2 py-1.5">
                    <Hash className="size-3.5 shrink-0 text-tertiary" />
                    <span className="text-sm min-w-0 flex-1 truncate text-primary">{r.nama}</span>
                    <button
                      type="button"
                      onClick={() => void gabung(r.id)}
                      className="text-xs shrink-0 rounded-md border border-subtle px-2 py-1 text-secondary hover:bg-layer-1"
                    >
                      Gabung
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default observer(ChatPage);
