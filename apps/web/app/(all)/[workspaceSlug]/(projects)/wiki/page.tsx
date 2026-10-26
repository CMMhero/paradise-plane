/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: beranda Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Plus } from "lucide-react";
import { useParams } from "react-router";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { getPageName } from "@plane/utils";
// components
import { PageHead } from "@/components/core/page-title";
import { GridKartu, KartuFolder, KartuKerangka } from "@/components/wiki/kartu";
// services
import { ProjectPageService } from "@/services/page";
// local imports
import { anakDari, halamanTerlihat, izinFolderDari, useIzinWiki, usePohonWiki, useProjectWiki } from "./data";
import { PencarianWiki } from "./pencarian";

const layananHalaman = new ProjectPageService();

/**
 * Beranda Wiki: pilih divisi.
 *
 * Ini rute Wiki yang sesungguhnya, bukan lagi pengalihan ke halaman daftar
 * Pages milik project. Bedanya terasa langsung: tidak ada tombol buat halaman,
 * tidak ada breadcrumb project, dan tidak ada Work Items, karena Wiki memang
 * bukan tempat mengerjakan tugas.
 */
function WikiBerandaPage() {
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  const { projectId, sedangMemuat: memuatProject } = useProjectWiki();
  const { halaman, sedangMemuat, muatUlang } = usePohonWiki(slug, projectId);
  const { izin } = useIzinWiki(slug, projectId);
  const [mencari, setMencari] = useState(false);
  const [sedangMembuat, setSedangMembuat] = useState(false);

  const terlihat = halamanTerlihat(halaman);
  const divisi = anakDari(terlihat, null);

  const buatDivisi = async () => {
    if (!projectId || sedangMembuat) return;
    setSedangMembuat(true);
    try {
      await layananHalaman.create(slug, projectId, { name: "Divisi baru" });
      await muatUlang();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: "Divisi dibuat",
        message:
          "Folder ini masih terkunci sampai divisi pemiliknya ditentukan. Buka menu di kartunya lalu pilih Kelola.",
      });
    } catch (error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Gagal",
        message: (error as { error?: string })?.error || "Divisi baru gagal dibuat.",
      });
    } finally {
      setSedangMembuat(false);
    }
  };

  if (!projectId && !memuatProject)
    return (
      <div className="flex h-full w-full items-center justify-center p-8 text-center">
        <div className="max-w-md">
          <h2 className="text-15 font-semibold text-primary">Wiki belum tersedia</h2>
          <p className="mt-1 text-13 text-tertiary">
            Wiki hidup di dalam sebuah project ber-identifier <span className="font-mono">WIKI</span>. Project itu belum
            ada di workspace ini, atau kamu belum menjadi anggotanya.
          </p>
          <p className="mt-3 text-13 text-tertiary">
            Kalau kamu admin workspace, buat project baru dengan identifier <span className="font-mono">WIKI</span> lalu
            tambahkan anggotanya. Kalau bukan, hubungi admin workspace.
          </p>
        </div>
      </div>
    );

  return (
    <>
      <PageHead title="Wiki Perusahaan" />
      <div className="flex h-full w-full flex-col overflow-y-auto">
        <div className="border-b border-subtle bg-surface-1 px-page-x py-8">
          <h1 className="text-3xl font-semibold tracking-tight text-primary">Wiki Perusahaan</h1>
          <p className="mt-1 max-w-2xl text-13 text-tertiary">
            Panduan, SOP, dan materi tiap divisi. Semua orang boleh membaca. Yang menaruh materi baru hanya divisi
            pemilik foldernya, dan hanya pengunggahnya sendiri yang bisa mengubah atau menghapusnya.
          </p>
          <div className="mt-5">
            {projectId && <PencarianWiki workspaceSlug={slug} projectId={projectId} onAktif={setMencari} />}
          </div>
        </div>

        {!mencari && (
          <div className="flex-1 px-page-x py-6">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="flex items-baseline gap-2">
                <h2 className="text-15 font-semibold text-primary">Pilih divisi</h2>
                <span className="rounded-full bg-layer-3 px-2 py-0.5 text-11 text-tertiary">
                  {divisi.length} divisi
                </span>
              </div>
              {izin?.is_project_admin && (
                <Button variant="primary" size="sm" onClick={buatDivisi} loading={sedangMembuat}>
                  <Plus className="size-3.5" />
                  Divisi baru
                </Button>
              )}
            </div>

            {sedangMemuat && divisi.length === 0 ? (
              <GridKartu>
                {[0, 1, 2, 3].map((i) => (
                  <KartuKerangka key={i} />
                ))}
              </GridKartu>
            ) : divisi.length === 0 ? (
              <div className="rounded-lg border border-dashed border-subtle px-6 py-14 text-center">
                <p className="text-14 font-medium text-secondary">Belum ada divisi di Wiki</p>
                <p className="mt-1 text-12 text-tertiary">
                  Admin project bisa menambahkannya lewat tombol di atas, lalu menentukan divisi pemiliknya di Setelan
                  project.
                </p>
              </div>
            ) : (
              <GridKartu>
                {divisi.map((d) => {
                  const izinFolder = izinFolderDari(izin, d.id);
                  const pemilik = izinFolder?.divisions.map((x) => x.name).join(", ");
                  return (
                    <KartuFolder
                      key={d.id}
                      to={`/${slug}/wiki/${d.id}`}
                      judul={getPageName(d.name)}
                      logoProps={d.logo_props}
                      terbuka={izinFolder?.is_general}
                      keterangan={
                        izinFolder?.is_general
                          ? "Terbuka dibaca semua karyawan"
                          : pemilik
                            ? `Dikelola ${pemilik}`
                            : "Belum ada divisi pengelola"
                      }
                      jumlahAnak={anakDari(terlihat, d.id).length}
                      satuanAnak="Materi"
                    />
                  );
                })}
              </GridKartu>
            )}
          </div>
        )}
      </div>
    </>
  );
}

export default observer(WikiBerandaPage);
