/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu divisi & departemen di God Mode (KEP-29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { Pencil, Trash2, X } from "lucide-react";
// plane imports
import { Button } from "@plane/propel/button";
import {
  TINGKAT_DIREKTUR,
  TINGKAT_MANAGER,
  type TAnggotaHierarki,
  type TDepartemenOrganisasi,
  type TDivisiOrganisasi,
  type TOrangOrganisasi,
} from "@plane/services";
// local
import { inputClass } from "../members/constants";
import { DivisiPicker } from "../members/divisi-picker";

export type TAksiOrganisasi = {
  ubahDivisi: (id: string, kode: string, nama: string) => Promise<void>;
  hapusDivisi: (id: string) => Promise<void>;
  ubahDepartemen: (id: string, data: { kode?: string; nama?: string; divisi_id?: string }) => Promise<void>;
  simpanProject: (id: string, projectIds: string[]) => Promise<void>;
  hapusDepartemen: (id: string) => Promise<void>;
  tempatkan: (
    orang: TAnggotaHierarki,
    tujuan: { departemen_id?: string | null; divisi_id?: string | null }
  ) => Promise<void>;
};

type Bersama = {
  aksi: TAksiOrganisasi;
  /** Semua anggota workspace (dari GET hierarki): sumber calon yang bisa ditempatkan. */
  orang: TAnggotaHierarki[];
  /** id -> "KODE Nama" untuk menyebut asal orang yang dipindah. */
  namaDepartemen: Record<string, string>;
  namaDivisi: Record<string, string>;
};

/** Kode + nama yang bisa diubah di tempat. */
function JudulBisaDiubah({
  kode,
  nama,
  ukuran,
  onSimpan,
  onHapus,
  tambahan,
}: {
  kode: string;
  nama: string;
  ukuran: "divisi" | "departemen";
  onSimpan: (kode: string, nama: string) => Promise<void>;
  onHapus: () => Promise<void>;
  tambahan?: React.ReactNode;
}) {
  const [ubah, setUbah] = useState(false);
  const [k, setK] = useState(kode);
  const [n, setN] = useState(nama);

  if (ubah) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <input className={`${inputClass} w-28`} maxLength={20} value={k} onChange={(e) => setK(e.target.value)} />
        <input className={`${inputClass} min-w-[160px] flex-1`} value={n} onChange={(e) => setN(e.target.value)} />
        <Button
          variant="primary"
          size="sm"
          disabled={!k.trim() || !n.trim()}
          onClick={async () => {
            await onSimpan(k.trim(), n.trim());
            setUbah(false);
          }}
        >
          Simpan
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            setK(kode);
            setN(nama);
            setUbah(false);
          }}
        >
          Batal
        </Button>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-2">
      <span className={ukuran === "divisi" ? "text-14 font-semibold text-primary" : "text-13 font-medium text-primary"}>
        {nama}
      </span>
      <span className="text-11 text-tertiary">{kode}</span>
      {tambahan}
      <button
        type="button"
        aria-label={`Ubah ${ukuran} ${nama}`}
        className="ml-auto text-tertiary hover:text-primary"
        onClick={() => setUbah(true)}
      >
        <Pencil className="size-3.5" />
      </button>
      <button
        type="button"
        aria-label={`Hapus ${ukuran} ${nama}`}
        className="text-tertiary hover:text-danger-primary"
        onClick={onHapus}
      >
        <Trash2 className="size-4" />
      </button>
    </div>
  );
}

