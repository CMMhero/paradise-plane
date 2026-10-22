/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: struktur divisi -> departemen -> project (KEP-29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu tempat untuk seluruh struktur: peta organisasi di atas (klik untuk
 * lompat), panel "belum ditempatkan" untuk penempatan cepat, lalu kartu per
 * divisi/departemen. Buat/ubah/hapus divisi & departemen, pindah departemen ke
 * divisi lain, pilih project departemen, dan tempatkan orang (staf/supervisor
 * ke departemen, manager ke divisi). Penempatan ke divisi otomatis menaikkan
 * jenjang ke Manager — tak perlu bolak-balik ke halaman Member.
 */

import { useState } from "react";
import useSWR from "swr";
// plane imports
import { Button } from "@plane/propel/button";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import {
  InstanceHierarkiService,
  InstanceOrganisasiService,
  TINGKAT_MANAGER,
  TINGKAT_MEMBER,
  type TAnggotaHierarki,
  type TPohonOrganisasi,
} from "@plane/services";
import { Loader } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
// local
import { GodmodeLangToggle, useGodmodeStrings } from "@/app/i18n/godmode";
import { inputClass } from "../members/constants";
import { KartuDepartemen, KartuDivisi, PanelBelumDitempatkan, PohonOrganisasi, type TAksiOrganisasi } from "./kartu";
import { BarisProjectLama } from "./project-lama";

const layanan = new InstanceOrganisasiService();
const hierarkiService = new InstanceHierarkiService();

const pesanGagal = (err: unknown, fallback: string): string => {
  const pesan = (err as { error?: string } | undefined)?.error;
  return typeof pesan === "string" && pesan.length > 0 ? pesan : fallback;
};

const lompat = (id: string) => {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
};

export default function OrganisasiPage() {
  const { s, lang, setLang, fill } = useGodmodeStrings();
  const { data, mutate, isLoading } = useSWR("INSTANCE_ORGANISASI", () => layanan.pohon());
  // Sumber calon penempatan + kunci yang sama dengan halaman Member, supaya
  // perubahan di sini langsung terlihat di sana.
  const { data: hierarki, mutate: mutateHierarki } = useSWR(["INSTANCE_HIERARKI"], () => hierarkiService.ringkasan());
  const [cari, setCari] = useState("");

  /** Aksi struktur: balasan server = pohon terbaru, jadi tidak perlu fetch ulang. */
  const jalankan = async (aksi: () => Promise<TPohonOrganisasi>, berhasil: string): Promise<void> => {
    try {
      await mutate(await aksi(), { revalidate: false });
      await mutateHierarki();
      setToast({ type: TOAST_TYPE.SUCCESS, title: berhasil });
    } catch (err) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: s.org.save_failed,
        message: pesanGagal(err, s.org.save_failed_message),
      });
    }
  };

  const aksi: TAksiOrganisasi = {
    ubahDivisi: (id, kode, nama) =>
      jalankan(() => layanan.ubahDivisi(id, { kode, nama }), fill(s.org.division_saved, { kode })),
    hapusDivisi: (id) => jalankan(() => layanan.hapusDivisi(id), s.org.division_deleted),
    ubahDepartemen: (id, isi) => jalankan(() => layanan.ubahDepartemen(id, isi), s.org.department_saved),
    simpanProject: (id, projectIds) =>
      jalankan(() => layanan.ubahDepartemen(id, { project_ids: projectIds }), s.org.department_saved),
    hapusDepartemen: (id) => jalankan(() => layanan.hapusDepartemen(id), s.org.department_deleted),
    tempatkan: async (orang: TAnggotaHierarki, tujuan) => {
      try {
        // Penempatan ke divisi = peran manager: naikkan jenjang sekalian bila
        // masih di bawah Manager (supervisor/staf/belum-diisi). Satu panggilan =
        // satu sinkron akses di server.
        const naikKeManager =
          tujuan.divisi_id !== undefined &&
          tujuan.divisi_id !== null &&
          orang.tingkat !== null &&
          orang.tingkat < TINGKAT_MANAGER;
        await hierarkiService.setel({
          member_id: orang.id,
          ...(orang.tingkat === null && tujuan.departemen_id ? { tingkat: TINGKAT_MEMBER } : {}),
          ...(naikKeManager ? { tingkat: TINGKAT_MANAGER } : {}),
          ...tujuan,
        });
        await Promise.all([mutate(), mutateHierarki()]);
        const keluar = tujuan.departemen_id === null || tujuan.divisi_id === null;
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: fill(keluar ? s.org.person_removed : s.org.person_placed, { name: orang.display_name }),
          message: s.org.placed_message,
        });
      } catch (err) {
        setToast({ type: TOAST_TYPE.ERROR, title: s.org.failed, message: pesanGagal(err, s.org.save_failed_message) });
      }
    },
    ubahTingkat: async (orang: TAnggotaHierarki, tingkat: number) => {
      try {
        await hierarkiService.setel({ member_id: orang.id, tingkat });
        await Promise.all([mutate(), mutateHierarki()]);
        setToast({ type: TOAST_TYPE.SUCCESS, title: s.org.department_saved });
      } catch (err) {
        setToast({ type: TOAST_TYPE.ERROR, title: s.org.failed, message: pesanGagal(err, s.org.save_failed_message) });
      }
    },
  };

  const semuaProject = data
    ? [...data.divisi.flatMap((v) => v.departemen.flatMap((d) => d.projects)), ...data.tanpa_departemen]
    : [];
  const namaProject = Object.fromEntries(semuaProject.map((p) => [p.id, `${p.identifier} · ${p.name}`]));
  const namaDivisi = Object.fromEntries((data?.divisi ?? []).map((v) => [v.id, v.nama]));
  const namaDepartemen = Object.fromEntries(
    (data?.divisi ?? []).flatMap((v) => v.departemen.map((d) => [d.id, `${d.kode} ${d.nama}`]))
  );
  const semuaDivisi = (data?.divisi ?? []).map((v) => ({ id: v.id, nama: v.nama, kode: v.kode }));
  const orang = (hierarki?.anggota ?? []).filter((o) => o.is_active);

  return (
    <PageWrapper
      size="lg"
      header={{
        title: s.org.title,
        description: s.org.description,
        actions: <GodmodeLangToggle lang={lang} onChange={setLang} />,
      }}
    >
      {isLoading || !data ? (
        <Loader className="space-y-2">
          <Loader.Item height="64px" />
          <Loader.Item height="64px" />
        </Loader>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <input
              className={`${inputClass} max-w-sm min-w-[220px] flex-1`}
              placeholder={s.org.search_person}
              aria-label={s.org.search_person}
              value={cari}
              onChange={(e) => setCari(e.target.value)}
            />
            <FormBaru
              label={s.org.new_division}
              simpanLabel={s.org.add}
              onSimpan={(kode, nama) =>
                jalankan(() => layanan.buatDivisi({ kode, nama }), fill(s.org.division_created, { kode }))
              }
            />
          </div>

          <PohonOrganisasi pohon={data} hierarki={hierarki?.anggota ?? []} onLompat={lompat} />

          <PanelBelumDitempatkan
            orang={hierarki?.anggota ?? []}
            pohon={data}
            namaDepartemen={namaDepartemen}
            namaDivisi={namaDivisi}
            aksi={aksi}
          />

          {data.divisi.length === 0 && <p className="text-13 text-secondary">{s.org.no_division}</p>}

          {data.divisi.map((divisi) => (
            <KartuDivisi
              key={divisi.id}
              divisi={divisi}
              aksi={aksi}
              orang={orang}
              namaDivisi={namaDivisi}
              namaDepartemen={namaDepartemen}
              cariGlobal={cari}
            >
              {divisi.departemen.map((dep) => (
                <KartuDepartemen
                  // Kunci ikut daftar project, supaya pilihan lokal di-reset sesudah disimpan.
                  key={`${dep.id}-${dep.projects.map((p) => p.id).join(",")}`}
                  dep={dep}
                  divisiId={divisi.id}
                  semuaDivisi={semuaDivisi}
                  opsiProject={semuaProject.map((p) => p.id)}
                  namaProject={namaProject}
                  aksi={aksi}
                  orang={orang}
                  namaDepartemen={namaDepartemen}
                  namaDivisi={namaDivisi}
                  cariGlobal={cari}
                />
              ))}
              <FormBaru
                label={s.org.new_department}
                simpanLabel={s.org.add}
                onSimpan={(kode, nama) =>
                  jalankan(
                    () => layanan.buatDepartemen({ divisi_id: divisi.id, kode, nama }),
                    fill(s.org.department_created, { kode })
                  )
                }
              />
            </KartuDivisi>
          ))}

          {data.tanpa_departemen.length > 0 && (
            <section className="space-y-2">
              <h2 className="text-13 font-semibold text-primary">
                {fill(s.org.legacy_title, { n: data.tanpa_departemen.length })}
              </h2>
              <p className="text-11 text-secondary">
                {s.org.legacy_description}
                {semuaDivisi.length === 0 && s.org.legacy_create_first}
              </p>
              {data.tanpa_departemen.map((p) => (
                <BarisProjectLama
                  key={p.id}
                  project={p}
                  semuaDivisi={semuaDivisi}
                  onJadikan={async (isi) => {
                    try {
                      const hasil = await layanan.jadikanDepartemen(isi);
                      await mutate(hasil.pohon, { revalidate: false });
                      await mutateHierarki();
                      setToast({
                        type: TOAST_TYPE.SUCCESS,
                        title: fill(s.org.legacy_done, { kode: isi.kode }),
                        message: fill(s.org.legacy_done_message, {
                          a: hasil.ditempatkan,
                          b: hasil.dilewati
                            ? fill(s.org.legacy_done_skipped, { n: hasil.dilewati })
                            : s.org.legacy_done_all,
                        }),
                      });
                    } catch (err) {
                      setToast({
                        type: TOAST_TYPE.ERROR,
                        title: s.org.failed,
                        message: pesanGagal(err, s.org.save_failed_message),
                      });
                    }
                  }}
                />
              ))}
            </section>
          )}
        </div>
      )}
    </PageWrapper>
  );
}

