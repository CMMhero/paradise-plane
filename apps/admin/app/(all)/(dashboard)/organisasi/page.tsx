/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: struktur divisi -> departemen -> project (KEP-29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tata letak master-detail: angka ringkas di atas, pohon organisasi di kiri
 * (perusahaan > divisi > departemen, plus "belum ditempatkan" dan project
 * lama), panel node terpilih di kanan. Ringkasan perusahaan menggambar bagan
 * atas-ke-bawah. Buat/ubah/hapus divisi & departemen, pindah departemen ke
 * divisi lain, pilih project departemen, dan tempatkan orang (staf/supervisor
 * ke departemen, manager ke divisi). Penempatan ke divisi otomatis menaikkan
 * jenjang ke Manager — tak perlu bolak-balik ke halaman Member.
 *
 * Bagan ringkasan bisa digeser & di-zoom (kanvas-bagan.tsx), panel pohon kiri
 * bisa dilipat jadi rel ikon (diingat di localStorage), dan setiap kotak bagan
 * serta baris pohon punya menu "..." untuk ubah, hapus, tambah orang, dan
 * pindah departemen. Semua modal kelola tinggal di satu tempat (kelola.tsx).
 */

import { useState } from "react";
import { FolderInput, Network, PanelLeftClose, PanelLeftOpen, Plus, Search, UserX } from "lucide-react";
import useSWR from "swr";
// plane imports
import { Button } from "@plane/propel/button";
import { IconButton } from "@plane/propel/icon-button";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import { Tooltip } from "@plane/propel/tooltip";
import {
  InstanceHierarkiService,
  InstanceOrganisasiService,
  TINGKAT_DIREKTUR,
  TINGKAT_MANAGER,
  TINGKAT_SUPERVISOR,
  type TAnggotaHierarki,
  type TPohonOrganisasi,
} from "@plane/services";
import { Input, Loader } from "@plane/ui";
import { cn } from "@plane/utils";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
import { StatCard, StateBox } from "@/components/common/paradise";
import { Panel } from "@/components/common/paradise-ui";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { MembersTabs } from "@/components/common/section-tabs";
import { DetailBelumDitempatkan, DetailDepartemen, DetailDivisi } from "./detail";
import { KanvasBagan } from "./kanvas-bagan";
import { KelolaOrganisasi } from "./kelola";
import { BaganOrganisasi, PohonNavigasi } from "./pohon";
import { BarisProjectLama } from "./project-lama";
import { cariDepartemen, type TAksiOrganisasi, type TPerintahKelola, type TPilihan } from "./util";

const layanan = new InstanceOrganisasiService();
const hierarkiService = new InstanceHierarkiService();

/** Panel pohon terlipat atau tidak, per peramban. */
const KUNCI_POHON_TERLIPAT = "paradise_org_tree_collapsed";
const bacaTerlipat = (): boolean => {
  try {
    return typeof window !== "undefined" && window.localStorage.getItem(KUNCI_POHON_TERLIPAT) === "1";
  } catch {
    return false;
  }
};

const pesanGagal = (err: unknown, fallback: string): string => {
  const pesan = (err as { error?: string } | undefined)?.error;
  return typeof pesan === "string" && pesan.length > 0 ? pesan : fallback;
};

export default function OrganisasiPage() {
  const { s, fill } = useGodmodeStrings();
  const { data, mutate, isLoading } = useSWR("INSTANCE_ORGANISASI", () => layanan.pohon());
  // Sumber calon penempatan + kunci yang sama dengan halaman Member, supaya
  // perubahan di sini langsung terlihat di sana.
  const { data: hierarki, mutate: mutateHierarki } = useSWR(["INSTANCE_HIERARKI"], () => hierarkiService.ringkasan());
  const [cari, setCari] = useState("");
  const [pilihan, setPilihan] = useState<TPilihan>({ jenis: "ringkasan" });
  const [perintah, setPerintah] = useState<TPerintahKelola | null>(null);
  const [terlipat, setTerlipat] = useState(bacaTerlipat);
  const ubahTerlipat = (nilai: boolean) => {
    setTerlipat(nilai);
    try {
      window.localStorage.setItem(KUNCI_POHON_TERLIPAT, nilai ? "1" : "0");
    } catch {
      // Mode privat / kuota penuh: lipatan tetap berlaku di sesi ini saja.
    }
  };

  /** Aksi struktur: balasan server = pohon terbaru, jadi tidak perlu fetch ulang. */
  const jalankan = async (aksi: () => Promise<TPohonOrganisasi>, berhasil: string): Promise<boolean> => {
    try {
      await mutate(await aksi(), { revalidate: false });
      await mutateHierarki();
      setToast({ type: TOAST_TYPE.SUCCESS, title: berhasil });
      return true;
    } catch (err) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: s.org.save_failed,
        message: pesanGagal(err, s.org.save_failed_message),
      });
      return false;
    }
  };

  const aksi: TAksiOrganisasi = {
    buatDivisi: (kode, nama) =>
      jalankan(() => layanan.buatDivisi({ kode, nama }), fill(s.org.division_created, { kode })),
    ubahDivisi: (id, kode, nama) =>
      jalankan(() => layanan.ubahDivisi(id, { kode, nama }), fill(s.org.division_saved, { kode })),
    hapusDivisi: async (id) => {
      const ok = await jalankan(() => layanan.hapusDivisi(id), s.org.division_deleted);
      // Node yang sedang dibuka ikut hilang: kembali ke ringkasan.
      if (ok) setPilihan((p) => (p.jenis === "divisi" && p.id === id ? { jenis: "ringkasan" } : p));
      return ok;
    },
    buatDepartemen: (divisiId, kode, nama) =>
      jalankan(
        () => layanan.buatDepartemen({ divisi_id: divisiId, kode, nama }),
        fill(s.org.department_created, { kode })
      ),
    ubahDepartemen: (id, isi) => jalankan(() => layanan.ubahDepartemen(id, isi), s.org.department_saved),
    simpanProject: (id, projectIds) =>
      jalankan(() => layanan.ubahDepartemen(id, { project_ids: projectIds }), s.org.department_saved),
    hapusDepartemen: async (id) => {
      // Induk dicatat sebelum dihapus, supaya panel bisa mundur ke divisinya.
      const induk = data ? cariDepartemen(data.divisi, id)?.divisi.id : undefined;
      const ok = await jalankan(() => layanan.hapusDepartemen(id), s.org.department_deleted);
      if (ok)
        setPilihan((p) =>
          p.jenis === "departemen" && p.id === id
            ? induk
              ? { jenis: "divisi", id: induk }
              : { jenis: "ringkasan" }
            : p
        );
      return ok;
    },
    // KEP-76: `departemen_id` / `divisi_id` di server = TAMBAH satu tempat,
    // penempatan lama tetap. Server juga yang menetapkan jenjang (tanpa jenjang
    // -> Staf; memimpin divisi -> Manager), jadi tidak ditebak di sini.
    tambahKeDepartemen: (o, departemenId) => aksi.tempatkan(o, { departemen_id: departemenId }),
    tempatkan: async (orang: TAnggotaHierarki, tujuan) => {
      try {
        await hierarkiService.setel({ member_id: orang.id, ...tujuan });
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
    setelEkstra: async (orangId: string, departemenIds: string[]) => {
      try {
        await hierarkiService.setel({ member_id: orangId, departemen_ids: departemenIds });
        await Promise.all([mutate(), mutateHierarki()]);
        setToast({ type: TOAST_TYPE.SUCCESS, title: s.org.department_saved });
      } catch (err) {
        setToast({ type: TOAST_TYPE.ERROR, title: s.org.failed, message: pesanGagal(err, s.org.save_failed_message) });
      }
    },
    setelDivisi: async (orangId: string, divisiIds: string[]) => {
      try {
        await hierarkiService.setel({ member_id: orangId, divisi_ids: divisiIds });
        await Promise.all([mutate(), mutateHierarki()]);
        setToast({ type: TOAST_TYPE.SUCCESS, title: s.org.department_saved });
      } catch (err) {
        setToast({ type: TOAST_TYPE.ERROR, title: s.org.failed, message: pesanGagal(err, s.org.save_failed_message) });
      }
    },
  };

  const header = {
    title: s.members.title,
    description: s.org.description,
    actions: (
      <Button variant="primary" size="lg" prependIcon={<Plus />} onClick={() => setPerintah({ jenis: "buat-divisi" })}>
        {s.org.new_division}
      </Button>
    ),
  };

  if (isLoading || !data) {
    return (
      <PageWrapper header={header}>
        <MembersTabs />
        <Loader className="grid gap-6 lg:grid-cols-[300px_1fr]">
          <Loader.Item height="420px" />
          <Loader.Item height="420px" />
        </Loader>
      </PageWrapper>
    );
  }

  const q = cari.trim().toLowerCase();
  const semuaProject = [
    ...data.divisi.flatMap((v) => v.departemen.flatMap((d) => d.projects)),
    ...data.tanpa_departemen,
  ];
  const namaDivisi = Object.fromEntries(data.divisi.map((v) => [v.id, v.nama]));
  const namaDepartemen = Object.fromEntries(data.divisi.flatMap((v) => v.departemen.map((d) => [d.id, d.nama])));
  const semuaDivisi = data.divisi.map((v) => ({ id: v.id, nama: v.nama, kode: v.kode }));
  const orang = (hierarki?.anggota ?? []).filter((o) => o.is_active);

  const direktur = orang.filter((o) => o.tingkat !== null && o.tingkat >= TINGKAT_DIREKTUR);
  const manager = orang.filter(
    (o) => o.tingkat !== null && o.tingkat >= TINGKAT_MANAGER && o.tingkat < TINGKAT_DIREKTUR
  );
  const supervisor = orang.filter(
    (o) => o.tingkat !== null && o.tingkat >= TINGKAT_SUPERVISOR && o.tingkat < TINGKAT_MANAGER
  );
  const staf = orang.filter((o) => o.tingkat === null || o.tingkat < TINGKAT_SUPERVISOR);
  const belum = orang.filter(
    (o) => (o.tingkat === null || o.tingkat < TINGKAT_DIREKTUR) && !o.departemen_id && !o.divisi_id
  );
  const totalDepartemen = data.divisi.reduce((n, v) => n + v.departemen.length, 0);

  // Node terpilih bisa hilang (dihapus, atau dipindah divisi): jatuh ke ringkasan.
  const divisiTerpilih = pilihan.jenis === "divisi" ? data.divisi.find((v) => v.id === pilihan.id) : undefined;
  const depTerpilih =
    pilihan.jenis === "departemen"
      ? data.divisi.flatMap((v) => v.departemen.map((d) => ({ d, v }))).find((x) => x.d.id === pilihan.id)
      : undefined;
  const bersama = { aksi, orang, namaDepartemen, namaDivisi, onPilih: setPilihan, onKelola: setPerintah, q };

  const isiKanan = (() => {
    if (divisiTerpilih) return <DetailDivisi key={divisiTerpilih.id} divisi={divisiTerpilih} {...bersama} />;
    if (depTerpilih)
      return (
        <DetailDepartemen
          // Kunci ikut daftar project, supaya pilihan lokal di-reset sesudah disimpan.
          key={`${depTerpilih.d.id}-${depTerpilih.d.projects.map((p) => p.id).join(",")}`}
          dep={depTerpilih.d}
          divisi={depTerpilih.v}
          semuaDivisi={semuaDivisi}
          semuaProject={semuaProject}
          {...bersama}
        />
      );
    if (pilihan.jenis === "belum") return <DetailBelumDitempatkan belum={belum} pohon={data} aksi={aksi} q={q} />;
    if (pilihan.jenis === "lama" && data.tanpa_departemen.length > 0)
      return (
        <div className="space-y-5">
          <div className="space-y-1">
            <h2 className="text-18 font-semibold text-primary">
              {fill(s.org.legacy_title, { n: data.tanpa_departemen.length })}
            </h2>
            <p className="text-12 text-tertiary">
              {s.org.legacy_description}
              {semuaDivisi.length === 0 && s.org.legacy_create_first}
            </p>
          </div>
          {
            <Panel flush title={s.org.legacy_node}>
              <ul className="divide-y divide-subtle">
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
              </ul>
            </Panel>
          }
        </div>
      );
    return (
      <div className="space-y-3">
        <p className="text-12 text-tertiary">{s.org.overview_hint}</p>
        {data.divisi.length === 0 ? (
          <StateBox>{s.org.no_division}</StateBox>
        ) : (
          <KanvasBagan judul={s.org.overview}>
            <BaganOrganisasi pohon={data} anggota={orang} onPilih={setPilihan} onKelola={setPerintah} />
          </KanvasBagan>
        )}
      </div>
    );
  })();

  return (
    <PageWrapper header={header}>
      <MembersTabs />
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
          <StatCard label={s.org.stat_division} value={data.divisi.length} />
          <StatCard label={s.org.stat_department} value={totalDepartemen} />
          <StatCard label={s.org.stat_project} value={semuaProject.length} />
          <StatCard label={s.org.stat_director} value={direktur.length} />
          <StatCard label={s.org.stat_manager} value={manager.length} />
          <StatCard label={s.org.stat_supervisor} value={supervisor.length} />
          <StatCard
            label={s.org.stat_staff}
            value={staf.length}
            hint={belum.length ? fill(s.org.unplaced_title, { n: belum.length }) : undefined}
          />
        </div>

        <div
          className={cn(
            "grid items-start gap-6",
            terlipat ? "lg:grid-cols-[44px_minmax(0,1fr)]" : "lg:grid-cols-[300px_minmax(0,1fr)]"
          )}
        >
          {terlipat ? (
            <RelPohon
              pilihan={pilihan}
              onPilih={setPilihan}
              onBuka={() => ubahTerlipat(false)}
              jumlahBelum={belum.length}
              adaLama={data.tanpa_departemen.length > 0}
            />
          ) : (
            <aside className="space-y-3 rounded-card border border-subtle bg-layer-1 p-3 lg:sticky lg:top-4">
              <div className="flex items-center gap-1.5">
                <div className="flex h-8 min-w-0 flex-1 items-center gap-1.5 search-field border border-subtle bg-layer-2 px-2.5 focus-within:border-accent-strong">
                  <Search className="size-3.5 shrink-0 text-placeholder" aria-hidden />
                  <Input
                    type="text"
                    mode="true-transparent"
                    className="w-full min-w-0 p-0 text-primary placeholder:text-placeholder"
                    placeholder={s.org.search_tree}
                    aria-label={s.org.search_tree}
                    value={cari}
                    onChange={(e) => setCari(e.target.value)}
                  />
                </div>
                <Tooltip tooltipContent={s.org.collapse_tree}>
                  <IconButton
                    variant="ghost"
                    size="lg"
                    icon={PanelLeftClose}
                    aria-label={s.org.collapse_tree}
                    onClick={() => ubahTerlipat(true)}
                  />
                </Tooltip>
              </div>
              <PohonNavigasi
                pohon={data}
                pilihan={pilihan}
                onPilih={setPilihan}
                q={q}
                jumlahBelum={belum.length}
                jumlahDirektur={direktur.length}
                onKelola={setPerintah}
              />
            </aside>
          )}
          <div className="min-w-0">{isiKanan}</div>
        </div>
      </div>

      <KelolaOrganisasi perintah={perintah} onTutup={() => setPerintah(null)} pohon={data} orang={orang} aksi={aksi} />
    </PageWrapper>
  );
}

/** Tombol ikon di rel pohon yang dilipat. */
function TombolRel({
  label,
  icon: Ikon,
  aktif = false,
  titik = false,
  onClick,
}: {
  label: string;
  icon: React.FC<{ className?: string }>;
  aktif?: boolean;
  /** Titik peringatan (mis. masih ada yang belum ditempatkan). */
  titik?: boolean;
  onClick: () => void;
}) {
  return (
    <Tooltip tooltipContent={label} position="right">
      <button
        type="button"
        aria-label={label}
        aria-current={aktif ? "true" : undefined}
        onClick={onClick}
        className={cn(
          "relative grid size-8 place-items-center rounded-item transition-colors",
          aktif
            ? "bg-layer-transparent-active text-primary"
            : "text-tertiary hover:bg-layer-transparent-hover hover:text-primary"
        )}
      >
        <Ikon className="size-4" />
        {titik && <span className="absolute top-1 right-1 size-1.5 rounded-full bg-warning-primary" aria-hidden />}
      </button>
    </Tooltip>
  );
}

/** Panel pohon yang dilipat: rel ikon sempit, tetap bisa melompat ke ringkasan & antrean. */
function RelPohon({
  pilihan,
  onPilih,
  onBuka,
  jumlahBelum,
  adaLama,
}: {
  pilihan: TPilihan;
  onPilih: (p: TPilihan) => void;
  onBuka: () => void;
  jumlahBelum: number;
  adaLama: boolean;
}) {
  const { s } = useGodmodeStrings();
  return (
    <aside className="flex flex-row items-center gap-1 rounded-card border border-subtle bg-layer-1 p-1.5 lg:sticky lg:top-4 lg:flex-col">
      <TombolRel label={s.org.expand_tree} icon={PanelLeftOpen} onClick={onBuka} />
      <div className="mx-1 h-5 w-px bg-layer-3 lg:mx-0 lg:my-1 lg:h-px lg:w-5" aria-hidden />
      <TombolRel
        label={s.org.overview}
        icon={Network}
        aktif={pilihan.jenis === "ringkasan"}
        onClick={() => onPilih({ jenis: "ringkasan" })}
      />
      {jumlahBelum > 0 && (
        <TombolRel
          label={s.org.unplaced_node}
          icon={UserX}
          aktif={pilihan.jenis === "belum"}
          titik
          onClick={() => onPilih({ jenis: "belum" })}
        />
      )}
      {adaLama && (
        <TombolRel
          label={s.org.legacy_node}
          icon={FolderInput}
          aktif={pilihan.jenis === "lama"}
          onClick={() => onPilih({ jenis: "lama" })}
        />
      )}
    </aside>
  );
}
