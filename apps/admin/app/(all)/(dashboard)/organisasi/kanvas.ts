/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: geser & zoom bagan organisasi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Kanvas bagan: isi digeser dengan `transform: translate() scale()` di atas
 * viewport yang `overflow-hidden`. Tanpa pustaka: cukup pointer events.
 *
 * - Seret di mana saja (termasuk di atas kotak) untuk menggeser. Seretan baru
 *   dianggap seretan sesudah lewat AMBANG_SERET piksel, jadi klik biasa pada
 *   kotak tetap membuka detail; klik yang mengakhiri seretan ditelan.
 * - Scroll = geser, Ctrl/Cmd + scroll (dan pinch trackpad) = zoom ke kursor.
 * - Selama admin belum menyentuh kanvas, isi selalu dipaskan ulang saat ukuran
 *   berubah (data dimuat, panel kiri dilipat, layar penuh).
 *
 * Catatan: elemen `position: fixed` di dalam isi yang di-transform ikut
 * tergeser, jadi menu di atas kotak bagan WAJIB di-portal ke body.
 */

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type MouseEvent,
  type PointerEvent,
} from "react";

export const ZOOM_MIN = 0.25;
export const ZOOM_MAKS = 2;
const LANGKAH_ZOOM = 1.2;
const AMBANG_SERET = 4;
const LANGKAH_PANAH = 60;
const MARGIN_PAS = 24;
/** Kepekaan zoom roda: deltaY 100 (satu takik) ~ 14%. */
const KEPEKAAN_RODA = 0.0015;
/** Elemen bertanda ini tidak memulai seretan (tombol menu, toolbar). */
export const ATRIBUT_ABAIKAN = "data-kanvas-abaikan";

type TTampilan = { x: number; y: number; k: number };
type TSeret = { id: number; x0: number; y0: number; tx: number; ty: number; aktif: boolean };

const batasi = (k: number): number => Math.min(ZOOM_MAKS, Math.max(ZOOM_MIN, k));

