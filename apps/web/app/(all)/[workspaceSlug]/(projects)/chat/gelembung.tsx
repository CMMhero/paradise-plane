/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: gelembung pesan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import { useState } from "react";
import { Check, CheckCheck, CornerUpLeft, Pencil, SmilePlus, Trash2 } from "lucide-react";
import { IconButton } from "@plane/propel/icon-button";
import { cn, renderFormattedTime } from "@plane/utils";
import { MemberProfileTrigger } from "@/components/member-profile";
import type { TPesan } from "@/services/chat.service";
import { KartuPesan, adalahKartu } from "./kartu/kartu-pesan";
import { bolehDihapus } from "./batas-hapus";
import { DaftarLampiran } from "./lampiran";
import { potongSebutan } from "./sebut";
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

/**
 * Teks pesan dengan `@nama` yang disorot, lalu tautan di potongan sisanya.
 *
 * Yang disorot HANYA nama orang yang memang tercatat di `muatan.sebut` (sudah
 * disaring server ke anggota ruang). Mengetik `@siapa` tanpa memilih dari daftar
 * tetap teks biasa, supaya sorotan tidak menjanjikan pemberitahuan yang tidak
 * pernah dikirim.
 */
const denganSebutan = (
  teks: string,
  orang: { id: string; nama: string }[],
  sayaId: string | undefined,
  terang: boolean
) =>
  potongSebutan(teks, orang).map((potongan, i) => {
    if (potongan.jenis === "teks") {
      // oxlint-disable-next-line no-array-index-key -- potongan dari satu teks yang tidak pernah diurut ulang
      return <span key={`teks-${i}`}>{denganTautan(potongan.isi)}</span>;
    }
    return (
      // oxlint-disable-next-line no-array-index-key -- lihat di atas
      <MemberProfileTrigger key={`sebut-${i}`} userId={potongan.id} className="align-baseline">
        <span className={gayaSebutan(terang, !!sayaId && potongan.id === sayaId)}>{potongan.isi}</span>
      </MemberProfileTrigger>
    );
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

/** Reaksi cepat. Sengaja sedikit: pemilih emoji penuh membuat orang memilih,
 * dan reaksi yang butuh dipikirkan tidak akan dipakai. */
export const REAKSI_CEPAT = ["👍", "✅", "🙏", "😄", "❗"];

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
  onReaksi?: (pesan: TPesan, emoji: string) => void;
  /** Telepon balik dari kartu log panggilan. */
  onTelepon?: (video: boolean) => void;
};

export function Gelembung(props: Props) {
  const { t } = useTranslation();
  const { pesan, dariSaya, awalKelompok, akhirKelompok, sayaId, namaOrang } = props;
  const [pilihReaksi, setPilihReaksi] = useState(false);

  // Kartu (log panggilan, catatan rilis, kartu tugas) selalu berlatar netral,
  // juga saat dikirim sendiri: tombol dan chip di dalamnya tidak terbaca di
  // atas warna aksen. Kartu juga tidak bisa disunting atau dihapus.
  const kartu = adalahKartu(pesan);
  const terang = dariSaya && !kartu;
  // Nama asli, bukan namaOrang: untuk diri sendiri namaOrang memberi "Anda",
  // padahal teksnya "@NamaSaya". Dulu ini yang membuat sebutan ke saya tidak
  // pernah tersorot.
  const disebut = idSebutan(pesan).map((id) => ({ id, nama: props.namaSebutan(id) }));
  // Pesan masuk yang menyebut saya diberi bingkai amber supaya tertangkap mata
  // saat menggulir, bukan hanya sebutannya yang berwarna.
  const sayaDisebut = !dariSaya && !kartu && !!sayaId && disebut.some((o) => o.id === sayaId);
  const gaya = kartu
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

  return (
    <div className={`group flex max-w-[68%] flex-col ${dariSaya ? "items-end" : "items-start"}`}>
      <div className={`relative rounded-overlay px-3 py-2 ${gaya} ${awalKelompok ? "" : "rounded-t-item"}`}>
        {/* Kutipan pesan yang dibalas. Ditaruh DI DALAM gelembung supaya
            terbaca sebagai bagian dari pesan ini, bukan pesan tersendiri. */}
        {/* Nama pengirim di awal kelompok pesan masuk, seperti WhatsApp. Pesan
            sistem (pengirim kosong) sudah bernama lewat kartunya. */}
        {!dariSaya && awalKelompok && pesan.pengirim ? (
          <p className="mb-0.5 truncate text-12 font-semibold text-accent-primary">
            <MemberProfileTrigger userId={pesan.pengirim}>
              <span className="truncate hover:underline">{namaOrang(pesan.pengirim)}</span>
            </MemberProfileTrigger>
          </p>
        ) : null}

        {/* Kutipan pesan yang dibalas. Garis aksen dipotong oleh sudut kotak
            (overflow-hidden), jadi ia ikut membulat hanya di sisi kiri.
            Seluruh kutipan satu tombol yang melompat ke pesan aslinya, jadi
            nama di dalamnya sengaja teks biasa (tombol tidak boleh bersarang). */}
        {pesan.balasan_ke ? (
          <button
            type="button"
            onClick={() => pesan.balasan_ke && props.onBukaKutipan?.(pesan.balasan_ke.id)}
            className={`relative mb-1.5 block w-full overflow-hidden rounded-item py-1 pr-2 pl-3 text-left transition-colors ${
              terang ? "bg-black/15 hover:bg-black/25" : "bg-accent-subtle hover:bg-accent-subtle-hover"
            }`}
          >
            <span
              aria-hidden
              className={`absolute inset-y-0 left-0 w-1 ${terang ? "bg-white/80" : "bg-accent-primary"}`}
            />
            <span
              className={`block truncate text-12 font-semibold ${terang ? "text-on-color" : "text-accent-primary"}`}
            >
              {namaOrang(pesan.balasan_ke.pengirim)}
            </span>
            <span className={`line-clamp-2 text-12 ${redup}`}>{pesan.balasan_ke.isi || t("chat_ui.attachment")}</span>
          </button>
        ) : null}

        {kartu ? (
          <KartuPesan pesan={pesan} namaOrang={namaOrang} onTelepon={props.onTelepon} />
        ) : pesan.isi ? (
          <p className="text-13 [overflow-wrap:anywhere] whitespace-pre-wrap">
            {disebut.length > 0 ? denganSebutan(pesan.isi, disebut, sayaId, terang) : denganTautan(pesan.isi)}
          </p>
        ) : null}
        <DaftarLampiran lampiran={pesan.lampiran} terang={terang} />

        {akhirKelompok || pesan.disunting ? (
          <p className={`mt-1 flex items-center gap-1 text-12 ${redup}`}>
            {renderFormattedTime(pesan.created_at)}
            {pesan.disunting ? <span>· {t("chat_ui.edited")}</span> : null}
            {/* Tanda dibaca hanya untuk pesan KELUAR. Menampilkannya pada pesan
                masuk tidak berarti apa-apa: kita jelas sudah membacanya. */}
            {terang ? pesan.sudah_dibaca ? <CheckCheck className="size-3.5" /> : <Check className="size-3.5" /> : null}
          </p>
        ) : null}
      </div>

      {pesan.reaksi.length > 0 ? (
        <div className="mt-1 flex flex-wrap gap-1">
          {pesan.reaksi.map((r) => {
            const punyaSaya = !!sayaId && r.orang.includes(sayaId);
            return (
              <button
                key={r.emoji}
                type="button"
                onClick={() => props.onReaksi?.(pesan, r.emoji)}
                title={r.orang.map(namaOrang).join(", ")}
                className={`flex items-center gap-1 rounded-control border px-1.5 py-0.5 text-12 ${
                  punyaSaya ? "border-accent-strong text-accent-primary" : "border-subtle text-secondary"
                } hover:bg-layer-1`}
              >
                <span>{r.emoji}</span>
                <span>{r.orang.length}</span>
              </button>
            );
          })}
        </div>
      ) : null}

      <div className="mt-0.5 flex items-center gap-0.5 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100 sentuh:gap-2 sentuh:opacity-100">
        <IconButton
          type="button"
          onClick={() => setPilihReaksi((v) => !v)}
          aria-label={t("chat_ui.add_reaction")}
          variant="ghost"
          size="sm"
          icon={SmilePlus}
        />
        <IconButton
          type="button"
          onClick={() => props.onBalas?.(pesan)}
          aria-label={t("chat_ui.reply")}
          variant="ghost"
          size="sm"
          icon={CornerUpLeft}
        />
        {terang ? (
          <>
            <IconButton
              type="button"
              onClick={() => props.onSunting?.(pesan)}
              aria-label={t("chat_ui.edit")}
              variant="ghost"
              size="sm"
              icon={Pencil}
            />
            {bolehHapus ? (
              <IconButton
                type="button"
                onClick={() => props.onHapus?.(pesan)}
                aria-label={t("chat_ui.delete")}
                variant="ghost"
                size="sm"
                icon={Trash2}
              />
            ) : null}
          </>
        ) : null}

        {pilihReaksi ? (
          <div className="flex items-center gap-0.5 rounded-control border border-subtle bg-layer-1 px-1.5 py-0.5">
            {REAKSI_CEPAT.map((e) => (
              <button
                key={e}
                type="button"
                onClick={() => {
                  props.onReaksi?.(pesan, e);
                  setPilihReaksi(false);
                }}
                className="rounded-button px-0.5 text-13 hover:bg-layer-2"
              >
                {e}
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
