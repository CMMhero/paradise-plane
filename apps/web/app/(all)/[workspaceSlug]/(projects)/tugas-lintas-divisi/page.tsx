/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: halaman pengirim permintaan lintas divisi 
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "react-router";
import { AlertTriangle, ArrowLeftRight, Clock, Inbox, ListTodo, Send } from "lucide-react";
// plane imports
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
// components
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

const inputClass = "rounded border border-subtle bg-layer-1 px-2 py-1 text-xs outline-none focus:border-accent";

const PRIORITAS: { value: string; label: string }[] = [
  { value: "none", label: "Tidak ada" },
  { value: "low", label: "Rendah" },
  { value: "medium", label: "Sedang" },
  { value: "high", label: "Tinggi" },
  { value: "urgent", label: "Mendesak" },
];

// Kosakata status dipakai APA ADANYA dari API (jangan diterjemahkan jadi teks
// lain); yang ada di sini hanya label tampilan. `Record<string, string>` supaya
// status yang belum dikenal tetap ditampilkan mentah, bukan hilang.
const LABEL_STATUS_PERMINTAAN: Record<string, string> = {
  menunggu: "Menunggu",
  ditunda: "Ditunda",
  ditolak: "Ditolak",
  duplikat: "Duplikat",
  diterima: "Diterima",
  dibatalkan: "Dibatalkan",
};

const KELAS_STATUS_PERMINTAAN: Record<string, string> = {
  menunggu: "bg-amber-500/10 text-amber-600",
  ditunda: "bg-layer-3 text-secondary",
  ditolak: "bg-red-500/10 text-red-600",
  duplikat: "bg-layer-3 text-tertiary",
  diterima: "bg-green-500/10 text-green-600",
  dibatalkan: "bg-layer-3 text-tertiary",
};

const LABEL_STATUS_TUGAS: Record<string, string> = {
  belum_diterima: "Belum diterima",
  terbuka: "Terbuka",
  selesai: "Selesai",
  dibatalkan: "Dibatalkan",
  tidak_dikerjakan: "Tidak dikerjakan",
};

const KELAS_STATUS_TUGAS: Record<string, string> = {
  belum_diterima: "bg-layer-3 text-tertiary",
  terbuka: "bg-blue-500/10 text-blue-600",
  selesai: "bg-green-500/10 text-green-600",
  dibatalkan: "bg-red-500/10 text-red-600",
  tidak_dikerjakan: "bg-layer-3 text-tertiary",
};

