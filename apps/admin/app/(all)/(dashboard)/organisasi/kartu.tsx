/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu divisi & departemen di God Mode (KEP-29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu berkas untuk semua balok halaman Struktur organisasi:
 * - Peta organisasi (ringkasan + pohon klik-untuk-lompat),
 * - Panel "belum ditempatkan" (penempatan massal cepat),
 * - Kartu divisi & departemen (ubah nama, pindah, tambah/keluarkan orang,
 *   naik/turun jabatan supervisor langsung di tempat).
 */

import { useMemo, useState } from "react";
import { ChevronDown, Pencil, Trash2, X } from "lucide-react";
// plane imports
import { Button } from "@plane/propel/button";
import {
  TINGKAT_DIREKTUR,
  TINGKAT_MANAGER,
  TINGKAT_MEMBER,
  TINGKAT_SUPERVISOR,
  type TAnggotaHierarki,
  type TDepartemenOrganisasi,
  type TDivisiOrganisasi,
  type TOrangOrganisasi,
  type TPohonOrganisasi,
} from "@plane/services";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
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
  /** Naik/turun jenjang tanpa memindahkan penempatan (mis. staf <-> supervisor). */
  ubahTingkat: (orang: TAnggotaHierarki, tingkat: number) => Promise<void>;
};

type Bersama = {
  aksi: TAksiOrganisasi;
  /** Semua anggota workspace (dari GET hierarki): sumber calon yang bisa ditempatkan. */
  orang: TAnggotaHierarki[];
  /** id -> "KODE Nama" untuk menyebut asal orang yang dipindah. */
  namaDepartemen: Record<string, string>;
  namaDivisi: Record<string, string>;
};

/** Warna lencana per jenjang: pindai sekilas siapa apa. */
export function LencanaTingkat({ tingkat, nama }: { tingkat: number | null; nama?: string | null }) {
  const { s } = useGodmodeStrings();
  const label =
    nama ?? (tingkat === null ? s.org.not_yet_leveled : tingkat >= TINGKAT_DIREKTUR ? "Direktur" : `T${tingkat}`);
  const warna =
    tingkat !== null && tingkat >= TINGKAT_DIREKTUR
      ? "border-purple-500/40 bg-purple-500/10 text-purple-600 dark:text-purple-300"
      : tingkat !== null && tingkat >= TINGKAT_MANAGER
        ? "border-blue-500/40 bg-blue-500/10 text-blue-600 dark:text-blue-300"
        : tingkat !== null && tingkat >= TINGKAT_SUPERVISOR
          ? "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300"
          : "border-subtle bg-layer-2 text-secondary";
  return (
    <span className={`inline-flex shrink-0 items-center rounded-full border px-1.5 py-px text-10 font-medium ${warna}`}>
      {label}
    </span>
  );
}

/** Label penempatan seseorang untuk daftar calon ("dari mana dia pindah"). */
function labelPenempatan(
  o: TAnggotaHierarki,
  namaDepartemen: Record<string, string>,
  namaDivisi: Record<string, string>
): string {
  const { s, fill } = useGodmodeStrings();
  if (o.departemen_id && namaDepartemen[o.departemen_id])
    return fill(s.org.moved_from, { from: namaDepartemen[o.departemen_id] });
  if (o.divisi_id && namaDivisi[o.divisi_id]) return fill(s.org.moved_from, { from: namaDivisi[o.divisi_id] });
  return "";
}

