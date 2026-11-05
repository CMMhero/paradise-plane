/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: gelembung pesan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import { useState } from "react";
import { Link, useParams } from "react-router";
import useSWR from "swr";
import type { LucideIcon } from "lucide-react";
import {
  Check,
  CheckCheck,
  Copy,
  CornerUpLeft,
  MoreHorizontal,
  Pencil,
  Lock,
  Pin,
  PinOff,
  Plus,
  SmilePlus,
  Trash2,
} from "lucide-react";
import { ContextMenu } from "@plane/propel/context-menu";
import { stringToEmoji } from "@plane/propel/emoji-icon-picker";
import { EmojiReactionPicker } from "@plane/propel/emoji-reaction";
import { Menu } from "@plane/propel/menu";
import { HoverCard } from "@plane/propel/popover";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { cn, renderFormattedTime } from "@plane/utils";
import { MemberProfileTrigger } from "@/components/member-profile";
import { KanalPreviewCard, TugasPreviewCard } from "@/components/rujukan-preview";
import { PratinjauTautanTeks } from "@/components/pratinjau-tautan/kartu";
import { ChatService } from "@/services/chat.service";
import type { TKanalDirujuk, TPesan, TTugasDirujuk } from "@/services/chat.service";
import { KartuPesan, adalahKartu } from "./kartu/kartu-pesan";
import { bolehDihapus } from "./batas-hapus";
import { KutipanBalasan } from "./kutipan-balasan";
import { DaftarLampiran } from "./lampiran";
import { potongRujukan } from "./sebut";
import { salinTeks } from "./salin";
import { alihkanReaksi, buatPenyaringGanda } from "./reaksi";
import { potongTautan } from "./tautan";

/**
 * Teks pesan dengan alamat yang bisa diklik.
 *
 * Dibuat karena penugasan sekarang otomatis masuk ke DM berikut tautan ke
 * tugasnya. Tautan yang harus disalin-tempel dulu adalah tautan yang tidak
 * dipakai, dan tugas yang tidak dibuka sama saja dengan tugas yang tidak
 * dikabarkan.
 *
 * Potongan bukan-alamat tetap teks React, tidak pernah lewat
 * `dangerouslySetInnerHTML`. Aturan alamat mana yang boleh jadi tautan, berikut
 * alasan keamanannya, ada di `tautan.ts`.
 */
const denganTautan = (teks: string) =>
  potongTautan(teks).map((potongan, i) =>
    potongan.jenis === "teks" ? (
      potongan.isi
    ) : (
      // Kunci dari posisi, dan di sini itu memang benar: potongannya lahir dari
      // memecah satu teks yang tidak pernah berubah sebagian. Seluruh daftar
      // dibuat ulang kalau isinya berganti, tidak ada yang bisa disisipkan atau
      // diurut ulang, dan anak-anaknya tidak menyimpan state apa pun.
      // oxlint-disable-next-line no-array-index-key
      <span key={`tautan-${i}`}>
        <a
          href={potongan.alamat}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="underline underline-offset-2 hover:opacity-80"
        >
          {potongan.alamat}
        </a>
        {potongan.ekor}
      </span>
    )
  );

/** ID yang disebut di pesan ini (`muatan.sebut`), dibaca tanpa percaya bentuknya. */
const idSebutan = (pesan: TPesan): string[] => {
  const daftar = (pesan.muatan as { sebut?: unknown } | undefined)?.sebut;
  return Array.isArray(daftar) ? daftar.filter((v): v is string => typeof v === "string") : [];
};

/** Rujukan di muatan pesan (KEP-91), dibaca tanpa percaya bentuknya. */
type TRujukanPesan = { semua: boolean; kanal: TKanalDirujuk[]; tugas: TTugasDirujuk[] };
const saringRujukan = <T,>(v: unknown, sah: (x: Record<string, unknown>) => boolean): T[] =>
  Array.isArray(v) ? ((v as Record<string, unknown>[]).filter((x) => x && typeof x === "object" && sah(x)) as T[]) : [];
const rujukanPesan = (pesan: TPesan): TRujukanPesan => {
  const m = (pesan.muatan ?? {}) as { semua?: unknown; kanal?: unknown; tugas?: unknown };
  return {
    semua: m.semua === true,
    kanal: saringRujukan<TKanalDirujuk>(m.kanal, (x) => typeof x.id === "string" && typeof x.nama === "string"),
    tugas: saringRujukan<TTugasDirujuk>(m.tugas, (x) => typeof x.id === "string" && typeof x.nomor === "string"),
  };
};

