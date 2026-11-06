/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: bingkai penampil Materi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useState } from "react";
import { Maximize2, Minimize2, RotateCcw, ZoomIn, ZoomOut } from "lucide-react";
import { useCloseOnBack } from "@plane/hooks";
import { useTranslation } from "@plane/i18n";
import { getButtonStyling } from "@plane/propel/button";
import { IconButton } from "@plane/propel/icon-button";
import { cn } from "@plane/utils";
// components
import { PratinjauDokumen } from "@/components/wiki/pratinjau/dokumen";
import { PratinjauTabel } from "@/components/wiki/pratinjau/tabel";
import { PratinjauMarkdown, PratinjauTeks } from "@/components/wiki/pratinjau/teks";
// services
import type { TWikiPreview } from "@/services/wiki.service";

const ZOOM_MIN = 0.25;
const ZOOM_MAKS = 5;
const ZOOM_LANGKAH = 0.25;

/**
 * Satu bingkai untuk semua tipe materi, berikut layar penuh dan zoom.
 *
 * Layar penuhnya sengaja overlay di dalam aplikasi, BUKAN Fullscreen API
 * peramban. Alasannya bukan selera: dengan overlay, bilah alat kita ikut
 * terbawa, jadi orang tetap punya tombol "kembali normal" yang terlihat.
 * Fullscreen API menyembunyikan seluruh chrome peramban dan menyisakan orang
 * dengan satu-satunya jalan keluar berupa tombol Escape yang tidak tertulis di
 * mana pun.
 *
 * Zoom hanya ditawarkan untuk gambar, dan itu jujur: PDF (termasuk hasil
 * konversi Word, Excel, dan PowerPoint) dirender oleh penampil bawaan peramban
 * di dalam iframe, yang PUNYA kontrol zoom sendiri dan tidak bisa kita setir
 * dari luar. Menampilkan tombol zoom yang tidak berbuat apa-apa lebih buruk
 * daripada tidak menampilkannya.
 */