/** Kode + nama yang bisa diubah di tempat, hapus dengan konfirmasi dua-klik. */
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
  const { s, fill } = useGodmodeStrings();
  const [ubah, setUbah] = useState(false);
  const [konfirmasi, setKonfirmasi] = useState(false);
  const labelUbah = fill(s.org.edit_label, {
    kind: ukuran === "divisi" ? s.org.kind_division : s.org.kind_department,
    name: nama,
  });
  const labelHapus = fill(s.org.delete_label, {
    kind: ukuran === "divisi" ? s.org.kind_division : s.org.kind_department,
    name: nama,
  });
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
          {s.org.save}
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
          {s.org.cancel}
        </Button>
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className={ukuran === "divisi" ? "text-14 font-semibold text-primary" : "text-13 font-medium text-primary"}>
        {nama}
      </span>
      <span className="text-11 text-tertiary">{kode}</span>
      {tambahan}
      {konfirmasi ? (
        <span className="ml-auto inline-flex flex-wrap items-center gap-2 text-11">
          <span className="text-danger-primary">{fill(s.org.delete_confirm_q, { name: nama })}</span>
          <Button
            variant="error-fill"
            size="sm"
            onClick={async () => {
              await onHapus();
              setKonfirmasi(false);
            }}
          >
            {s.org.delete_yes}
          </Button>
          <Button variant="secondary" size="sm" onClick={() => setKonfirmasi(false)}>
            {s.org.cancel}
          </Button>
        </span>
      ) : (
        <>
          <button
            type="button"
            aria-label={labelUbah}
            title={labelUbah}
            className="ml-auto text-tertiary hover:text-primary"
            onClick={() => setUbah(true)}
          >
            <Pencil className="size-3.5" aria-hidden />
          </button>
          <button
            type="button"
            aria-label={labelHapus}
            title={labelHapus}
            className="text-tertiary hover:text-danger-primary"
            onClick={() => setKonfirmasi(true)}
          >
            <Trash2 className="size-4" aria-hidden />
          </button>
        </>
      )}
    </div>
  );
}

/**
 * Pemilih orang dengan cari-ketik: daftar calon bisa puluhan orang, select
 * native tanpa cari tidak kepakai. Tiap baris ada tombol + langsung.
 */
function PemilihOrang({
  calon,
  labelCalon,
  onTambah,
  kosong,
}: {
  calon: TAnggotaHierarki[];
  labelCalon: (o: TAnggotaHierarki) => string;
  onTambah: (o: TAnggotaHierarki) => Promise<void>;
  kosong: string;
}) {
  const { s } = useGodmodeStrings();
  const [cari, setCari] = useState("");
  const [sibuk, setSibuk] = useState<string | null>(null);
  const q = cari.trim().toLowerCase();
  const saring = q ? calon.filter((o) => `${o.display_name} ${o.email}`.toLowerCase().includes(q)) : calon;
  const tampil = saring.slice(0, 8);

  return (
    <div className="space-y-1.5 rounded border border-dashed border-subtle bg-layer-2/40 p-2">
      <input
        className={`${inputClass} w-full`}
        placeholder={s.org.add_person}
        aria-label={s.org.add_person}
        value={cari}
        onChange={(e) => setCari(e.target.value)}
      />
      {calon.length === 0 ? (
        <p className="px-1 text-11 text-tertiary">{kosong}</p>
      ) : tampil.length === 0 ? (
        <p className="px-1 text-11 text-tertiary">{s.members.empty}</p>
      ) : (
        <ul className="max-h-44 space-y-0.5 overflow-y-auto">
          {tampil.map((o) => (
            <li
              key={o.id}
              className="flex items-center gap-2 rounded px-1.5 py-1 text-11 hover:bg-layer-2"
              title={o.email}
            >
              <span className="min-w-0 flex-1 truncate text-primary">
                {o.display_name} <span className="text-tertiary">{labelCalon(o) ? `· ${labelCalon(o)}` : ""}</span>
              </span>
              <LencanaTingkat tingkat={o.tingkat} nama={o.tingkat_nama} />
              <Button
                variant="secondary"
                size="sm"
                disabled={sibuk === o.id}
                onClick={async () => {
                  setSibuk(o.id);
                  try {
                    await onTambah(o);
                    setCari("");
                  } finally {
                    setSibuk(null);
                  }
                }}
              >
                +
              </Button>
            </li>
          ))}
        </ul>
      )}
      {saring.length > tampil.length && (
        <p className="px-1 text-10 text-tertiary">
          +{saring.length - tampil.length} — {s.org.search_person}
        </p>
      )}
    </div>
  );
}