const chatService = new ChatService();

const KELAS_PIL_RUJUKAN = "rounded-sm px-1 font-semibold hover:opacity-85";
const gayaRujukan = (terang: boolean) =>
  cn(KELAS_PIL_RUJUKAN, terang ? "bg-white/25 text-on-color" : "bg-layer-1 text-accent-primary");

/** Pil `#kanal`. Kanal privat yang tidak bisa dibuka penonton: gembok, tanpa tautan. */
function PilKanal({ kanal, slug, terang }: { kanal: TKanalDirujuk; slug: string | undefined; terang: boolean }) {
  const { t } = useTranslation();
  if (!kanal.boleh || !slug) {
    return (
      <HoverCard content={<KanalPreviewCard id={kanal.id} />}>
        <span className={cn(gayaRujukan(terang), "inline-flex items-center gap-0.5 align-baseline")}>
          <Lock className="size-3" />
          {t("rujukan_ui.private_channel")}
        </span>
      </HoverCard>
    );
  }
  return (
    <HoverCard content={<KanalPreviewCard id={kanal.id} />}>
      <Link
        to={`/${slug}/chat/?ruang=${kanal.id}`}
        onClick={(e) => e.stopPropagation()}
        aria-label={t("rujukan_ui.open_channel")}
        className={cn(gayaRujukan(terang), "align-baseline")}
      >
        #{kanal.nama}
      </Link>
    </HoverCard>
  );
}

/** Pil `#PRJ-12`. Judul diambil malas lewat `infoRujukan`; tanpa akses: gembok, tanpa tautan. */
function PilTugas({
  tugas,
  slug,
  judul,
  boleh,
  terang,
}: {
  tugas: TTugasDirujuk;
  slug: string | undefined;
  judul: string | undefined;
  boleh: boolean;
  terang: boolean;
}) {
  if (!boleh || !slug) {
    return (
      <HoverCard content={<TugasPreviewCard id={tugas.id} />}>
        <span className={cn(gayaRujukan(terang), "inline-flex items-center gap-0.5 align-baseline")}>
          <Lock className="size-3" />
          {tugas.nomor}
        </span>
      </HoverCard>
    );
  }
  return (
    <HoverCard content={<TugasPreviewCard id={tugas.id} />}>
      <Link
        to={`/${slug}/browse/${tugas.nomor}/`}
        onClick={(e) => e.stopPropagation()}
        aria-label={judul ? `${tugas.nomor} ${judul}` : tugas.nomor}
        className={cn(gayaRujukan(terang), "align-baseline")}
      >
        #{tugas.nomor}
      </Link>
    </HoverCard>
  );
}

/**
 * Teks pesan dengan `@nama`, `@all`, `#kanal`, dan `#PRJ-12` yang disorot, lalu
 * tautan di potongan sisanya.
 *
 * Yang disorot HANYA yang memang tercatat di muatan pesan (sudah disaring server
 * ke anggota ruang dan ke yang boleh dilihat). Mengetik `@siapa` tanpa memilih dari
 * daftar tetap teks biasa, supaya sorotan tidak menjanjikan pemberitahuan yang
 * tidak pernah dikirim.
 */
