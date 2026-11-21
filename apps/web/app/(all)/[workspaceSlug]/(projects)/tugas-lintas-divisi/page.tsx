/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: halaman pengirim permintaan lintas divisi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import { useParams } from "react-router";
import { AlertTriangle, ArrowLeftRight, Clock, Inbox, ListTodo, Send } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Badge } from "@plane/propel/badge";
import type { TBadgeVariant } from "@plane/propel/badge";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { CustomSearchSelect, CustomSelect, Input, Loader, TextArea } from "@plane/ui";
// components
import { PageShell } from "@/components/common/page-shell";
import { PageHead } from "@/components/core/page-title";
// hooks
import { useProject } from "@/hooks/store/use-project";
// services
import {
  CrossDivisionService,
  type TDivisiLintasDivisi,
  type TPermintaanLintasDivisi,
  type TRingkasanLintasDivisi,
  type TStatusPermintaan,
  type TStatusTugas,
} from "@/services/cross_division.service";

const crossDivisionService = new CrossDivisionService();

const inputClass =
  "rounded-field border border-subtle bg-layer-1 px-2 py-1 text-12 outline-none focus:border-accent-strong";
// TextArea menumbuhkan tingginya sendiri dan mengabaikan `rows`, jadi tinggi
// awal tiga baris dipatok lewat min-height (3 baris + py-1 + border 1px).
const TINGGI_TIGA_BARIS = "min-h-[calc(3lh+0.5rem+2px)]";

/** "Nama (KODE)", atau strip kalau divisinya belum ada. */
const labelDivisi = (divisi: Pick<TDivisiLintasDivisi, "name" | "identifier"> | undefined) =>
  divisi ? `${divisi.name} (${divisi.identifier})` : "-";

// `label` di semua peta ini adalah KUNCI i18n, diterjemahkan saat dirender.
const PRIORITAS: { value: string; label: string }[] = [
  { value: "none", label: "cross_division_ui.priority.none" },
  { value: "low", label: "cross_division_ui.priority.low" },
  { value: "medium", label: "cross_division_ui.priority.medium" },
  { value: "high", label: "cross_division_ui.priority.high" },
  { value: "urgent", label: "cross_division_ui.priority.urgent" },
];

// Kosakata status dipakai APA ADANYA dari API (jangan diterjemahkan jadi teks
// lain); yang ada di sini hanya label tampilan. `Record<string, string>` supaya
// status yang belum dikenal tetap ditampilkan mentah, bukan hilang.
const LABEL_STATUS_PERMINTAAN: Record<string, string> = {
  menunggu: "cross_division_ui.request_status.pending",
  ditunda: "cross_division_ui.request_status.snoozed",
  ditolak: "cross_division_ui.request_status.declined",
  duplikat: "cross_division_ui.request_status.duplicate",
  diterima: "cross_division_ui.request_status.accepted",
  dibatalkan: "cross_division_ui.request_status.cancelled",
};

const VARIAN_STATUS_PERMINTAAN: Record<string, TBadgeVariant> = {
  menunggu: "warning",
  ditunda: "neutral",
  ditolak: "danger",
  duplikat: "neutral",
  diterima: "success",
  dibatalkan: "neutral",
};

const LABEL_STATUS_TUGAS: Record<string, string> = {
  belum_diterima: "cross_division_ui.task_status.not_accepted",
  terbuka: "cross_division_ui.task_status.open",
  selesai: "cross_division_ui.task_status.done",
  dibatalkan: "cross_division_ui.task_status.cancelled",
  tidak_dikerjakan: "cross_division_ui.task_status.wont_do",
};

const VARIAN_STATUS_TUGAS: Record<string, TBadgeVariant> = {
  belum_diterima: "neutral",
  terbuka: "brand",
  selesai: "success",
  dibatalkan: "danger",
  tidak_dikerjakan: "neutral",
};

type TTerjemah = (key: string, params?: Record<string, unknown>) => string;

// `error_code` dari API (`_galat` di views/issue/cross_division.py) yang punya
// terjemahan di `cross_division_ui.errors`. Kode lain jatuh ke teks API atau fallback.
const KODE_GALAT = new Set([
  "title_required",
  "title_too_long",
  "unknown_priority",
  "note_too_long",
  "route_required",
  "origin_not_found",
  "not_origin_member",
  "target_not_found",
  "same_department",
  "member_of_target",
  "intake_off",
  "target_not_allowed",
  "invalid_description",
]);

