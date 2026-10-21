/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: struktur divisi -> departemen -> project (KEP-29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu tempat untuk seluruh struktur: buat/ubah/hapus divisi & departemen, pindah
 * departemen ke divisi lain, pilih project departemen, dan tempatkan orang
 * (staf/supervisor ke departemen, manager ke divisi). Mengisi divisi pertama
 * menyalakan aturan jangkauan: akses project lalu mengikuti penempatan.
 */

import { useState } from "react";
import useSWR from "swr";
// plane imports
import { Button } from "@plane/propel/button";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import {
  InstanceHierarkiService,
  InstanceOrganisasiService,
  TINGKAT_MEMBER,
  type TAnggotaHierarki,
  type TPohonOrganisasi,
} from "@plane/services";
import { Loader } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
// local
import { inputClass } from "../members/constants";
import { KartuDepartemen, KartuDivisi, type TAksiOrganisasi } from "./kartu";
import { BarisProjectLama } from "./project-lama";

const layanan = new InstanceOrganisasiService();
const hierarkiService = new InstanceHierarkiService();

const pesanGagal = (err: unknown): string => {
  const pesan = (err as { error?: string } | undefined)?.error;
  return typeof pesan === "string" && pesan.length > 0 ? pesan : "Tidak bisa menyimpan.";
};

export default function OrganisasiPage() {
  const { data, mutate, isLoading } = useSWR("INSTANCE_ORGANISASI", () => layanan.pohon());
  // Sumber calon penempatan + kunci yang sama dengan halaman Member, supaya
  // perubahan di sini langsung terlihat di sana.
  const { data: hierarki, mutate: mutateHierarki } = useSWR(["INSTANCE_HIERARKI"], () => hierarkiService.ringkasan());

  /** Aksi struktur: balasan server = pohon terbaru, jadi tidak perlu fetch ulang. */
  const jalankan = async (aksi: () => Promise<TPohonOrganisasi>, berhasil: string): Promise<void> => {
    try {
      await mutate(await aksi(), { revalidate: false });
      await mutateHierarki();
      setToast({ type: TOAST_TYPE.SUCCESS, title: berhasil });
    } catch (err) {
      setToast({ type: TOAST_TYPE.ERROR, title: "Gagal", message: pesanGagal(err) });
    }
  };

  const aksi: TAksiOrganisasi = {
    ubahDivisi: (id, kode, nama) => jalankan(() => layanan.ubahDivisi(id, { kode, nama }), `Divisi ${kode} disimpan`),
    hapusDivisi: (id) => jalankan(() => layanan.hapusDivisi(id), "Divisi dihapus"),
    ubahDepartemen: (id, isi) => jalankan(() => layanan.ubahDepartemen(id, isi), "Departemen disimpan"),
    simpanProject: (id, projectIds) =>
      jalankan(() => layanan.ubahDepartemen(id, { project_ids: projectIds }), "Project departemen disimpan"),
    hapusDepartemen: (id) => jalankan(() => layanan.hapusDepartemen(id), "Departemen dihapus"),
    tempatkan: async (orang: TAnggotaHierarki, tujuan) => {
      try {
        await hierarkiService.setel({
          member_id: orang.id,
          // Jenjang belum diisi: ditempatkan sebagai staf (aturan yang sama dengan editor Member).
          ...(orang.tingkat === null ? { tingkat: TINGKAT_MEMBER } : {}),
          ...tujuan,
        });
        await Promise.all([mutate(), mutateHierarki()]);
        const keluar = tujuan.departemen_id === null || tujuan.divisi_id === null;
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: keluar ? `${orang.display_name} dikeluarkan` : `${orang.display_name} ditempatkan`,
          message: "Akses project-nya sudah disesuaikan.",
        });
      } catch (err) {
        setToast({ type: TOAST_TYPE.ERROR, title: "Gagal", message: pesanGagal(err) });
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
        title: "Struktur organisasi",
        description:
          "Divisi berisi departemen, departemen berisi project dan orang. Staf & supervisor melihat project " +
          "departemennya, manager melihat semua departemen di divisinya, direktur melihat semuanya.",
      }}
    >
      {isLoading || !data ? (
        <Loader className="space-y-2">
          <Loader.Item height="64px" />
          <Loader.Item height="64px" />
        </Loader>
      ) : (
        <div className="space-y-4">
          <FormBaru
            label="Divisi baru"
            onSimpan={(kode, nama) => jalankan(() => layanan.buatDivisi({ kode, nama }), `Divisi ${kode} dibuat`)}
          />

          {data.divisi.length === 0 && (
            <p className="text-13 text-secondary">
              Belum ada divisi. Selama kosong, akses tetap mengikuti keanggotaan project seperti sebelumnya.
            </p>
          )}

          {data.divisi.map((divisi) => (
            <KartuDivisi key={divisi.id} divisi={divisi} aksi={aksi} orang={orang} namaDivisi={namaDivisi}>
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
                />
              ))}
              <FormBaru
                label="Departemen baru"
                onSimpan={(kode, nama) =>
                  jalankan(
                    () => layanan.buatDepartemen({ divisi_id: divisi.id, kode, nama }),
                    `Departemen ${kode} dibuat`
                  )
                }
              />
            </KartuDivisi>
          ))}

          {data.tanpa_departemen.length > 0 && (
            <section className="space-y-2">
              <h2 className="text-13 font-semibold text-primary">
                Project yang belum punya departemen ({data.tanpa_departemen.length})
              </h2>
              <p className="text-11 text-secondary">
                Ini struktur lama (satu divisi = satu project). Jadikan departemen di sebuah divisi untuk membawanya ke
                struktur baru; sampai saat itu ia hanya terlihat oleh anggota eksplisitnya.
                {semuaDivisi.length === 0 && " Buat divisi dulu di atas."}
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
                        title: `${isi.kode} jadi departemen`,
                        message:
                          `${hasil.ditempatkan} orang ditempatkan` +
                          (hasil.dilewati ? `, ${hasil.dilewati} manager/direktur dilewati.` : "."),
                      });
                    } catch (err) {
                      setToast({ type: TOAST_TYPE.ERROR, title: "Gagal", message: pesanGagal(err) });
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

function FormBaru({ label, onSimpan }: { label: string; onSimpan: (kode: string, nama: string) => Promise<void> }) {
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
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-11 text-secondary">{label}</span>
      <input
        className={`${inputClass} w-28`}
        placeholder="Kode"
        maxLength={20}
        value={kode}
        onChange={(e) => setKode(e.target.value)}
      />
      <input
        className={`${inputClass} min-w-[180px] flex-1`}
        placeholder="Nama"
        value={nama}
        onChange={(e) => setNama(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && siap) void simpan();
        }}
      />
      <Button variant="secondary" size="sm" disabled={!siap} onClick={simpan}>
        Tambah
      </Button>
    </div>
  );
}