const denganRujukan = (
  teks: string,
  ctx: {
    orang: { id: string; nama: string }[];
    rujukan: TRujukanPesan;
    sayaId: string | undefined;
    terang: boolean;
    slug: string | undefined;
    infoTugas: Record<string, { boleh: boolean; judul?: string }> | undefined;
  }
) =>
  potongRujukan(teks, {
    orang: ctx.orang,
    kanal: ctx.rujukan.kanal,
    tugas: ctx.rujukan.tugas,
    semua: ctx.rujukan.semua,
  }).map((potongan, i) => {
    // oxlint-disable-next-line no-array-index-key -- potongan dari satu teks yang tidak pernah diurut ulang
    const kunci = `${potongan.jenis}-${i}`;
    switch (potongan.jenis) {
      case "teks":
        return <span key={kunci}>{denganTautan(potongan.isi)}</span>;
      case "sebut":
        return (
          <MemberProfileTrigger key={kunci} userId={potongan.id} className="align-baseline" openOnHover>
            <span className={gayaSebutan(ctx.terang, !!ctx.sayaId && potongan.id === ctx.sayaId)}>{potongan.isi}</span>
          </MemberProfileTrigger>
        );
      case "semua":
        // @all juga memberi tahu saya, jadi rupanya sama dengan sebutan ke saya.
        return (
          <span key={kunci} className={gayaSebutan(ctx.terang, true)}>
            {potongan.isi}
          </span>
        );
      case "kanal": {
        const kanal = ctx.rujukan.kanal.find((k) => k.id === potongan.id);
        return kanal ? <PilKanal key={kunci} kanal={kanal} slug={ctx.slug} terang={ctx.terang} /> : null;
      }
      case "tugas": {
        const tugas = ctx.rujukan.tugas.find((w) => w.id === potongan.id);
        const info = ctx.infoTugas?.[potongan.id];
        return tugas ? (
          <PilTugas
            key={kunci}
            tugas={tugas}
            slug={ctx.slug}
            judul={info?.judul}
            boleh={info?.boleh !== false}
            terang={ctx.terang}
          />
        ) : null;
      }
    }
  });

/**
 * Tiga rupa sebutan, sengaja beda jelas satu sama lain:
 * - saya disebut orang lain: pil amber pekat, paling mencolok;
 * - saya menyebut orang (gelembung keluar): pil putih transparan di atas aksen;
 * - orang lain disebut di pesan masuk: pil aksen lembut.
 */
const gayaSebutan = (terang: boolean, sayaDisebut: boolean) =>
  cn(
    "rounded-sm px-1 font-semibold hover:opacity-85",
    terang
      ? "bg-white/25 text-on-color"
      : sayaDisebut
        ? "bg-warning-primary text-on-color"
        : "bg-accent-subtle text-accent-primary"
  );

/** Reaksi cepat, baris yang sama dengan WhatsApp/Instagram supaya tidak perlu
 * dipelajari. Emoji lain tetap bisa lewat tombol "+" (pemilih penuh). */
export const REAKSI_CEPAT = ["👍", "❤️", "😂", "😮", "😢", "🙏", "✅"];

/** Satu aksi pesan. Ditulis sekali, dirender di dua tempat: menu klik kanan /
 * tekan lama, dan menu tombol "..." yang muncul saat gelembung diarahkan. */
type TAksi = { kunci: string; label: string; ikon: LucideIcon; jalankan: () => void; bahaya?: boolean };

type Props = {
  pesan: TPesan;
  dariSaya: boolean;
  awalKelompok: boolean;
  akhirKelompok: boolean;
  sayaId?: string;
  namaOrang: (id: string) => string;
  /** Nama tampilan asli, TANPA ganti "Anda" untuk diri sendiri. Dipakai mencocokkan
   * `@nama` di teks: teks pesan memuat nama asli, bukan "Anda". */
  namaSebutan: (id: string) => string;
  /** Klik kutipan balasan: lompat ke pesan aslinya. */
  onBukaKutipan?: (pesanId: string) => void;
  onBalas?: (pesan: TPesan) => void;
  onSunting?: (pesan: TPesan) => void;
  onHapus?: (pesan: TPesan) => void;
  /** Batas umur hapus dari God Mode (jam). 0 atau tidak ada = tanpa batas. */
  batasHapusJam?: number;
  /** `reaksiBaru` = daftar reaksi sesudah tombol ini (lihat `alihkanReaksi`),
   * untuk pemanggil yang menyimpan pesan di luar SWR (riwayat lama). */
  onReaksi?: (pesan: TPesan, emoji: string, reaksiBaru: TPesan["reaksi"]) => void;
  /** Sematkan (true) atau lepas (false). Tidak diisi = orang ini tidak boleh
   * menyematkan di ruang ini, tombolnya tidak ditawarkan. */
  onSematkan?: (pesan: TPesan, sematkan: boolean) => void;
  /** Telepon balik dari kartu log panggilan. */
  onTelepon?: (video: boolean) => void;
};