type TGalatApi = { error?: unknown; error_code?: unknown; params?: Record<string, unknown>; detail?: unknown };

const pesanGagal = (err: unknown, fallback: string, t: TTerjemah): string => {
  const galat = (err ?? {}) as TGalatApi;
  if (typeof galat.error_code === "string" && KODE_GALAT.has(galat.error_code))
    return t(`cross_division_ui.errors.${galat.error_code}`, galat.params ?? {});
  // Izin kelas DRF menjawab `detail`, bukan `error`: pemanggil tamu workspace.
  if (typeof galat.detail === "string") return t("cross_division_ui.errors.forbidden");
  return typeof galat.error === "string" && galat.error.length > 0 ? galat.error : fallback;
};

/**
 * Escape HTML sebelum teks textarea dibungkus jadi `<p>`.
 *
 * Pemakai mengetik teks biasa, dan backend menyimpannya sebagai
 * `description_html`. Menyisipkan masukan mentah ke HTML = XSS di origin
 * aplikasi, jadi seluruh isi di-escape lebih dulu dan hanya `<p>`/`<br>` kita
 * sendiri yang lolos.
 */
const escapeHtml = (teks: string): string =>
  teks
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

/** Paragraf kosong dikirim sebagai `<p></p>` (bukan string kosong). */
const keHtmlParagraf = (teks: string): string => {
  const bersih = teks.trim();
  if (!bersih) return "<p></p>";
  return bersih
    .split(/\n{2,}/)
    .map((blok) => `<p>${escapeHtml(blok).replace(/\n/g, "<br>")}</p>`)
    .join("");
};

const formatTanggal = (nilai: string, lokal: string): string => {
  const tanggal = new Date(nilai);
  if (Number.isNaN(tanggal.getTime())) return "—";
  return tanggal.toLocaleDateString(lokal, { day: "2-digit", month: "short", year: "numeric" });
};

const labelStatusPermintaan = (nilai: TStatusPermintaan, t: TTerjemah): string =>
  LABEL_STATUS_PERMINTAAN[nilai] ? t(LABEL_STATUS_PERMINTAAN[nilai]) : nilai;

const labelStatusTugas = (nilai: TStatusTugas, t: TTerjemah): string =>
  LABEL_STATUS_TUGAS[nilai] ? t(LABEL_STATUS_TUGAS[nilai]) : nilai;

type TStatCard = { label: string; value: string; keterangan: string; icon: React.ReactNode };

function StatCard({ label, value, keterangan, icon }: TStatCard) {
  return (
    <div className="flex items-center gap-3 rounded-card border border-subtle bg-layer-1 px-4 py-3">
      <div className="shrink-0 text-secondary">{icon}</div>
      <div className="min-w-0">
        <p className="text-16 font-semibold text-primary">{value}</p>
        <p className="truncate text-12 text-tertiary">{label}</p>
        <p className="truncate text-11 text-tertiary">{keterangan}</p>
      </div>
    </div>
  );
}

type TTabelPermintaan = {
  baris: TPermintaanLintasDivisi[];
  workspaceSlug: string;
  tampilkanPeminta?: boolean;
};

