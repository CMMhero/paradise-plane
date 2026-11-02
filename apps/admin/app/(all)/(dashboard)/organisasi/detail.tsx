/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: panel kanan Struktur organisasi (KEP-29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Isi panel kanan untuk node yang dipilih di pohon:
 * - Divisi: kepala (ubah/hapus), manager, daftar departemen.
 * - Departemen: kepala, setelan (divisi induk, project), orang (supervisor/staf
 *   + naik/turun jenjang di tempat), supervisor multi-departemen (KEP-32).
 * - Belum ditempatkan: penempatan cepat satu baris per orang.
 * Ubah kode/nama, hapus, dan buat departemen mengirim perintah ke modal
 * bersama di kelola.tsx (yang juga dipakai menu bagan & pohon).
 */

import { useState, type ReactNode } from "react";
import { Building2, ChevronRight, FolderKanban, Pencil, Plus, Settings2, Trash2, UserCog, Users } from "lucide-react";
// plane imports
import { Badge } from "@plane/propel/badge";
import { Button } from "@plane/propel/button";
import {
  TINGKAT_MEMBER,
  TINGKAT_SUPERVISOR,
  type TAnggotaHierarki,
  type TDepartemenOrganisasi,
  type TDivisiOrganisasi,
  type TOrangOrganisasi,
  type TPohonOrganisasi,
} from "@plane/services";
import { CustomSearchSelect, CustomSelect } from "@plane/ui";
// components
import { Field, Panel, PersonCell } from "@/components/common/paradise-ui";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { BadgeJabatan } from "../members/jabatan";
import { BarisOrang, PanelOrang, PemilihOrang, SubjudulKelompok } from "./orang";
import { IKON_AKSI } from "./ikon";
import { MenuDepartemen } from "./menu-node";
import {
  asalOrang,
  calonAnggota,
  calonManager,
  cocokOrang,
  type TAksiOrganisasi,
  type TKelola,
  type TPilihan,
} from "./util";

const TOMBOL_SELECT = "w-full rounded-md border-subtle bg-layer-2";

// ---------------------------------------------------------------------------
// Kepala node: ikon, nama, kode, remah roti, ubah, hapus
// ---------------------------------------------------------------------------

function KepalaNode({
  jenis,
  kode,
  nama,
  remah,
  ringkasan,
  onUbah,
  onHapus,
}: {
  jenis: "divisi" | "departemen";
  kode: string;
  nama: string;
  remah?: ReactNode;
  ringkasan?: ReactNode;
  onUbah: () => void;
  onHapus: () => void;
}) {
  const { s } = useGodmodeStrings();
  const Ikon = jenis === "divisi" ? Building2 : Users;

  return (
    <div className="space-y-3">
      {remah}
      <div className="flex flex-wrap items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-lg border border-subtle bg-layer-2 text-secondary">
          <Ikon className="size-5" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="truncate text-18 font-semibold text-primary">{nama}</h2>
            <Badge variant="neutral">{kode}</Badge>
          </div>
          <div className="mt-0.5 text-12 text-tertiary">
            {jenis === "divisi" ? s.org.division_short : s.org.department_short}
            {ringkasan && <> · {ringkasan}</>}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button variant="secondary" size="sm" prependIcon={<Pencil />} onClick={onUbah}>
            {s.org.edit}
          </Button>
          <Button variant="error-outline" size="sm" prependIcon={<Trash2 />} onClick={onHapus}>
            {s.org.delete}
          </Button>
        </div>
      </div>
    </div>
  );
}

function Remah({ items }: { items: { label: string; onClick?: () => void }[] }) {
  return (
    <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-1 text-12 text-tertiary">
      {items.map((it, i) => (
        <span key={it.label} className="flex items-center gap-1">
          {i > 0 && <ChevronRight className="size-3" aria-hidden />}
          {it.onClick ? (
            <button type="button" onClick={it.onClick} className="hover:text-primary hover:underline">
              {it.label}
            </button>
          ) : (
            <span className="text-secondary">{it.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}

type Bersama = {
  aksi: TAksiOrganisasi;
  /** Anggota aktif workspace (dari GET hierarki): sumber calon yang bisa ditempatkan. */
  orang: TAnggotaHierarki[];
  namaDepartemen: Record<string, string>;
  namaDivisi: Record<string, string>;
  onPilih: (p: TPilihan) => void;
  /** Buka modal kelola di tingkat halaman (kelola.tsx). */
  onKelola: TKelola;
  /** Kata cari global, sudah huruf kecil. */
  q: string;
};

// ---------------------------------------------------------------------------
// Divisi
// ---------------------------------------------------------------------------

export function DetailDivisi({
  divisi,
  aksi,
  orang,
  namaDepartemen,
  namaDivisi,
  onPilih,
  onKelola,
  q,
}: Bersama & { divisi: TDivisiOrganisasi }) {
  const { s, fill } = useGodmodeStrings();
  const calon = calonManager(orang, divisi);
  const cariOrang = (id: string) => orang.find((x) => x.id === id);
  const manager = divisi.manager.filter((m) => cocokOrang(q, m));
  const jumlahOrang = divisi.departemen.reduce((n, d) => n + d.anggota.length, 0) + divisi.manager.length;

  return (
    <div className="space-y-5">
      <KepalaNode
        jenis="divisi"
        kode={divisi.kode}
        nama={divisi.nama}
        remah={
          <Remah
            items={[{ label: s.org.overview, onClick: () => onPilih({ jenis: "ringkasan" }) }, { label: divisi.nama }]}
          />
        }
        ringkasan={`${fill(s.org.departments_n, { n: divisi.departemen.length })} · ${fill(s.org.people_count, { n: jumlahOrang })}`}
        onUbah={() => onKelola({ jenis: "ubah-divisi", id: divisi.id })}
        onHapus={() => onKelola({ jenis: "hapus-divisi", id: divisi.id })}
      />

      <PanelOrang
        icon={<UserCog className="size-4" />}
        judul={s.org.division_manager}
        catatan={s.org.managers_note}
        jumlah={manager.length}
        kosong={q ? s.members.empty : s.org.no_manager}
        tambah={
          <PemilihOrang
            label={s.org.add_to}
            calon={calon}
            keterangan={(o) => asalOrang(o, namaDepartemen, namaDivisi, s, fill)}
            onTambah={(o) => aksi.tempatkan(o, { divisi_id: divisi.id })}
          />
        }
      >
        {manager.map((m) => (
          <BarisOrang
            key={m.id}
            nama={m.nama}
            email={m.email}
            tingkat={m.tingkat}
            aksi={[
              {
                label: fill(s.org.remove_person, { name: m.nama }),
                icon: IKON_AKSI.cabut,
                onClick: async () => {
                  const o = cariOrang(m.id);
                  if (o) await aksi.tempatkan(o, { divisi_id: null });
                },
              },
            ]}
          />
        ))}
      </PanelOrang>

      <Panel
        flush
        icon={<Users className="size-4" />}
        title={
          <span className="flex items-center gap-2">
            {s.org.departments}
            <Badge variant="neutral" size="sm">
              {divisi.departemen.length}
            </Badge>
          </span>
        }
        description={s.org.departments_note}
        actions={
          <Button
            variant="secondary"
            size="sm"
            prependIcon={<Plus />}
            onClick={() => onKelola({ jenis: "buat-departemen", divisiId: divisi.id })}
          >
            {s.org.new_department}
          </Button>
        }
      >
        {divisi.departemen.length === 0 ? (
          <p className="px-4 py-6 text-center text-12 text-tertiary">{s.org.no_departments}</p>
        ) : (
          <ul className="divide-y divide-subtle">
            {divisi.departemen.map((d) => {
              const sup = d.anggota.filter((a) => a.tingkat >= TINGKAT_SUPERVISOR).length;
              return (
                <li key={d.id} className="group flex items-center pr-3 transition-colors hover:bg-layer-1-hover">
                  <button
                    type="button"
                    onClick={() => onPilih({ jenis: "departemen", id: d.id })}
                    className="flex min-w-0 flex-1 items-center gap-3 px-4 py-3 text-left"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-13 font-medium text-primary">{d.nama}</span>
                        <span className="text-11 text-placeholder">{d.kode}</span>
                      </div>
                      <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-11 text-tertiary">
                        <span>{fill(s.org.sup_staff, { sup, staff: d.anggota.length - sup })}</span>
                        <span className="flex items-center gap-1">
                          <FolderKanban className="size-3" aria-hidden />
                          {d.projects[0] ? (
                            d.projects[0].name
                          ) : (
                            <span className="text-warning-primary">{s.org.project_none}</span>
                          )}
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="size-4 shrink-0 text-placeholder" aria-hidden />
                  </button>
                  <MenuDepartemen id={d.id} nama={d.nama} onKelola={onKelola} />
                </li>
              );
            })}
          </ul>
        )}
      </Panel>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Departemen
// ---------------------------------------------------------------------------

export function DetailDepartemen({
  dep,
  divisi,
  semuaDivisi,
  semuaProject,
  aksi,
  orang,
  namaDepartemen,
  namaDivisi,
  onPilih,
  onKelola,
  q,
}: Bersama & {
  dep: TDepartemenOrganisasi;
  divisi: TDivisiOrganisasi;
  semuaDivisi: { id: string; nama: string; kode: string }[];
  semuaProject: { id: string; name: string }[];
}) {
  const { s, fill } = useGodmodeStrings();
  // Satu departemen tepat satu project (2026-10-23, ditegakkan juga di database):
  // pemilih tunggal, bukan multi. Daftar kosong = lepas project (transien).
  const awal = dep.projects[0]?.id ?? "";
  const [dipilih, setDipilih] = useState<string>(awal);
  const [sibukProject, setSibukProject] = useState(false);
  const berubah = dipilih !== awal;
  const cariOrang = (id: string) => orang.find((x) => x.id === id);
  const calon = calonAnggota(orang, dep);
  // Satu orang bisa ditempatkan di beberapa departemen (satu baris jabatan per
  // departemen, 2026-10-23): ekstra = yang multi-departemen.
  const jmlDept = new Map(orang.map((o) => [o.id, (o.departemen_ids ?? []).length]));
  const utama = dep.anggota.filter((a) => (jmlDept.get(a.id) ?? 1) <= 1 && cocokOrang(q, a));
  const ekstra = dep.anggota.filter((a) => (jmlDept.get(a.id) ?? 0) > 1 && cocokOrang(q, a));
  // Calon tambahan = supervisor yang sudah ditempatkan di departemen LAIN dan belum
  // mengawasi departemen ini. Manager/direktur tidak masuk: jangkauan mereka lebih luas.
  const calonEkstra = orang.filter(
    (o) =>
      o.tingkat === TINGKAT_SUPERVISOR &&
      o.departemen_id &&
      o.departemen_id !== dep.id &&
      !(o.departemen_ids ?? []).includes(dep.id)
  );
  const supervisor = utama.filter((o) => o.tingkat >= TINGKAT_SUPERVISOR);
  const staf = utama.filter((o) => o.tingkat < TINGKAT_SUPERVISOR);

  /** Cabut dari departemen ini saja: kirim himpunan minus departemen ini (kosong = keluar). */
  const cabut = async (id: string) => {
    const penuh = cariOrang(id);
    if (!penuh) return;
    await aksi.setelEkstra(
      id,
      (penuh.departemen_ids ?? []).filter((d) => d !== dep.id)
    );
  };
  const ubahJenjang = async (id: string, tingkat: number) => {
    const penuh = cariOrang(id);
    if (penuh) await aksi.ubahTingkat(penuh, tingkat);
  };

  const barisUtama = (o: TOrangOrganisasi) => (
    <BarisOrang
      key={o.id}
      nama={o.nama}
      email={o.email}
      tingkat={o.tingkat}
      aksi={[
        o.tingkat >= TINGKAT_SUPERVISOR
          ? {
              label: `${s.org.make_staff}: ${o.nama}`,
              icon: IKON_AKSI.turun,
              onClick: () => ubahJenjang(o.id, TINGKAT_MEMBER),
            }
          : {
              label: `${s.org.make_supervisor}: ${o.nama}`,
              icon: IKON_AKSI.naik,
              onClick: () => ubahJenjang(o.id, TINGKAT_SUPERVISOR),
            },
        { label: fill(s.org.remove_person, { name: o.nama }), icon: IKON_AKSI.cabut, onClick: () => cabut(o.id) },
      ]}
    />
  );

  return (
    <div className="space-y-5">
      <KepalaNode
        jenis="departemen"
        kode={dep.kode}
        nama={dep.nama}
        remah={
          <Remah
            items={[
              { label: s.org.overview, onClick: () => onPilih({ jenis: "ringkasan" }) },
              { label: divisi.nama, onClick: () => onPilih({ jenis: "divisi", id: divisi.id }) },
              { label: dep.nama },
            ]}
          />
        }
        ringkasan={fill(s.org.people_count, { n: dep.anggota.length })}
        onUbah={() => onKelola({ jenis: "ubah-departemen", id: dep.id })}
        onHapus={() => onKelola({ jenis: "hapus-departemen", id: dep.id })}
      />

      <Panel icon={<Settings2 className="size-4" />} title={s.org.settings}>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={s.org.belongs_to}>
            <CustomSelect
              value={divisi.id}
              label={divisi.nama}
              onChange={(v: string) => {
                if (v !== divisi.id) void aksi.ubahDepartemen(dep.id, { divisi_id: v });
              }}
              buttonClassName={TOMBOL_SELECT}
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
          <Field label={s.org.project} hint={berubah ? s.org.projects_moved_note : s.org.project_note}>
            <div className="flex items-center gap-2">
              <div className="min-w-0 flex-1">
                <CustomSearchSelect
                  value={dipilih}
                  label={semuaProject.find((p) => p.id === dipilih)?.name ?? s.org.project_picker}
                  onChange={(v: string) => setDipilih(v)}
                  buttonClassName={TOMBOL_SELECT}
                  className="w-full"
                  input
                  maxHeight="lg"
                  options={semuaProject.map((p) => ({ value: p.id, query: p.name, content: p.name }))}
                />
              </div>
              {berubah && (
                <Button
                  variant="primary"
                  size="sm"
                  loading={sibukProject}
                  onClick={async () => {
                    setSibukProject(true);
                    try {
                      await aksi.simpanProject(dep.id, dipilih ? [dipilih] : []);
                    } finally {
                      setSibukProject(false);
                    }
                  }}
                >
                  {s.org.save}
                </Button>
              )}
            </div>
          </Field>
        </div>
      </Panel>

      <PanelOrang
        icon={<Users className="size-4" />}
        judul={s.org.members}
        catatan={`${s.org.supervisors}: ${s.org.supervisors_note} ${s.org.staff}: ${s.org.staff_note}`}
        jumlah={utama.length}
        kosong={q ? s.members.empty : s.org.no_members}
        tambah={
          <PemilihOrang
            label={s.org.add_to}
            calon={calon}
            keterangan={(o) => asalOrang(o, namaDepartemen, namaDivisi, s, fill)}
            onTambah={(o) => aksi.tambahKeDepartemen(o, dep.id)}
          />
        }
      >
        {supervisor.length > 0 && (
          <SubjudulKelompok>
            {s.org.supervisors} · {supervisor.length}
          </SubjudulKelompok>
        )}
        {supervisor.map(barisUtama)}
        {staf.length > 0 && (
          <SubjudulKelompok>
            {s.org.staff} · {staf.length}
          </SubjudulKelompok>
        )}
        {staf.map(barisUtama)}
      </PanelOrang>

      <PanelOrang
        icon={<UserCog className="size-4" />}
        judul={s.org.extra_supervisors}
        catatan={s.org.extra_note}
        jumlah={ekstra.length}
        kosong={s.org.extra_supervisor_hint}
        tambah={
          <PemilihOrang
            label={s.org.add_extra}
            calon={calonEkstra}
            keterangan={(o) => asalOrang(o, namaDepartemen, namaDivisi, s, fill)}
            onTambah={(o) => aksi.setelEkstra(o.id, [...(o.departemen_ids ?? []), dep.id])}
          />
        }
      >
        {ekstra.map((o) => (
          <BarisOrang
            key={o.id}
            nama={o.nama}
            email={o.email}
            tingkat={o.tingkat}
            badges={
              <Badge variant="brand" size="sm">
                {s.org.extra_badge}
              </Badge>
            }
            aksi={[
              {
                label: fill(s.org.remove_extra, { name: o.nama, dept: dep.nama }),
                icon: IKON_AKSI.cabut,
                onClick: () => cabut(o.id),
              },
            ]}
          />
        ))}
      </PanelOrang>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Belum ditempatkan
// ---------------------------------------------------------------------------

export function DetailBelumDitempatkan({
  belum,
  pohon,
  aksi,
  q,
}: {
  belum: TAnggotaHierarki[];
  pohon: TPohonOrganisasi;
  aksi: TAksiOrganisasi;
  q: string;
}) {
  const { s, fill } = useGodmodeStrings();
  const [tujuan, setTujuan] = useState<Record<string, string>>({});
  const [sibuk, setSibuk] = useState<string | null>(null);
  const tampil = belum.filter((o) => cocokOrang(q, { nama: o.display_name, email: o.email }));

  const opsi = [
    ...pohon.divisi.map((v) => ({
      value: `div:${v.id}`,
      query: `${v.nama} ${v.kode} ${s.org.division_manager}`,
      content: (
        <span className="flex w-64 items-center justify-between gap-2">
          <span className="truncate">{fill(s.org.div_of, { div: v.nama })}</span>
          <span className="text-10 text-tertiary">{s.members.level_manager}</span>
        </span>
      ),
    })),
    ...pohon.divisi.flatMap((v) =>
      v.departemen.map((d) => ({
        value: `dep:${d.id}`,
        query: `${d.nama} ${d.kode} ${v.nama}`,
        content: (
          <span className="flex w-64 items-center justify-between gap-2">
            <span className="truncate">{d.nama}</span>
            <span className="truncate text-10 text-tertiary">{v.nama}</span>
          </span>
        ),
      }))
    ),
  ];
  const labelTujuan = (kode: string | undefined): string => {
    if (!kode) return s.org.assign_target;
    const id = kode.slice(4);
    if (kode.startsWith("div:")) {
      const v = pohon.divisi.find((x) => x.id === id);
      return v ? fill(s.org.div_of, { div: v.nama }) : s.org.assign_target;
    }
    for (const v of pohon.divisi) {
      const d = v.departemen.find((x) => x.id === id);
      if (d) return `${d.nama} · ${v.nama}`;
    }
    return s.org.assign_target;
  };

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
    <div className="space-y-5">
      <div className="space-y-1">
        <h2 className="text-18 font-semibold text-primary">{fill(s.org.unplaced_title, { n: belum.length })}</h2>
        <p className="text-12 text-tertiary">{s.org.unplaced_hint}</p>
      </div>
      <Panel flush title={s.org.unplaced_node} tone="warning">
        {tampil.length === 0 ? (
          <p className="px-4 py-6 text-center text-12 text-tertiary">
            {belum.length === 0 ? s.org.unplaced_empty : s.members.empty}
          </p>
        ) : (
          <ul className="divide-y divide-subtle">
            {tampil.map((o) => (
              <li key={o.id} className="flex flex-wrap items-center gap-3 px-4 py-2.5">
                <div className="min-w-[200px] flex-1">
                  <PersonCell name={o.display_name} email={o.email} size="sm" />
                </div>
                <BadgeJabatan tingkat={o.tingkat} />
                {o.tingkat === null && (
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={sibuk === o.id}
                    onClick={async () => {
                      setSibuk(o.id);
                      try {
                        await aksi.ubahTingkat(o, TINGKAT_MEMBER);
                      } finally {
                        setSibuk(null);
                      }
                    }}
                  >
                    {s.org.make_staff}
                  </Button>
                )}
                <div className="w-60">
                  <CustomSearchSelect
                    value={tujuan[o.id] ?? ""}
                    label={
                      <span className={tujuan[o.id] ? "text-primary" : "text-placeholder"}>
                        {labelTujuan(tujuan[o.id])}
                      </span>
                    }
                    onChange={(v: string) => setTujuan((t) => ({ ...t, [o.id]: v }))}
                    buttonClassName={TOMBOL_SELECT}
                    className="w-full"
                    input
                    maxHeight="lg"
                    options={opsi}
                  />
                </div>
                <Button
                  variant="primary"
                  size="sm"
                  loading={sibuk === o.id}
                  disabled={!tujuan[o.id]}
                  onClick={() => tempatkan(o)}
                >
                  {s.org.place}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
