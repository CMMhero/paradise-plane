/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: orang yang bisa diseret di papan organisasi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * - ChipOrang: satu orang yang bisa diseret (pragmatic-drag-and-drop, sama
 *   dengan apps/web). Menu "..." di chip memuat padanan papan ketik untuk
 *   setiap seretan: Add to, Move to, Remove from, Make <jenjang>.
 * - useTujuanLepas: menjadikan elemen tujuan lepas + tahu mode yang akan terjadi
 *   (tambah/pindah/pimpin/jenjang) selagi kursor di atasnya, untuk labelnya.
 * - PanelOrangPapan: daftar semua orang, bisa dicari, dengan saring "Unassigned".
 *   Juga tujuan lepas: chip dari departemen/divisi yang diseret kembali ke sini
 *   dicabut dari tempat itu saja, jenjangnya tetap (KEP-86).
 * - ModalPilihTujuan: pemilih tujuan untuk Add to / Move to.
 */

import { useEffect, useRef, useState, type RefObject } from "react";
import { sortBy } from "lodash-es";
import { Search } from "lucide-react";
import { draggable, dropTargetForElements } from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
// plane imports
import { Button } from "@plane/propel/button";
import { Tabs } from "@plane/propel/tabs";
import {
  TINGKAT_DIREKTUR,
  TINGKAT_MEMBER,
  TINGKAT_SEKRETARIS,
  TINGKAT_SUPERVISOR,
  menjangkauSeluruhOrganisasi,
  type TPohonOrganisasi,
} from "@plane/services";
import { CustomMenu, CustomSearchSelect, Input } from "@plane/ui";
import { cn } from "@plane/utils";
// components
import { EModalWidth, Field, ParadiseModal, PersonAvatar } from "@/components/common/paradise-ui";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { BadgeJabatan } from "../members/jabatan";
import { usePapan, type TPemilihTujuan } from "./papan-konteks";
import {
  bacaSeret,
  belumDitempatkan,
  dataSeret,
  dataTujuan,
  modeLepas,
  namaJenjang,
  tombolSalin,
  type TAsal,
  type TTujuan,
} from "./papan-logika";

// ---------------------------------------------------------------------------
// Tujuan lepas
// ---------------------------------------------------------------------------

export type TModeLepas = ReturnType<typeof modeLepas> | null;

/**
 * Daftarkan `ref` sebagai tujuan lepas. Mode hanya terisi selagi elemen ini
 * tujuan TERDALAM (lajur di dalam kartu departemen menang atas kartunya).
 */
export function useTujuanLepas(ref: RefObject<HTMLElement | null>, tujuan: TTujuan, aktif = true): TModeLepas {
  const [mode, setMode] = useState<TModeLepas>(null);
  const kunci = JSON.stringify(tujuan);
  useEffect(() => {
    const el = ref.current;
    // `aktif=false`: elemen ini hanya sumber seretan (lajur Levels selain Direktur, KEP-93).
    if (!el || !aktif) return;
    const t = JSON.parse(kunci) as TTujuan;
    return dropTargetForElements({
      element: el,
      getData: () => dataTujuan(t),
      canDrop: ({ source }) => bacaSeret(source.data) !== null,
      onDrag: ({ source, location }) => {
        const seret = bacaSeret(source.data);
        const terdalam = location.current.dropTargets[0]?.element === el;
        setMode(seret && terdalam ? modeLepas(seret.asal, t, tombolSalin(location.current.input)) : null);
      },
      onDragLeave: () => setMode(null),
      onDrop: () => setMode(null),
    });
  }, [ref, kunci, aktif]);
  return mode;
}

/** Kelas sorotan tujuan yang sedang dituju. Garis putus aksen, tanpa mengubah ukuran. */
export const kelasSorot = (mode: TModeLepas): string =>
  mode ? "outline-2 outline-offset-2 outline-dashed outline-accent-strong bg-layer-transparent-hover" : "";