export function PenampilMateri({ pratinjau, title }: { pratinjau: TWikiPreview; title: string }) {
  const { t } = useTranslation();
  const { kind, url } = pratinjau;
  const [layarPenuh, setLayarPenuh] = useState(false);
  const [zoom, setZoom] = useState(1);
  // lebar gambar saat pas-bingkai (zoom 100%), dasar perhitungan zoom
  const [lebarDasar, setLebarDasar] = useState(0);

  const bisaZoom = kind === "image";

  const keluar = useCallback(() => {
    setLayarPenuh(false);
    setZoom(1);
  }, []);

  // Tombol Kembali peramban/Android menutup layar penuh, bukan meninggalkan
  // halaman materi (dulu orang terlempar ke daftar materi).
  useCloseOnBack(layarPenuh, keluar);

  // Escape harus bekerja, karena itu yang pertama dicoba orang untuk keluar
  // dari layar penuh, sebelum mencari tombol.
  useEffect(() => {
    if (!layarPenuh) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") keluar();
    };
    window.addEventListener("keydown", onKey);
    // Halaman di belakang jangan ikut bergulir saat overlay terbuka.
    const sebelumnya = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = sebelumnya;
    };
  }, [layarPenuh, keluar]);

  if (!url) return null;

  const tinggi = layarPenuh ? "h-[calc(100vh-3.5rem)]" : "h-[calc(100vh-16rem)]";

  const isi = () => {
    if (kind === "image")
      return (
        // Zoom lewat LEBAR, bukan transform scale: scale tidak menambah area
        // gulir, jadi tepi kiri dan atas gambar yang diperbesar terpotong dan
        // tidak bisa dijangkau. `m-auto` di dalam grid memusatkan gambar saat
        // lebih kecil dari bingkai dan membiarkannya bergulir saat lebih besar.
        <div className={cn("grid w-full overflow-auto", tinggi)}>
          <img
            src={url}
            alt={title}
            onLoad={(e) => {
              if (zoom === 1) setLebarDasar(e.currentTarget.clientWidth);
            }}
            style={
              zoom !== 1 && lebarDasar > 0
                ? { width: `${lebarDasar * zoom}px`, maxWidth: "none", maxHeight: "none" }
                : undefined
            }
            className="m-auto max-h-full w-auto max-w-full rounded-card object-contain"
          />
        </div>
      );

    if (kind === "video")
      return (
        // oxlint-disable-next-line jsx-a11y/media-has-caption
        <video src={url} controls preload="metadata" className={cn("w-full rounded-card bg-black", tinggi)} />
      );

    if (kind === "audio")
      return (
        <div className="grid place-items-center py-16">
          {/* oxlint-disable-next-line jsx-a11y/media-has-caption */}
          <audio src={url} controls className="w-full max-w-xl" />
        </div>
      );

    // Teks, Markdown, tabel, dan dokumen dibaca SERVER dan dirender sebagai
    // elemen React biasa. Tidak ada iframe untuk isi unggahan orang.
    if (kind === "text")
      return <PratinjauTeks text={pratinjau.text ?? ""} truncated={pratinjau.truncated} className={tinggi} />;
    if (kind === "markdown")
      return <PratinjauMarkdown text={pratinjau.text ?? ""} truncated={pratinjau.truncated} className={tinggi} />;
    if (kind === "table")
      return (
        <PratinjauTabel sheets={pratinjau.sheets ?? []} truncated={pratinjau.sheets_truncated} className={tinggi} />
      );
    if (kind === "document")
      return <PratinjauDokumen blocks={pratinjau.blocks ?? []} truncated={pratinjau.truncated} className={tinggi} />;

    return (
      <iframe
        src={url}
        title={title}
        // Hanya PDF yang sampai ke sini, dan SENGAJA tanpa sandbox: Chrome
        // menolak memuat penampil PDF bawaannya di dalam iframe ber-sandbox,
        // apa pun kombinasi tokennya.
        sandbox={kind === "pdf" ? undefined : ""}
        className={cn("w-full rounded-card border border-subtle bg-layer-1", tinggi)}
      />
    );
  };

  const bilah = (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
      <div className="flex items-center gap-1">
        {bisaZoom ? (
          <>
            <IconButton
              type="button"
              aria-label={t("wiki_ui.viewer.zoom_out")}
              onClick={() => setZoom((z) => Math.max(ZOOM_MIN, z - ZOOM_LANGKAH))}
              variant="secondary"
              size="lg"
              icon={ZoomOut}
            />
            <span className="min-w-14 text-center text-12 text-tertiary tabular-nums">{Math.round(zoom * 100)}%</span>
            <IconButton
              type="button"
              aria-label={t("wiki_ui.viewer.zoom_in")}
              onClick={() => setZoom((z) => Math.min(ZOOM_MAKS, z + ZOOM_LANGKAH))}
              variant="secondary"
              size="lg"
              icon={ZoomIn}
            />
            <IconButton
              type="button"
              aria-label={t("wiki_ui.viewer.reset_zoom")}
              onClick={() => setZoom(1)}
              variant="secondary"
              size="lg"
              icon={RotateCcw}
            />
          </>
        ) : (
          <span className="text-11 text-tertiary">
            {kind === "pdf"
              ? t("wiki_ui.viewer.pdf_hint")
              : kind === "video" || kind === "audio"
                ? t("wiki_ui.viewer.player_hint")
                : kind === "table"
                  ? t("wiki_ui.viewer.sheet_hint")
                  : kind === "text" || kind === "markdown" || kind === "document"
                    ? t("wiki_ui.viewer.text_hint")
                    : ""}
          </span>
        )}
      </div>

      <button
        type="button"
        onClick={() => {
          if (layarPenuh) return keluar();
          // bingkai berubah ukuran, jadi zoom dihitung ulang dari 100%
          setZoom(1);
          setLayarPenuh(true);
        }}
        className={getButtonStyling("secondary", "lg")}
      >
        {layarPenuh ? (
          <>
            <Minimize2 className="size-3.5" />
            {t("wiki_ui.viewer.exit_fullscreen")}
          </>
        ) : (
          <>
            <Maximize2 className="size-3.5" />
            {t("wiki_ui.viewer.fullscreen")}
          </>
        )}
      </button>
    </div>
  );

  if (layarPenuh)
    return (
      <div className="fixed inset-0 z-50 flex flex-col bg-canvas p-4">
        <div className="mb-1 truncate text-13 font-medium text-primary">{title}</div>
        {bilah}
        <div className="flex-1 overflow-auto">{isi()}</div>
      </div>
    );

  return (
    <div>
      {bilah}
      {isi()}
    </div>
  );
}
