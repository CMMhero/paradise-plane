/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pohon & bagan organisasi (KEP-29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Dua tampilan dari data yang sama:
 * - PohonNavigasi: pohon berlekuk di kiri (perusahaan > divisi > departemen),
 *   klik untuk membuka node di panel kanan. Divisi TERLIPAT secara bawaan
 *   (kecuali yang memuat node terpilih), dengan tombol buka/lipat semua. Tiap
 *   baris punya menu "..." (menu-node.tsx). Gaya aktif/hover meniru sidebar
 *   God Mode (`bg-layer-transparent-active`).
 * - BaganOrganisasi: bagan atas-ke-bawah untuk ringkasan perusahaan
 *   (direktur > divisi + manager > departemen), garis penghubung dari border.
 *   Dipasang di dalam KanvasBagan (geser/zoom), tiap kotak punya menu "...".
 */

import { useState, type ReactNode } from "react";
import {
  AlertTriangle,
  Building2,
  ChevronRight,
  ChevronsDownUp,
  ChevronsUpDown,
  Crown,
  FolderInput,
  FolderKanban,
  Network,
  Plus,
  UserX,
  Users,
} from "lucide-react";
// plane imports
import { Badge } from "@plane/propel/badge";
import { IconButton } from "@plane/propel/icon-button";
import { Tooltip } from "@plane/propel/tooltip";
import {
  TINGKAT_DIREKTUR,
  TINGKAT_SUPERVISOR,
  type TAnggotaHierarki,
  type TDepartemenOrganisasi,
  type TDivisiOrganisasi,
  type TPohonOrganisasi,
} from "@plane/services";
import { cn } from "@plane/utils";
// components
import { PersonAvatar } from "@/components/common/paradise-ui";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { MenuDepartemen, MenuDivisi } from "./menu-node";
import { cocokTeks, depCocok, divisiCocok, samaPilihan, type TKelola, type TPilihan } from "./util";

const jumlahDivisi = (v: TDivisiOrganisasi) =>
  v.manager.length + v.departemen.reduce((n, d) => n + d.anggota.length, 0);

function BarisPohon({
  aktif,
  onClick,
  icon,
  label,
  trailing,
  kedalaman = 0,
  toggle,
  menu,
}: {
  aktif: boolean;
  onClick: () => void;
  icon: ReactNode;
  label: string;
  trailing?: ReactNode;
  kedalaman?: 0 | 1;
  toggle?: ReactNode;
  /** Menu aksi; muncul saat baris di-hover atau fokus (tetap terlihat selagi menunya terbuka). */
  menu?: ReactNode;
}) {
  return (
    <div className={cn("group flex items-center", kedalaman === 1 && "ml-[18px] border-l border-subtle pl-2")}>
      {toggle ?? (kedalaman === 0 && <span className="w-5 shrink-0" />)}
      <button
        type="button"
        onClick={onClick}
        aria-current={aktif ? "true" : undefined}
        className={cn(
          "flex min-w-0 flex-1 items-center gap-2 rounded-md px-2 py-1.5 text-left text-13 transition-colors",
          aktif
            ? "bg-layer-transparent-active text-primary"
            : "text-secondary hover:bg-layer-transparent-hover active:bg-layer-transparent-active"
        )}
      >
        <span className="shrink-0 text-tertiary">{icon}</span>
        <span className="min-w-0 flex-1 truncate">
          <span className={cn(aktif && "font-medium")}>{label}</span>
        </span>
        {trailing}
      </button>
      {menu && (
        <div className="opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
          {menu}
        </div>
      )}
    </div>
  );
}

export function PohonNavigasi({
  pohon,
  pilihan,
  onPilih,
  q,
  jumlahBelum,
  jumlahDirektur,
  onKelola,
}: {
  pohon: TPohonOrganisasi;
  pilihan: TPilihan;
  onPilih: (p: TPilihan) => void;
  /** Kata cari, sudah huruf kecil. */
  q: string;
  jumlahBelum: number;
  jumlahDirektur: number;
  onKelola: TKelola;
}) {
  const { s } = useGodmodeStrings();
  // Divisi yang DIBUKA: bawaan semua terlipat supaya daftar tetap pendek.
  const [dibuka, setDibuka] = useState<Set<string>>(new Set());
  const tampil = pohon.divisi.filter((v) => divisiCocok(q, v));
  // Divisi yang memuat node terpilih selalu terbuka, kalau tidak sorotannya tersembunyi.
  const divisiAktif =
    pilihan.jenis === "divisi"
      ? pilihan.id
      : pilihan.jenis === "departemen"
        ? pohon.divisi.find((v) => v.departemen.some((d) => d.id === pilihan.id))?.id
        : undefined;
  const terbuka = (id: string) => Boolean(q) || dibuka.has(id) || id === divisiAktif;
  const bisaDilipat = pohon.divisi.filter((v) => v.departemen.length > 0);
  const semuaTerbuka = bisaDilipat.length > 0 && bisaDilipat.every((v) => terbuka(v.id));
  const lipat = (id: string) =>
    setDibuka((lama) => {
      const baru = new Set(lama);
      if (terbuka(id)) baru.delete(id);
      else baru.add(id);
      return baru;
    });

  return (
    <nav aria-label={s.org.structure} className="space-y-0.5">
      <div className="flex items-center justify-between px-2 pb-1">
        <span className="text-11 font-semibold tracking-wide text-tertiary uppercase">{s.org.structure}</span>
        {bisaDilipat.length > 0 && !q && (
          <Tooltip tooltipContent={semuaTerbuka ? s.org.collapse_all : s.org.expand_all}>
            <IconButton
              variant="ghost"
              size="sm"
              icon={semuaTerbuka ? ChevronsDownUp : ChevronsUpDown}
              aria-label={semuaTerbuka ? s.org.collapse_all : s.org.expand_all}
              onClick={() => setDibuka(semuaTerbuka ? new Set() : new Set(bisaDilipat.map((v) => v.id)))}
            />
          </Tooltip>
        )}
      </div>
      <BarisPohon
        aktif={pilihan.jenis === "ringkasan"}
        onClick={() => onPilih({ jenis: "ringkasan" })}
        icon={<Network className="size-4" />}
        label={s.org.overview}
        trailing={<span className="text-11 text-tertiary">{jumlahDirektur}</span>}
      />

      <div className="py-1">
        {tampil.length === 0 && q && <p className="px-3 py-2 text-12 text-tertiary">{s.org.no_tree_match}</p>}
        {tampil.map((v) => {
          // Mencari selalu membuka divisi, kalau tidak hasilnya tersembunyi.
          const buka = terbuka(v.id);
          const deps = v.departemen.filter((d) => !q || cocokTeks(q, v.nama, v.kode) || depCocok(q, d));
          return (
            <div key={v.id}>
              <BarisPohon
                aktif={samaPilihan(pilihan, { jenis: "divisi", id: v.id })}
                onClick={() => onPilih({ jenis: "divisi", id: v.id })}
                icon={<Building2 className="size-4" />}
                label={v.nama}
                trailing={<span className="text-11 text-tertiary">{jumlahDivisi(v)}</span>}
                menu={<MenuDivisi id={v.id} nama={v.nama} onKelola={onKelola} />}
                toggle={
                  <button
                    type="button"
                    onClick={() => lipat(v.id)}
                    aria-expanded={buka}
                    aria-label={v.nama}
                    disabled={v.departemen.length === 0}
                    className="grid size-5 shrink-0 place-items-center rounded-sm text-placeholder hover:text-secondary disabled:invisible"
                  >
                    <ChevronRight className={cn("size-3.5 transition-transform", buka && "rotate-90")} />
                  </button>
                }
              />
              {buka &&
                deps.map((d) => (
                  <BarisPohon
                    key={d.id}
                    kedalaman={1}
                    aktif={samaPilihan(pilihan, { jenis: "departemen", id: d.id })}
                    onClick={() => onPilih({ jenis: "departemen", id: d.id })}
                    icon={<Users className="size-3.5" />}
                    label={d.nama}
                    menu={<MenuDepartemen id={d.id} nama={d.nama} onKelola={onKelola} />}
                    trailing={
                      <span className="flex items-center gap-1.5">
                        {d.projects.length === 0 && (
                          <Tooltip tooltipContent={s.org.project_none}>
                            <AlertTriangle className="size-3 text-warning-primary" aria-label={s.org.project_none} />
                          </Tooltip>
                        )}
                        <span className="text-11 text-tertiary">{d.anggota.length}</span>
                      </span>
                    }
                  />
                ))}
            </div>
          );
        })}
      </div>

      {(jumlahBelum > 0 || pohon.tanpa_departemen.length > 0) && <div className="mx-2 border-t border-subtle" />}
      {jumlahBelum > 0 && (
        <BarisPohon
          aktif={pilihan.jenis === "belum"}
          onClick={() => onPilih({ jenis: "belum" })}
          icon={<UserX className="size-4" />}
          label={s.org.unplaced_node}
          trailing={
            <Badge variant="warning" size="sm">
              {jumlahBelum}
            </Badge>
          }
        />
      )}
      {pohon.tanpa_departemen.length > 0 && (
        <BarisPohon
          aktif={pilihan.jenis === "lama"}
          onClick={() => onPilih({ jenis: "lama" })}
          icon={<FolderInput className="size-4" />}
          label={s.org.legacy_node}
          trailing={
            <Badge variant="neutral" size="sm">
              {pohon.tanpa_departemen.length}
            </Badge>
          }
        />
      )}
    </nav>
  );
}

// ---------------------------------------------------------------------------
// Bagan organisasi (ringkasan perusahaan)
// ---------------------------------------------------------------------------

/**
 * Kotak bagan. Bisa diklik lewat tombol judul yang "direntangkan" (`after:inset-0`)
 * menutupi seluruh kotak, sehingga menu "..." bisa jadi saudara tombol itu,
 * bukan tombol di dalam tombol.
 */
function KotakBagan({
  judul,
  onClick,
  menu,
  children,
  tone = "neutral",
}: {
  judul: ReactNode;
  onClick?: () => void;
  menu?: ReactNode;
  children?: ReactNode;
  tone?: "neutral" | "accent";
}) {
  return (
    <div
      className={cn(
        "relative w-full rounded-lg border bg-surface-1 px-3 py-2.5 text-left shadow-raised-100 transition-all",
        tone === "accent" ? "border-accent-subtle" : "border-subtle",
        onClick &&
          "hover:border-strong hover:shadow-raised-200 has-[button:focus-visible]:ring-2 has-[button:focus-visible]:ring-accent-strong"
      )}
    >
      <div className="flex items-center gap-2">
        {onClick ? (
          <button
            type="button"
            onClick={onClick}
            className="flex min-w-0 flex-1 items-center gap-2 text-left outline-none after:absolute after:inset-0 after:rounded-lg"
          >
            {judul}
          </button>
        ) : (
          <div className="flex min-w-0 flex-1 items-center gap-2">{judul}</div>
        )}
        {menu && <div className="relative z-[1] -my-1 -mr-1.5">{menu}</div>}
      </div>
      {children}
    </div>
  );
}

/** Garis tegak penghubung antar-tingkat. */
const GarisTegak = () => <div className="mx-auto h-6 w-0 border-l border-strong" aria-hidden />;

function KotakDepartemen({
  d,
  onPilih,
  onKelola,
}: {
  d: TDepartemenOrganisasi;
  onPilih: (p: TPilihan) => void;
  onKelola: TKelola;
}) {
  const { s, fill } = useGodmodeStrings();
  const sup = d.anggota.filter((a) => a.tingkat >= TINGKAT_SUPERVISOR).length;
  return (
    <KotakBagan
      onClick={() => onPilih({ jenis: "departemen", id: d.id })}
      menu={<MenuDepartemen id={d.id} nama={d.nama} onKelola={onKelola} onPilih={onPilih} />}
      judul={
        <>
          <span className="truncate text-12 font-medium text-primary">{d.nama}</span>
          <span className="ml-auto shrink-0 text-10 text-placeholder">{d.kode}</span>
        </>
      }
    >
      <div className="mt-1 text-10 text-tertiary">{fill(s.org.sup_staff, { sup, staff: d.anggota.length - sup })}</div>
      <div className="mt-1 flex items-center gap-1 text-10">
        <FolderKanban className="size-3 shrink-0 text-placeholder" aria-hidden />
        {d.projects[0] ? (
          <span className="truncate text-secondary">{d.projects[0].name}</span>
        ) : (
          <span className="text-warning-primary">{s.org.project_none}</span>
        )}
      </div>
    </KotakBagan>
  );
}

function KolomDivisi({
  v,
  onPilih,
  onKelola,
}: {
  v: TDivisiOrganisasi;
  onPilih: (p: TPilihan) => void;
  onKelola: TKelola;
}) {
  const { s } = useGodmodeStrings();
  return (
    // Garis datar: tiap kolom menggambar setengah kiri + kanan; kolom
    // pertama/terakhir memotong sisi luarnya, jadi garis berhenti di tengah.
    <div className="relative w-64 shrink-0 px-2.5 pt-6 before:absolute before:top-0 before:right-0 before:left-0 before:border-t before:border-strong first:before:left-1/2 last:before:right-1/2 only:before:hidden">
      <div className="absolute top-0 left-1/2 h-6 w-0 border-l border-strong" aria-hidden />
      <KotakBagan
        onClick={() => onPilih({ jenis: "divisi", id: v.id })}
        menu={<MenuDivisi id={v.id} nama={v.nama} onKelola={onKelola} onPilih={onPilih} />}
        judul={
          <>
            <Building2 className="size-4 shrink-0 text-tertiary" aria-hidden />
            <span className="truncate text-13 font-semibold text-primary">{v.nama}</span>
            <span className="ml-auto shrink-0 text-11 text-placeholder">{v.kode}</span>
          </>
        }
      >
        <div className="mt-2 space-y-1">
          {v.manager.length === 0 ? (
            <span className="text-11 text-danger-primary">{s.org.no_manager_short}</span>
          ) : (
            v.manager.map((m) => (
              <div key={m.id} className="flex items-center gap-1.5 text-12 text-secondary" title={m.email}>
                <PersonAvatar name={m.nama} size="sm" />
                <span className="truncate">{m.nama}</span>
              </div>
            ))
          )}
        </div>
      </KotakBagan>

      <ul className="mt-2 ml-4 space-y-2 border-l border-strong pt-2 pl-3">
        {v.departemen.map((d) => (
          <li
            key={d.id}
            className="relative before:absolute before:top-1/2 before:-left-3 before:w-3 before:border-t before:border-strong"
          >
            <KotakDepartemen d={d} onPilih={onPilih} onKelola={onKelola} />
          </li>
        ))}
        <li className="relative before:absolute before:top-1/2 before:-left-3 before:w-3 before:border-t before:border-dashed before:border-subtle">
          <button
            type="button"
            onClick={() => onKelola({ jenis: "buat-departemen", divisiId: v.id })}
            className="flex w-full items-center justify-center gap-1 rounded-lg border border-dashed border-subtle py-1.5 text-11 text-tertiary transition-colors hover:border-strong hover:text-primary"
          >
            <Plus className="size-3" aria-hidden />
            {s.org.new_department}
          </button>
        </li>
      </ul>
    </div>
  );
}

export function BaganOrganisasi({
  pohon,
  anggota,
  onPilih,
  onKelola,
}: {
  pohon: TPohonOrganisasi;
  anggota: TAnggotaHierarki[];
  onPilih: (p: TPilihan) => void;
  onKelola: TKelola;
}) {
  const { s, fill } = useGodmodeStrings();
  const direktur = anggota.filter((o) => o.is_active && o.tingkat !== null && o.tingkat >= TINGKAT_DIREKTUR);

  return (
    // Lebar alami (w-max): ukuran ini yang dibaca kanvas untuk "pas ke layar".
    <div className="w-max min-w-72 p-6">
      {/* Puncak: perusahaan + direktur */}
      <div className="mx-auto w-72">
        <KotakBagan
          tone="accent"
          judul={
            <>
              <Crown className="size-4 text-accent-primary" aria-hidden />
              <span className="text-13 font-semibold text-primary">{s.org.company}</span>
              <span className="ml-auto text-11 text-tertiary">{fill(s.org.people_count, { n: direktur.length })}</span>
            </>
          }
        >
          {direktur.length === 0 ? (
            <p className="mt-1.5 text-11 text-tertiary">{s.org.no_directors}</p>
          ) : (
            <ul className="mt-2 space-y-1">
              {direktur.map((d) => (
                <li key={d.id} className="flex items-center gap-2 text-12 text-primary" title={d.email}>
                  <PersonAvatar name={d.display_name} size="sm" />
                  <span className="truncate">{d.display_name}</span>
                </li>
              ))}
            </ul>
          )}
        </KotakBagan>
      </div>

      {pohon.divisi.length > 0 && (
        <>
          <GarisTegak />
          <div className="flex justify-center">
            {pohon.divisi.map((v) => (
              <KolomDivisi key={v.id} v={v} onPilih={onPilih} onKelola={onKelola} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
