/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pencarian Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Fragment, useEffect, useMemo, useState } from "react";
import { FileText, Search } from "lucide-react";
import { Link } from "react-router";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import { Logo } from "@plane/propel/emoji-icon-picker";
import { Input } from "@plane/ui";
// services
import type { TWikiDepartmentPage, TWikiSearchSnippet } from "@/services/wiki.service";
// local imports
import { labelTipe, layananWiki, ukuranTerbaca } from "./data";
import { BacaHalaman, LencanaAkses } from "./halaman-departemen";

const KELAS_BARIS =
  "flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-layer-1-hover focus-visible:bg-layer-1-hover";

const escapeRegex = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Teks dengan kata-kata yang cocok ditebalkan. Tanpa HTML: isi berkas adalah unggahan orang. */
function Sorot({ teks, kata }: { teks: string; kata: string[] }) {
  const pola = useMemo(() => {
    // Salinan lewat spread; kata yang lebih panjang lebih dulu supaya "surat jalan" tidak terpotong oleh "surat".
    // oxlint-disable-next-line unicorn/no-array-sort
    const unik = [...new Set(kata.filter(Boolean))].sort((a, b) => b.length - a.length);
    return unik.length ? new RegExp(`(${unik.map(escapeRegex).join("|")})`, "gi") : null;
  }, [kata]);
  if (!pola) return <>{teks}</>;
  // Hasil split dengan grup penangkap: bagian ganjil = yang cocok. Kuncinya
  // posisi awal bagian di teks, unik dan tetap selama teksnya sama.
  const potongan = teks.split(pola);
  const bagian = potongan.map((isi, urutan) => ({
    isi,
    awal: potongan.slice(0, urutan).join("").length,
    cocok: urutan % 2 === 1,
  }));
  return (
    <>
      {bagian.map((b) =>
        b.cocok ? (
          <mark key={b.awal} className="rounded-sm bg-accent-subtle px-0.5 font-medium text-primary">
            {b.isi}
          </mark>
        ) : (
          <Fragment key={b.awal}>{b.isi}</Fragment>
        )
      )}
    </>
  );
}

function JudulBagian({ judul, angka }: { judul: string; angka: number }) {
  return (
    <div className="mb-2 flex items-baseline gap-2">
      <h3 className="text-13 font-semibold text-secondary">{judul}</h3>
      <span className="rounded-control bg-layer-3 px-2 py-0.5 text-11 text-tertiary">{angka}</span>
    </div>
  );
}

function Cuplikan({ hasil, kata }: { hasil: TWikiSearchSnippet; kata: string[] }) {
  if (!hasil.cuplikan) return null;
  return (
    <span className="mt-0.5 line-clamp-2 block text-12 text-secondary">
      <Sorot teks={hasil.cuplikan} kata={[...kata, ...hasil.sorot]} />
    </span>
  );
}

/**
 * Kotak "Cari materi dan halaman..." yang mencari seluruh Wiki.
 *
 * Ia menembak seluruh Wiki, bukan menyaring kartu yang kebetulan sedang di
 * layar, karena orang mencari justru ketika BELUM tahu materinya ada di divisi
 * mana. Server mencocokkan judul, nama berkas, ISI dokumen (PDF, Word, Excel,
 * teks), dan halaman departemen yang boleh dilihat orang ini; salah ketik kecil
 * tetap ketemu. Tiap hasil membawa potongan isi dengan kata yang cocok disorot.
 */