const pesanGagal = (err: unknown, fallback: string): string => {
  const pesan = (err as { error?: string } | undefined)?.error;
  return typeof pesan === "string" && pesan.length > 0 ? pesan : fallback;
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

const formatTanggal = (nilai: string): string => {
  const tanggal = new Date(nilai);
  if (Number.isNaN(tanggal.getTime())) return "—";
  return tanggal.toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" });
};

const labelStatusPermintaan = (nilai: TStatusPermintaan): string => LABEL_STATUS_PERMINTAAN[nilai] ?? nilai;

const labelStatusTugas = (nilai: TStatusTugas): string => LABEL_STATUS_TUGAS[nilai] ?? nilai;

function Badge({ label, className }: { label: string; className: string }) {
  return <span className={`inline-block rounded-full px-2 py-0.5 text-[11px] font-medium ${className}`}>{label}</span>;
}

type TStatCard = { label: string; value: string; keterangan: string; icon: React.ReactNode };

function StatCard({ label, value, keterangan, icon }: TStatCard) {
  return (
    <div className="flex items-center gap-3 rounded-md border border-subtle bg-layer-1 px-4 py-3">
      <div className="shrink-0 text-secondary">{icon}</div>
      <div className="min-w-0">
        <p className="text-lg font-semibold text-primary">{value}</p>
        <p className="text-xs truncate text-tertiary">{label}</p>
        <p className="truncate text-[11px] text-tertiary">{keterangan}</p>
      </div>
    </div>
  );
}

function TugasLintasDivisiPage() {
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
      setGagalMuat(pesanGagal(err, "Gagal memuat data lintas divisi. Coba muat ulang halaman."));
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug]);

  useEffect(() => {
    void muatSemua();
  }, [muatSemua]);

  const tujuanTersedia = daftarTujuan.filter((divisi) => divisi.id !== asalId);

  const keluarMenunggu = Object.values(ringkasan).reduce((total, baris) => total + baris.keluar_menunggu, 0);
  const keluarTerbuka = Object.values(ringkasan).reduce((total, baris) => total + baris.keluar_terbuka, 0);
  const rincianKeluar = Object.entries(ringkasan)
    .map(([projectId, baris]) => ({ projectId, baris, nama: getProjectById(projectId)?.name ?? null }))
    .filter((item) => item.baris.keluar_menunggu + item.baris.keluar_terbuka > 0);

  const handleKirim = async () => {
    if (!workspaceSlug) return;
    setGagalKirim(null);
    if (!asalId) {
      setGagalKirim("Pilih divisi asal dulu.");
      return;
    }
    if (!tujuanDipilih) {
      setGagalKirim("Pilih divisi tujuan dulu.");
      return;
    }
    if (!judul.trim()) {
      setGagalKirim("Judul permintaan wajib diisi.");
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
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Terkirim", message: "Permintaan diteruskan ke divisi tujuan." });
    } catch (err) {
      const pesan = pesanGagal(err, "Gagal mengirim permintaan.");
      setGagalKirim(pesan);
      setToast({ type: TOAST_TYPE.ERROR, title: "Gagal mengirim", message: pesan });
    } finally {
      setIsSending(false);
    }
  };

  if (!workspaceSlug) return <></>;

  return (
    <div className="h-full w-full overflow-y-auto px-6 py-5">
      <PageHead title="Tugas Lintas Divisi" />

      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        <p className="text-xs text-tertiary">
          Pekerjaan yang lahir di divisimu tapi harus dikerjakan divisi lain dikirim lewat halaman ini. Permintaan masuk
          ke kotak masuk (Intake) divisi tujuan, dan admin divisi itu yang memutuskan menerima atau menolak. Kamu tidak
          mendapat akses ke isi divisi tujuan, dan sebaliknya.
        </p>

        {gagalMuat ? (
          <div className="border-red-500/30 bg-red-500/5 text-xs text-red-600 flex items-start gap-2 rounded-md border px-3 py-2">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            <div className="flex flex-col gap-1">
              <span>{gagalMuat}</span>
              <button
                type="button"
                onClick={() => void muatSemua()}
                className="self-start rounded border border-subtle px-2 py-0.5 font-medium text-secondary hover:bg-layer-2"
              >
                Coba lagi
              </button>
            </div>
          </div>
        ) : isLoading ? (
          <p className="text-sm text-tertiary">Memuat…</p>
        ) : (
          <>
            {/* 1. Ringkasan saya */}
            <section className="flex flex-col gap-3">
              <h2 className="text-lg font-semibold text-primary">Ringkasan</h2>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <StatCard
                  label="Menunggu jawaban"
                  value={String(keluarMenunggu)}
                  keterangan="dikirim divisi asal saya, belum diputuskan"
                  icon={<Clock className="size-5" />}
                />
                <StatCard
                  label="Masih terbuka"
                  value={String(keluarTerbuka)}
                  keterangan="sudah diterima, tugasnya belum selesai"
                  icon={<ListTodo className="text-amber-500 size-5" />}
                />
                <StatCard
                  label="Permintaan saya"
                  value={String(permintaan.length)}
                  keterangan="baris di tabel bawah"
                  icon={<ArrowLeftRight className="size-5" />}
                />
              </div>
              <p className="text-[11px] text-tertiary">
                Dua angka pertama menghitung seluruh permintaan yang{" "}
                <span className="font-medium">dikirim divisi asalmu</span> (endpoint ringkasan hanya membuka divisi
                tempat kamu menjadi anggota). Tabel di bawah hanya menampilkan permintaan yang{" "}
                <span className="font-medium">kamu kirim sendiri</span>.
              </p>
              {rincianKeluar.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {rincianKeluar.map((item) => (
                    <span
                      key={item.projectId}
                      className="rounded-full border border-subtle px-2 py-0.5 text-[11px] text-secondary"
                    >
                      {item.nama ?? item.projectId}: {item.baris.keluar_menunggu} menunggu · {item.baris.keluar_terbuka}{" "}
                      terbuka
                    </span>
                  ))}
                </div>
              )}
            </section>

            {/* 2. Form kirim permintaan */}
            <section className="flex flex-col gap-3">
              <h2 className="text-lg font-semibold text-primary">Minta bantuan divisi lain</h2>

              {divisiSaya.length === 0 ? (
                <p className="text-sm text-tertiary">
                  Kamu belum menjadi anggota divisi mana pun di workspace ini, jadi belum ada divisi asal yang bisa kamu
                  ajukan. Minta admin menambahkanmu ke divisimu dulu.
                </p>
              ) : tujuanTersedia.length === 0 ? (
                <div className="text-xs flex items-start gap-2 rounded-md border border-subtle bg-layer-1 px-3 py-2 text-secondary">
                  <Inbox className="mt-0.5 size-4 shrink-0 text-tertiary" />
                  <span>
                    Belum ada divisi yang bisa menerima permintaan. Hanya divisi yang{" "}
                    <span className="font-medium">sudah menyalakan pintu Intake</span> yang muncul di sini, dan
                    menyalakannya adalah keputusan divisi itu sendiri — bukan sesuatu yang bisa dinyalakan dari halaman
                    ini. Hubungi admin divisi tujuan dan minta mereka mengaktifkan Inbox/Intake di pengaturan
                    projectnya.
                  </span>
                </div>
              ) : (
                <div className="flex flex-col gap-3 rounded-md border border-subtle bg-layer-1 p-4">
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <label className="flex flex-col gap-1">
                      <span className="text-xs font-medium text-secondary">Divisi asal</span>
                      <select value={asalId} onChange={(e) => setAsalDipilih(e.target.value)} className={inputClass}>
                        {divisiSaya.map((divisi) => (
                          <option key={divisi.id} value={divisi.id}>
                            {divisi.name} ({divisi.identifier})
                          </option>
                        ))}
                      </select>
                      <span className="text-[11px] text-tertiary">Hanya divisi tempat kamu menjadi anggota.</span>
                    </label>

                    <label className="flex flex-col gap-1">
                      <span className="text-xs font-medium text-secondary">Divisi tujuan</span>
                      <select
                        value={tujuanDipilih}
                        onChange={(e) => setTujuanDipilih(e.target.value)}
                        className={inputClass}
                      >
                        <option value="">— pilih divisi tujuan —</option>
                        {tujuanTersedia.map((divisi) => (
                          <option key={divisi.id} value={divisi.id}>
                            {divisi.name} ({divisi.identifier})
                          </option>
                        ))}
                      </select>
                      <span className="text-[11px] text-tertiary">Hanya divisi yang sudah menyalakan Intake.</span>
                    </label>
                  </div>

                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-[2fr_1fr]">
                    <label className="flex flex-col gap-1">
                      <span className="text-xs font-medium text-secondary">Judul permintaan</span>
                      <input
                        type="text"
                        value={judul}
                        maxLength={255}
                        onChange={(e) => setJudul(e.target.value)}
                        placeholder="mis. Siapkan akun dokumen tender"
                        className={inputClass}
                      />
                    </label>

                    <label className="flex flex-col gap-1">
                      <span className="text-xs font-medium text-secondary">Prioritas</span>
                      <select value={prioritas} onChange={(e) => setPrioritas(e.target.value)} className={inputClass}>
                        {PRIORITAS.map((pilihan) => (
                          <option key={pilihan.value} value={pilihan.value}>
                            {pilihan.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>

                  <label className="flex flex-col gap-1">
                    <span className="text-xs font-medium text-secondary">Catatan untuk divisi tujuan</span>
                    <textarea
                      value={catatan}
                      maxLength={2000}
                      rows={3}
                      onChange={(e) => setCatatan(e.target.value)}
                      placeholder="Konteks singkat: apa yang dibutuhkan, untuk apa, kapan."
                      className={inputClass}
                    />
                    <span className="text-[11px] text-tertiary">{catatan.length}/2000 karakter.</span>
                  </label>

                  <label className="flex flex-col gap-1">
                    <span className="text-xs font-medium text-secondary">Keterangan tugas (opsional)</span>
                    <textarea
                      value={keterangan}
                      rows={3}
                      onChange={(e) => setKeterangan(e.target.value)}
                      placeholder="Rincian langkah atau bahan yang perlu disiapkan."
                      className={inputClass}
                    />
                    <span className="text-[11px] text-tertiary">
                      Dikirim sebagai teks biasa (tanpa format HTML). Baris kosong jadi paragraf baru.
                    </span>
                  </label>

                  {gagalKirim && (
                    <p className="border-red-500/30 bg-red-500/5 text-xs text-red-600 rounded border px-2 py-1">
                      {gagalKirim}
                    </p>
                  )}

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={isSending}
                      onClick={() => void handleKirim()}
                      className="text-xs flex items-center gap-1.5 rounded border border-subtle px-3 py-1.5 font-medium text-secondary hover:bg-layer-2 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <Send className="size-3.5" />
                      {isSending ? "Mengirim…" : "Kirim permintaan"}
                    </button>
                    <span className="text-[11px] text-tertiary">
                      Judul dan catatanmu terlihat divisi tujuan. Isi divisimu yang lain tidak.
                    </span>
                  </div>
                </div>
              )}
            </section>

            {/* 3. Tabel permintaan saya */}
            <section className="flex flex-col gap-3">
              <h2 className="text-lg font-semibold text-primary">Permintaan saya</h2>
              {permintaan.length === 0 ? (
                <p className="text-sm text-tertiary">
                  Belum ada permintaan yang kamu kirim. Permintaan yang sudah dikirim akan muncul di sini beserta
                  statusnya di divisi tujuan.
                </p>
              ) : (
                <div className="overflow-x-auto rounded-md border border-subtle">
                  <table className="text-sm w-full min-w-[720px] text-left">
                    <thead>
                      <tr className="text-xs border-b border-subtle bg-layer-2 text-tertiary">
                        <th className="px-3 py-2 font-medium">Judul</th>
                        <th className="px-3 py-2 font-medium">Asal → Tujuan</th>
                        <th className="px-3 py-2 font-medium">Status permintaan</th>
                        <th className="px-3 py-2 font-medium">Status tugas</th>
                        <th className="px-3 py-2 font-medium">No. tugas</th>
                        <th className="px-3 py-2 font-medium">Tanggal</th>
                      </tr>
                    </thead>
                    <tbody>
                      {permintaan.map((baris) => (
                        <tr key={baris.id} className="border-b border-subtle last:border-0 hover:bg-layer-2">
                          <td className="px-3 py-2">
                            <span className="font-medium text-primary">{baris.judul ?? "—"}</span>
                            {baris.catatan && <p className="text-[11px] text-tertiary">{baris.catatan}</p>}
                          </td>
                          <td className="px-3 py-2 text-secondary">
                            {baris.asal.identifier} → {baris.tujuan.identifier}
                          </td>
                          <td className="px-3 py-2">
                            <Badge
                              label={labelStatusPermintaan(baris.status_permintaan)}
                              className={KELAS_STATUS_PERMINTAAN[baris.status_permintaan] ?? "bg-layer-3 text-tertiary"}
                            />
                          </td>
                          <td className="px-3 py-2">
                            <Badge
                              label={labelStatusTugas(baris.status_tugas)}
                              className={KELAS_STATUS_TUGAS[baris.status_tugas] ?? "bg-layer-3 text-tertiary"}
                            />
                          </td>
                          <td className="px-3 py-2 text-secondary">{baris.nomor_tugas_tujuan ?? "—"}</td>
                          <td className="px-3 py-2 text-secondary">{formatTanggal(baris.dibuat_pada)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <p className="text-[11px] text-tertiary">
                Status tugas di divisi tujuan hanya ditampilkan kasar (terbuka / selesai / tidak dikerjakan). Siapa yang
                mengerjakan, tenggat, label, dan komentar tidak dibuka lewat halaman ini.
              </p>
            </section>
          </>
        )}
      </div>
    </div>
  );
}

export default observer(TugasLintasDivisiPage);
