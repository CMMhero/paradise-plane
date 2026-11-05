/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kotak tulis obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useImperativeHandle, useState } from "react";
import type { ReactNode, RefObject } from "react";
import { Send, SmilePlus } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { stringToEmoji } from "@plane/propel/emoji-icon-picker";
import { EmojiReactionPicker } from "@plane/propel/emoji-reaction";
import { IconButton } from "@plane/propel/icon-button";
import { PratinjauTautanDraf } from "@/components/pratinjau-tautan/kartu";
import { DaftarRujukan, useRujukan } from "./pemilih-rujukan";
import { DaftarSebut, useSebutan } from "./pemilih-sebut";
import type { TCalonSebut } from "./pemilih-sebut";
import type { TRujukanKirim } from "@/services/chat.service";
import { sambungTip } from "@/hooks/editor/placeholder-rujukan";
import { berkasDariTempel } from "./unggah-lampiran";

const TINGGI_TULIS_MAKS = 160;

/** Pegangan halaman obrolan ke draf yang hidup di sini. */
export type TKendaliKotakTulis = {
  /** Ganti isi draf dari luar: mulai menyunting, batal menyunting, sesudah tersimpan. */
  setDraf: (teks: string) => void;
  /** Sesudah pesan terkirim: draf kosong, sebutan dilupakan, tinggi kembali satu baris. */
  kosongkan: () => void;
};

type TProps = {
  kendaliRef: RefObject<TKendaliKotakTulis>;
  tulisRef: RefObject<HTMLTextAreaElement>;
  /** Salinan draf milik halaman, supaya draf bertahan saat kotak ini dilepas
   * (kembali ke daftar di layar sempit lalu membuka percakapan lagi). */
  drafRef: { current: string };
  calonSebut: TCalonSebut[];
  /** Slug workspace, untuk mencari kanal dan work item di pemilih `#`. */
  slug: string | undefined;
  /** `@all` ditawarkan hanya di kanal, bukan DM. */
  bolehSemua: boolean;
  maksPanjang: number | undefined;
  menyunting: boolean;
  membalas: boolean;
  adaLampiran: boolean;
  /** Sedang mengirim atau lampiran masih naik. */
  sibuk: boolean;
  onKirim: (isi: string, rujukan: TRujukanKirim) => void;
  onSimpanSuntingan: (isi: string) => void;
  /** Escape saat membalas/menyunting. */
  onBatal: () => void;
  onTempelBerkas: (berkas: File[]) => void;
  /** Tombol lampiran; tetap milik halaman karena seret-lepas memakai jalur yang sama. */
  sebelumTulis: ReactNode;
};

/**
 * Draf obrolan hidup di komponen ini, BUKAN di halaman.
 *
 * Dulu `draf` ada di ChatPage, jadi tiap huruf merender ulang seluruh halaman:
 * daftar orang, bilah sematan, dan semua gelembung pesan (masing-masing
 * memindai tautan dan sebutan di isinya). Di percakapan panjang itulah yang
 * membuat mengetik terasa berat. Sekarang tiap huruf cuma merender kotak ini.
 */