/** Satu chip orang: nama + lencana jenjang + (opsional) tombol naik/turun + cabut. */
function ChipOrang({
  id,
  nama,
  email,
  tingkat,
  tingkatNama,
  onNaik,
  onTurun,
  onCabut,
  labelNaik,
  labelTurun,
}: {
  id: string;
  nama: string;
  email: string;
  tingkat: number;
  tingkatNama: string | null;
  onNaik?: () => Promise<void>;
  onTurun?: () => Promise<void>;
  onCabut: (id: string) => void;
  labelNaik: string;
  labelTurun: string;
}) {
  const { s, fill } = useGodmodeStrings();
  const [sibuk, setSibuk] = useState(false);
  const klik = async (fn?: () => Promise<void>) => {
    if (!fn) return;
    setSibuk(true);
    try {
      await fn();
    } finally {
      setSibuk(false);
    }
  };
  return (
    <span
      className="inline-flex max-w-full items-center gap-1.5 rounded-md border border-subtle bg-layer-2 py-0.5 pr-1 pl-2 text-11 text-primary"
      title={email}
    >
      <span className="truncate font-medium">{nama}</span>
      <LencanaTingkat tingkat={tingkat} nama={tingkatNama} />
      {onNaik && (
        <button
          type="button"
          disabled={sibuk}
          title={labelNaik}
          aria-label={`${labelNaik}: ${nama}`}
          className="text-amber-700 hover:bg-amber-500/20 dark:text-amber-300 rounded px-1 text-10 font-semibold"
          onClick={() => klik(onNaik)}
        >
          ▲
        </button>
      )}
      {onTurun && (
        <button
          type="button"
          disabled={sibuk}
          title={labelTurun}
          aria-label={`${labelTurun}: ${nama}`}
          className="rounded px-1 text-10 font-semibold text-secondary hover:bg-layer-3"
          onClick={() => klik(onTurun)}
        >
          ▼
        </button>
      )}
      <button
        type="button"
        aria-label={fill(s.org.remove_person, { name: nama })}
        title={fill(s.org.remove_person, { name: nama })}
        className="rounded p-0.5 text-tertiary hover:text-danger-primary"
        onClick={() => onCabut(id)}
      >
        <X className="size-3" aria-hidden />
      </button>
    </span>
  );
}

