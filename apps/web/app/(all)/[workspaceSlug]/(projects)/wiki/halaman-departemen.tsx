/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: halaman departemen di Wiki (KEP-95, KEP-97)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { Eye, FileText, Globe2, Lock } from "lucide-react";
import { Link } from "react-router";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { Logo } from "@plane/propel/emoji-icon-picker";
import { EModalPosition, EModalWidth, ModalCore } from "@plane/ui";
import { cn, renderFormattedDate, sanitizeRichHTML } from "@plane/utils";
// services
import type { TWikiDepartmentPage } from "@/services/wiki.service";
// local imports
import { layananWiki } from "./data";

type TProps = {
  workspaceSlug: string;
  folderId: string;
};

const KELAS_BARIS =
  "flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-layer-1-hover focus-visible:bg-layer-1-hover";

/**
 * Halaman (Pages) project departemen, ditampilkan di folder departemennya.
 *
 * Halamannya tetap tinggal di project departemen; Wiki hanya mendaftarnya.
 * Siapa melihat halaman privat diputuskan server; klien tidak menyaring apa pun.
 *
 * Klik = buka halaman aslinya di project, di tab yang sama (KEP-97). Halaman
 * yang terlihat di Wiki tapi tidak akan terbuka di project menurut aturan Plane
 * (`can_open_in_project` false: bukan anggota project, atau privat orang lain)
 * dibuka di jendela baca sebagai gantinya, supaya tidak berakhir di halaman
 * "tidak ditemukan".
 */
