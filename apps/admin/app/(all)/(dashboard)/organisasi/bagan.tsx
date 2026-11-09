/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: bagan struktur organisasi (KEP-29, KEP-86)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Bagan atas-ke-bawah (direktur > divisi + manager > departemen) dengan garis
 * penghubung dari border, dipasang di dalam KanvasBagan (geser/zoom). Tampil di
 * atas papan: klik kotak = buka divisinya di papan lalu gulir ke sana, menu "..."
 * mengirim perintah ke modal kelola yang sama dengan papan.
 */

import type { ReactNode } from "react";
import { Building2, Crown, Plus } from "lucide-react";
// plane imports
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
import { ATRIBUT_KELUAR_BAGAN } from "./kanvas-bagan";
import { MenuDepartemen, MenuDivisi } from "./menu-node";
import type { TKelola } from "./util";

/** Buka divisi di papan; `departemenId` = kartu yang disorot sesudah digulir. */
export type TBukaDiPapan = (divisiId: string, departemenId?: string) => void;

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
        "relative w-full rounded-card border bg-surface-1 px-3 py-2.5 text-left shadow-raised-100 transition-all",
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
            className="flex min-w-0 flex-1 items-center gap-2 text-left outline-none after:absolute after:inset-0 after:rounded-card"
            {...{ [ATRIBUT_KELUAR_BAGAN]: "" }}
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

/**
 * Tinggi garis tegak per departemen, kunci `pertama-terakhir`. Garis mulai 0,5rem
 * (jarak antar-baris) di atas baris, atau 1rem untuk baris pertama (sampai ke kotak
 * divisi); baris terakhir berhenti tepat di tengah (50%).
 */
const GARIS_TEGAK: Record<string, string> = {
  "true-true": "after:h-[calc(50%+1rem)]",
  "true-false": "after:h-[calc(100%+1.5rem)]",
  "false-true": "after:h-[calc(50%+0.5rem)]",
  "false-false": "after:h-[calc(100%+1rem)]",
};

/** Garis tegak penghubung antar-tingkat. */
const GarisTegak = () => <div className="mx-auto h-6 w-0 border-l border-strong" aria-hidden />;

function KotakDepartemen({
  d,
  divisiId,
  onBuka,
  onKelola,
}: {
  d: TDepartemenOrganisasi;
  divisiId: string;
  onBuka: TBukaDiPapan;
  onKelola: TKelola;
}) {
  const { s, fill } = useGodmodeStrings();
  const sup = d.anggota.filter((a) => a.tingkat >= TINGKAT_SUPERVISOR).length;
  return (
    <KotakBagan
      onClick={() => onBuka(divisiId, d.id)}
      menu={<MenuDepartemen id={d.id} nama={d.nama} onKelola={onKelola} />}
      judul={
        <>
          <span className="truncate text-12 font-medium text-primary">{d.nama}</span>
          <span className="ml-auto shrink-0 text-10 text-placeholder">{d.kode}</span>
        </>
      }
    >
      <div className="mt-1 text-10 text-tertiary">{fill(s.org.sup_staff, { sup, staff: d.anggota.length - sup })}</div>
      {!d.projects[0] && <div className="mt-1 text-10 text-warning-primary">{s.org.project_none}</div>}
    </KotakBagan>
  );
}

function KolomDivisi({ v, onBuka, onKelola }: { v: TDivisiOrganisasi; onBuka: TBukaDiPapan; onKelola: TKelola }) {
  const { s } = useGodmodeStrings();
  return (
    // Garis datar: tiap kolom menggambar setengah kiri + kanan; kolom
    // pertama/terakhir memotong sisi luarnya, jadi garis berhenti di tengah.
    <div className="relative w-64 shrink-0 px-2.5 pt-6 before:absolute before:top-0 before:right-0 before:left-0 before:border-t before:border-strong first:before:left-1/2 last:before:right-1/2 only:before:hidden">
      <div className="absolute top-0 left-1/2 h-6 w-0 border-l border-strong" aria-hidden />
      <KotakBagan
        onClick={() => onBuka(v.id)}
        menu={<MenuDivisi id={v.id} nama={v.nama} onKelola={onKelola} />}
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

      {/* Garis tegak digambar per departemen (bukan border-l pada ul) supaya berhenti
          di tengah departemen terakhir dan tidak menggantung sampai tombol tambah. */}
      <ul className="mt-2 ml-4 space-y-2 pt-2 pl-3">
        {v.departemen.map((d, i) => {
          const pertama = i === 0;
          const terakhir = i === v.departemen.length - 1;
          return (
            <li
              key={d.id}
              className={`relative before:absolute before:top-1/2 before:-left-3 before:w-3 before:border-t before:border-strong after:absolute after:-left-3 after:border-l after:border-strong ${
                pertama ? "after:-top-4" : "after:-top-2"
              } ${GARIS_TEGAK[`${pertama}-${terakhir}`]}`}
            >
              <KotakDepartemen d={d} divisiId={v.id} onBuka={onBuka} onKelola={onKelola} />
            </li>
          );
        })}
        <li className="relative">
          <button
            type="button"
            onClick={() => onKelola({ jenis: "buat-departemen", divisiId: v.id })}
            className="flex w-full items-center justify-center gap-1 rounded-card border border-dashed border-subtle py-1.5 text-11 text-tertiary transition-colors hover:border-strong hover:text-primary"
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
  onBuka,
  onKelola,
}: {
  pohon: TPohonOrganisasi;
  anggota: TAnggotaHierarki[];
  onBuka: TBukaDiPapan;
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
              <KolomDivisi key={v.id} v={v} onBuka={onBuka} onKelola={onKelola} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