export function PencarianWiki({
  workspaceSlug,
  onAktif,
}: {
  workspaceSlug: string;
  onAktif: (aktif: boolean) => void;
}) {
  const { t } = useTranslation();
  const [kueri, setKueri] = useState("");
  const [tertunda, setTertunda] = useState("");
  const [halamanTerpilih, setHalamanTerpilih] = useState<TWikiDepartmentPage | null>(null);

  // Ditunda supaya tiap ketukan tombol tidak jadi satu permintaan.
  useEffect(() => {
    const id = setTimeout(() => setTertunda(kueri.trim()), 300);
    return () => clearTimeout(id);
  }, [kueri]);

  const aktif = tertunda.length >= 2;
  useEffect(() => onAktif(kueri.trim().length >= 2), [kueri, onAktif]);

  const { data, isLoading } = useSWR(
    aktif ? `WIKI_SEARCH_${workspaceSlug}_${tertunda}` : null,
    aktif ? () => layananWiki.search(workspaceSlug, tertunda) : null,
    { revalidateOnFocus: false, keepPreviousData: true }
  );
  const materi = data?.materials ?? [];
  const halaman = data?.pages ?? [];
  const total = materi.length + halaman.length;
  const kata = useMemo(
    () =>
      tertunda
        .toLowerCase()
        .split(/[^\p{L}\p{N}_]+/u)
        .filter((k) => k.length >= 2),
    [tertunda]
  );

  return (
    <>
      <div className="relative max-w-md">
        <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-placeholder" />
        <Input
          type="text"
          value={kueri}
          onChange={(e) => setKueri(e.target.value)}
          placeholder={t("wiki_ui.search.placeholder")}
          className="w-full search-field border border-subtle py-2 pr-3 pl-9 text-primary transition-colors placeholder:text-placeholder focus:border-accent-strong"
        />
      </div>

      {kueri.trim().length >= 2 && (
        <div className="mt-6 space-y-6">
          <div className="flex items-baseline gap-2">
            <h2 className="text-14 font-semibold text-primary">{t("wiki_ui.search.results")}</h2>
            <span className="rounded-control bg-layer-3 px-2 py-0.5 text-11 text-tertiary">
              {isLoading ? t("wiki_ui.search.searching") : total}
            </span>
          </div>

          {isLoading && total === 0 ? (
            <div className="space-y-2" aria-hidden>
              {["a", "b", "c"].map((k) => (
                <div key={k} className="h-14 animate-pulse rounded-card bg-layer-2" />
              ))}
            </div>
          ) : total === 0 ? (
            <div className="rounded-card border border-dashed border-subtle px-6 py-14 text-center">
              <p className="text-14 font-medium text-secondary">
                {t("wiki_ui.search.no_results", { query: tertunda })}
              </p>
              <p className="mt-1 text-12 text-tertiary">{t("wiki_ui.search.hint")}</p>
            </div>
          ) : (
            <>
              {materi.length > 0 && (
                <section>
                  <JudulBagian judul={t("wiki_ui.search.materials")} angka={materi.length} />
                  <ul className="divide-y divide-subtle overflow-hidden rounded-card border border-subtle bg-layer-1">
                    {materi.map((m) => (
                      <li key={m.id}>
                        <Link to={`/${workspaceSlug}/wiki/materi/${m.id}`} className={KELAS_BARIS}>
                          <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-control bg-layer-3 text-secondary">
                            <FileText className="size-4" />
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-13 font-medium text-primary">
                              <Sorot teks={m.judul} kata={kata} />
                            </span>
                            <span className="block truncate text-11 text-tertiary">
                              {[
                                m.jejak.map((j) => j.nama).join(" › ") || "Wiki",
                                labelTipe(m.type, t),
                                ukuranTerbaca(m.size),
                              ]
                                .filter(Boolean)
                                .join(" · ")}
                            </span>
                            <Cuplikan hasil={m} kata={kata} />
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {halaman.length > 0 && (
                <section>
                  <JudulBagian judul={t("wiki_ui.search.pages")} angka={halaman.length} />
                  <ul className="divide-y divide-subtle overflow-hidden rounded-card border border-subtle bg-layer-1">
                    {halaman.map((h) => {
                      const isi = (
                        <>
                          <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-control bg-layer-3 text-secondary">
                            {h.logo_props?.in_use ? (
                              <Logo logo={h.logo_props} size={16} type="lucide" />
                            ) : (
                              <FileText className="size-4" />
                            )}
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-13 font-medium text-primary">
                              <Sorot teks={h.name || t("wiki_ui.pages.untitled")} kata={kata} />
                            </span>
                            <span className="block truncate text-11 text-tertiary">
                              {t("wiki_ui.pages.from_department", { name: h.departemen_nama })}
                            </span>
                            <Cuplikan hasil={h} kata={kata} />
                          </span>
                          <LencanaAkses akses={h.access} />
                        </>
                      );
                      return (
                        <li key={h.id}>
                          {h.can_open_in_project ? (
                            <Link
                              to={`/${workspaceSlug}/projects/${h.project_id}/pages/${h.id}`}
                              className={KELAS_BARIS}
                            >
                              {isi}
                            </Link>
                          ) : (
                            <button type="button" onClick={() => setHalamanTerpilih(h)} className={KELAS_BARIS}>
                              {isi}
                            </button>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </section>
              )}
            </>
          )}
        </div>
      )}

      {halamanTerpilih && (
        <BacaHalaman workspaceSlug={workspaceSlug} halaman={halamanTerpilih} onClose={() => setHalamanTerpilih(null)} />
      )}
    </>
  );
}
