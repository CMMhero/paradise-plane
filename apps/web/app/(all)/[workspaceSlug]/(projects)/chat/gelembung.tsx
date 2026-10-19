/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: gelembung pesan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { Check, CheckCheck, CornerUpLeft, Pencil, SmilePlus, Trash2 } from "lucide-react";
import { renderFormattedTime } from "@plane/utils";
import type { TPesan } from "@/services/chat.service";
import { DaftarLampiran } from "./lampiran";
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
  onBalas?: (pesan: TPesan) => void;
  onSunting?: (pesan: TPesan) => void;
  onHapus?: (pesan: TPesan) => void;
  onReaksi?: (pesan: TPesan, emoji: string) => void;
};

export function Gelembung(props: Props) {
  const { pesan, dariSaya, awalKelompok, akhirKelompok, sayaId, namaOrang } = props;
  const [pilihReaksi, setPilihReaksi] = useState(false);

  const gaya = dariSaya ? "bg-accent-primary text-white" : "bg-layer-3 text-primary";
  const redup = dariSaya ? "text-white/70" : "text-tertiary";

  return (
    <div className={`group flex max-w-[68%] flex-col ${dariSaya ? "items-end" : "items-start"}`}>
      <div className={`relative rounded-2xl px-3 py-2 ${gaya} ${awalKelompok ? "" : "rounded-t-md"}`}>
        {/* Kutipan pesan yang dibalas. Ditaruh DI DALAM gelembung supaya
            terbaca sebagai bagian dari pesan ini, bukan pesan tersendiri. */}
        {pesan.balasan_ke ? (
          <div className={`mb-1.5 rounded border-l-2 pl-2 ${dariSaya ? "border-white/50" : "border-accent-primary"}`}>
            <p className={`text-xs font-medium ${redup}`}>{namaOrang(pesan.balasan_ke.pengirim)}</p>
            <p className={`text-xs line-clamp-2 ${redup}`}>{pesan.balasan_ke.isi || "lampiran"}</p>
          </div>
        ) : null}

        {pesan.isi ? <p className="text-sm break-words whitespace-pre-wrap">{denganTautan(pesan.isi)}</p> : null}
        <DaftarLampiran lampiran={pesan.lampiran} terang={dariSaya} />

        {akhirKelompok || pesan.disunting ? (
          <p className={`text-xs mt-1 flex items-center gap-1 ${redup}`}>
            {renderFormattedTime(pesan.created_at)}
            {pesan.disunting ? <span>· disunting</span> : null}
            {/* Tanda dibaca hanya untuk pesan KELUAR. Menampilkannya pada pesan
                masuk tidak berarti apa-apa: kita jelas sudah membacanya. */}
            {dariSaya ? (
              pesan.sudah_dibaca ? (
                <CheckCheck className="size-3.5" />
              ) : (
                <Check className="size-3.5" />
              )
            ) : null}
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
                className={`text-xs flex items-center gap-1 rounded-full border px-1.5 py-0.5 ${
                  punyaSaya ? "border-accent-primary text-accent-primary" : "border-subtle text-secondary"
                } hover:bg-layer-1`}
              >
                <span>{r.emoji}</span>
                <span>{r.orang.length}</span>
              </button>
            );
          })}
        </div>
      ) : null}

      <div className="mt-0.5 flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
        <button
          type="button"
          onClick={() => setPilihReaksi((v) => !v)}
          aria-label="Beri reaksi"
          className="rounded p-1 text-tertiary hover:bg-layer-1 hover:text-secondary"
        >
          <SmilePlus className="size-3.5" />
        </button>
        <button
          type="button"
          onClick={() => props.onBalas?.(pesan)}
          aria-label="Balas pesan"
          className="rounded p-1 text-tertiary hover:bg-layer-1 hover:text-secondary"
        >
          <CornerUpLeft className="size-3.5" />
        </button>
        {dariSaya ? (
          <>
            <button
              type="button"
              onClick={() => props.onSunting?.(pesan)}
              aria-label="Sunting pesan"
              className="rounded p-1 text-tertiary hover:bg-layer-1 hover:text-secondary"
            >
              <Pencil className="size-3.5" />
            </button>
            <button
              type="button"
              onClick={() => props.onHapus?.(pesan)}
              aria-label="Hapus pesan"
              className="rounded p-1 text-tertiary hover:bg-layer-1 hover:text-danger-primary"
            >
              <Trash2 className="size-3.5" />
            </button>
          </>
        ) : null}

        {pilihReaksi ? (
          <div className="flex items-center gap-0.5 rounded-full border border-subtle bg-layer-1 px-1.5 py-0.5">
            {REAKSI_CEPAT.map((e) => (
              <button
                key={e}
                type="button"
                onClick={() => {
                  props.onReaksi?.(pesan, e);
                  setPilihReaksi(false);
                }}
                className="text-sm rounded px-0.5 hover:bg-layer-2"
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