export function useKanvasGeser() {
  const viewportRef = useRef<HTMLDivElement>(null);
  const kontenRef = useRef<HTMLDivElement>(null);
  const [tampilan, setTampilan] = useState<TTampilan>({ x: 0, y: 0, k: 1 });
  const [sedangSeret, setSedangSeret] = useState(false);
  const seret = useRef<TSeret | null>(null);
  const telanKlik = useRef(false);
  const sudahDisentuh = useRef(false);

  const pas = useCallback(() => {
    const vp = viewportRef.current;
    const isi = kontenRef.current;
    if (!vp || !isi) return;
    // offsetWidth/Height tidak terpengaruh transform: ukuran asli isi.
    const w = isi.offsetWidth;
    const h = isi.offsetHeight;
    if (!w || !h || !vp.clientWidth || !vp.clientHeight) return;
    const k = batasi(Math.min((vp.clientWidth - 2 * MARGIN_PAS) / w, (vp.clientHeight - 2 * MARGIN_PAS) / h, 1));
    setTampilan({ k, x: (vp.clientWidth - w * k) / 2, y: Math.max(MARGIN_PAS, (vp.clientHeight - h * k) / 2) });
  }, []);

  /** Zoom dengan faktor, berpusat di titik (koordinat viewport); default tengah viewport. */
  const zoomDi = useCallback((faktor: number, px?: number, py?: number) => {
    const vp = viewportRef.current;
    if (!vp) return;
    const cx = px ?? vp.clientWidth / 2;
    const cy = py ?? vp.clientHeight / 2;
    sudahDisentuh.current = true;
    setTampilan((t) => {
      const k = batasi(t.k * faktor);
      const r = k / t.k;
      return { k, x: cx - (cx - t.x) * r, y: cy - (cy - t.y) * r };
    });
  }, []);

  const geserOleh = useCallback((dx: number, dy: number) => {
    sudahDisentuh.current = true;
    setTampilan((t) => ({ ...t, x: t.x + dx, y: t.y + dy }));
  }, []);

  const zoomMasuk = useCallback(() => zoomDi(LANGKAH_ZOOM), [zoomDi]);
  const zoomKeluar = useCallback(() => zoomDi(1 / LANGKAH_ZOOM), [zoomDi]);
  const zoomAsli = useCallback(() => {
    setTampilan((t) => {
      // Kembali ke 100% di sekitar tengah viewport.
      const vp = viewportRef.current;
      if (!vp) return { ...t, k: 1 };
      const cx = vp.clientWidth / 2;
      const cy = vp.clientHeight / 2;
      const r = 1 / t.k;
      return { k: 1, x: cx - (cx - t.x) * r, y: cy - (cy - t.y) * r };
    });
    sudahDisentuh.current = true;
  }, []);
  const pasUlang = useCallback(() => {
    sudahDisentuh.current = false;
    pas();
  }, [pas]);

  // Roda: harus non-passive supaya preventDefault menahan scroll halaman.
  useEffect(() => {
    const vp = viewportRef.current;
    if (!vp) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      if (e.ctrlKey || e.metaKey) {
        const rect = vp.getBoundingClientRect();
        zoomDi(Math.exp(-e.deltaY * KEPEKAAN_RODA), e.clientX - rect.left, e.clientY - rect.top);
        return;
      }
      // Shift + roda biasa = geser mendatar (sebagian peramban tidak mengubahnya jadi deltaX).
      const dx = e.shiftKey && e.deltaX === 0 ? e.deltaY : e.deltaX;
      const dy = e.shiftKey && e.deltaX === 0 ? 0 : e.deltaY;
      geserOleh(-dx, -dy);
    };
    vp.addEventListener("wheel", onWheel, { passive: false });
    return () => vp.removeEventListener("wheel", onWheel);
  }, [zoomDi, geserOleh]);

  // Paskan otomatis saat ukuran viewport/isi berubah, selama admin belum menggeser.
  useEffect(() => {
    const vp = viewportRef.current;
    const isi = kontenRef.current;
    if (!vp || !isi || typeof ResizeObserver === "undefined") return;
    const pengamat = new ResizeObserver(() => {
      if (!sudahDisentuh.current) pas();
    });
    pengamat.observe(vp);
    pengamat.observe(isi);
    return () => pengamat.disconnect();
  }, [pas]);

  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    telanKlik.current = false;
    if (e.button !== 0) return;
    if ((e.target as HTMLElement).closest(`[${ATRIBUT_ABAIKAN}]`)) return;
    seret.current = { id: e.pointerId, x0: e.clientX, y0: e.clientY, tx: tampilan.x, ty: tampilan.y, aktif: false };
  };

  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    const s = seret.current;
    if (!s || s.id !== e.pointerId) return;
    const dx = e.clientX - s.x0;
    const dy = e.clientY - s.y0;
    if (!s.aktif) {
      if (Math.hypot(dx, dy) < AMBANG_SERET) return;
      seret.current = { ...s, aktif: true };
      sudahDisentuh.current = true;
      setSedangSeret(true);
      e.currentTarget.setPointerCapture(e.pointerId);
    }
    setTampilan((t) => ({ ...t, x: s.tx + dx, y: s.ty + dy }));
  };

  const akhiriSeret = (e: PointerEvent<HTMLDivElement>) => {
    const s = seret.current;
    if (!s || s.id !== e.pointerId) return;
    if (s.aktif) {
      telanKlik.current = true;
      setSedangSeret(false);
    }
    seret.current = null;
  };

  /** Klik yang mengakhiri seretan bukan klik: jangan buka detail kotak yang kebetulan di bawah kursor. */
  const onClickCapture = (e: MouseEvent<HTMLDivElement>) => {
    if (!telanKlik.current) return;
    telanKlik.current = false;
    e.preventDefault();
    e.stopPropagation();
  };

  /** Papan ketik hanya saat viewport sendiri yang fokus, supaya panah di dalam menu tetap milik menu. */
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget) return;
    const aksi: Record<string, () => void> = {
      ArrowLeft: () => geserOleh(LANGKAH_PANAH, 0),
      ArrowRight: () => geserOleh(-LANGKAH_PANAH, 0),
      ArrowUp: () => geserOleh(0, LANGKAH_PANAH),
      ArrowDown: () => geserOleh(0, -LANGKAH_PANAH),
      "+": zoomMasuk,
      "=": zoomMasuk,
      "-": zoomKeluar,
      "0": pasUlang,
    };
    const jalankan = aksi[e.key];
    if (!jalankan) return;
    e.preventDefault();
    jalankan();
  };

  return {
    viewportRef,
    kontenRef,
    tampilan,
    sedangSeret,
    zoomMasuk,
    zoomKeluar,
    zoomAsli,
    pasUlang,
    viewportProps: {
      onPointerDown,
      onPointerMove,
      onPointerUp: akhiriSeret,
      onPointerCancel: akhiriSeret,
      onClickCapture,
      onKeyDown,
    },
  };
}
