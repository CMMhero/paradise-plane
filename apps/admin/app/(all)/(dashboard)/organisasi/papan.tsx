/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: papan seret-lepas Struktur organisasi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Permintaan user 4 Nov 2026: "easier management for organization. like drag
 * and drop member for assignment to department/division/role level. also less
 * click for department. directly view open and expand it when i click division."
 *
 * Susunan: People (kiri, bisa dicari + saring Unassigned) | Levels (empat lajur
 * jenjang) di atas daftar divisi. Klik divisi = buka di tempat: manager dan
 * semua departemennya dengan orangnya langsung terlihat. Kartu departemen bisa
 * diganti nama di tempat dan ditambah orang; pindah divisi / ganti project
 * lewat menu "...". Sejak 4 Nov 2026 tab "Chart & details" dibuang (KEP-86):
 * bagan struktur tampil di atas papan, klik kotaknya membuka divisi di sini.
 *
 * Semantik seret (KEP-76): dari People = tambah; dari departemen/divisi ke
 * tempat sejenis = pindah (Ctrl/Alt = tambah); ke lajur Levels = ganti jenjang.
 * Setiap hasil bisa di-Undo dari toast; itu menggantikan dialog konfirmasi.
 */

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  Building2,
  ChevronRight,
  ChevronsDownUp,
  ChevronsUpDown,
  FolderKanban,
  AlertTriangle,
  Plus,
} from "lucide-react";
import { combine } from "@atlaskit/pragmatic-drag-and-drop/combine";
import { monitorForElements } from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import { autoScrollForElements } from "@atlaskit/pragmatic-drag-and-drop-auto-scroll/element";
// plane imports
import { Button } from "@plane/propel/button";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import {
  TINGKAT_MANAGER,
  TINGKAT_MEMBER,
  TINGKAT_SUPERVISOR,
  type TAnggotaHierarki,
  type TDepartemenOrganisasi,
  type TDivisiOrganisasi,
  type TOrangOrganisasi,
  type TPohonOrganisasi,
} from "@plane/services";
import { Input } from "@plane/ui";
import { cn } from "@plane/utils";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { BadgeJabatan } from "../members/jabatan";
import { MenuDepartemen, MenuDivisi } from "./menu-node";
import { PemilihOrang } from "./orang";
import { KonteksPapan, type TKonteksPapan, type TPemilihTujuan } from "./papan-konteks";
import {
  akunTerhapus,
  bacaSeret,
  bacaTujuan,
  LAJUR_JENJANG,
  namaJenjang,
  rencanaCabut,
  rencanakan,
  tombolSalin,
  type TAsal,
  type TRencana,
  type TTujuan,
} from "./papan-logika";
import { ChipOrang, kelasSorot, LabelLepas, ModalPilihTujuan, PanelOrangPapan, useTujuanLepas } from "./papan-orang";
import { asalOrang, calonAnggota, type TAksiOrganisasi, type TKelola } from "./util";

type TJalankan = (
  o: TAnggotaHierarki,
  rencana: Extract<TRencana, { hasil: "kirim" }>,
  judul: string
) => Promise<boolean>;

/** Induk gulir terdekat (PageWrapper menggulir di div sendiri, bukan window). */
const indukGulir = (el: HTMLElement): HTMLElement | null => {
  for (let p = el.parentElement; p; p = p.parentElement) {
    const oy = getComputedStyle(p).overflowY;
    if (oy === "auto" || oy === "scroll") return p;
  }
  return null;
};

/** Jangkar DOM supaya klik di bagan bisa menggulir ke divisi/departemen di papan. */
export const idDivisi = (id: string) => `org-divisi-${id}`;
export const idDepartemen = (id: string) => `org-departemen-${id}`;

const tampilOrang = (daftar: TOrangOrganisasi[]) => daftar.filter((o) => !akunTerhapus(o.email));

// ---------------------------------------------------------------------------
// Lajur jenjang
// ---------------------------------------------------------------------------