function TabelPermintaan({ baris: daftar, workspaceSlug, tampilkanPeminta = false }: TTabelPermintaan) {
  const { t, currentLocale } = useTranslation();
  return (
    <div className="overflow-x-auto rounded-card border border-subtle gulir-berpenanda">
      <table className="w-full min-w-[720px] text-left text-13">
        <thead>
          <tr className="border-b border-subtle bg-layer-2 text-12 text-tertiary">
            <th className="px-3 py-2 font-medium">{t("cross_division_ui.col_title")}</th>
            {tampilkanPeminta && <th className="px-3 py-2 font-medium">{t("cross_division_ui.col_requester")}</th>}
            <th className="px-3 py-2 font-medium">{t("cross_division_ui.col_route")}</th>
            <th className="px-3 py-2 font-medium">{t("cross_division_ui.col_request_status")}</th>
            <th className="px-3 py-2 font-medium">{t("cross_division_ui.col_task_status")}</th>
            <th className="px-3 py-2 font-medium">{t("cross_division_ui.col_task_no")}</th>
            <th className="px-3 py-2 font-medium">{t("cross_division_ui.col_date")}</th>
          </tr>
        </thead>
        <tbody>
          {daftar.map((baris) => (
            <tr key={baris.id} className="border-b border-subtle last:border-0 hover:bg-layer-2">
              <td className="px-3 py-2">
                <span className="font-medium text-primary">{baris.judul ?? "—"}</span>
                {baris.arah === "keluar" && baris.catatan && <p className="text-11 text-tertiary">{baris.catatan}</p>}
              </td>
              {tampilkanPeminta && <td className="px-3 py-2 text-secondary">{baris.peminta ?? "—"}</td>}
              <td className="px-3 py-2 text-secondary">
                {baris.asal.identifier} → {baris.tujuan.identifier}
              </td>
              <td className="px-3 py-2">
                <Badge variant={VARIAN_STATUS_PERMINTAAN[baris.status_permintaan] ?? "neutral"}>
                  {labelStatusPermintaan(baris.status_permintaan, t)}
                </Badge>
                {baris.alasan_tolak && (
                  <p className="mt-1 text-11 text-tertiary">
                    {t("persetujuan_p29.decline_reason", { reason: baris.alasan_tolak })}
                  </p>
                )}
              </td>
              <td className="px-3 py-2">
                <Badge variant={VARIAN_STATUS_TUGAS[baris.status_tugas] ?? "neutral"}>
                  {labelStatusTugas(baris.status_tugas, t)}
                </Badge>
              </td>
              <td className="px-3 py-2 text-secondary">
                {baris.boleh_dibuka && baris.nomor_tugas_tujuan ? (
                  <Link
                    href={`/${workspaceSlug}/browse/${baris.nomor_tugas_tujuan}/`}
                    className="text-accent-primary hover:underline"
                  >
                    {baris.nomor_tugas_tujuan}
                  </Link>
                ) : (
                  (baris.nomor_tugas_tujuan ?? "—")
                )}
              </td>
              <td className="px-3 py-2 text-secondary">{formatTanggal(baris.dibuat_pada, currentLocale)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TugasLintasDivisiPage() {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  // store: divisi asal = divisi tempat SAYA anggota. `joinedProjectIds`
  // menyaring `member_role` dari project store, jadi tidak perlu endpoint baru;
  // project store sudah memuat seluruh divisi workspace beserta peran saya.
  const { joinedProjectIds, getProjectById } = useProject();
  // data
  const [daftarTujuan, setDaftarTujuan] = useState<TDivisiLintasDivisi[]>([]);
  const [permintaan, setPermintaan] = useState<TPermintaanLintasDivisi[]>([]);
  const [ringkasan, setRingkasan] = useState<TRingkasanLintasDivisi>({});
  const [isLoading, setIsLoading] = useState(true);
  const [gagalMuat, setGagalMuat] = useState<string | null>(null);
  // form
  const [asalDipilih, setAsalDipilih] = useState("");
  const [tujuanDipilih, setTujuanDipilih] = useState("");
  const [judul, setJudul] = useState("");
  const [prioritas, setPrioritas] = useState("none");
  const [catatan, setCatatan] = useState("");
  const [keterangan, setKeterangan] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [gagalKirim, setGagalKirim] = useState<string | null>(null);

  // Divisi asal diturunkan dari store, bukan disalin ke state: kalau
  // keanggotaan berubah, pilihannya ikut berubah tanpa state basi.
  const divisiSaya: TDivisiLintasDivisi[] = [];
  for (const projectId of joinedProjectIds ?? []) {
    const proyek = getProjectById(projectId);
    if (proyek) divisiSaya.push({ id: proyek.id, identifier: proyek.identifier, name: proyek.name });
  }
  const asalId = asalDipilih || (divisiSaya.length > 0 ? divisiSaya[0].id : "");

  const muatSemua = useCallback(async () => {
    if (!workspaceSlug) return;
    setIsLoading(true);
    setGagalMuat(null);
    try {
      const [tujuanRes, permintaanRes, ringkasanRes] = await Promise.all([
        crossDivisionService.listTujuan(workspaceSlug),
        crossDivisionService.listPermintaan(workspaceSlug),
        crossDivisionService.listRingkasan(workspaceSlug),
      ]);
      setDaftarTujuan(tujuanRes ?? []);
      setPermintaan(permintaanRes ?? []);
      setRingkasan(ringkasanRes ?? {});
    } catch (err) {
      // Pesan dari API ditampilkan apa adanya; kegagalan senyap adalah kelas bug
      // termahal di proyek ini.
      setGagalMuat(pesanGagal(err, t("cross_division_ui.load_failed"), t));
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug, t]);

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- initial data load triggers state updates by design
    void muatSemua();
  }, [muatSemua]);

  const tujuanTersedia = daftarTujuan.filter((divisi) => divisi.id !== asalId);
  // Server lama belum mengirim `arah`: semua barisnya milik pemanggil.
  const permintaanKeluar = permintaan.filter((baris) => (baris.arah ?? "keluar") === "keluar");
  const permintaanMasuk = permintaan.filter((baris) => baris.arah === "masuk");

  const keluarMenunggu = Object.values(ringkasan).reduce((total, baris) => total + baris.keluar_menunggu, 0);
  const keluarTerbuka = Object.values(ringkasan).reduce((total, baris) => total + baris.keluar_terbuka, 0);
  const rincianKeluar = Object.entries(ringkasan)
    .map(([projectId, baris]) => ({ projectId, baris, nama: getProjectById(projectId)?.name ?? null }))
    .filter((item) => item.baris.keluar_menunggu + item.baris.keluar_terbuka > 0);

  const handleKirim = async () => {
    if (!workspaceSlug) return;
    setGagalKirim(null);
    if (!asalId) {
      setGagalKirim(t("cross_division_ui.error_pick_origin"));
      return;
    }
    if (!tujuanDipilih) {
      setGagalKirim(t("cross_division_ui.error_pick_target"));
      return;
    }
    if (!judul.trim()) {
      setGagalKirim(t("cross_division_ui.error_title_required"));
      return;
    }
    setIsSending(true);
    try {
      await crossDivisionService.buatPermintaan(workspaceSlug, {
        judul: judul.trim(),
        prioritas,
        catatan: catatan.trim(),
        deskripsi_html: keHtmlParagraf(keterangan),
        asal_project: asalId,
        tujuan_project: tujuanDipilih,
      });
      setJudul("");
      setCatatan("");
      setKeterangan("");
      // Muat ulang daftarnya supaya baris baru langsung terlihat, alih-alih
      // menebak bentuk balasan POST di state lokal.
      await muatSemua();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("cross_division_ui.sent_title"),
        message: t("cross_division_ui.sent_message"),
      });
    } catch (err) {
      const pesan = pesanGagal(err, t("cross_division_ui.send_failed_message"), t);
      setGagalKirim(pesan);
      setToast({ type: TOAST_TYPE.ERROR, title: t("cross_division_ui.send_failed_title"), message: pesan });
    } finally {
      setIsSending(false);
    }
  };

  if (!workspaceSlug) return <></>;

  return (
    <>
      <PageHead title={t("persetujuan_p29.nav_requests")} />

      <PageShell>
        <PageShell.Header title={t("persetujuan_p29.nav_requests")} description={t("persetujuan_p29.requests_intro")} />

        {gagalMuat ? (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-card border border-danger-subtle bg-danger-subtle px-3 py-2 text-12 text-danger-primary"
          >
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            <div className="flex flex-col gap-1">
              <span>{gagalMuat}</span>
              <Button variant="secondary" size="base" className="self-start" onClick={() => void muatSemua()}>
                {t("cross_division_ui.retry")}
              </Button>
            </div>
          </div>
        ) : isLoading ? (
          <Loader className="flex flex-col gap-6">
            <span className="sr-only">{t("common.loading")}</span>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Loader.Item height="76px" />
              <Loader.Item height="76px" />
              <Loader.Item height="76px" />
            </div>
            <Loader.Item height="320px" />
            <Loader.Item height="160px" />
          </Loader>
        ) : (
          <>
            {/* 1. Ringkasan saya */}
            <section className="flex flex-col gap-3">
              <h2 className="text-16 font-semibold text-primary">{t("cross_division_ui.summary")}</h2>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <StatCard
                  label={t("cross_division_ui.stat_waiting")}
                  value={String(keluarMenunggu)}
                  keterangan={t("cross_division_ui.stat_waiting_hint")}
                  icon={<Clock className="size-5" />}
                />
                <StatCard
                  label={t("cross_division_ui.stat_open")}
                  value={String(keluarTerbuka)}
                  keterangan={t("cross_division_ui.stat_open_hint")}
                  icon={<ListTodo className="size-5 text-warning-primary" />}
                />
                <StatCard
                  label={t("cross_division_ui.stat_mine")}
                  value={String(permintaanKeluar.length)}
                  keterangan={t("cross_division_ui.stat_mine_hint")}
                  icon={<ArrowLeftRight className="size-5" />}
                />
              </div>
              <p className="text-11 text-tertiary">{t("cross_division_ui.summary_note")}</p>
              {rincianKeluar.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {rincianKeluar.map((item) => (
                    <span
                      key={item.projectId}
                      className="rounded-control border border-subtle px-2 py-0.5 text-11 text-secondary"
                    >
                      {item.nama ?? item.projectId}:{" "}
                      {t("cross_division_ui.breakdown", {
                        pending: item.baris.keluar_menunggu,
                        open: item.baris.keluar_terbuka,
                      })}
                    </span>
                  ))}
                </div>
              )}
            </section>

            {/* 2. Form kirim permintaan */}
            <section className="flex flex-col gap-3">
              <h2 className="text-16 font-semibold text-primary">{t("cross_division_ui.request_help")}</h2>

              {divisiSaya.length === 0 ? (
                <p className="text-13 text-tertiary">{t("cross_division_ui.no_origin")}</p>
              ) : tujuanTersedia.length === 0 ? (
                <div className="flex items-start gap-2 rounded-card border border-subtle bg-layer-1 px-3 py-2 text-12 text-secondary">
                  <Inbox className="mt-0.5 size-4 shrink-0 text-tertiary" />
                  <span>{t("cross_division_ui.no_targets")}</span>
                </div>
              ) : (
                <div className="flex flex-col gap-3 rounded-card border border-subtle bg-layer-1 p-4">
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <fieldset
                      aria-labelledby="lintas-divisi-origin"
                      className="m-0 flex min-w-0 flex-col gap-1 border-0 p-0"
                    >
                      <span id="lintas-divisi-origin" className="text-12 font-medium text-secondary">
                        {t("cross_division_ui.origin")}
                      </span>
                      <CustomSelect
                        value={asalId}
                        onChange={(v: string) => setAsalDipilih(v)}
                        label={labelDivisi(divisiSaya.find((d) => d.id === asalId))}
                        buttonClassName="w-full"
                        className="w-full"
                        input
                      >
                        {divisiSaya.map((divisi) => (
                          <CustomSelect.Option key={divisi.id} value={divisi.id}>
                            {labelDivisi(divisi)}
                          </CustomSelect.Option>
                        ))}
                      </CustomSelect>
                      <span className="text-11 text-tertiary">{t("cross_division_ui.origin_hint")}</span>
                    </fieldset>

                    <fieldset
                      aria-labelledby="lintas-divisi-target"
                      className="m-0 flex min-w-0 flex-col gap-1 border-0 p-0"
                    >
                      <span id="lintas-divisi-target" className="text-12 font-medium text-secondary">
                        {t("cross_division_ui.target")}
                      </span>
                      <CustomSearchSelect
                        value={tujuanDipilih}
                        onChange={(v: string) => setTujuanDipilih(v)}
                        label={
                          tujuanDipilih
                            ? labelDivisi(tujuanTersedia.find((d) => d.id === tujuanDipilih))
                            : t("cross_division_ui.target_placeholder")
                        }
                        options={tujuanTersedia.map((divisi) => ({
                          value: divisi.id,
                          query: `${divisi.name} ${divisi.identifier}`,
                          content: labelDivisi(divisi),
                        }))}
                        buttonClassName="w-full"
                        className="w-full"
                        input
                      />
                      <span className="text-11 text-tertiary">{t("cross_division_ui.target_hint")}</span>
                    </fieldset>
                  </div>

                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-[2fr_1fr]">
                    <label className="flex flex-col gap-1">
                      <span className="text-12 font-medium text-secondary">{t("cross_division_ui.request_title")}</span>
                      <Input
                        type="text"
                        value={judul}
                        maxLength={255}
                        onChange={(e) => setJudul(e.target.value)}
                        placeholder={t("cross_division_ui.request_title_placeholder")}
                        className={inputClass}
                      />
                    </label>

                    <fieldset
                      aria-labelledby="lintas-divisi-priority"
                      className="m-0 flex min-w-0 flex-col gap-1 border-0 p-0"
                    >
                      <span id="lintas-divisi-priority" className="text-12 font-medium text-secondary">
                        {t("cross_division_ui.priority_label")}
                      </span>
                      <CustomSelect
                        value={prioritas}
                        onChange={(v: string) => setPrioritas(v)}
                        label={t(PRIORITAS.find((p) => p.value === prioritas)?.label ?? PRIORITAS[0].label)}
                        buttonClassName="w-full"
                        className="w-full"
                        input
                      >
                        {PRIORITAS.map((pilihan) => (
                          <CustomSelect.Option key={pilihan.value} value={pilihan.value}>
                            {t(pilihan.label)}
                          </CustomSelect.Option>
                        ))}
                      </CustomSelect>
                    </fieldset>
                  </div>

                  <label className="flex flex-col gap-1">
                    <span className="text-12 font-medium text-secondary">{t("cross_division_ui.note_label")}</span>
                    <TextArea
                      value={catatan}
                      maxLength={2000}
                      rows={3}
                      onChange={(e) => setCatatan(e.target.value)}
                      placeholder={t("cross_division_ui.note_placeholder")}
                      className={`${inputClass} ${TINGGI_TIGA_BARIS}`}
                    />
                    <span className="text-11 text-tertiary">
                      {t("cross_division_ui.char_count", { count: catatan.length, max: 2000 })}
                    </span>
                  </label>

                  <label className="flex flex-col gap-1">
                    <span className="text-12 font-medium text-secondary">
                      {t("cross_division_ui.description_label")}
                    </span>
                    <TextArea
                      value={keterangan}
                      rows={3}
                      onChange={(e) => setKeterangan(e.target.value)}
                      placeholder={t("cross_division_ui.description_placeholder")}
                      className={`${inputClass} ${TINGGI_TIGA_BARIS}`}
                    />
                    <span className="text-11 text-tertiary">{t("cross_division_ui.description_hint")}</span>
                  </label>

                  {gagalKirim && (
                    <p
                      role="alert"
                      className="rounded-item border border-danger-subtle bg-danger-subtle px-2 py-1 text-12 text-danger-primary"
                    >
                      {gagalKirim}
                    </p>
                  )}

                  <div className="flex items-center gap-2">
                    <Button
                      variant="primary"
                      size="lg"
                      prependIcon={<Send />}
                      disabled={isSending}
                      onClick={() => void handleKirim()}
                    >
                      {isSending ? t("cross_division_ui.sending") : t("cross_division_ui.send")}
                    </Button>
                    <span className="text-11 text-tertiary">{t("cross_division_ui.visibility_hint")}</span>
                  </div>
                </div>
              )}
            </section>

            {/* 3. Tabel permintaan saya */}
            <section className="flex flex-col gap-3">
              <h2 className="text-16 font-semibold text-primary">{t("cross_division_ui.stat_mine")}</h2>
              {permintaanKeluar.length === 0 ? (
                <p className="text-13 text-tertiary">{t("cross_division_ui.no_requests")}</p>
              ) : (
                <TabelPermintaan baris={permintaanKeluar} workspaceSlug={workspaceSlug} />
              )}
              <p className="text-11 text-tertiary">{t("cross_division_ui.footer_note")}</p>
            </section>

            {/* 4. Permintaan yang masuk ke departemen yang saya awasi */}
            {permintaanMasuk.length > 0 && (
              <section className="flex flex-col gap-3">
                <h2 className="text-16 font-semibold text-primary">{t("cross_division_ui.incoming_title")}</h2>
                <TabelPermintaan baris={permintaanMasuk} workspaceSlug={workspaceSlug} tampilkanPeminta />
                <p className="text-11 text-tertiary">{t("cross_division_ui.incoming_hint")}</p>
              </section>
            )}
          </>
        )}
      </PageShell>
    </>
  );
}

export default observer(TugasLintasDivisiPage);