/** Daftar orang + pemilih cari-ketik. `kelompokkan` = pisah Supervisor / Staf. */
function DaftarOrang({
  judul,
  isi,
  calon,
  labelCalon,
  onTambah,
  onCabut,
  kosong,
  kelompokkan = false,
  onNaik,
  onTurun,
  namaDepartemen,
  namaDivisi,
  saringGlobal = "",
}: {
  judul: string;
  isi: TOrangOrganisasi[];
  calon: TAnggotaHierarki[];
  labelCalon: (o: TAnggotaHierarki) => string;
  onTambah: (o: TAnggotaHierarki) => Promise<void>;
  onCabut: (id: string) => void;
  kosong: string;
  kelompokkan?: boolean;
  onNaik?: (orang: TAnggotaHierarki) => Promise<void>;
  onTurun?: (orang: TAnggotaHierarki) => Promise<void>;
  namaDepartemen: Record<string, string>;
  namaDivisi: Record<string, string>;
  saringGlobal?: string;
}) {
  const { s } = useGodmodeStrings();
  const [terbuka, setTerbuka] = useState(false);
  const q = saringGlobal.trim().toLowerCase();
  const cocokGlobal = (o: TOrangOrganisasi) => !q || `${o.nama} ${o.email}`.toLowerCase().includes(q);
  const tampil = isi.filter(cocokGlobal);
  const olehId = useMemo(() => {
    void namaDepartemen;
    void namaDivisi;
    return null;
  }, [namaDepartemen, namaDivisi]);

  void olehId;

  const chip = (o: TOrangOrganisasi) => (
    <ChipOrang
      key={o.id}
      id={o.id}
      nama={o.nama}
      email={o.email}
      tingkat={o.tingkat}
      tingkatNama={o.tingkat_nama}
      onCabut={onCabut}
      labelNaik={s.org.make_supervisor}
      labelTurun={s.org.make_staff}
      onNaik={
        onNaik
          ? async () => {
              // Dipetakan ulang ke record hierarki penuh saat diklik.
              await onNaik({ id: o.id } as TAnggotaHierarki);
            }
          : undefined
      }
      onTurun={
        onTurun
          ? async () => {
              await onTurun({ id: o.id } as TAnggotaHierarki);
            }
          : undefined
      }
    />
  );

  const supervisor = tampil.filter((o) => o.tingkat >= TINGKAT_SUPERVISOR);
  const staf = tampil.filter((o) => o.tingkat < TINGKAT_SUPERVISOR);

  return (
    <div className="space-y-1.5">
      <button
        type="button"
        onClick={() => setTerbuka((v) => !v)}
        aria-expanded={terbuka}
        className="flex w-full items-center gap-1 text-left text-11 font-medium text-secondary hover:text-primary"
      >
        <ChevronDown className={`size-3.5 transition-transform ${terbuka ? "" : "-rotate-90"}`} aria-hidden />
        {judul} ({isi.length})
      </button>
      {isi.length === 0 ? (
        <p className="pl-5 text-11 text-tertiary">{kosong}</p>
      ) : tampil.length === 0 ? (
        <p className="pl-5 text-11 text-tertiary">{s.members.empty}</p>
      ) : kelompokkan ? (
        <div className="space-y-1.5 pl-5">
          <div className="space-y-1">
            <span className="block text-10 font-semibold tracking-wide text-tertiary uppercase">
              {s.org.supervisors} ({supervisor.length})
            </span>
            {supervisor.length === 0 ? (
              <p className="text-11 text-tertiary">—</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">{supervisor.map(chip)}</div>
            )}
          </div>
          <div className="space-y-1">
            <span className="block text-10 font-semibold tracking-wide text-tertiary uppercase">
              {s.org.staff} ({staf.length})
            </span>
            {staf.length === 0 ? (
              <p className="text-11 text-tertiary">—</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">{staf.map(chip)}</div>
            )}
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap gap-1.5 pl-5">{tampil.map(chip)}</div>
      )}
      <div className="pl-5">
        {terbuka ? (
          <PemilihOrang calon={calon} labelCalon={labelCalon} onTambah={onTambah} kosong={kosong} />
        ) : (
          <button
            type="button"
            onClick={() => setTerbuka(true)}
            className="text-11 text-accent-primary hover:underline"
          >
            + {s.org.add_person}
          </button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Peta organisasi: statistik + pohon klik-untuk-lompat
// ---------------------------------------------------------------------------

export function PohonOrganisasi({
  pohon,
  hierarki,
  onLompat,
}: {
  pohon: TPohonOrganisasi;
  hierarki: TAnggotaHierarki[];
  onLompat: (id: string) => void;
}) {
  const { s } = useGodmodeStrings();
  const aktif = hierarki.filter((o) => o.is_active);
  const direktur = aktif.filter((o) => o.tingkat !== null && o.tingkat >= TINGKAT_DIREKTUR);
  const manager = aktif.filter(
    (o) => o.tingkat !== null && o.tingkat >= TINGKAT_MANAGER && o.tingkat < TINGKAT_DIREKTUR
  );
  const supervisor = aktif.filter(
    (o) => o.tingkat !== null && o.tingkat >= TINGKAT_SUPERVISOR && o.tingkat < TINGKAT_MANAGER
  );
  const staf = aktif.filter((o) => o.tingkat !== null && o.tingkat < TINGKAT_SUPERVISOR);
  const belumBerjenjang = aktif.filter((o) => o.tingkat === null);
  const belumDitempatkan = aktif.filter(
    (o) => (o.tingkat === null || o.tingkat < TINGKAT_DIREKTUR) && !o.departemen_id && !o.divisi_id
  );
  const totalDepartemen = pohon.divisi.reduce((n, v) => n + v.departemen.length, 0);
  const totalProject =
    pohon.divisi.reduce((n, v) => n + v.departemen.reduce((m, d) => m + d.projects.length, 0), 0) +
    pohon.tanpa_departemen.length;

  const stat: [string, number, string][] = [
    [s.org.stat_division, pohon.divisi.length, "text-blue-600 dark:text-blue-300"],
    [s.org.stat_department, totalDepartemen, "text-emerald-600 dark:text-emerald-300"],
    [s.org.stat_project, totalProject, "text-secondary"],
    [s.org.stat_manager, manager.length, "text-blue-600 dark:text-blue-300"],
    [s.org.stat_supervisor, supervisor.length, "text-amber-700 dark:text-amber-300"],
    [s.org.stat_staff, staf.length + belumBerjenjang.length, "text-secondary"],
    [s.org.stat_unplaced, belumDitempatkan.length, belumDitempatkan.length ? "text-danger-primary" : "text-secondary"],
    [s.org.stat_unleveled, belumBerjenjang.length, belumBerjenjang.length ? "text-danger-primary" : "text-secondary"],
  ];

  return (
    <section aria-label={s.org.tree_title} className="space-y-3 rounded-md border border-subtle bg-layer-1 p-3">
      <div>
        <h2 className="text-13 font-semibold text-primary">{s.org.tree_title}</h2>
        <p className="text-11 text-secondary">{s.org.tree_hint}</p>
      </div>

      <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
        {stat.map(([label, n, warna]) => (
          <div key={label} className="rounded border border-subtle bg-layer-2/50 px-2 py-1.5 text-center">
            <div className={`text-16 font-semibold ${warna}`}>{n}</div>
            <div className="text-10 text-secondary">{label}</div>
          </div>
        ))}
      </div>

      <div className="border-purple-500/30 bg-purple-500/5 rounded border px-2.5 py-2">
        <span className="text-purple-600 dark:text-purple-300 block text-10 font-semibold tracking-wide uppercase">
          {s.org.directors}
        </span>
        {direktur.length === 0 ? (
          <p className="mt-0.5 text-11 text-tertiary">{s.org.no_directors}</p>
        ) : (
          <div className="mt-1 flex flex-wrap gap-1.5">
            {direktur.map((d) => (
              <span
                key={d.id}
                className="border-purple-500/30 inline-flex items-center gap-1.5 rounded-md border bg-layer-1 px-2 py-0.5 text-11 text-primary"
                title={d.email}
              >
                <span className="font-medium">{d.display_name}</span>
                <LencanaTingkat tingkat={d.tingkat} nama={d.tingkat_nama} />
              </span>
            ))}
          </div>
        )}
      </div>

      {pohon.divisi.length > 0 && (
        <div className="grid items-start gap-2 md:grid-cols-2 xl:grid-cols-3">
          {pohon.divisi.map((v) => (
            <button
              key={v.id}
              type="button"
              onClick={() => onLompat(`divisi-${v.id}`)}
              className="border-blue-500/30 bg-blue-500/5 hover:border-blue-500/60 hover:bg-blue-500/10 space-y-1.5 rounded-md border p-2 text-left transition-colors"
            >
              <div className="flex items-baseline gap-1.5">
                <span className="text-12 font-semibold text-primary">{v.nama}</span>
                <span className="text-10 text-tertiary">{v.kode}</span>
              </div>
              <div className="flex flex-wrap gap-1">
                {v.manager.length === 0 ? (
                  <span className="text-10 text-tertiary">{s.org.no_manager}</span>
                ) : (
                  v.manager.map((m) => (
                    <span key={m.id} className="text-blue-700 dark:text-blue-300 text-10">
                      👤 {m.nama}
                    </span>
                  ))
                )}
              </div>
              <ul className="border-blue-500/30 space-y-1 border-l-2 pl-2">
                {v.departemen.length === 0 && <li className="text-10 text-tertiary">—</li>}
                {v.departemen.map((d) => {
                  const sup = d.anggota.filter((a) => a.tingkat >= TINGKAT_SUPERVISOR).length;
                  const sff = d.anggota.length - sup;
                  return (
                    <li key={d.id} className="text-10">
                      <span className="font-medium text-primary">
                        {d.kode} {d.nama}
                      </span>{" "}
                      <span className="text-tertiary">
                        · {sup} sup / {sff} staf · {d.projects.length} proj
                      </span>
                    </li>
                  );
                })}
              </ul>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Panel belum ditempatkan: penempatan cepat satu baris per orang
// ---------------------------------------------------------------------------

export function PanelBelumDitempatkan({
  orang,
  pohon,
  namaDepartemen,
  namaDivisi,
  aksi,
}: {
  orang: TAnggotaHierarki[];
  pohon: TPohonOrganisasi;
  namaDepartemen: Record<string, string>;
  namaDivisi: Record<string, string>;
  aksi: TAksiOrganisasi;
}) {
  const { s, fill } = useGodmodeStrings();
  const [cari, setCari] = useState("");
  const [tujuan, setTujuan] = useState<Record<string, string>>({});
  const [sibuk, setSibuk] = useState<string | null>(null);

  const belum = orang.filter(
    (o) => o.is_active && (o.tingkat === null || o.tingkat < TINGKAT_DIREKTUR) && !o.departemen_id && !o.divisi_id
  );
  const q = cari.trim().toLowerCase();
  const tampil = q ? belum.filter((o) => `${o.display_name} ${o.email}`.toLowerCase().includes(q)) : belum;
  if (belum.length === 0) return null;

  const tempatkan = async (o: TAnggotaHierarki) => {
    const kode = tujuan[o.id];
    if (!kode) return;
    setSibuk(o.id);
    try {
      if (kode.startsWith("div:")) await aksi.tempatkan(o, { divisi_id: kode.slice(4) });
      else if (kode.startsWith("dep:")) await aksi.tempatkan(o, { departemen_id: kode.slice(4) });
      setTujuan((t) => {
        const baru = { ...t };
        delete baru[o.id];
        return baru;
      });
    } finally {
      setSibuk(null);
    }
  };

  return (
    <section
      aria-label={fill(s.org.unplaced_title, { n: belum.length })}
      className="border-warning-primary/40 space-y-2 rounded-md border bg-warning-subtle/10 p-3"
    >
      <h2 className="text-13 font-semibold text-primary">{fill(s.org.unplaced_title, { n: belum.length })}</h2>
      <p className="text-11 text-secondary">{s.org.unplaced_hint}</p>
      {belum.length > 6 && (
        <input
          className={`${inputClass} w-full max-w-sm`}
          placeholder={s.org.search_person}
          aria-label={s.org.search_person}
          value={cari}
          onChange={(e) => setCari(e.target.value)}
        />
      )}
      {tampil.length === 0 ? (
        <p className="text-11 text-tertiary">{s.members.empty}</p>
      ) : (
        <ul className="space-y-1.5">
          {tampil.map((o) => (
            <li
              key={o.id}
              className="flex flex-wrap items-center gap-2 rounded border border-subtle bg-layer-1 px-2 py-1.5"
            >
              <span className="min-w-40 flex-1 text-12 text-primary" title={o.email}>
                <span className="font-medium">{o.display_name}</span>{" "}
                <span className="text-11 text-tertiary">{o.email}</span>
              </span>
              <LencanaTingkat tingkat={o.tingkat} nama={o.tingkat_nama} />
              {o.tingkat === null && (
                <button
                  type="button"
                  disabled={sibuk === o.id}
                  className="text-11 text-accent-primary hover:underline"
                  onClick={async () => {
                    setSibuk(o.id);
                    try {
                      await aksi.ubahTingkat(o, TINGKAT_MEMBER);
                    } finally {
                      setSibuk(null);
                    }
                  }}
                >
                  → {s.editor.position_member}
                </button>
              )}
              <select
                className={`${inputClass} min-w-[220px] flex-1 py-1 text-11`}
                value={tujuan[o.id] ?? ""}
                aria-label={`${s.org.assign_target} ${o.display_name}`}
                onChange={(e) => setTujuan((t) => ({ ...t, [o.id]: e.target.value }))}
              >
                <option value="">{s.org.assign_target}</option>
                <optgroup label={s.org.division_manager}>
                  {pohon.divisi.map((v) => (
                    <option key={v.id} value={`div:${v.id}`}>
                      {fill(s.org.div_of, { div: `${v.kode} ${v.nama}` })}
                    </option>
                  ))}
                </optgroup>
                {pohon.divisi.map((v) => (
                  <optgroup key={v.id} label={`${v.kode} ${v.nama}`}>
                    {v.departemen.map((d) => (
                      <option key={d.id} value={`dep:${d.id}`}>
                        {d.kode} {d.nama}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
              <Button
                variant="primary"
                size="sm"
                disabled={!tujuan[o.id] || sibuk === o.id}
                onClick={() => tempatkan(o)}
              >
                {s.org.place}
              </Button>
            </li>
          ))}
        </ul>
      )}
      <span className="hidden">
        {namaDepartemen[""]}
        {namaDivisi[""]}
      </span>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Kartu divisi & departemen
// ---------------------------------------------------------------------------

export function KartuDivisi({
  divisi,
  aksi,
  orang,
  namaDivisi,
  namaDepartemen,
  cariGlobal = "",
  children,
}: Bersama & { divisi: TDivisiOrganisasi; cariGlobal?: string; children: React.ReactNode }) {
  const { s, fill } = useGodmodeStrings();
  const sudah = new Set(divisi.manager.map((m) => m.id));
  // Manager divisi = jenjang Manager (calon termasuk supervisor/staf: penempatan
  // otomatis menaikkan ke Manager, jadi tak perlu bolak-balik ke halaman Member).
  const calon = orang.filter(
    (o) => o.is_active && o.tingkat !== null && o.tingkat < TINGKAT_DIREKTUR && !sudah.has(o.id)
  );

  const cariOrang = (id: string): TAnggotaHierarki | undefined => orang.find((x) => x.id === id);

  return (
    <section
      id={`divisi-${divisi.id}`}
      className="scroll-mt-4 space-y-3 rounded-md border border-subtle bg-layer-1 p-3"
    >
      <JudulBisaDiubah
        kode={divisi.kode}
        nama={divisi.nama}
        ukuran="divisi"
        onSimpan={(k, n) => aksi.ubahDivisi(divisi.id, k, n)}
        onHapus={() => aksi.hapusDivisi(divisi.id)}
        tambahan={
          <span className="text-11 text-tertiary">
            {fill(s.org.departments_count, { n: divisi.departemen.length })}
          </span>
        }
      />
      <DaftarOrang
        judul={s.org.division_manager}
        isi={divisi.manager}
        calon={calon}
        labelCalon={(o) =>
          o.divisi_id
            ? fill(s.org.member_moved_from, {
                name: o.display_name,
                from: namaDivisi[o.divisi_id] ?? s.org.move_division_other,
              })
            : o.display_name
        }
        onTambah={(o) => aksi.tempatkan(o, { divisi_id: divisi.id })}
        onCabut={async (id) => {
          const o = cariOrang(id);
          if (o) await aksi.tempatkan(o, { divisi_id: null });
        }}
        kosong={s.org.no_manager}
        namaDepartemen={namaDepartemen}
        namaDivisi={namaDivisi}
        saringGlobal={cariGlobal}
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
  namaDivisi,
  cariGlobal = "",
}: Bersama & {
  dep: TDepartemenOrganisasi;
  divisiId: string;
  semuaDivisi: { id: string; nama: string; kode: string }[];
  opsiProject: string[];
  namaProject: Record<string, string>;
  cariGlobal?: string;
}) {
  const { s, fill } = useGodmodeStrings();
  const awal = dep.projects.map((p) => p.id);
  const [dipilih, setDipilih] = useState<string[]>(awal);
  const berubah = dipilih.length !== awal.length || dipilih.some((id) => !awal.includes(id));
  const sudah = new Set(dep.anggota.map((a) => a.id));
  // Staf, supervisor, dan jenjang belum diisi (disimpan sebagai staf). Manager &
  // direktur tidak ditempatkan di departemen.
  const calon = orang.filter(
    (o) => o.is_active && (o.tingkat === null || o.tingkat < TINGKAT_MANAGER) && !sudah.has(o.id)
  );

  const cariOrang = (id: string): TAnggotaHierarki | undefined => orang.find((x) => x.id === id);

  const naik = async (sebagian: TAnggotaHierarki) => {
    const penuh = cariOrang(sebagian.id);
    if (penuh) await aksi.ubahTingkat(penuh, TINGKAT_SUPERVISOR);
  };
  const turun = async (sebagian: TAnggotaHierarki) => {
    const penuh = cariOrang(sebagian.id);
    if (penuh) await aksi.ubahTingkat(penuh, TINGKAT_MEMBER);
  };

  return (
    <div id={`dep-${dep.id}`} className="scroll-mt-4 space-y-2 rounded border border-subtle px-3 py-2">
      <JudulBisaDiubah
        kode={dep.kode}
        nama={dep.nama}
        ukuran="departemen"
        onSimpan={(k, n) => aksi.ubahDepartemen(dep.id, { kode: k, nama: n })}
        onHapus={() => aksi.hapusDepartemen(dep.id)}
        tambahan={
          <select
            aria-label={fill(s.org.division_of_dept, { name: dep.nama })}
            title={fill(s.org.division_of_dept, { name: dep.nama })}
            className={`${inputClass} ml-2 py-0.5 text-11`}
            value={divisiId}
            onChange={(e) => aksi.ubahDepartemen(dep.id, { divisi_id: e.target.value })}
          >
            {semuaDivisi.map((v) => (
              <option key={v.id} value={v.id}>
                {s.org.division_of}: {v.nama}
              </option>
            ))}
          </select>
        }
      />

      <DaftarOrang
        judul={s.org.members}
        isi={dep.anggota}
        calon={calon}
        kelompokkan
        onNaik={naik}
        onTurun={turun}
        labelCalon={(o) => {
          const jenjang = o.tingkat === null ? s.org.not_yet_leveled : (o.tingkat_nama ?? "");
          const asal = labelPenempatan(o, namaDepartemen, namaDivisi);
          return `${jenjang}${asal}`;
        }}
        onTambah={(o) => aksi.tempatkan(o, { departemen_id: dep.id })}
        onCabut={async (id) => {
          const o = cariOrang(id);
          if (o) await aksi.tempatkan(o, { departemen_id: null });
        }}
        kosong={s.org.no_members}
        namaDepartemen={namaDepartemen}
        namaDivisi={namaDivisi}
        saringGlobal={cariGlobal}
      />

      <div className="space-y-1.5">
        <span className="block text-11 text-secondary">{fill(s.org.projects, { n: dep.projects.length })}</span>
        <DivisiPicker
          opsi={opsiProject}
          dipilih={dipilih}
          onUbah={setDipilih}
          nama={namaProject}
          placeholder={s.org.project_picker}
        />
        {berubah && (
          <div className="flex items-center gap-2">
            <Button variant="primary" size="sm" onClick={() => aksi.simpanProject(dep.id, dipilih)}>
              {s.org.save_projects}
            </Button>
            <span className="text-11 text-tertiary">{s.org.projects_moved_note}</span>
          </div>
        )}
      </div>
    </div>
  );
}