export function HalamanDepartemen({ workspaceSlug, folderId }: TProps) {
  const { t } = useTranslation();
  const [terpilih, setTerpilih] = useState<TWikiDepartmentPage | null>(null);
  const { data, isLoading, error } = useSWR(`WIKI_DEPARTMENT_PAGES_${workspaceSlug}_${folderId}`, () =>
    layananWiki.fetchDepartmentPages(workspaceSlug, folderId)
  );

  if (isLoading) return null;
  // Departemen tanpa project tidak punya halaman untuk ditampilkan.
  if (!error && !data?.departemen) return null;
  const halaman = data?.pages ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-baseline gap-2">
        <h2 className="text-14 font-semibold text-primary">{t("wiki_ui.pages.title")}</h2>
        {data?.departemen && (
          <>
            <span className="rounded-control bg-layer-3 px-2 py-0.5 text-11 text-tertiary">{halaman.length}</span>
            <span className="text-12 text-tertiary">
              {t("wiki_ui.pages.from_department", { name: data.departemen.nama })}
            </span>
          </>
        )}
      </div>

      {error ? (
        <p className="text-13 text-tertiary">{t("wiki_ui.pages.load_failed")}</p>
      ) : halaman.length === 0 ? (
        <p className="rounded-card border border-dashed border-subtle px-6 py-8 text-center text-13 text-tertiary">
          {t("wiki_ui.pages.empty")}
        </p>
      ) : (
        <ul className="divide-y divide-subtle overflow-hidden rounded-card border border-subtle bg-layer-1">
          {halaman.map((h) => (
            <li key={h.id}>
              {h.can_open_in_project ? (
                <Link to={`/${workspaceSlug}/projects/${h.project_id}/pages/${h.id}`} className={KELAS_BARIS}>
                  <IsiBaris halaman={h} />
                </Link>
              ) : (
                <button
                  type="button"
                  onClick={() => setTerpilih(h)}
                  className={KELAS_BARIS}
                  title={t("wiki_ui.pages.read_only_hint")}
                >
                  <IsiBaris halaman={h} hanyaBaca />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {terpilih && <BacaHalaman workspaceSlug={workspaceSlug} halaman={terpilih} onClose={() => setTerpilih(null)} />}
    </div>
  );
}

function IsiBaris({ halaman, hanyaBaca }: { halaman: TWikiDepartmentPage; hanyaBaca?: boolean }) {
  const { t } = useTranslation();
  return (
    <>
      <span className="grid size-8 shrink-0 place-items-center rounded-control bg-layer-3 text-secondary">
        {halaman.logo_props?.in_use ? (
          <Logo logo={halaman.logo_props} size={16} type="lucide" />
        ) : (
          <FileText className="size-4" />
        )}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-13 font-medium text-primary">
          {halaman.name || t("wiki_ui.pages.untitled")}
        </span>
        <span className="block truncate text-11 text-tertiary">
          {t("wiki_ui.pages.from_department", { name: halaman.departemen_nama })} ·{" "}
          {renderFormattedDate(halaman.updated_at)}
        </span>
      </span>
      {hanyaBaca && (
        <span className="inline-flex shrink-0 items-center gap-1 text-11 text-tertiary">
          <Eye className="size-3" />
          {t("wiki_ui.pages.read_only")}
        </span>
      )}
      <LencanaAkses akses={halaman.access} />
    </>
  );
}

export function LencanaAkses({ akses }: { akses: TWikiDepartmentPage["access"] }) {
  const { t } = useTranslation();
  const privat = akses === "private";
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-control px-2 py-0.5 text-11 font-medium",
        privat ? "bg-layer-3 text-secondary" : "bg-accent-subtle text-accent-primary"
      )}
      title={privat ? t("wiki_ui.pages.private_hint") : undefined}
    >
      {privat ? <Lock className="size-3" /> : <Globe2 className="size-3" />}
      {privat ? t("wiki_ui.pages.private") : t("wiki_ui.pages.public")}
    </span>
  );
}

type TBaca = {
  workspaceSlug: string;
  halaman: TWikiDepartmentPage;
  onClose: () => void;
};

/**
 * Cadangan hanya-baca untuk halaman yang tidak akan terbuka di project bagi
 * orang ini. Halaman yang bisa dibuka tidak pernah sampai ke sini.
 */
export function BacaHalaman({ workspaceSlug, halaman, onClose }: TBaca) {
  const { t } = useTranslation();
  const { data, isLoading, error } = useSWR(`WIKI_DEPARTMENT_PAGE_${workspaceSlug}_${halaman.id}`, () =>
    layananWiki.fetchDepartmentPage(workspaceSlug, halaman.id)
  );
  const isi = data?.description_html ? sanitizeRichHTML(data.description_html).trim() : "";

  return (
    <ModalCore isOpen handleClose={onClose} position={EModalPosition.CENTER} width={EModalWidth.XXXL}>
      <div className="flex max-h-[80vh] flex-col">
        <div className="border-b border-subtle px-5 py-4">
          <p className="text-11 text-tertiary">
            {t("wiki_ui.pages.from_department", { name: halaman.departemen_nama })}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <h3 className="min-w-0 flex-1 truncate text-16 font-semibold text-primary">
              {halaman.name || t("wiki_ui.pages.untitled")}
            </h3>
            <LencanaAkses akses={halaman.access} />
          </div>
          <p className="mt-2 text-12 text-tertiary">{t("wiki_ui.pages.read_only_hint")}</p>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {isLoading ? (
            <div className="space-y-2">
              <div className="h-4 w-2/3 animate-pulse rounded-item bg-layer-3" />
              <div className="h-4 w-1/2 animate-pulse rounded-item bg-layer-3" />
            </div>
          ) : error ? (
            <p className="text-13 text-tertiary">{t("wiki_ui.pages.load_failed")}</p>
          ) : isi ? (
            <div
              className="text-13 text-secondary [&_a]:text-accent-primary [&_a]:underline [&_h1]:text-16 [&_h1]:font-semibold [&_h2]:text-14 [&_h2]:font-semibold [&_h3]:font-semibold [&_img]:max-w-full [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-1.5 [&_ul]:list-disc [&_ul]:pl-5"
              // Sudah disanitasi dengan allowlist (sanitizeRichHTML); hanya baca.
              // oxlint-disable-next-line react/no-danger
              dangerouslySetInnerHTML={{ __html: isi }}
            />
          ) : (
            <p className="text-13 text-tertiary">{t("wiki_ui.pages.no_content")}</p>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-subtle px-5 py-3">
          <Button variant="secondary" size="lg" onClick={onClose}>
            {t("wiki_ui.pages.close")}
          </Button>
        </div>
      </div>
    </ModalCore>
  );
}
