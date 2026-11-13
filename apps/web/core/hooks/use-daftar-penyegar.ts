/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: daftarkan penarik data sebuah layar
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef } from "react";
import { daftarkanPenyegar } from "@/lib/data-live";

type TOpsi = {
  /** Jenis sinyal yang membuat layar ini menarik ulang (`JENIS_TUGAS`, dst.). */
  jenis: readonly string[];
  /** Id project yang diurus layar ini; kosong = semua project. */
  proyek?: string | null;
  /** Id tugas yang diurus layar ini (detail/peek); kosong = tak dibatasi. */
  tugas?: string | null;
  /** Fungsi penarik. Boleh berubah tiap render; yang terbaru selalu dipakai. */
  tarik: () => Promise<unknown> | unknown;
  /** Matikan pendaftaran (mis. data belum siap dimuat). */
  aktif?: boolean;
};

/**
 * Daftarkan penarik layar ke `data-live`, sehingga sinyal dari server dan tombol
 * segarkan ikut menyegarkan layar ini. Dipakai layar yang datanya hidup di store
 * MobX (kunci SWR tidak butuh ini: ia ditarik lewat `mutate`).
 */
export function useDaftarPenyegar({ jenis, proyek, tugas, tarik, aktif = true }: TOpsi) {
  const tarikTerbaru = useRef(tarik);
  useEffect(() => {
    tarikTerbaru.current = tarik;
  });

  const kunciJenis = jenis.join("|");
  useEffect(() => {
    if (!aktif) return;
    return daftarkanPenyegar({
      jenis: kunciJenis.split("|"),
      proyek,
      tugas,
      tarik: () => tarikTerbaru.current(),
    });
  }, [kunciJenis, proyek, tugas, aktif]);
}
