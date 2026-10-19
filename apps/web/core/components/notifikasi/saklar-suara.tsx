/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: saklar suara pemberitahuan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Volume2, VolumeX } from "lucide-react";
import { useSuaraNotifikasi } from "@/hooks/use-suara-notifikasi";

/**
 * SATU saklar untuk seluruh bunyi pemberitahuan, bukan satu per jenis.
 *
 * Ditempatkan di dua tempat, dan itu bukan duplikasi: keduanya menulis ke kunci
 * penyimpanan yang sama. Orang yang terganggu bunyi pesan mencarinya di halaman
 * Obrolan, orang yang terganggu bunyi tugas mencarinya di panel Pemberitahuan,
 * dan keduanya menemukan saklar yang sama.
 */
export const SaklarSuara = ({ className = "" }: { className?: string }) => {
  const { nyala, setNyala } = useSuaraNotifikasi();

  return (
    <button
      type="button"
      onClick={() => setNyala(!nyala)}
      aria-label={nyala ? "Matikan suara notifikasi" : "Nyalakan suara notifikasi"}
      title={nyala ? "Suara notifikasi menyala" : "Suara notifikasi mati"}
      className={`flex size-9 shrink-0 items-center justify-center rounded-md text-tertiary hover:bg-layer-1 hover:text-secondary ${className}`}
    >
      {nyala ? <Volume2 className="size-4" /> : <VolumeX className="size-4" />}
    </button>
  );
};
