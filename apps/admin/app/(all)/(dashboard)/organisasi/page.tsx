/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: struktur divisi -> departemen -> project (KEP-29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Bagan struktur di atas (bisa disembunyikan, diingat per peramban), papan
 * seret-lepas di bawahnya (papan.tsx): panel People di kiri, lajur jenjang +
 * divisi yang bisa dibuka di kanan. Klik kotak bagan = buka divisinya di papan
 * dan gulir ke sana. Buat/ubah/hapus divisi & departemen, pindah departemen,
 * ganti project, dan tempatkan orang lewat papan atau menu "..." (bagan dan papan
 * memakai modal yang sama di kelola.tsx).
 *
 * Sampai 4 Nov 2026 ada dua tab, Board dan "Chart & details" (pohon kiri, bagan,
 * panel detail). Digabung atas permintaan user (KEP-86). Panel project lama
 * tanpa departemen ikut dibuang: project bisa diubah/dihapus langsung, dan
 * menghapus departemen sudah mengarsipkan project-nya.
 */

import { useState } from "react";
import { ChevronDown, Plus } from "lucide-react";
import useSWR, { useSWRConfig } from "swr";
// plane imports
import { Button } from "@plane/propel/button";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import {
  InstanceHierarkiService,
  InstanceOrganisasiService,
  TINGKAT_DIREKTUR,
  TINGKAT_MANAGER,
  TINGKAT_SEKRETARIS,
  TINGKAT_SUPERVISOR,
  menjangkauSeluruhOrganisasi,
  type TAnggotaHierarki,
  type TPohonOrganisasi,
} from "@plane/services";
import { Loader } from "@plane/ui";
import { cn } from "@plane/utils";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
import { StatCard } from "@/components/common/paradise";
// local
import { godmodeStrings, useGodmodeStrings } from "@/app/i18n/godmode";
import { MenuTabs } from "@/components/common/section-tabs";
import { BaganOrganisasi, type TBukaDiPapan } from "./bagan";
import { KanvasBagan } from "./kanvas-bagan";
import { KelolaOrganisasi } from "./kelola";
import { idDepartemen, idDivisi, PapanOrganisasi } from "./papan";
import { akunTerhapus } from "./papan-logika";
import { usePenempatanOptimis } from "./use-penempatan";
import { pesanGagalSimpan, type TAksiOrganisasi, type TPerintahKelola } from "./util";

const layanan = new InstanceOrganisasiService();
const hierarkiService = new InstanceHierarkiService();

/**
 * Semua kunci SWR God Mode yang membawa penempatan atau jenjang (Jebakan L4):
 * pohon, hierarki (juga dipakai halaman Accounts), daftar member, kartu profil.
 */
const kunciTerkait = (key: unknown): boolean => {
  const k: unknown = Array.isArray(key) ? key[0] : key;
  return (
    typeof k === "string" &&
    (k === "INSTANCE_ORGANISASI" ||
      k.includes("INSTANCE_HIERARKI") ||
      k === "INSTANCE_MEMBERS_ALL" ||
      k.startsWith("GODMODE_MEMBER_PROFILE_"))
  );
};

/** Bagan struktur tampil atau disembunyikan, per peramban. Bawaan: tampil. */
const KUNCI_BAGAN_TERSEMBUNYI = "paradise_org_chart_hidden";
const bacaBaganTersembunyi = (): boolean => {
  try {
    return typeof window !== "undefined" && window.localStorage.getItem(KUNCI_BAGAN_TERSEMBUNYI) === "1";
  } catch {
    return false;
  }
};

const pesanGagal = (err: unknown, fallback: string): string =>
  pesanGagalSimpan(err, fallback, godmodeStrings.org.session_expired);

export default function OrganisasiPage() {
  const { s, fill } = useGodmodeStrings();
  const { data, mutate, isLoading } = useSWR("INSTANCE_ORGANISASI", () => layanan.pohon());
  // Sumber calon penempatan + kunci yang sama dengan halaman Member, supaya
  // perubahan di sini langsung terlihat di sana.
  const { data: hierarki, mutate: mutateHierarki } = useSWR(["INSTANCE_HIERARKI"], () => hierarkiService.ringkasan());
  const [perintah, setPerintah] = useState<TPerintahKelola | null>(null);
  // Divisi yang terbuka di papan. Klik divisi membukanya di tempat.
  const [dibuka, setDibuka] = useState<Set<string>>(() => new Set());
  const [baganTersembunyi, setBaganTersembunyi] = useState(bacaBaganTersembunyi);
  const ubahBagan = (sembunyi: boolean) => {
    setBaganTersembunyi(sembunyi);
    try {
      window.localStorage.setItem(KUNCI_BAGAN_TERSEMBUNYI, sembunyi ? "1" : "0");
    } catch {
      // Mode privat: pilihan berlaku di sesi ini saja.
    }
  };
  /** Klik kotak bagan: buka divisinya di papan, lalu gulir ke divisi/departemen itu. */
  const bukaDiPapan: TBukaDiPapan = (divisiId, departemenId) => {
    setDibuka((lama) => (lama.has(divisiId) ? lama : new Set(lama).add(divisiId)));
    // Tunggu papan merender departemen yang baru dibuka sebelum menggulir.
    requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        const el = document.getElementById(departemenId ? idDepartemen(departemenId) : idDivisi(divisiId));
        const halus = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        el?.scrollIntoView({ behavior: halus ? "smooth" : "auto", block: "start" });
      })
    );
  };
  const { mutate: mutateGlobal } = useSWRConfig();
  const muatUlangSemua = () => mutateGlobal(kunciTerkait);
  const jalankanPapan = usePenempatanOptimis({ mutatePohon: mutate, mutateHierarki, muatUlangSemua });
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
    hapusDivisi: (id) => jalankan(() => layanan.hapusDivisi(id), s.org.division_deleted),
    buatDepartemen: (divisiId, kode, nama) =>
      jalankan(
        () => layanan.buatDepartemen({ divisi_id: divisiId, kode, nama }),
        fill(s.org.department_created, { kode })
      ),
    ubahDepartemen: (id, isi) => jalankan(() => layanan.ubahDepartemen(id, isi), s.org.department_saved),
    simpanProject: (id, projectIds) =>
      jalankan(() => layanan.ubahDepartemen(id, { project_ids: projectIds }), s.org.department_saved),
    hapusDepartemen: (id) => jalankan(() => layanan.hapusDepartemen(id), s.org.department_deleted),
    // KEP-76: `departemen_id` / `divisi_id` di server = TAMBAH satu tempat,
    // penempatan lama tetap. Server juga yang menetapkan jenjang (tanpa jenjang
    // -> Staf; memimpin divisi -> Manager), jadi tidak ditebak di sini.
    tambahKeDepartemen: (o, departemenId) => aksi.tempatkan(o, { departemen_id: departemenId }),
    tempatkan: async (orang: TAnggotaHierarki, tujuan) => {
      try {
        await hierarkiService.setel({ member_id: orang.id, ...tujuan });
        await muatUlangSemua();
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
        const hasil = await hierarkiService.setel({ member_id: orang.id, tingkat });
        await muatUlangSemua();
        const akhir = hasil.member.tingkat ?? tingkat;
        const namaJenjang =
          akhir >= TINGKAT_DIREKTUR
            ? s.members.level_director
            : akhir >= TINGKAT_SEKRETARIS
              ? s.members.level_secretary
              : akhir >= TINGKAT_MANAGER
                ? s.members.level_manager
                : akhir >= TINGKAT_SUPERVISOR
                  ? s.members.level_supervisor
                  : s.members.level_staff;
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: fill(s.org.level_saved, { name: orang.display_name, level: namaJenjang }),
          message: hasil.member.divisi_dilepas.length > 0 ? s.org.level_saved_divisions_released : undefined,
        });
      } catch (err) {
        setToast({ type: TOAST_TYPE.ERROR, title: s.org.failed, message: pesanGagal(err, s.org.save_failed_message) });
      }
    },
    setelEkstra: async (orangId: string, departemenIds: string[]) => {
      try {
        await hierarkiService.setel({ member_id: orangId, departemen_ids: departemenIds });
        await muatUlangSemua();
        setToast({ type: TOAST_TYPE.SUCCESS, title: s.org.department_saved });
      } catch (err) {
        setToast({ type: TOAST_TYPE.ERROR, title: s.org.failed, message: pesanGagal(err, s.org.save_failed_message) });
      }
    },
    setelDivisi: async (orangId: string, divisiIds: string[]) => {
      try {
        await hierarkiService.setel({ member_id: orangId, divisi_ids: divisiIds });
        await muatUlangSemua();
        setToast({ type: TOAST_TYPE.SUCCESS, title: s.org.department_saved });
      } catch (err) {
        setToast({ type: TOAST_TYPE.ERROR, title: s.org.failed, message: pesanGagal(err, s.org.save_failed_message) });
      }
    },
  };

  const header = {
    title: s.settings.tabs.people_organization.title,
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
        <MenuTabs menu="people" />
        <Loader className="grid gap-6 lg:grid-cols-[280px_1fr]">
          <Loader.Item height="420px" />
          <Loader.Item height="420px" />
        </Loader>
      </PageWrapper>
    );
  }

  const semuaProject = [
    ...data.divisi.flatMap((v) => v.departemen.flatMap((d) => d.projects)),
    ...data.tanpa_departemen,
  ];
  const namaDivisi = Object.fromEntries(data.divisi.map((v) => [v.id, v.nama]));
  const namaDepartemen = Object.fromEntries(data.divisi.flatMap((v) => v.departemen.map((d) => [d.id, d.nama])));
  const orang = (hierarki?.anggota ?? []).filter((o) => o.is_active && !akunTerhapus(o.email));

  const direktur = orang.filter((o) => o.tingkat !== null && o.tingkat >= TINGKAT_DIREKTUR);
  const sekretaris = orang.filter(
    (o) => o.tingkat !== null && o.tingkat >= TINGKAT_SEKRETARIS && o.tingkat < TINGKAT_DIREKTUR
  );
  const manager = orang.filter(
    (o) => o.tingkat !== null && o.tingkat >= TINGKAT_MANAGER && o.tingkat < TINGKAT_SEKRETARIS
  );
  const supervisor = orang.filter(
    (o) => o.tingkat !== null && o.tingkat >= TINGKAT_SUPERVISOR && o.tingkat < TINGKAT_MANAGER
  );
  const staf = orang.filter((o) => o.tingkat === null || o.tingkat < TINGKAT_SUPERVISOR);
  const belum = orang.filter((o) => !menjangkauSeluruhOrganisasi(o.tingkat) && !o.departemen_id && !o.divisi_id);
  const totalDepartemen = data.divisi.reduce((n, v) => n + v.departemen.length, 0);

  return (
    <PageWrapper header={header}>
      <MenuTabs menu="people" />
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
          <StatCard label={s.org.stat_division} value={data.divisi.length} />
          <StatCard label={s.org.stat_department} value={totalDepartemen} />
          <StatCard label={s.org.stat_project} value={semuaProject.length} />
          <StatCard label={s.org.stat_director} value={direktur.length} />
          <StatCard label={s.org.stat_secretary} value={sekretaris.length} />
          <StatCard label={s.org.stat_manager} value={manager.length} />
          <StatCard label={s.org.stat_supervisor} value={supervisor.length} />
          <StatCard
            label={s.org.stat_staff}
            value={staf.length}
            hint={belum.length ? fill(s.org.unplaced_title, { n: belum.length }) : undefined}
          />
        </div>

        <section className="space-y-2" aria-label={s.org.chart}>
          <div className="flex items-center justify-between gap-3">
            <span className="text-11 font-semibold text-tertiary">{s.org.chart}</span>
            <Button
              variant="ghost"
              size="base"
              aria-expanded={!baganTersembunyi}
              appendIcon={<ChevronDown className={cn("transition-transform", !baganTersembunyi && "rotate-180")} />}
              onClick={() => ubahBagan(!baganTersembunyi)}
            >
              {baganTersembunyi ? s.org.chart_show : s.org.chart_hide}
            </Button>
          </div>
          {!baganTersembunyi && (
            <KanvasBagan judul={s.org.chart_hint} kelasTinggi="h-[min(60vh,560px)] min-h-[360px]">
              <BaganOrganisasi pohon={data} anggota={orang} onBuka={bukaDiPapan} onKelola={setPerintah} />
            </KanvasBagan>
          )}
        </section>

        <PapanOrganisasi
          pohon={data}
          anggota={orang}
          aksi={aksi}
          jalankan={jalankanPapan}
          namaDepartemen={namaDepartemen}
          namaDivisi={namaDivisi}
          onKelola={setPerintah}
          dibuka={dibuka}
          onDibuka={setDibuka}
        />
      </div>

      <KelolaOrganisasi perintah={perintah} onTutup={() => setPerintah(null)} pohon={data} orang={orang} aksi={aksi} />
    </PageWrapper>
  );
}

export const meta = () => [{ title: `${godmodeStrings.settings.tabs.people_organization.title} - God Mode` }];
