/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: panel kiri layar masuk
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Dipakai layar masuk web (AuthBase) dan God Mode (layout home). Isinya logo,
 * nama merek, lalu empat gambar aplikasi yang bergilir tiap 6 detik dengan
 * keterangan satu baris. Sengaja TANPA daftar fitur bernomor, slogan, atau hak
 * cipta: ini alat internal, bukan halaman promosi (keputusan user 3 Nov 2026).
 *
 * Keterangan datang dari pemanggil supaya web bisa menerjemahkan lewat i18n,
 * sedangkan God Mode (English saja) mengirim teks langsung.
 */

import * as React from "react";
import { cn } from "../utils";
import { SlideChat, SlideDashboard, SlidePapan, SlideTugas } from "./slides";

export type AuthShowcaseCaption = { title: string; description: string };

export type AuthShowcaseProps = {
  brandName: string;
  logoSrc: string;
  /** Label wilayah untuk pembaca layar, misalnya "App preview". */
  label: string;
  /** Urutannya tetap: papan, dashboard divisi, detail tugas, chat. */
  captions: [AuthShowcaseCaption, AuthShowcaseCaption, AuthShowcaseCaption, AuthShowcaseCaption];
  className?: string;
};

const SLIDES = [SlidePapan, SlideDashboard, SlideTugas, SlideChat];
const JEDA_MS = 6000;

function useGerakDikurangi(): boolean {
  return React.useSyncExternalStore(
    (onChange) => {
      const kueri = window.matchMedia("(prefers-reduced-motion: reduce)");
      kueri.addEventListener("change", onChange);
      return () => kueri.removeEventListener("change", onChange);
    },
    () =>
      window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
      document.documentElement.dataset.gerak === "kurangi",
    () => false
  );
}

export function AuthShowcase({ brandName, logoSrc, label, captions, className }: AuthShowcaseProps) {
  const [aktif, setAktif] = React.useState(0);
  const gerakDikurangi = useGerakDikurangi();

  // Satu timeout per slide: berpindah slide (otomatis atau lewat titik) memulai
  // hitungan 6 detik dari nol, jadi slide yang baru dipilih tidak langsung lewat.
  React.useEffect(() => {
    if (gerakDikurangi) return;
    const id = window.setTimeout(() => setAktif((aktif + 1) % SLIDES.length), JEDA_MS);
    return () => window.clearTimeout(id);
  }, [aktif, gerakDikurangi]);

  const handlePilih = (indeks: number) => setAktif(indeks);

  const keterangan = captions[aktif];

  return (
    <aside
      aria-label={label}
      className={cn(
        "relative flex-col overflow-hidden rounded-card px-7 pt-7 pb-6 text-pamer-panel-teks pamer-panel",
        className
      )}
    >
      <div className="flex items-center gap-2.5">
        <img src={logoSrc} alt="" width={32} height={32} className="size-8 object-contain" />
        <span className="text-16 font-semibold tracking-tight">{brandName}</span>
      </div>

      <div className="relative mt-5 mb-2 min-h-0 flex-1">
        {SLIDES.map((Slide, indeks) => (
          <div
            key={Slide.name}
            aria-hidden
            className={cn(
              "absolute inset-0 grid place-items-center transition-[opacity,translate] duration-500 ease-smooth",
              indeks === aktif ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-2.5 opacity-0"
            )}
          >
            <Slide />
          </div>
        ))}
      </div>

      <div className="min-h-16 text-center" aria-live="polite">
        <h2 className="text-20 font-semibold tracking-tight">{keterangan.title}</h2>
        <p className="mt-1.5 text-14 text-pamer-panel-teks-2">{keterangan.description}</p>
      </div>

      <div className="mt-4 flex justify-center gap-2">
        {captions.map((caption, indeks) => (
          <button
            key={caption.title}
            type="button"
            aria-label={caption.title}
            aria-current={indeks === aktif}
            onClick={() => handlePilih(indeks)}
            className={cn(
              "h-1 rounded-full transition-[width,background-color] duration-300 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-highlight",
              indeks === aktif ? "w-10 bg-pamer-titik-aktif" : "w-5.5 bg-pamer-titik hover:bg-pamer-panel-teks-2"
            )}
          />
        ))}
      </div>
    </aside>
  );
}