/** Label kecil di pojok tujuan: apa yang terjadi kalau dilepas sekarang. */
export function LabelLepas({ mode, tingkat }: { mode: TModeLepas; tingkat?: number }) {
  const { s, fill } = useGodmodeStrings();
  if (!mode) return null;
  const teks =
    mode === "pindah"
      ? s.org.board.drop_move
      : mode === "pimpin"
        ? s.org.board.drop_lead
        : mode === "jenjang" && tingkat !== undefined
          ? fill(s.org.board.drop_level, { level: namaJenjang(tingkat, s) })
          : s.org.board.drop_add;
  return (
    <span
      className="pointer-events-none absolute -top-2.5 right-2 z-[1] rounded-control bg-accent-primary px-1.5 text-11 font-medium text-on-color"
      aria-hidden
    >
      {teks}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Chip orang
// ---------------------------------------------------------------------------

function MenuOrang({ orangId, nama, asal, tingkat }: { orangId: string; nama: string; asal?: TAsal; tingkat: number }) {
  const { s, fill } = useGodmodeStrings();
  const { eksekusi, cabut, bukaPemilih, namaTempat } = usePapan();
  return (
    <CustomMenu
      ellipsis
      closeOnSelect
      placement="bottom-end"
      ariaLabel={fill(s.org.actions_for, { name: nama })}
      portalElement={typeof document === "undefined" ? undefined : document.body}
    >
      <CustomMenu.MenuItem onClick={() => bukaPemilih({ orangId, asal, mode: "tambah" })}>
        {s.org.board.menu_add_to}
      </CustomMenu.MenuItem>
      {asal && (
        <CustomMenu.MenuItem onClick={() => bukaPemilih({ orangId, asal, mode: "pindah" })}>
          {s.org.board.menu_move_to}
        </CustomMenu.MenuItem>
      )}
      {/* KEP-93: peran melekat pada tempat. Di departemen: ganti peran di sana saja.
          Jenjang umum hanya Sekretaris dan Direktur (jenjang tanpa tempat). */}
      {asal?.jenis === "departemen" && !menjangkauSeluruhOrganisasi(tingkat) && (
        <CustomMenu.MenuItem
          onClick={() => {
            const lain = tingkat >= TINGKAT_SUPERVISOR ? TINGKAT_MEMBER : TINGKAT_SUPERVISOR;
            void eksekusi(orangId, asal, { jenis: "departemen", id: asal.id, tingkat: lain }, false);
          }}
        >
          {fill(s.org.board.menu_role_here, {
            role: namaJenjang(tingkat >= TINGKAT_SUPERVISOR ? TINGKAT_MEMBER : TINGKAT_SUPERVISOR, s),
            place: namaTempat(asal),
          })}
        </CustomMenu.MenuItem>
      )}
      {[TINGKAT_SEKRETARIS, TINGKAT_DIREKTUR]
        .filter((t) => t !== tingkat)
        .map((t) => (
          <CustomMenu.MenuItem
            key={t}
            onClick={() => void eksekusi(orangId, asal, { jenis: "jenjang", tingkat: t }, false)}
          >
            {fill(s.org.board.menu_level, { level: namaJenjang(t, s) })}
          </CustomMenu.MenuItem>
        ))}
      {menjangkauSeluruhOrganisasi(tingkat) && (
        <CustomMenu.MenuItem
          onClick={() => void eksekusi(orangId, asal, { jenis: "jenjang", tingkat: TINGKAT_MEMBER }, false)}
        >
          {fill(s.org.board.menu_remove_level, { level: namaJenjang(tingkat, s) })}
        </CustomMenu.MenuItem>
      )}
      {asal && (
        <CustomMenu.MenuItem variant="danger" onClick={() => void cabut(orangId, asal)}>
          {fill(s.org.board.menu_remove_from, { place: namaTempat(asal) })}
        </CustomMenu.MenuItem>
      )}
    </CustomMenu>
  );
}

/**
 * Satu orang di papan. `asal` = tempat chip ini tinggal (departemen/divisi);
 * tanpa asal (daftar People) seretannya selalu menambah.
 */
export function ChipOrang({
  orangId,
  nama,
  email,
  tingkat,
  asal,
  ringkas = false,
}: {
  orangId: string;
  nama: string;
  email: string;
  tingkat: number;
  asal?: TAsal;
  /** Lajur Levels: jenjangnya sudah jadi judul lajur, jadi tanpa label dan tanpa menu. */
  ringkas?: boolean;
}) {
  const { orangById } = usePapan();
  const ref = useRef<HTMLDivElement>(null);
  const [diseret, setDiseret] = useState(false);
  // Orang yang tak ada di daftar member (mis. akun terhapus) tampil tapi tak bisa diseret.
  const bisa = orangById.has(orangId);
  const kunciAsal = asal ? `${asal.jenis}:${asal.id}` : "";
  // Hanya chip lajur Levels: direktur di daftar People sendiri tidak ikut turun saat dilepas di panelnya.
  const direktur = ringkas && !asal && menjangkauSeluruhOrganisasi(tingkat);

  useEffect(() => {
    const el = ref.current;
    if (!el || !bisa) return;
    const [jenis, id] = kunciAsal.split(":");
    const a: TAsal | undefined = kunciAsal ? { jenis: jenis as TAsal["jenis"], id } : undefined;
    return draggable({
      element: el,
      getInitialData: () => dataSeret({ orangId, asal: a, direktur }),
      onDragStart: () => setDiseret(true),
      onDrop: () => setDiseret(false),
    });
  }, [orangId, kunciAsal, bisa, direktur]);

  return (
    <div
      ref={ref}
      title={email}
      className={cn(
        "group flex min-w-0 items-center gap-2 rounded-item border border-subtle bg-layer-2 py-1 pr-0.5 pl-1.5 transition-colors",
        bisa && "cursor-grab hover:border-strong active:cursor-grabbing",
        diseret && "opacity-40"
      )}
    >
      <PersonAvatar name={nama || email} size="sm" />
      <span className="min-w-0 flex-1 truncate text-12 text-primary">{nama || email}</span>
      {!ringkas && <BadgeJabatan tingkat={tingkat} size="sm" />}
      {bisa && !ringkas && <MenuOrang orangId={orangId} nama={nama || email} asal={asal} tingkat={tingkat} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Panel People
// ---------------------------------------------------------------------------

/**
 * Panel People sebagai tujuan "lepas". Tidak memakai useTujuanLepas karena labelnya
 * butuh nama tempat ASAL seretan ("Remove from Finance"), bukan nama tujuan.
 */
type TLepasPanel = { asal: TAsal } | { direktur: true } | null;

function useLepasKePanel(ref: RefObject<HTMLElement | null>): TLepasPanel {
  const [lepas, setLepas] = useState<TLepasPanel>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const baca = (data: Record<string | symbol, unknown>): TLepasPanel => {
      const seret = bacaSeret(data);
      if (seret?.asal) return { asal: seret.asal };
      // Direktur tidak punya tempat; diseret ke People = turun ke Staf.
      return seret?.direktur ? { direktur: true } : null;
    };
    return dropTargetForElements({
      element: el,
      getData: () => dataTujuan({ jenis: "lepas" }),
      // Chip tanpa tempat (daftar ini sendiri, lajur Levels) tidak bisa dilepas,
      // kecuali direktur.
      canDrop: ({ source }) => baca(source.data) !== null,
      onDragEnter: ({ source }) => setLepas(baca(source.data)),
      onDragLeave: () => setLepas(null),
      onDrop: () => setLepas(null),
    });
  }, [ref]);
  return lepas;
}

export function PanelOrangPapan() {
  const { s, fill } = useGodmodeStrings();
  const { orangById, namaTempat } = usePapan();
  const ref = useRef<HTMLElement>(null);
  const lepas = useLepasKePanel(ref);
  const [cari, setCari] = useState("");
  const [saring, setSaring] = useState<"semua" | "belum">("semua");
  const semua = sortBy([...orangById.values()], (o) => o.display_name.toLowerCase());
  const belum = semua.filter(belumDitempatkan);
  const q = cari.trim().toLowerCase();
  const tampil = (saring === "belum" ? belum : semua).filter(
    (o) => !q || `${o.display_name} ${o.email}`.toLowerCase().includes(q)
  );

  return (
    <aside
      ref={ref}
      title={s.org.board.drop_remove_hint}
      className={cn(
        // Lengket selama papan digulir (md ke atas, saat dua kolom). Tingginya dibatasi
        // layar supaya panel tidak pernah lebih tinggi dari viewport (sticky mati kalau iya).
        "relative space-y-3 rounded-card border border-subtle bg-layer-1 p-3 transition-colors md:sticky md:top-2 md:max-h-[calc(100dvh-7rem)] md:self-start",
        lepas && "bg-danger-subtle outline-2 outline-offset-2 outline-danger-strong outline-dashed"
      )}
    >
      {lepas && (
        <span
          className="pointer-events-none absolute -top-2.5 right-2 z-[1] rounded-control bg-danger-primary px-1.5 text-11 font-medium text-on-color"
          aria-hidden
        >
          {"asal" in lepas
            ? fill(s.org.board.drop_remove, { place: namaTempat(lepas.asal) })
            : s.org.board.drop_remove_top}
        </span>
      )}
      <div className="flex items-center justify-between px-1">
        <span className="text-11 font-semibold text-tertiary">{s.org.board.people}</span>
        <span className="text-11 text-tertiary">{fill(s.org.people_count, { n: semua.length })}</span>
      </div>
      <div className="flex h-8 items-center gap-1.5 search-field border border-subtle bg-layer-2 px-2.5 focus-within:border-accent-strong">
        <Search className="size-3.5 shrink-0 text-placeholder" aria-hidden />
        <Input
          type="text"
          mode="true-transparent"
          className="w-full min-w-0 p-0 text-primary placeholder:text-placeholder"
          placeholder={s.org.board.people_search}
          aria-label={s.org.board.people_search}
          value={cari}
          onChange={(e) => setCari(e.target.value)}
        />
      </div>
      <Tabs value={saring} onValueChange={(v) => setSaring(v === "belum" ? "belum" : "semua")}>
        <Tabs.List aria-label={s.org.board.filter_label}>
          <Tabs.Trigger value="semua" size="sm">
            {s.org.board.filter_all} · {semua.length}
          </Tabs.Trigger>
          <Tabs.Trigger value="belum" size="sm">
            {s.org.board.filter_unassigned} · {belum.length}
          </Tabs.Trigger>
        </Tabs.List>
      </Tabs>
      {tampil.length === 0 ? (
        <p className="px-1 py-4 text-center text-12 text-tertiary">{s.org.board.people_empty}</p>
      ) : (
        <ul className="vertical-scrollbar -mr-1 scrollbar-sm max-h-[calc(100dvh-280px)] space-y-1 overflow-y-auto pr-1">
          {tampil.map((o) => (
            <li key={o.id}>
              <ChipOrang orangId={o.id} nama={o.display_name} email={o.email} tingkat={o.tingkat ?? 10} />
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}

// ---------------------------------------------------------------------------
// Pemilih tujuan (padanan papan ketik untuk seretan)
// ---------------------------------------------------------------------------

export function ModalPilihTujuan({
  pemilih,
  pohon,
  onTutup,
}: {
  pemilih: TPemilihTujuan | null;
  pohon: TPohonOrganisasi;
  onTutup: () => void;
}) {
  const { s, fill } = useGodmodeStrings();
  const { orangById, eksekusi, namaTempat } = usePapan();
  const [nilai, setNilai] = useState("");
  const [sibuk, setSibuk] = useState(false);
  const o = pemilih ? orangById.get(pemilih.orangId) : undefined;
  const pindah = pemilih?.mode === "pindah" && pemilih.asal;

  // Pindah hanya ke tempat sejenis (departemen -> departemen, divisi -> divisi).
  const bolehDivisi = !pindah || pemilih?.asal?.jenis === "divisi";
  const bolehDep = !pindah || pemilih?.asal?.jenis === "departemen";
  const opsi = [
    ...(bolehDivisi
      ? pohon.divisi
          .filter((v) => !(pindah && pemilih?.asal?.id === v.id))
          .map((v) => ({
            value: `div:${v.id}`,
            query: `${v.nama} ${v.kode}`,
            content: <span className="truncate">{fill(s.org.board.lead_option, { div: v.nama })}</span>,
          }))
      : []),
    ...(bolehDep
      ? pohon.divisi.flatMap((v) =>
          v.departemen
            .filter((d) => !(pindah && pemilih?.asal?.id === d.id))
            .map((d) => ({
              value: `dep:${d.id}`,
              query: `${d.nama} ${d.kode} ${v.nama}`,
              content: (
                <span className="flex w-64 items-center justify-between gap-2">
                  <span className="truncate">{d.nama}</span>
                  <span className="truncate text-10 text-tertiary">{v.nama}</span>
                </span>
              ),
            }))
        )
      : []),
  ];
  const labelNilai = (() => {
    if (!nilai) return s.org.assign_target;
    const id = nilai.slice(4);
    return nilai.startsWith("div:")
      ? fill(s.org.board.lead_option, { div: namaTempat({ jenis: "divisi", id }) })
      : namaTempat({ jenis: "departemen", id });
  })();

  const tutup = () => {
    setNilai("");
    onTutup();
  };
  const kirim = async () => {
    if (!pemilih || !nilai) return;
    const id = nilai.slice(4);
    const tujuan: TTujuan = nilai.startsWith("div:") ? { jenis: "divisi", id } : { jenis: "departemen", id };
    setSibuk(true);
    try {
      await eksekusi(pemilih.orangId, pindah ? pemilih.asal : undefined, tujuan, !pindah);
      tutup();
    } finally {
      setSibuk(false);
    }
  };

  const nama = o?.display_name ?? "";
  return (
    <ParadiseModal
      isOpen={Boolean(pemilih && o)}
      onClose={tutup}
      width={EModalWidth.MD}
      title={
        pindah && pemilih?.asal
          ? fill(s.org.board.pick_title_move, { name: nama, from: namaTempat(pemilih.asal) })
          : fill(s.org.board.pick_title_add, { name: nama })
      }
      closeLabel={s.editor.close}
      footer={
        <>
          <Button variant="secondary" size="base" onClick={tutup}>
            {s.org.cancel}
          </Button>
          <Button variant="primary" size="base" loading={sibuk} disabled={!nilai} onClick={() => void kirim()}>
            {pindah ? s.org.board.pick_move : s.org.board.pick_add}
          </Button>
        </>
      }
    >
      <Field label={s.org.board.pick_label} hint={bolehDivisi ? s.org.board.pick_division_note : undefined}>
        <CustomSearchSelect
          value={nilai}
          label={<span className={nilai ? "text-primary" : "text-placeholder"}>{labelNilai}</span>}
          onChange={(v: string) => setNilai(v)}
          buttonClassName="w-full"
          className="w-full"
          input
          maxHeight="lg"
          options={opsi}
        />
      </Field>
    </ParadiseModal>
  );
}
