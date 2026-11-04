/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: modal kelola Struktur organisasi (KEP-29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu tempat untuk semua modal kelola: buat/ubah/hapus divisi & departemen,
 * tambah manager atau anggota, pindah departemen + ganti project. Papan dan menu
 * "..." hanya mengirim `TPerintahKelola`; aturan penempatan tetap di
 * `aksi` halaman, jadi tidak ada salinan kedua.
 */

import { useState } from "react";
// plane imports
import { Button } from "@plane/propel/button";
import type { TAnggotaHierarki, TPohonOrganisasi } from "@plane/services";
import { AlertModalCore, CustomSearchSelect, CustomSelect, Input } from "@plane/ui";
// components
import { EModalWidth, Field, ParadiseModal, PersonCell } from "@/components/common/paradise-ui";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { BadgeJabatan } from "../members/jabatan";
import {
  asalOrang,
  calonAnggota,
  calonManager,
  cariDepartemen,
  kodeDariNama,
  type TAksiOrganisasi,
  type TPerintahKelola,
} from "./util";

const TANPA_KODE: string[] = [];

// ---------------------------------------------------------------------------
// Nama + kode (buat & ubah divisi/departemen)
// ---------------------------------------------------------------------------

export function ModalKodeNama({
  isOpen,
  judul,
  kodeAwal = "",
  namaAwal = "",
  kodeTerpakai = TANPA_KODE,
  labelSimpan,
  onTutup,
  onSimpan,
}: {
  isOpen: boolean;
  judul: string;
  kodeAwal?: string;
  namaAwal?: string;
  /** Kode yang sudah dipakai, supaya kode usulan dari nama tidak bentrok. */
  kodeTerpakai?: string[];
  labelSimpan: string;
  onTutup: () => void;
  /** false = gagal (sudah di-toast): modal tetap terbuka supaya isian tidak hilang. */
  onSimpan: (kode: string, nama: string) => Promise<boolean>;
}) {
  const { s } = useGodmodeStrings();
  const [kode, setKode] = useState(kodeAwal);
  const [nama, setNama] = useState(namaAwal);
  // Saat membuat, kode mengikuti nama sampai admin mengetik sendiri di kolom kode.
  // Saat mengubah, kode lama dipertahankan: kode yang ikut berganti diam-diam
  // waktu nama dirapikan membingungkan orang yang sudah hafal kodenya.
  const [kodeManual, setKodeManual] = useState(kodeAwal !== "");
  const [sibuk, setSibuk] = useState(false);
  const siap = kode.trim().length > 0 && nama.trim().length > 0 && !sibuk;

  const ubahNama = (nilai: string) => {
    setNama(nilai);
    if (!kodeManual) setKode(kodeDariNama(nilai, kodeTerpakai));
  };
  const ubahKode = (nilai: string) => {
    // Mengosongkan kolom kode = kembali ke kode otomatis dari nama.
    const kosong = nilai.trim() === "";
    setKodeManual(!kosong);
    setKode(kosong ? kodeDariNama(nama, kodeTerpakai) : nilai.toUpperCase());
  };
  const simpan = async () => {
    if (!siap) return;
    setSibuk(true);
    try {
      if (await onSimpan(kode.trim(), nama.trim())) onTutup();
    } finally {
      setSibuk(false);
    }
  };

  return (
    <ParadiseModal
      isOpen={isOpen}
      onClose={onTutup}
      width={EModalWidth.MD}
      title={judul}
      closeLabel={s.editor.close}
      footer={
        <>
          <Button variant="secondary" size="base" onClick={onTutup}>
            {s.org.cancel}
          </Button>
          <Button variant="primary" size="base" loading={sibuk} disabled={!siap} onClick={simpan}>
            {labelSimpan}
          </Button>
        </>
      }
    >
      <form
        className="grid gap-4 sm:grid-cols-[1fr_8rem]"
        onSubmit={(e) => {
          e.preventDefault();
          void simpan();
        }}
      >
        <Field label={s.org.name}>
          <Input
            className="w-full"
            placeholder={s.org.name_placeholder}
            value={nama}
            onChange={(e) => ubahNama(e.target.value)}
          />
        </Field>
        <Field label={s.org.code}>
          <Input
            className="w-full uppercase"
            maxLength={20}
            placeholder={s.org.code_placeholder}
            value={kode}
            onChange={(e) => ubahKode(e.target.value)}
          />
        </Field>
        <p className="text-11 text-tertiary sm:col-span-2">{s.org.code_hint}</p>
        <button type="submit" hidden aria-hidden tabIndex={-1} />
      </form>
    </ParadiseModal>
  );
}

// ---------------------------------------------------------------------------
// Tambah orang (manager divisi / anggota departemen)
// ---------------------------------------------------------------------------

function ModalTambahOrang({
  judul,
  catatan,
  calon,
  keterangan,
  onTambah,
  onTutup,
}: {
  judul: string;
  catatan: string;
  calon: TAnggotaHierarki[];
  keterangan: (o: TAnggotaHierarki) => string;
  onTambah: (o: TAnggotaHierarki) => Promise<void>;
  onTutup: () => void;
}) {
  const { s } = useGodmodeStrings();
  const [cari, setCari] = useState("");
  const [sibuk, setSibuk] = useState<string | null>(null);
  const q = cari.trim().toLowerCase();
  const tampil = calon.filter((o) => !q || `${o.display_name} ${o.email}`.toLowerCase().includes(q));

  const tambah = async (o: TAnggotaHierarki) => {
    setSibuk(o.id);
    try {
      // Modal tetap terbuka supaya bisa menambah beberapa orang berturut-turut;
      // yang sudah ditambah hilang sendiri dari daftar calon (data dimuat ulang).
      await onTambah(o);
    } finally {
      setSibuk(null);
    }
  };

  return (
    <ParadiseModal
      isOpen
      onClose={onTutup}
      width={EModalWidth.XL}
      title={judul}
      subtitle={catatan}
      closeLabel={s.editor.close}
      footer={
        <Button variant="secondary" size="base" onClick={onTutup}>
          {s.editor.close}
        </Button>
      }
    >
      <div className="space-y-3">
        <Input
          className="w-full"
          placeholder={s.org.search_person}
          aria-label={s.org.search_person}
          value={cari}
          onChange={(e) => setCari(e.target.value)}
        />
        {tampil.length === 0 ? (
          <p className="py-8 text-center text-12 text-tertiary">
            {calon.length === 0 ? s.org.no_candidates : s.members.empty}
          </p>
        ) : (
          <ul className="divide-y divide-subtle rounded-card border border-subtle">
            {tampil.map((o) => {
              const ket = keterangan(o);
              return (
                <li key={o.id} className="flex items-center gap-3 px-3 py-2">
                  <div className="min-w-0 flex-1">
                    <PersonCell userId={o.id} name={o.display_name} email={ket || o.email} size="sm" />
                  </div>
                  <BadgeJabatan tingkat={o.tingkat} size="sm" />
                  <Button
                    variant="secondary"
                    size="base"
                    loading={sibuk === o.id}
                    disabled={sibuk !== null && sibuk !== o.id}
                    onClick={() => void tambah(o)}
                  >
                    {s.org.add}
                  </Button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </ParadiseModal>
  );
}

// ---------------------------------------------------------------------------
// Pindah departemen + ganti project
// ---------------------------------------------------------------------------

function ModalSetelanDepartemen({
  judul,
  divisiAwal,
  projectAwal,
  semuaDivisi,
  semuaProject,
  onSimpan,
  onTutup,
}: {
  judul: string;
  divisiAwal: string;
  projectAwal: string;
  semuaDivisi: { id: string; nama: string; kode: string }[];
  semuaProject: { id: string; name: string }[];
  onSimpan: (data: { divisi_id?: string; project_ids?: string[] }) => Promise<boolean>;
  onTutup: () => void;
}) {
  const { s } = useGodmodeStrings();
  const [divisi, setDivisi] = useState(divisiAwal);
  const [project, setProject] = useState(projectAwal);
  const [sibuk, setSibuk] = useState(false);
  const berubah = divisi !== divisiAwal || project !== projectAwal;

  const simpan = async () => {
    if (!berubah) return;
    setSibuk(true);
    try {
      // Satu PATCH: server menulis keduanya dalam satu transaksi.
      const ok = await onSimpan({
        ...(divisi !== divisiAwal ? { divisi_id: divisi } : {}),
        ...(project !== projectAwal ? { project_ids: project ? [project] : [] } : {}),
      });
      if (ok) onTutup();
    } finally {
      setSibuk(false);
    }
  };

  return (
    <ParadiseModal
      isOpen
      onClose={onTutup}
      width={EModalWidth.LG}
      title={judul}
      closeLabel={s.editor.close}
      footerNote={berubah ? s.org.department_settings_note : s.org.nothing_changed}
      footer={
        <>
          <Button variant="secondary" size="base" onClick={onTutup}>
            {s.org.cancel}
          </Button>
          <Button variant="primary" size="base" loading={sibuk} disabled={!berubah || sibuk} onClick={simpan}>
            {s.org.save}
          </Button>
        </>
      }
    >
      <div className="grid gap-4">
        <Field label={s.org.belongs_to}>
          <CustomSelect
            value={divisi}
            label={semuaDivisi.find((v) => v.id === divisi)?.nama ?? ""}
            onChange={(v: string) => setDivisi(v)}
            buttonClassName="w-full"
            className="w-full"
            input
          >
            {semuaDivisi.map((v) => (
              <CustomSelect.Option key={v.id} value={v.id}>
                <span className="flex w-full items-center justify-between gap-2">
                  <span>{v.nama}</span>
                  <span className="text-11 text-tertiary">{v.kode}</span>
                </span>
              </CustomSelect.Option>
            ))}
          </CustomSelect>
        </Field>
        <Field label={s.org.project} hint={project !== projectAwal ? s.org.projects_moved_note : s.org.project_note}>
          <CustomSearchSelect
            value={project}
            label={semuaProject.find((p) => p.id === project)?.name ?? s.org.project_picker}
            onChange={(v: string) => setProject(v)}
            buttonClassName="w-full"
            className="w-full"
            input
            maxHeight="lg"
            options={semuaProject.map((p) => ({ value: p.id, query: p.name, content: p.name }))}
          />
        </Field>
      </div>
    </ParadiseModal>
  );
}

// ---------------------------------------------------------------------------
// Konfirmasi hapus
// ---------------------------------------------------------------------------

function ModalHapus({
  judul,
  onHapus,
  onTutup,
}: {
  judul: string;
  onHapus: () => Promise<boolean>;
  onTutup: () => void;
}) {
  const { s } = useGodmodeStrings();
  const [sibuk, setSibuk] = useState(false);
  return (
    <AlertModalCore
      isOpen
      variant="danger"
      title={judul}
      content={s.org.delete_body}
      isSubmitting={sibuk}
      primaryButtonText={{ default: s.org.delete_yes, loading: s.org.deleting }}
      secondaryButtonText={s.org.cancel}
      handleClose={onTutup}
      handleSubmit={async () => {
        setSibuk(true);
        try {
          if (await onHapus()) onTutup();
        } finally {
          setSibuk(false);
        }
      }}
    />
  );
}

// ---------------------------------------------------------------------------
// Penerjemah perintah -> modal
// ---------------------------------------------------------------------------

export function KelolaOrganisasi({
  perintah,
  onTutup,
  pohon,
  orang,
  aksi,
}: {
  perintah: TPerintahKelola | null;
  onTutup: () => void;
  pohon: TPohonOrganisasi;
  /** Anggota aktif workspace (dari GET hierarki): sumber calon. */
  orang: TAnggotaHierarki[];
  aksi: TAksiOrganisasi;
}) {
  const { s, fill } = useGodmodeStrings();
  if (!perintah) return null;

  const namaDivisi = Object.fromEntries(pohon.divisi.map((v) => [v.id, v.nama]));
  const namaDepartemen = Object.fromEntries(pohon.divisi.flatMap((v) => v.departemen.map((d) => [d.id, d.nama])));
  const keterangan = (o: TAnggotaHierarki) => asalOrang(o, namaDepartemen, namaDivisi, s, fill);
  const semuaDivisi = pohon.divisi.map((v) => ({ id: v.id, nama: v.nama, kode: v.kode }));
  const kodeDepartemen = pohon.divisi.flatMap((v) => v.departemen.map((d) => d.kode));
  // Kunci ikut perintah: isian modal mulai bersih tiap perintah baru.
  const kunci = JSON.stringify(perintah);

  switch (perintah.jenis) {
    case "buat-divisi":
      return (
        <ModalKodeNama
          key={kunci}
          isOpen
          judul={s.org.new_division_title}
          kodeTerpakai={semuaDivisi.map((v) => v.kode)}
          labelSimpan={s.org.create}
          onTutup={onTutup}
          onSimpan={aksi.buatDivisi}
        />
      );
    case "buat-departemen": {
      const v = pohon.divisi.find((x) => x.id === perintah.divisiId);
      if (!v) return null;
      return (
        <ModalKodeNama
          key={kunci}
          isOpen
          judul={fill(s.org.new_department_title, { div: v.nama })}
          kodeTerpakai={kodeDepartemen}
          labelSimpan={s.org.create}
          onTutup={onTutup}
          onSimpan={(kode, nama) => aksi.buatDepartemen(v.id, kode, nama)}
        />
      );
    }
    case "ubah-divisi":
    case "hapus-divisi":
    case "tambah-manager": {
      const v = pohon.divisi.find((x) => x.id === perintah.id);
      if (!v) return null;
      if (perintah.jenis === "ubah-divisi")
        return (
          <ModalKodeNama
            key={kunci}
            isOpen
            judul={s.org.edit_division}
            kodeAwal={v.kode}
            namaAwal={v.nama}
            labelSimpan={s.org.save}
            onTutup={onTutup}
            onSimpan={(kode, nama) => aksi.ubahDivisi(v.id, kode, nama)}
          />
        );
      if (perintah.jenis === "hapus-divisi")
        return (
          <ModalHapus
            key={kunci}
            judul={fill(s.org.delete_division_title, { name: v.nama })}
            onHapus={() => aksi.hapusDivisi(v.id)}
            onTutup={onTutup}
          />
        );
      return (
        <ModalTambahOrang
          key={kunci}
          judul={fill(s.org.add_manager_title, { name: v.nama })}
          catatan={s.org.managers_note}
          calon={calonManager(orang, v)}
          keterangan={keterangan}
          onTambah={(o) => aksi.tempatkan(o, { divisi_id: v.id })}
          onTutup={onTutup}
        />
      );
    }
    case "ubah-departemen":
    case "hapus-departemen":
    case "setelan-departemen":
    case "tambah-anggota": {
      const hasil = cariDepartemen(pohon.divisi, perintah.id);
      if (!hasil) return null;
      const { dep, divisi } = hasil;
      if (perintah.jenis === "ubah-departemen")
        return (
          <ModalKodeNama
            key={kunci}
            isOpen
            judul={s.org.edit_department}
            kodeAwal={dep.kode}
            namaAwal={dep.nama}
            labelSimpan={s.org.save}
            onTutup={onTutup}
            onSimpan={(kode, nama) => aksi.ubahDepartemen(dep.id, { kode, nama })}
          />
        );
      if (perintah.jenis === "hapus-departemen")
        return (
          <ModalHapus
            key={kunci}
            judul={fill(s.org.delete_department_title, { name: dep.nama })}
            onHapus={() => aksi.hapusDepartemen(dep.id)}
            onTutup={onTutup}
          />
        );
      if (perintah.jenis === "setelan-departemen")
        return (
          <ModalSetelanDepartemen
            key={kunci}
            judul={fill(s.org.department_settings_title, { name: dep.nama })}
            divisiAwal={divisi.id}
            projectAwal={dep.projects[0]?.id ?? ""}
            semuaDivisi={semuaDivisi}
            semuaProject={[
              ...pohon.divisi.flatMap((v) => v.departemen.flatMap((d) => d.projects)),
              ...pohon.tanpa_departemen,
            ]}
            onSimpan={(data) => aksi.ubahDepartemen(dep.id, data)}
            onTutup={onTutup}
          />
        );
      return (
        <ModalTambahOrang
          key={kunci}
          judul={fill(s.org.add_member_title, { name: dep.nama })}
          catatan={`${s.org.supervisors}: ${s.org.supervisors_note} ${s.org.staff}: ${s.org.staff_note}`}
          calon={calonAnggota(orang, dep)}
          keterangan={keterangan}
          onTambah={(o) => aksi.tambahKeDepartemen(o, dep.id)}
          onTutup={onTutup}
        />
      );
    }
    default:
      return null;
  }
}
