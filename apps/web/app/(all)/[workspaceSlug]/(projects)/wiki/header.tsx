/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kepala Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Library, Trash2 } from "lucide-react";
import { Link, useMatches, useNavigate } from "react-router";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import { getButtonStyling } from "@plane/propel/button";
import { Breadcrumbs, Header } from "@plane/ui";
// components
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
// local imports
import { jalurFolder, layananWiki, usePohonWiki } from "./data";

type TLangkah = { label: string; href?: string };

/**
 * Kepala Wiki: jalur lengkap tempat orang berada (Wiki > Divisi > Departemen >
 * Sub-topik > Materi), tiap langkahnya bisa diklik.
 *
 * Wiki dulu menumpang halaman daftar Pages project, dan kepalanya membawa serta
 * tombol "buat halaman" beserta breadcrumb project. Orang yang datang untuk
 * MEMBACA materi tidak sedang membuat halaman, dan pemilik instance benar
 * ketika bilang Wiki tidak seharusnya terlihat seperti project biasa.
 *
 * Header hidup di layout, jadi parameter halaman anak dibaca dari kecocokan
 * rute paling dalam (`useMatches`), bukan `useParams`.
 */
export const WikiHeader = observer(function WikiHeader() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const cocok = useMatches();
  const params = cocok.at(-1)?.params ?? {};
  const slug = params.workspaceSlug ?? "";
  const folderId = params.folderId;
  // `trash` adalah rute sendiri, bukan folder.
  const idMateri = params.assetId;

  const { folder } = usePohonWiki(slug);
  // Kunci dan pengambil sama dengan halaman materi, jadi tidak ada permintaan tambahan.
  const { data: materi } = useSWR(
    idMateri && slug ? `WIKI_MATERIAL_${idMateri}` : null,
    idMateri && slug ? () => layananWiki.fetchMaterial(slug, idMateri) : null
  );

  const langkah: TLangkah[] = [];
  if (idMateri) {
    for (const j of materi?.jejak ?? []) langkah.push({ label: j.nama, href: `/${slug}/wiki/${j.id}` });
    if (materi) langkah.push({ label: materi.judul });
  } else if (folderId) {
    for (const f of jalurFolder(folder ?? [], folderId)) langkah.push({ label: f.nama, href: `/${slug}/wiki/${f.id}` });
  }

  return (
    <Header>
      <Header.LeftItem>
        {/* Layar kecil hanya menampilkan langkah terakhir; tombol "..." naik satu tingkat. */}
        <Breadcrumbs
          onBack={
            langkah.length > 0
              ? () => void navigate(langkah.length > 1 ? (langkah.at(-2)?.href ?? `/${slug}/wiki`) : `/${slug}/wiki`)
              : undefined
          }
        >
          <Breadcrumbs.Item
            component={
              <BreadcrumbLink
                label="Wiki"
                href={langkah.length > 0 ? `/${slug}/wiki` : undefined}
                icon={<Library className="h-4 w-4 text-tertiary" />}
                isLast={langkah.length === 0}
              />
            }
          />
          {langkah.map((l, i) => (
            <Breadcrumbs.Item
              key={l.href ?? `akhir-${l.label}`}
              component={
                <BreadcrumbLink
                  label={l.label}
                  href={i === langkah.length - 1 ? undefined : l.href}
                  isLast={i === langkah.length - 1}
                />
              }
            />
          ))}
        </Breadcrumbs>
      </Header.LeftItem>
      <Header.RightItem>
        <Link to={`/${slug}/wiki/trash`} className={getButtonStyling("secondary", "base")}>
          <Trash2 className="size-3.5" />
          {t("wiki_ui.trash.button")}
        </Link>
      </Header.RightItem>
    </Header>
  );
});