/** Daftar orang + pemilih untuk menambah. Hapus = cabut penempatan, bukan hapus akun. */
function DaftarOrang({
  judul,
  isi,
  calon,
  labelCalon,
  onTambah,
  onCabut,
  kosong,
}: {
  judul: string;
  isi: TOrangOrganisasi[];
  calon: TAnggotaHierarki[];
  labelCalon: (o: TAnggotaHierarki) => string;
  onTambah: (o: TAnggotaHierarki) => Promise<void>;
  onCabut: (id: string) => Promise<void>;
  kosong: string;
}) {
  const [pilih, setPilih] = useState("");
  const terpilih = calon.find((o) => o.id === pilih);

  return (
    <div className="space-y-1.5">
      <span className="block text-11 text-secondary">
        {judul} ({isi.length})
      </span>
      {isi.length === 0 ? (
        <p className="text-11 text-tertiary">{kosong}</p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {isi.map((o) => (
            <span
              key={o.id}
              className="inline-flex items-center gap-1 rounded border border-subtle bg-layer-2 px-2 py-0.5 text-11 text-primary"
              title={o.email}
            >
              {o.nama}
              <span className="text-tertiary">· {o.tingkat_nama}</span>
              <button
                type="button"
                aria-label={`Keluarkan ${o.nama}`}
                className="text-tertiary hover:text-danger-primary"
                onClick={() => onCabut(o.id)}
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <select
          className={`${inputClass} min-w-[220px] flex-1`}
          value={pilih}
          onChange={(e) => setPilih(e.target.value)}
        >
          <option value="">Tambah orang…</option>
          {calon.map((o) => (
            <option key={o.id} value={o.id}>
              {labelCalon(o)}
            </option>
          ))}
        </select>
        <Button
          variant="secondary"
          size="sm"
          disabled={!terpilih}
          onClick={async () => {
            if (!terpilih) return;
            await onTambah(terpilih);
            setPilih("");
          }}
        >
          Tambah
        </Button>
      </div>
    </div>
  );
}

export function KartuDivisi({
  divisi,
  aksi,
  orang,
  namaDivisi,
  children,
}: Omit<Bersama, "namaDepartemen"> & { divisi: TDivisiOrganisasi; children: React.ReactNode }) {
  const sudah = new Set(divisi.manager.map((m) => m.id));
  // Hanya jenjang manager: penempatan divisi tidak memberi apa-apa ke jenjang lain.
  const calon = orang.filter(
    (o) => o.tingkat !== null && o.tingkat >= TINGKAT_MANAGER && o.tingkat < TINGKAT_DIREKTUR && !sudah.has(o.id)
  );

  return (
    <section className="space-y-3 rounded-md border border-subtle bg-layer-1 p-3">
      <JudulBisaDiubah
        kode={divisi.kode}
        nama={divisi.nama}
        ukuran="divisi"
        onSimpan={(k, n) => aksi.ubahDivisi(divisi.id, k, n)}
        onHapus={() => aksi.hapusDivisi(divisi.id)}
        tambahan={<span className="text-11 text-tertiary">· {divisi.departemen.length} departemen</span>}
      />
      <DaftarOrang
        judul="Manager divisi"
        isi={divisi.manager}
        calon={calon}
        labelCalon={(o) =>
          o.divisi_id ? `${o.display_name} (pindah dari ${namaDivisi[o.divisi_id] ?? "divisi lain"})` : o.display_name
        }
        onTambah={(o) => aksi.tempatkan(o, { divisi_id: divisi.id })}
        onCabut={async (id) => {
          const o = orang.find((x) => x.id === id);
          if (o) await aksi.tempatkan(o, { divisi_id: null });
        }}
        kosong="Belum ada manager. Calon hanya orang berjenjang Manager (atur jenjang di halaman Member)."
      />
      <div className="space-y-2">{children}</div>
    </section>
  );
}

export function KartuDepartemen({
  dep,
  divisiId,
  semuaDivisi,
  opsiProject,
  namaProject,
  aksi,
  orang,
  namaDepartemen,
}: Omit<Bersama, "namaDivisi"> & {
  dep: TDepartemenOrganisasi;
  divisiId: string;
  semuaDivisi: { id: string; nama: string; kode: string }[];
  opsiProject: string[];
  namaProject: Record<string, string>;
}) {
  const awal = dep.projects.map((p) => p.id);
  const [dipilih, setDipilih] = useState<string[]>(awal);
  const berubah = dipilih.length !== awal.length || dipilih.some((id) => !awal.includes(id));
  const sudah = new Set(dep.anggota.map((a) => a.id));
  // Staf, supervisor, dan jenjang belum diisi (disimpan sebagai staf). Manager &
  // direktur tidak ditempatkan di departemen.
  const calon = orang.filter((o) => (o.tingkat === null || o.tingkat < TINGKAT_MANAGER) && !sudah.has(o.id));

  return (
    <div className="space-y-2 rounded border border-subtle px-3 py-2">
      <JudulBisaDiubah
        kode={dep.kode}
        nama={dep.nama}
        ukuran="departemen"
        onSimpan={(k, n) => aksi.ubahDepartemen(dep.id, { kode: k, nama: n })}
        onHapus={() => aksi.hapusDepartemen(dep.id)}
        tambahan={
          <select
            aria-label={`Divisi departemen ${dep.nama}`}
            className={`${inputClass} ml-2 py-0.5 text-11`}
            value={divisiId}
            onChange={(e) => aksi.ubahDepartemen(dep.id, { divisi_id: e.target.value })}
          >
            {semuaDivisi.map((v) => (
              <option key={v.id} value={v.id}>
                Divisi: {v.nama}
              </option>
            ))}
          </select>
        }
      />

      <DaftarOrang
        judul="Anggota"
        isi={dep.anggota}
        calon={calon}
        labelCalon={(o) => {
          const jenjang = o.tingkat === null ? "belum berjenjang, jadi Staf" : (o.tingkat_nama ?? "");
          const asal = o.departemen_id ? `, pindah dari ${namaDepartemen[o.departemen_id] ?? "departemen lain"}` : "";
          return `${o.display_name} (${jenjang}${asal})`;
        }}
        onTambah={(o) => aksi.tempatkan(o, { departemen_id: dep.id })}
        onCabut={async (id) => {
          const o = orang.find((x) => x.id === id);
          if (o) await aksi.tempatkan(o, { departemen_id: null });
        }}
        kosong="Belum ada orang di departemen ini."
      />

      <div className="space-y-1.5">
        <span className="block text-11 text-secondary">Project ({dep.projects.length})</span>
        <DivisiPicker
          opsi={opsiProject}
          dipilih={dipilih}
          onUbah={setDipilih}
          nama={namaProject}
          placeholder="Pilih project…"
        />
        {berubah && (
          <div className="flex items-center gap-2">
            <Button variant="primary" size="sm" onClick={() => aksi.simpanProject(dep.id, dipilih)}>
              Simpan project
            </Button>
            <span className="text-11 text-tertiary">
              Project yang sudah di departemen lain akan dipindah ke sini; akses orangnya menyesuaikan.
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
