/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: editor dimuat saat dirender
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { forwardRef, lazy, Suspense, useState } from "react";
import type { ComponentType, ReactNode, RefAttributes } from "react";

/**
 * Bungkus komponen editor supaya `@plane/editor` (tiptap, prosemirror,
 * lowlight, yjs, data emoji; ±435 KB gzip) baru diunduh saat editor benar-benar
 * dirender.
 *
 * KENAPA
 * Barrel `@/components/editor/*` dulu mengekspor editornya langsung. Kartu
 * notifikasi di popover navigasi atas, modal buat work item di header daftar,
 * dan lain-lain mengimpor barrel itu, jadi SETIAP halaman workspace memuat
 * seluruh editor di bundel awalnya, padahal editor baru tampil setelah data
 * datang atau modal dibuka.
 *
 * Ref diteruskan ke editor asli (React.lazy meneruskan ref). Selama chunk
 * belum tiba `ref.current` masih null, sama seperti sebelum editor siap;
 * pemanggil sudah memakai `ref.current?.`.
 */
export type TPropsEditorMalas = {
  /** Ditampilkan selama chunk editor belum tiba. Bawaan: kosong. Isi dengan
   * kerangka seukuran editor bila lompatan tata letak terlihat. */
  fallbackMemuat?: ReactNode;
};

export function buatEditorMalas<TProps extends object, TRef>(
  muat: () => Promise<ComponentType<TProps & RefAttributes<TRef>>>,
  nama: string
) {
  type TEditor = ComponentType<TProps & RefAttributes<TRef>>;
  // Satu janji per modul: `muatAwal()` dan render pertama berbagi unduhan yang sama.
  let janji: Promise<{ default: TEditor }> | undefined;
  let termuat: TEditor | undefined;
  const muatSekali = () =>
    (janji ??= muat().then((c) => {
      termuat = c;
      return { default: c };
    }));
  // Tipe props `LazyExoticComponent` atas ComponentType generik tidak bisa
  // diselesaikan TS untuk ref; di runtime ia merender komponen yang sama.
  const Malas = lazy(muatSekali) as unknown as TEditor;
  const EditorMalas = forwardRef<TRef, TProps & TPropsEditorMalas>(function EditorMalas(props, ref) {
    const { fallbackMemuat = null, ...rest } = props;
    // React 18 `lazy` selalu menangguhkan sekali walau chunk sudah ada, jadi
    // kerangka sempat dilukis satu frame lalu diganti editor (lompatan tata
    // letak). Bila chunk sudah termuat (mis. lewat `muatAwal()`), render editor
    // aslinya langsung. Pilihan ini dikunci saat mount: berganti tipe elemen di
    // tengah jalan akan me-remount editor dan membuang isinya.
    const [Langsung] = useState(() => termuat);
    if (Langsung) return <Langsung {...(rest as TProps)} ref={ref} />;
    return (
      <Suspense fallback={fallbackMemuat}>
        <Malas {...(rest as TProps)} ref={ref} />
      </Suspense>
    );
  });
  EditorMalas.displayName = nama;
  /** Mulai mengunduh editor sebelum dirender, mis. saat data deskripsi masih dimuat. */
  const muatAwal = () => {
    muatSekali().catch(() => {
      // Gagal di sini tidak fatal: render berikutnya mencoba lagi lewat janji baru.
      janji = undefined;
    });
  };
  return Object.assign(EditorMalas, { muatAwal });
}