function LajurJenjang({ tingkat, jumlah }: { tingkat: number; jumlah: number }) {
  const { s, fill } = useGodmodeStrings();
  const ref = useRef<HTMLDivElement>(null);
  const mode = useTujuanLepas(ref, { jenis: "jenjang", tingkat });
  return (
    <div
      ref={ref}
      className={cn(
        "relative flex min-h-14 flex-col justify-center gap-1 rounded-card border border-dashed border-strong bg-layer-1 px-3 py-2 transition-colors",
        kelasSorot(mode)
      )}
    >
      <LabelLepas mode={mode} tingkat={tingkat} />
      <div className="flex items-center justify-between gap-2">
        <BadgeJabatan tingkat={tingkat} />
        <span className="text-11 text-tertiary">{fill(s.org.people_count, { n: jumlah })}</span>
      </div>
      <span className="truncate text-11 text-tertiary">
        {fill(s.org.board.drop_level, { level: namaJenjang(tingkat, s) })}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Departemen
// ---------------------------------------------------------------------------

function LajurDepartemen({
  dep,
  tingkat,
  judul,
  orang,
}: {
  dep: TDepartemenOrganisasi;
  tingkat: number;
  judul: string;
  orang: TOrangOrganisasi[];
}) {
  const { s } = useGodmodeStrings();
  const ref = useRef<HTMLDivElement>(null);
  const mode = useTujuanLepas(ref, { jenis: "departemen", id: dep.id, tingkat });
  return (
    <div ref={ref} className={cn("relative space-y-1 rounded-item p-1.5 transition-colors", kelasSorot(mode))}>
      <LabelLepas mode={mode} />
      <div className="px-0.5 text-10 font-semibold tracking-wide text-tertiary uppercase">
        {judul} · {orang.length}
      </div>
      {orang.length === 0 ? (
        <p className="rounded-item border border-dashed border-subtle px-2 py-1.5 text-11 text-placeholder">
          {s.org.board.empty_lane}
        </p>
      ) : (
        orang.map((o) => (
          <ChipOrang
            key={o.id}
            orangId={o.id}
            nama={o.nama}
            email={o.email}
            tingkat={o.tingkat}
            asal={{ jenis: "departemen", id: dep.id }}
          />
        ))
      )}
    </div>
  );
}

/** Nama departemen yang bisa diganti di tempat: klik, ketik, Enter. */
function NamaDiTempat({ dep, aksi }: { dep: TDepartemenOrganisasi; aksi: TAksiOrganisasi }) {
  const { s, fill } = useGodmodeStrings();
  const [ubah, setUbah] = useState(false);
  const [nama, setNama] = useState(dep.nama);
  const [sibuk, setSibuk] = useState(false);
  const masukan = useRef<HTMLInputElement>(null);
  // Enter lalu blur (kolom dimatikan selagi menyimpan) jangan mengirim dua kali.
  const sedangSimpan = useRef(false);
  useEffect(() => {
    if (ubah) masukan.current?.focus();
  }, [ubah]);

  const simpan = async () => {
    if (sedangSimpan.current) return;
    const baru = nama.trim();
    if (!baru || baru === dep.nama) {
      setNama(dep.nama);
      setUbah(false);
      return;
    }
    sedangSimpan.current = true;
    setSibuk(true);
    try {
      if (await aksi.ubahDepartemen(dep.id, { nama: baru })) setUbah(false);
    } finally {
      sedangSimpan.current = false;
      setSibuk(false);
    }
  };

  if (ubah)
    return (
      <Input
        ref={masukan}
        value={nama}
        disabled={sibuk}
        aria-label={fill(s.org.board.rename, { name: dep.nama })}
        title={s.org.board.rename_hint}
        className="h-7 min-w-0 flex-1 px-2 text-13"
        onChange={(e) => setNama(e.target.value)}
        onBlur={() => void simpan()}
        onKeyDown={(e) => {
          if (e.key === "Enter") void simpan();
          if (e.key === "Escape") {
            setNama(dep.nama);
            setUbah(false);
          }
        }}
      />
    );
  return (
    <button
      type="button"
      onClick={() => {
        setNama(dep.nama);
        setUbah(true);
      }}
      title={fill(s.org.board.rename, { name: dep.nama })}
      className="min-w-0 flex-1 truncate rounded-item px-1 py-0.5 text-left text-13 font-medium text-primary hover:bg-layer-transparent-hover"
    >
      {dep.nama}
    </button>
  );
}

function KartuDepartemen({
  dep,
  aksi,
  orang,
  namaDepartemen,
  namaDivisi,
  onKelola,
}: {
  dep: TDepartemenOrganisasi;
  aksi: TAksiOrganisasi;
  orang: TAnggotaHierarki[];
  namaDepartemen: Record<string, string>;
  namaDivisi: Record<string, string>;
  onKelola: TKelola;
}) {
  const { s, fill } = useGodmodeStrings();
  const ref = useRef<HTMLDivElement>(null);
  const mode = useTujuanLepas(ref, { jenis: "departemen", id: dep.id });
  const anggota = tampilOrang(dep.anggota);
  const manager = anggota.filter((a) => a.tingkat >= TINGKAT_MANAGER);
  const supervisor = anggota.filter((a) => a.tingkat >= TINGKAT_SUPERVISOR && a.tingkat < TINGKAT_MANAGER);
  const staf = anggota.filter((a) => a.tingkat < TINGKAT_SUPERVISOR);

  return (
    <div
      ref={ref}
      id={idDepartemen(dep.id)}
      className={cn(
        "relative scroll-mt-4 space-y-1 rounded-card border border-subtle bg-layer-1 p-2 transition-colors",
        kelasSorot(mode)
      )}
    >
      <LabelLepas mode={mode} />
      <div className="flex items-center gap-1">
        <NamaDiTempat key={dep.nama} dep={dep} aksi={aksi} />
        <span className="shrink-0 text-10 text-placeholder">{dep.kode}</span>
        <MenuDepartemen id={dep.id} nama={dep.nama} onKelola={onKelola} />
      </div>
      <div className="flex items-center gap-1 px-1 text-11">
        <FolderKanban className="size-3 shrink-0 text-placeholder" aria-hidden />
        {dep.projects[0] ? (
          <span className="truncate text-tertiary">{dep.projects[0].name}</span>
        ) : (
          <span className="flex items-center gap-1 text-warning-primary">
            <AlertTriangle className="size-3" aria-hidden />
            {s.org.project_none}
          </span>
        )}
      </div>
      {manager.length > 0 && (
        <div className="space-y-1 p-1.5">
          <div className="px-0.5 text-10 font-semibold tracking-wide text-tertiary uppercase">
            {s.org.managers} · {manager.length}
          </div>
          {manager.map((o) => (
            <ChipOrang
              key={o.id}
              orangId={o.id}
              nama={o.nama}
              email={o.email}
              tingkat={o.tingkat}
              asal={{ jenis: "departemen", id: dep.id }}
            />
          ))}
        </div>
      )}
      <LajurDepartemen dep={dep} tingkat={TINGKAT_SUPERVISOR} judul={s.org.supervisors} orang={supervisor} />
      <LajurDepartemen dep={dep} tingkat={TINGKAT_MEMBER} judul={s.org.staff} orang={staf} />
      <div className="flex justify-end pt-1">
        <PemilihOrang
          label={s.org.add_to}
          calon={calonAnggota(orang, dep)}
          keterangan={(o) => asalOrang(o, namaDepartemen, namaDivisi, s, fill)}
          onTambah={(o) => aksi.tambahKeDepartemen(o, dep.id)}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Divisi
// ---------------------------------------------------------------------------

function ZonaManager({ v }: { v: TDivisiOrganisasi }) {
  const { s } = useGodmodeStrings();
  const ref = useRef<HTMLDivElement>(null);
  const mode = useTujuanLepas(ref, { jenis: "divisi", id: v.id });
  const manager = tampilOrang(v.manager);
  return (
    <div
      ref={ref}
      className={cn("relative space-y-1.5 rounded-card border border-subtle bg-layer-2 p-2", kelasSorot(mode))}
    >
      <LabelLepas mode={mode} />
      <div className="px-0.5 text-10 font-semibold tracking-wide text-tertiary uppercase">
        {s.org.board.managers} · {manager.length}
      </div>
      {manager.length === 0 ? (
        <p className="rounded-item border border-dashed border-subtle px-2 py-1.5 text-11 text-placeholder">
          {s.org.board.no_manager}
        </p>
      ) : (
        <div className="grid gap-1.5 sm:grid-cols-2 xl:grid-cols-3">
          {manager.map((m) => (
            <ChipOrang
              key={m.id}
              orangId={m.id}
              nama={m.nama}
              email={m.email}
              tingkat={m.tingkat}
              asal={{ jenis: "divisi", id: v.id }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function BarisDivisi({
  v,
  buka,
  onLipat,
  ...bersama
}: {
  v: TDivisiOrganisasi;
  buka: boolean;
  onLipat: () => void;
  aksi: TAksiOrganisasi;
  orang: TAnggotaHierarki[];
  namaDepartemen: Record<string, string>;
  namaDivisi: Record<string, string>;
  onKelola: TKelola;
}) {
  const { s, fill } = useGodmodeStrings();
  // Kepala divisi juga tujuan "pimpin divisi", supaya divisi terlipat tetap bisa dituju.
  const ref = useRef<HTMLDivElement>(null);
  const mode = useTujuanLepas(ref, { jenis: "divisi", id: v.id });
  const jumlah = v.manager.length + v.departemen.reduce((n, d) => n + d.anggota.length, 0);
  const label = fill(buka ? s.org.board.collapse : s.org.board.expand, { name: v.nama });

  return (
    <section id={idDivisi(v.id)} className="scroll-mt-4 overflow-visible rounded-card border border-subtle bg-layer-1">
      <div ref={ref} className={cn("relative flex items-center gap-2 px-2 py-1.5", kelasSorot(mode))}>
        <LabelLepas mode={mode} />
        <button
          type="button"
          onClick={onLipat}
          aria-expanded={buka}
          aria-label={label}
          className="flex min-w-0 flex-1 items-center gap-2 rounded-item px-1.5 py-1 text-left hover:bg-layer-transparent-hover"
        >
          <ChevronRight className={cn("size-4 shrink-0 text-tertiary transition-transform", buka && "rotate-90")} />
          <Building2 className="size-4 shrink-0 text-tertiary" aria-hidden />
          <span className="truncate text-14 font-semibold text-primary">{v.nama}</span>
          <span className="shrink-0 text-11 text-placeholder">{v.kode}</span>
          <span className="ml-auto shrink-0 text-11 text-tertiary">
            {fill(s.org.departments_n, { n: v.departemen.length })} · {fill(s.org.people_count, { n: jumlah })}
            {v.manager.length === 0 && <span className="ml-2 text-danger-primary">{s.org.no_manager_short}</span>}
          </span>
        </button>
        <MenuDivisi id={v.id} nama={v.nama} onKelola={bersama.onKelola} />
      </div>
      {buka && (
        <div className="space-y-3 border-t border-subtle p-3">
          <ZonaManager v={v} />
          <div className="grid items-start gap-3 md:grid-cols-2 2xl:grid-cols-3">
            {v.departemen.map((d) => (
              <KartuDepartemen key={d.id} dep={d} {...bersama} />
            ))}
            <button
              type="button"
              onClick={() => bersama.onKelola({ jenis: "buat-departemen", divisiId: v.id })}
              className="flex min-h-24 items-center justify-center gap-1 rounded-card border border-dashed border-subtle text-12 text-tertiary transition-colors hover:border-strong hover:text-primary"
            >
              <Plus className="size-3.5" aria-hidden />
              {s.org.new_department}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Papan
// ---------------------------------------------------------------------------

export function PapanOrganisasi({
  pohon,
  anggota,
  aksi,
  jalankan,
  namaDepartemen,
  namaDivisi,
  onKelola,
  dibuka,
  onDibuka,
}: {
  pohon: TPohonOrganisasi;
  /** Anggota aktif workspace (sudah tanpa akun terhapus). */
  anggota: TAnggotaHierarki[];
  aksi: TAksiOrganisasi;
  jalankan: TJalankan;
  namaDepartemen: Record<string, string>;
  namaDivisi: Record<string, string>;
  onKelola: TKelola;
  /** Divisi yang terbuka. Diangkat ke halaman supaya tetap terbuka sesudah data dimuat ulang. */
  dibuka: Set<string>;
  onDibuka: (baru: Set<string>) => void;
}) {
  const { s, fill } = useGodmodeStrings();
  const akar = useRef<HTMLDivElement>(null);
  const [pemilih, setPemilih] = useState<TPemilihTujuan | null>(null);
  // Satu objek konteks per perubahan data, supaya chip tidak dirender ulang tanpa sebab.
  const konteks = useMemo<TKonteksPapan>(() => {
    const orangById = new Map(anggota.map((o) => [o.id, o]));
    const namaTempat = (a: TAsal): string => (a.jenis === "departemen" ? namaDepartemen[a.id] : namaDivisi[a.id]) ?? "";
    const namaTujuan = (t: TTujuan): string =>
      t.jenis === "jenjang"
        ? namaJenjang(t.tingkat, s)
        : t.jenis === "lepas"
          ? ""
          : namaTempat({ jenis: t.jenis, id: t.id });
    /** Toast cabut: sebut tempatnya dan tegaskan jenjangnya tidak berubah (KEP-86). */
    const judulCabut = (o: TAnggotaHierarki, asal: TAsal) =>
      fill(s.org.board.removed_from, { name: o.display_name, place: namaTempat(asal) });

    const eksekusi: TKonteksPapan["eksekusi"] = async (orangId, asal, tujuan, salin) => {
      const o = orangById.get(orangId);
      if (!o) return;
      const r = rencanakan(o, asal, tujuan, salin);
      const nama = o.display_name;
      if (r.hasil === "direktur") {
        setToast({
          type: TOAST_TYPE.WARNING,
          title: s.org.board.director_blocked,
          message: s.org.board.director_blocked_message,
        });
        return;
      }
      // Dilepas kembali di tempatnya sendiri: tidak ada yang berubah, tak perlu toast.
      if (
        r.hasil === "sudah" &&
        (tujuan.jenis === "lepas" || (asal && tujuan.jenis !== "jenjang" && asal.id === tujuan.id))
      )
        return;
      if (r.hasil === "sudah") {
        setToast({ type: TOAST_TYPE.INFO, title: fill(s.org.board.already_there, { name: nama }) });
        return;
      }
      if (r.mode === "lepas" && asal) {
        await jalankan(o, r, judulCabut(o, asal));
        return;
      }
      const ke = namaTujuan(tujuan);
      const judul =
        r.mode === "jenjang"
          ? fill(s.org.level_saved, { name: nama, level: ke })
          : r.mode === "pindah"
            ? fill(s.org.board.moved_to, { name: nama, to: ke })
            : r.mode === "pimpin"
              ? fill(s.org.board.leads, { name: nama, to: ke })
              : fill(s.org.board.added_to, { name: nama, to: ke });
      await jalankan(o, r, judul);
    };

    const cabut: TKonteksPapan["cabut"] = async (orangId, asal) => {
      const o = orangById.get(orangId);
      if (!o) return;
      await jalankan(o, rencanaCabut(o, asal), judulCabut(o, asal));
    };

    return { orangById, eksekusi, cabut, bukaPemilih: setPemilih, namaTempat };
  }, [anggota, namaDepartemen, namaDivisi, jalankan, s, fill]);

  // Monitor didaftar sekali; ia memanggil fungsi terbaru lewat ref (diperbarui sesudah render).
  const eksekusiRef = useRef(konteks.eksekusi);
  useLayoutEffect(() => {
    eksekusiRef.current = konteks.eksekusi;
  }, [konteks]);

  useEffect(() => {
    const el = akar.current;
    const gulir = el ? indukGulir(el) : null;
    return combine(
      monitorForElements({
        canMonitor: ({ source }) => bacaSeret(source.data) !== null,
        onDrop: ({ source, location }) => {
          const seret = bacaSeret(source.data);
          const target = location.current.dropTargets[0];
          const tujuan = target ? bacaTujuan(target.data) : null;
          if (!seret || !tujuan) return;
          void eksekusiRef.current(seret.orangId, seret.asal, tujuan, tombolSalin(location.current.input));
        },
      }),
      ...(gulir ? [autoScrollForElements({ element: gulir })] : [])
    );
  }, []);

  const jumlahJenjang = (t: number) =>
    anggota.filter((o) => {
      const tk = o.tingkat ?? TINGKAT_MEMBER;
      const idx = LAJUR_JENJANG.indexOf(t as (typeof LAJUR_JENJANG)[number]);
      const atas = LAJUR_JENJANG[idx + 1];
      return tk >= t && (atas === undefined || tk < atas);
    }).length;

  const bisaDibuka = pohon.divisi.map((v) => v.id);
  const semuaTerbuka = bisaDibuka.length > 0 && bisaDibuka.every((id) => dibuka.has(id));
  const lipat = (id: string) => {
    const baru = new Set(dibuka);
    if (baru.has(id)) baru.delete(id);
    else baru.add(id);
    onDibuka(baru);
  };

  const bersama = { aksi, orang: anggota, namaDepartemen, namaDivisi, onKelola };

  return (
    <KonteksPapan.Provider value={konteks}>
      <div ref={akar} className="grid items-start gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <PanelOrangPapan />
        <div className="min-w-0 space-y-4">
          <p className="text-12 text-tertiary">{s.org.board.hint}</p>

          <div className="space-y-2">
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-11 font-semibold tracking-wide text-tertiary uppercase">{s.org.board.levels}</span>
              <span className="text-11 text-tertiary">{s.org.board.levels_hint}</span>
            </div>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
              {LAJUR_JENJANG.map((t) => (
                <LajurJenjang key={t} tingkat={t} jumlah={jumlahJenjang(t)} />
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <span className="text-11 font-semibold tracking-wide text-tertiary uppercase">{s.org.structure}</span>
              <div className="flex items-center gap-2">
                {bisaDibuka.length > 0 && (
                  <Button
                    variant="ghost"
                    size="base"
                    prependIcon={semuaTerbuka ? <ChevronsDownUp /> : <ChevronsUpDown />}
                    onClick={() => onDibuka(semuaTerbuka ? new Set() : new Set(bisaDibuka))}
                  >
                    {semuaTerbuka ? s.org.collapse_all : s.org.expand_all}
                  </Button>
                )}
              </div>
            </div>
            {pohon.divisi.length === 0 ? (
              <p className="rounded-card border border-dashed border-subtle px-4 py-6 text-center text-12 text-tertiary">
                {s.org.no_division}
              </p>
            ) : (
              pohon.divisi.map((v) => (
                <BarisDivisi key={v.id} v={v} buka={dibuka.has(v.id)} onLipat={() => lipat(v.id)} {...bersama} />
              ))
            )}
          </div>
        </div>
      </div>
      <ModalPilihTujuan pemilih={pemilih} pohon={pohon} onTutup={() => setPemilih(null)} />
    </KonteksPapan.Provider>
  );
}