export function Gelembung(props: Props) {
  const { t } = useTranslation();
  const { pesan, dariSaya, awalKelompok, akhirKelompok, sayaId, namaOrang } = props;
  // Menu aksi (klik kanan / tekan lama), pemilih emoji penuh, dan menu "...".
  // Dua yang terakhir menahan tombol melayang tetap tampak selama terbuka.
  const [menuBuka, setMenuBuka] = useState(false);
  const [pemilihPenuh, setPemilihPenuh] = useState(false);
  const [menuTitikBuka, setMenuTitikBuka] = useState(false);
  // Satu gestur = satu aksi. Di Windows satu klik pada item menu konteks
  // memanggil onClick DUA kali (lihat JENDELA_GEMA_KLIK_MS); tanpa ini reaksi
  // ditambah lalu langsung dibatalkan, dan sematan bolak-balik.
  const [bolehJalan] = useState(() => buatPenyaringGanda());
  const dihapus = !!pesan.dihapus;
  const disematkan = !!pesan.disematkan;

  const beriReaksi = (emoji: string) => {
    setMenuBuka(false);
    if (!bolehJalan(`reaksi:${emoji}`)) return;
    props.onReaksi?.(pesan, emoji, sayaId ? alihkanReaksi(pesan.reaksi, emoji, sayaId) : pesan.reaksi);
  };
  const jalankanAksi = (a: TAksi) => {
    if (bolehJalan(`aksi:${a.kunci}`)) a.jalankan();
  };

  const salin = async () => {
    const berhasil = await salinTeks(pesan.isi);
    setToast(
      berhasil
        ? { type: TOAST_TYPE.SUCCESS, title: t("chat_ui.copied") }
        : { type: TOAST_TYPE.ERROR, title: t("chat_ui.copy_failed") }
    );
  };

  // Kartu (panggilan, tugas, persetujuan) yang SAYA picu berwarna sama dengan
  // gelembung keluar saya (permintaan user 5 Nov); kartunya menyesuaikan teks,
  // kotak, dan chip lewat `terang`. Kartu tanpa pengirim (catatan rilis, ruang
  // kabar) dan kartu dari orang lain tetap netral. Kartu tidak bisa disunting
  // atau dihapus, jadi izin ubah dihitung terpisah dari warnanya.
  const kartu = !dihapus && adalahKartu(pesan);
  const terang = dariSaya && !dihapus;
  const bolehUbah = terang && !kartu;
  // Nama asli, bukan namaOrang: untuk diri sendiri namaOrang memberi "Anda",
  // padahal teksnya "@NamaSaya". Dulu ini yang membuat sebutan ke saya tidak
  // pernah tersorot.
  const disebut = idSebutan(pesan).map((id) => ({ id, nama: props.namaSebutan(id) }));
  const rujukan = rujukanPesan(pesan);
  const { workspaceSlug: slug } = useParams();
  // Judul work item diambil malas, satu permintaan per pesan; kuncinya ID terurut
  // supaya pesan yang merujuk hal yang sama berbagi hasilnya.
  // oxlint-disable-next-line unicorn/no-array-sort -- larik hasil map, aman diurut di tempat; toSorted tidak ada di lib TS
  const idTugas = rujukan.tugas.map((w) => w.id).sort();
  const { data: infoRujukan } = useSWR(
    slug && idTugas.length > 0 ? `CHAT_RUJUKAN_INFO_${slug}_${idTugas.join(",")}` : null,
    slug && idTugas.length > 0 ? () => chatService.infoRujukan(slug, [], idTugas) : null,
    { revalidateOnFocus: false }
  );
  const adaRujukan = disebut.length > 0 || rujukan.semua || rujukan.kanal.length > 0 || rujukan.tugas.length > 0;
  // Pesan masuk yang menyebut saya diberi bingkai amber supaya tertangkap mata
  // saat menggulir, bukan hanya sebutannya yang berwarna.
  const sayaDisebut = !dariSaya && !kartu && !!sayaId && (rujukan.semua || disebut.some((o) => o.id === sayaId));
  const gaya = dihapus
    ? "border border-subtle bg-layer-1 text-tertiary"
    : kartu && !dariSaya
      ? "border border-subtle bg-layer-1 text-primary"
      : dariSaya
        ? "bg-accent-primary text-on-color"
        : sayaDisebut
          ? "border-2 border-warning-strong bg-layer-3 text-primary"
          : "bg-layer-3 text-primary";
  const redup = terang ? "text-on-color/70" : "text-tertiary";
  // Server tetap menolak pesan yang lewat batas; ini hanya supaya tombolnya
  // tidak ditawarkan untuk aksi yang pasti gagal.
  const bolehHapus = bolehDihapus(pesan.created_at, props.batasHapusJam);

  // Urutan sama di kedua menu. Izin tetap dicek di sini: sematkan hanya kalau
  // onSematkan diisi, sunting dan hapus hanya pesan teks sendiri.
  const aksi: TAksi[] = [
    { kunci: "balas", label: t("chat_ui.reply"), ikon: CornerUpLeft, jalankan: () => props.onBalas?.(pesan) },
  ];
  if (pesan.isi) aksi.push({ kunci: "salin", label: t("chat_ui.copy"), ikon: Copy, jalankan: () => void salin() });
  if (props.onSematkan)
    aksi.push({
      kunci: "sematkan",
      label: disematkan ? t("chat_ui.unpin") : t("chat_ui.pin"),
      ikon: disematkan ? PinOff : Pin,
      jalankan: () => props.onSematkan?.(pesan, !disematkan),
    });
  if (bolehUbah)
    aksi.push({ kunci: "sunting", label: t("chat_ui.edit"), ikon: Pencil, jalankan: () => props.onSunting?.(pesan) });
  if (bolehUbah && bolehHapus)
    aksi.push({
      kunci: "hapus",
      label: t("chat_ui.delete"),
      ikon: Trash2,
      jalankan: () => props.onHapus?.(pesan),
      bahaya: true,
    });

  const isiGelembung = (
    <>
      {/* Nama pengirim di awal kelompok pesan masuk, seperti WhatsApp. Pesan
          sistem (pengirim kosong) sudah bernama lewat kartunya. */}
      {!dariSaya && awalKelompok && pesan.pengirim ? (
        <p className="mb-0.5 truncate text-12 font-semibold text-accent-primary">
          <MemberProfileTrigger userId={pesan.pengirim}>
            <span className="truncate hover:underline">{namaOrang(pesan.pengirim)}</span>
          </MemberProfileTrigger>
        </p>
      ) : null}

      {/* Kutipan pesan yang dibalas, DI DALAM gelembung supaya terbaca sebagai
          bagian dari pesan ini. Seluruh kutipan satu tombol yang melompat ke
          pesan aslinya, jadi nama di dalamnya sengaja teks biasa. */}
      {pesan.balasan_ke && !dihapus ? (
        <KutipanBalasan
          className="mb-1.5"
          nama={namaOrang(pesan.balasan_ke.pengirim)}
          isi={
            pesan.balasan_ke.dihapus ? t("chat_ui.message_deleted") : pesan.balasan_ke.isi || t("chat_ui.attachment")
          }
          miring={!!pesan.balasan_ke.dihapus}
          terang={terang}
          onBuka={() => pesan.balasan_ke && props.onBukaKutipan?.(pesan.balasan_ke.id)}
        />
      ) : null}

      {dihapus ? (
        <p className={`text-13 italic ${redup}`}>{t("chat_ui.message_deleted")}</p>
      ) : kartu ? (
        <KartuPesan pesan={pesan} namaOrang={namaOrang} onTelepon={props.onTelepon} terang={terang} />
      ) : pesan.isi ? (
        <p className="text-13 [overflow-wrap:anywhere] whitespace-pre-wrap">
          {adaRujukan
            ? denganRujukan(pesan.isi, { orang: disebut, rujukan, sayaId, terang, slug, infoTugas: infoRujukan?.tugas })
            : denganTautan(pesan.isi)}
        </p>
      ) : null}
      {!dihapus && !kartu && pesan.isi ? (
        // Margin bawah 6px + py-1.5 gelembung = 12px di bawah kartu, sama dengan
        // px-3 di sisinya. Kalau baris jam menyusul, jaraknya 6px + mt-0.5.
        <PratinjauTautanTeks teks={pesan.isi} terang={terang} className="my-1.5" />
      ) : null}
      {dihapus ? null : <DaftarLampiran lampiran={pesan.lampiran} terang={terang} />}

      {akhirKelompok || pesan.disunting || disematkan ? (
        <p className={`mt-0.5 flex items-center justify-end gap-1 text-11 ${redup}`}>
          {disematkan ? <Pin className="size-3" aria-label={t("chat_ui.pinned")} /> : null}
          {renderFormattedTime(pesan.created_at)}
          {pesan.disunting ? <span>· {t("chat_ui.edited")}</span> : null}
          {/* Tanda dibaca hanya untuk pesan KELUAR: pesan masuk jelas sudah kita baca. */}
          {terang ? pesan.sudah_dibaca ? <CheckCheck className="size-3.5" /> : <Check className="size-3.5" /> : null}
        </p>
      ) : null}
    </>
  );

  // Semua gelembung, termasuk kartu (panggilan, tugas, rilis) dan pesan yang
  // dihapus, memakai SATU radius kecil yang sama: `rounded-item`. Keputusan user
  // 5 Nov, tanpa pengecualian awal/akhir kelompok.
  const kelasGelembung = cn("relative block rounded-item px-3 py-1.5 text-left", gaya);
  const kelasTombolMelayang =
    "flex size-6 items-center justify-center rounded-button text-secondary hover:bg-layer-transparent-hover";

  return (
    <div className={cn("group flex max-w-[68%] min-w-0 flex-col", dariSaya ? "items-end" : "items-start")}>
      <div className="relative max-w-full">
        {dihapus ? (
          <div className={kelasGelembung}>{isiGelembung}</div>
        ) : (
          // Klik kanan, tekan lama di layar sentuh (ditangani Base UI), atau
          // Shift+F10 / tombol Menu saat gelembung difokus membuka menu yang sama.
          <ContextMenu open={menuBuka} onOpenChange={setMenuBuka}>
            <ContextMenu.Trigger
              tabIndex={0}
              className={cn(
                kelasGelembung,
                "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-strong",
                "sentuh:select-none sentuh:[-webkit-touch-callout:none]",
                menuBuka && "outline-2 outline-offset-2 outline-accent-strong"
              )}
            >
              {isiGelembung}
            </ContextMenu.Trigger>
            <ContextMenu.Portal>
              <ContextMenu.Content className="min-w-48" sideOffset={6}>
                <div className="flex items-center gap-0.5 pb-1">
                  {REAKSI_CEPAT.map((e) => {
                    const punyaSaya = !!sayaId && pesan.reaksi.some((r) => r.emoji === e && r.orang.includes(sayaId));
                    return (
                      <ContextMenu.Item
                        key={e}
                        onClick={() => beriReaksi(e)}
                        aria-label={t("chat_ui.react_with", { emoji: e })}
                        className={cn(
                          "size-8 justify-center rounded-button px-0 text-16 sentuh:size-10",
                          punyaSaya && "bg-accent-subtle"
                        )}
                      >
                        {e}
                      </ContextMenu.Item>
                    );
                  })}
                  <ContextMenu.Item
                    // Pemilih penuh dibuka SESUDAH menu tertutup; kalau bersamaan,
                    // klik ini terbaca sebagai klik di luar pemilih dan ia langsung tutup.
                    onClick={() => requestAnimationFrame(() => setPemilihPenuh(true))}
                    aria-label={t("chat_ui.more_reactions")}
                    className="size-8 justify-center rounded-button px-0 text-secondary sentuh:size-10"
                  >
                    <Plus className="size-4" />
                  </ContextMenu.Item>
                </div>
                <ContextMenu.Separator />
                {aksi.map((a) => (
                  <ContextMenu.Item
                    key={a.kunci}
                    onClick={() => jalankanAksi(a)}
                    className={cn("gap-2.5 sentuh:py-2.5 sentuh:text-14", a.bahaya && "text-danger-primary")}
                  >
                    <a.ikon className="size-4 shrink-0" />
                    {a.label}
                  </ContextMenu.Item>
                ))}
              </ContextMenu.Content>
            </ContextMenu.Portal>
          </ContextMenu>
        )}

        {/* Tombol melayang di samping gelembung, dalam dua lapis:
            - Rel: absolute setinggi gelembung tepat di sisinya, jadi tidak
              memakan lebar 68% maupun tinggi baris. Celahnya ke gelembung
              berupa PADDING rel, bukan margin, supaya penunjuk yang bergeser
              dari gelembung ke tombol tidak pernah lewat ruang di luar `group`
              (dulu celah `mr-1` itulah yang membuat tombol hilang). Rel hanya
              menangkap penunjuk selama gelembung diarahkan, jadi geser miring ke
              tombol di bawah tetap di dalam `group`, sementara ruang kosong di
              samping pesan lain tidak ikut menyalakan tombol.
            - Tombol: rata bawah gelembung dan `sticky`, jadi pada pesan yang
              lebih tinggi dari layar ia tetap di tepi bawah area gulir selama
              gelembungnya tampak. Sticky di dalam rel absolute tetap sah: batas
              geraknya rel itu sendiri, yaitu setinggi gelembung.
            Di layar sentuh keduanya tidak tampak, tapi tetap ada sebagai jangkar
            pemilih emoji penuh. Saat menu klik kanan terbuka keduanya disembunyikan
            supaya tidak bersaing dengan menu. */}
        {dihapus ? null : (
          <div
            className={cn(
              "pointer-events-none absolute inset-y-0 flex flex-col justify-end",
              dariSaya ? "right-full pr-1" : "left-full pl-1",
              "group-focus-within:pointer-events-auto group-hover:pointer-events-auto",
              (pemilihPenuh || menuTitikBuka) && "pointer-events-auto",
              menuBuka && "pointer-events-none!",
              "sentuh:pointer-events-none!"
            )}
          >
            <div
              className={cn(
                "sticky bottom-2 flex items-center gap-0.5 opacity-0 transition-opacity",
                "group-focus-within:opacity-100 group-hover:opacity-100",
                (pemilihPenuh || menuTitikBuka) && "opacity-100",
                menuBuka && "opacity-0!",
                "sentuh:opacity-0!"
              )}
            >
              <EmojiReactionPicker
                isOpen={pemilihPenuh}
                handleToggle={setPemilihPenuh}
                placement={dariSaya ? "top-end" : "top-start"}
                onChange={(kode) => {
                  // Picker memberi kode desimal, bukan karakternya.
                  const emoji = stringToEmoji(kode);
                  if (emoji) beriReaksi(emoji);
                }}
                label={
                  <span
                    className={kelasTombolMelayang}
                    aria-label={t("chat_ui.add_reaction")}
                    title={t("chat_ui.add_reaction")}
                  >
                    <SmilePlus className="size-3.5" />
                  </span>
                }
              />
              <Menu
                ariaLabel={t("common.options")}
                handleOpenChange={setMenuTitikBuka}
                optionsClassName="min-w-44"
                customButton={
                  <span className={kelasTombolMelayang} title={t("common.options")}>
                    <MoreHorizontal className="size-3.5" />
                  </span>
                }
              >
                {aksi.map((a) => (
                  <Menu.MenuItem
                    key={a.kunci}
                    onClick={() => jalankanAksi(a)}
                    className={cn("flex items-center gap-2", a.bahaya && "text-danger-primary")}
                  >
                    <a.ikon className="size-3.5 shrink-0" />
                    {a.label}
                  </Menu.MenuItem>
                ))}
              </Menu>
            </div>
          </div>
        )}
      </div>

      {/* Reaksi menumpang tepi bawah gelembung, bukan baris sendiri di bawahnya.
          `relative` tanpa z-index sudah cukup: ia datang sesudah gelembung di
          urutan dokumen, jadi tergambar di atasnya. Z-index positif dulu (z-[1])
          ikut menimpa menu klik kanan yang positioner-nya tanpa z-index. */}
      {!dihapus && pesan.reaksi.length > 0 ? (
        <div className={cn("relative -mt-1.5 flex flex-wrap gap-1 px-2", dariSaya && "justify-end")}>
          {pesan.reaksi.map((r) => {
            const punyaSaya = !!sayaId && r.orang.includes(sayaId);
            return (
              <button
                key={r.emoji}
                type="button"
                // Lewat penyaring yang sama: klik ganda cepat pada chip = satu kali.
                onClick={() => beriReaksi(r.emoji)}
                title={r.orang.map(namaOrang).join(", ")}
                aria-pressed={punyaSaya}
                className={cn(
                  "flex items-center gap-1 rounded-control border bg-layer-1 px-1.5 py-px text-12 hover:bg-layer-2",
                  punyaSaya ? "border-accent-strong text-accent-primary" : "border-subtle text-secondary"
                )}
              >
                <span>{r.emoji}</span>
                <span>{r.orang.length}</span>
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
