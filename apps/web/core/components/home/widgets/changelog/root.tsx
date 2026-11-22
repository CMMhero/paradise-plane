/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: widget Changelog di Home
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Dulunya catatan rilis hidup sebagai kanal "Changelogs" di Obrolan. Sekarang
 * ia widget Home biasa: bisa dimatikan dan diurut lewat "Manage widgets". Awalnya
 * hanya rilis terbaru yang dimuat; "Lihat rilis sebelumnya" memuat seluruhnya
 * sampai rilis tertua.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { Loader } from "@plane/ui";
// hooks
import { useAturan } from "@/hooks/use-aturan";
// services
import { ChangelogService } from "@/services/changelog.service";
import type { TCatatanRilis, TJenisEntri } from "@/services/changelog.service";
import type { THomeWidgetProps } from "@plane/types";

const changelogService = new ChangelogService();
/** Sama dengan `BATAS_MAKS` di views/changelog.py: seluruh riwayat dalam satu permintaan. */
const BATAS_SEMUA = 1000;

const URUTAN_ENTRI: TJenisEntri[] = ["Added", "Changed", "Fixed"];

const GAYA_ENTRI: Record<TJenisEntri, string> = {
  Added: "bg-success-subtle text-success-primary",
  Changed: "bg-accent-subtle text-accent-primary",
  Fixed: "bg-warning-subtle text-warning-primary",
};

const KUNCI_ENTRI: Record<TJenisEntri, string> = {
  Added: "chatkartu_ui.type_added",
  Changed: "chatkartu_ui.type_changed",
  Fixed: "chatkartu_ui.type_fixed",
};

function KartuRilis({ catatan }: { catatan: TCatatanRilis }) {
  const { t } = useTranslation();
  // Dikelompokkan per jenis supaya "apa yang baru" terbaca dulu, apa pun
  // urutan penulisannya di berkas catatan rilis.
  const urut = URUTAN_ENTRI.flatMap((jenis) => catatan.entri.filter((e) => e.type === jenis));
  return (
    <article className="flex flex-col gap-2 rounded-card border border-subtle bg-surface-1 p-4">
      <div className="flex items-baseline justify-between gap-3 border-b border-subtle pb-1.5">
        <h3 className="text-13 font-semibold text-primary">{t("chatkartu_ui.release", { version: catatan.versi })}</h3>
        {catatan.tanggal ? <p className="shrink-0 text-12 text-tertiary">{catatan.tanggal}</p> : null}
      </div>
      <ul className="flex flex-col gap-1.5">
        {urut.map((e) => (
          <li key={`${e.type}-${e.text}`} className="flex items-start gap-2 text-13 text-secondary">
            <span
              className={`mt-px w-auto min-w-16 shrink-0 rounded-control px-1.5 py-px text-center text-11 font-medium whitespace-nowrap ${GAYA_ENTRI[e.type]}`}
            >
              {t(KUNCI_ENTRI[e.type])}
            </span>
            <span className="min-w-0 [overflow-wrap:anywhere]">{e.text}</span>
          </li>
        ))}
      </ul>
    </article>
  );
}

export const ChangelogWidget = observer(function ChangelogWidget({ workspaceSlug }: THomeWidgetProps) {
  const { t } = useTranslation();
  const [semua, setSemua] = useState(false);
  // Rilis yang tampil sebelum "Lihat rilis sebelumnya" dibuka (aturan CHANGELOG_RELEASES_SHOWN).
  const jumlahAwal = useAturan().get("CHANGELOG_RELEASES_SHOWN");
  // Satu lebih banyak dari yang tampil, hanya untuk tahu masih ada rilis lama atau tidak.
  // Sesudah dibuka, seluruh riwayat dimuat; datanya bertahan selama permintaan baru berjalan.
  // 0 = widget dimatikan lewat God Mode: tidak ada yang digambar, dan tidak ada request.
  const { data, error, mutate, isValidating } = useSWR(
    jumlahAwal > 0 ? `HOME_CHANGELOG_${workspaceSlug}_${semua ? "semua" : jumlahAwal}` : null,
    () => changelogService.getCatatanRilis(workspaceSlug, semua ? BATAS_SEMUA : jumlahAwal + 1),
    { revalidateOnFocus: false, dedupingInterval: 60_000, keepPreviousData: true }
  );

  // Belum ada rilis tercatat: widget tidak perlu memenuhi Home dengan
  // kotak kosong. Gagal memuat tetap ditunjukkan, supaya "kosong" dan "rusak" tidak sama.
  if (data && data.length === 0) return null;
  if (jumlahAwal <= 0) return null;

  const tampil = data ? (semua ? data : data.slice(0, jumlahAwal)) : [];
  const adaLebihLama = !!data && data.length > jumlahAwal;

  return (
    <section aria-labelledby="home-changelog-title" className="flex flex-col gap-3">
      <h2 id="home-changelog-title" className="text-14 font-semibold text-primary">
        {t("changelog_ui.title")}
      </h2>
      {!data ? (
        error ? (
          <div
            role="alert"
            className="flex flex-wrap items-center justify-between gap-2 rounded-card border border-subtle px-4 py-3 text-13 text-tertiary"
          >
            <span>{t("pengumuman_ui.load_failed")}</span>
            <Button variant="secondary" size="base" onClick={() => void mutate()}>
              {t("common.retry")}
            </Button>
          </div>
        ) : (
          <Loader>
            <span className="sr-only">{t("common.loading")}</span>
            <Loader.Item height="120px" />
          </Loader>
        )
      ) : (
        <>
          {tampil.map((catatan) => (
            <KartuRilis key={catatan.id} catatan={catatan} />
          ))}
          {adaLebihLama ? (
            <div>
              <Button
                variant="secondary"
                size="base"
                onClick={() => setSemua((v) => !v)}
                loading={semua && isValidating}
              >
                {semua ? t("changelog_ui.show_less") : t("changelog_ui.show_more")}
              </Button>
            </div>
          ) : null}
        </>
      )}
    </section>
  );
});