function FormBaru({
  label,
  simpanLabel,
  onSimpan,
}: {
  label: string;
  simpanLabel: string;
  onSimpan: (kode: string, nama: string) => Promise<void>;
}) {
  const { s } = useGodmodeStrings();
  const [kode, setKode] = useState("");
  const [nama, setNama] = useState("");
  const [sibuk, setSibuk] = useState(false);
  const siap = kode.trim().length > 0 && nama.trim().length > 0 && !sibuk;

  const simpan = async () => {
    setSibuk(true);
    await onSimpan(kode.trim(), nama.trim());
    setSibuk(false);
    setKode("");
    setNama("");
  };

  return (
    <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
      <span className="text-11 text-secondary">{label}</span>
      <input
        className={`${inputClass} w-28`}
        placeholder={s.org.code_placeholder}
        aria-label={s.org.code_placeholder}
        maxLength={20}
        value={kode}
        onChange={(e) => setKode(e.target.value)}
      />
      <input
        className={`${inputClass} min-w-[180px] flex-1`}
        placeholder={s.org.name_placeholder}
        aria-label={s.org.name_placeholder}
        value={nama}
        onChange={(e) => setNama(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && siap) void simpan();
        }}
      />
      <Button variant="secondary" size="sm" disabled={!siap} onClick={simpan}>
        {simpanLabel}
      </Button>
    </div>
  );
}