export function KotakTulis({
  kendaliRef,
  tulisRef,
  drafRef,
  calonSebut,
  slug,
  bolehSemua,
  maksPanjang,
  menyunting,
  membalas,
  adaLampiran,
  sibuk,
  onKirim,
  onSimpanSuntingan,
  onBatal,
  onTempelBerkas,
  sebelumTulis,
}: TProps) {
  const { t } = useTranslation();
  // Dibaca sekali saat dipasang (penginisialisasi malas), bukan tiap render.
  // oxlint-disable-next-line react/refs -- memulihkan draf yang tersimpan saat kotak ini dilepas
  const [draf, setDraf] = useState(() => drafRef.current);
  const [emojiTerbuka, setEmojiTerbuka] = useState(false);
  const sebutan = useSebutan({ calon: calonSebut, bolehSemua, draf, setDraf, tulisRef });
  const rujukan = useRujukan({ slug, draf, setDraf, tulisRef });
  const { reset: resetSebutan } = sebutan;
  const { reset: resetRujukan } = rujukan;

  useEffect(() => {
    drafRef.current = draf;
  }, [draf, drafRef]);

  useImperativeHandle(
    kendaliRef,
    () => ({
      setDraf,
      kosongkan: () => {
        setDraf("");
        resetSebutan();
        resetRujukan();
        if (tulisRef.current) tulisRef.current.style.height = "auto";
      },
    }),
    [resetSebutan, resetRujukan, tulisRef]
  );

  const aturTinggiTulis = () => {
    const el = tulisRef.current;
    if (!el) return;
    // Tinggi dinolkan dulu; tanpa itu scrollHeight ikut tinggi lama dan kotaknya
    // tumbuh terus tapi tidak pernah menyusut lagi.
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, TINGGI_TULIS_MAKS)}px`;
  };

  const isi = draf.trim();
  const kirimAtauSimpan = () => {
    if (menyunting) onSimpanSuntingan(isi);
    else
      onKirim(isi, {
        sebut: sebutan.idUntukKirim(isi),
        ...rujukan.idUntukKirim(isi),
        semua: sebutan.semuaUntukKirim(isi),
      });
  };

  return (
    <>
      <PratinjauTautanDraf teks={draf} className="mb-2" />
      <div className="flex items-end gap-2">
        {sebelumTulis}
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
          {rujukan.terbuka ? (
            <DaftarRujukan
              cocok={rujukan.cocok}
              memuat={rujukan.memuat}
              sorot={rujukan.sorot}
              onSorot={rujukan.setSorot}
              onPilih={rujukan.pilih}
            />
          ) : null}
          <textarea
            ref={tulisRef}
            maxLength={maksPanjang}
            value={draf}
            onChange={(e) => {
              setDraf(e.target.value);
              sebutan.onChange(e);
              rujukan.onChange(e);
              aturTinggiTulis();
            }}
            onClick={(e) => {
              sebutan.onKursor(e.currentTarget.value, e.currentTarget.selectionStart ?? 0);
              rujukan.onKursor(e.currentTarget.value, e.currentTarget.selectionStart ?? 0);
            }}
            onBlur={() => {
              sebutan.onKursor("", 0);
              rujukan.onKursor("", 0);
            }}
            onPaste={(e) => {
              // Tempel gambar/berkas = lampiran. Tempelan teks biasa
              // dibiarkan jalan seperti biasa.
              const berkas = berkasDariTempel(e.clipboardData);
              if (berkas.length === 0) return;
              e.preventDefault();
              onTempelBerkas(berkas);
            }}
            onKeyDown={(e) => {
              // Pemilih sebutan yang terbuka menang atas Enter/Escape.
              if (sebutan.onKeyDown(e) || rujukan.onKeyDown(e)) return;
              // Enter mengirim, Shift+Enter ganti baris. Kebiasaan yang
              // sudah dibawa orang dari aplikasi obrolan lain.
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                kirimAtauSimpan();
              }
              // Escape membatalkan balas atau sunting. Tanpa ini, satu
              // satunya jalan keluar adalah mengklik tanda silang kecil.
              if (e.key === "Escape" && (menyunting || membalas)) {
                if (menyunting) setDraf("");
                onBatal();
              }
            }}
            rows={1}
            // Petunjuk @/# ikut di placeholder (KEP-91), jadi hanya terlihat saat kotak kosong.
            placeholder={sambungTip(t("chat_ui.write_message"), t("rujukan_ui.tip_inline"))}
            aria-label={t("chat_ui.write_message")}
            className="block min-h-9 w-full resize-none rounded-field border border-subtle bg-transparent px-3 py-2 text-13 text-primary outline-none placeholder:text-placeholder focus:border-accent-strong"
          />
        </div>
        <IconButton
          variant="primary"
          size="xl"
          icon={Send}
          onClick={kirimAtauSimpan}
          disabled={sibuk || (menyunting ? isi.length === 0 : isi.length === 0 && !adaLampiran)}
          aria-label={t("chat_ui.send_message")}
        />
      </div>
    </>
  );
}
