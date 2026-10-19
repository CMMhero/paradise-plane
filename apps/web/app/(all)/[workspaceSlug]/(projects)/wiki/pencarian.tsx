/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pencarian Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import useSWR from "swr";
// components
import { GridKartu, KartuKerangka, KartuMateri } from "@/components/wiki/kartu";
// services
import { WikiMaterialService, type TMateriWiki } from "@/services/wiki_material.service";
// local imports
import { labelTipe, ukuranTerbaca } from "./data";

const layanan = new WikiMaterialService();

type THasil = TMateriWiki & { topic_id: string | null; breadcrumb: string[] };

/**
 * Kotak "Cari materi..." yang benar-benar mencari materi.
 *
 * Ia menembak seluruh Wiki, bukan menyaring kartu yang kebetulan sedang di
 * layar, karena orang mencari justru ketika BELUM tahu materinya ada di divisi
 * mana. Yang dicocokkan judul dan nama berkasnya; isi dokumennya tidak, dan
 * kalimat di bawah kotaknya mengatakan itu terus terang alih-alih membiarkan
 * orang mengira pencariannya rusak.
 */
export function PencarianWiki({
  workspaceSlug,
  projectId,
  onAktif,
}: {
  workspaceSlug: string;
  projectId: string;
  onAktif: (aktif: boolean) => void;
}) {
  const [kueri, setKueri] = useState("");
  const [tertunda, setTertunda] = useState("");

  // Ditunda supaya tiap ketukan tombol tidak jadi satu permintaan.
  useEffect(() => {
    const id = setTimeout(() => setTertunda(kueri.trim()), 300);
    return () => clearTimeout(id);
  }, [kueri]);

  const aktif = tertunda.length >= 2;
  useEffect(() => onAktif(kueri.trim().length >= 2), [kueri, onAktif]);

  const { data, isLoading } = useSWR(
    aktif ? `WIKI_SEARCH_${projectId}_${tertunda}` : null,
    aktif ? () => layanan.search(workspaceSlug, projectId, tertunda) : null,
    { revalidateOnFocus: false, keepPreviousData: true }
  );
  const hasil = (data?.materials ?? []) as THasil[];

  return (
    <>
      <div className="relative max-w-md">
        <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-placeholder" />
        <input
          type="text"
          value={kueri}
          onChange={(e) => setKueri(e.target.value)}
          placeholder="Cari materi..."
          className="w-full rounded-full border border-subtle bg-layer-2 py-2 pr-3 pl-9 text-13 text-primary transition-colors outline-none placeholder:text-placeholder focus:border-accent-strong"
        />
      </div>

      {kueri.trim().length >= 2 && (
        <div className="mt-6">
          <div className="mb-4 flex items-baseline gap-2">
            <h2 className="text-15 font-semibold text-primary">Hasil pencarian</h2>
            <span className="rounded-full bg-layer-3 px-2 py-0.5 text-11 text-tertiary">
              {isLoading ? "mencari…" : `${hasil.length} materi`}
            </span>
          </div>

          {isLoading && hasil.length === 0 ? (
            <GridKartu>
              {[0, 1, 2, 3].map((i) => (
                <KartuKerangka key={i} />
              ))}
            </GridKartu>
          ) : hasil.length === 0 ? (
            <div className="rounded-lg border border-dashed border-subtle px-6 py-14 text-center">
              <p className="text-14 font-medium text-secondary">Tidak ada materi bernama &quot;{tertunda}&quot;</p>
              <p className="mt-1 text-12 text-tertiary">
                Pencarian mencocokkan judul dan nama berkas, bukan isi dokumennya.
              </p>
            </div>
          ) : (
            <GridKartu>
              {hasil.map((m) => (
                <KartuMateri
                  key={m.id}
                  to={`/${workspaceSlug}/wiki/materi/${m.id}`}
                  judul={m.title}
                  keterangan={m.breadcrumb.filter(Boolean).join(" › ") || "Wiki"}
                  tipe={m.type}
                  label={labelTipe(m.type)}
                  ukuran={ukuranTerbaca(m.size)}
                />
              ))}
            </GridKartu>
          )}
        </div>
      )}
    </>
  );
}
