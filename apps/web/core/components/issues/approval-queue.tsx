/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: antrean persetujuan per divisi 
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Aturan yang ditampilkan (diputuskan user 2026-10-15, disederhanakan 2026-10-16):
 * - Yang butuh persetujuan HANYA staf (member) yang menugaskan ke dirinya sendiri.
 * - Yang menyetujui adalah atasan pembuat di divisinya: supervisor, manager, atau direktur.
 * - Tugas yang ditolak KEMBALI ke draft tak-terlihat; staf mengajukan ulang dari sini.
 * - Penolakan WAJIB beralasan; pembuat tidak boleh menyetujui tugasnya sendiri.
 *
 * Dipakai di dua tempat: tab Persetujuan tiap divisi (`projectId` tetap) dan
 * halaman antrean workspace lama (`projectId` dipilih). Satu komponen supaya
 * keduanya tidak berbeda pendapat tentang bentuk antrean.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { observer } from "mobx-react";
import { AlertTriangle, CheckCircle2, Clock, Inbox, Send, XCircle } from "lucide-react";
// plane imports
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { EmptyStateCompact } from "@plane/propel/empty-state";
import { EPillSize, EPillVariant, Pill } from "@plane/propel/pill";
import { Loader } from "@plane/ui";
import { useProject } from "@/hooks/store/use-project";
import { useSetelStatusPersetujuan } from "@/hooks/use-aturan-tugas";
// services
import {
  PersetujuanService,
  type TDaftarPersetujuan,
  type TPersetujuanPenugasan,
  type TStatusPersetujuan,
} from "@/services/persetujuan.service";

const persetujuanService = new PersetujuanService();

const inputClass = "rounded border border-subtle bg-layer-1 px-2 py-1 text-xs outline-none focus:border-accent";

const pesanGagal = (err: unknown, fallback: string): string => {
  const pesan = (err as { error?: string } | undefined)?.error;
  return typeof pesan === "string" && pesan.length > 0 ? pesan : fallback;
};

const formatTanggal = (nilai: string | null): string => {
  if (!nilai) return "—";
  const tanggal = new Date(nilai);
  if (Number.isNaN(tanggal.getTime())) return "—";
  return tanggal.toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" });
};

function Badge({ status }: { status: TStatusPersetujuan }) {
  if (status === "menunggu") {
    return (
      <Pill variant={EPillVariant.WARNING} size={EPillSize.XS}>
        Menunggu persetujuan
      </Pill>
    );
  }
  if (status === "ditolak") {
    return (
      <Pill variant={EPillVariant.ERROR} size={EPillSize.XS}>
        Ditolak
      </Pill>
    );
  }
  return (
    <Pill variant={EPillVariant.SUCCESS} size={EPillSize.XS}>
      Disetujui
    </Pill>
  );
}
type TBarisAntrean = TPersetujuanPenugasan & { divisi: string; projectId: string };

function KartuKeputusan({
  baris,
  workspaceSlug,
  projectId,
  onSelesai,
}: {
  baris: TBarisAntrean;
  workspaceSlug: string;
  projectId: string;
  onSelesai: () => void;
}) {
  const [alasan, setAlasan] = useState("");
  const [isWorking, setIsWorking] = useState(false);
  const [gagal, setGagal] = useState<string | null>(null);
  const setelStatus = useSetelStatusPersetujuan();

  const putuskan = async (aksi: "setujui" | "tolak") => {
    setGagal(null);
    if (aksi === "tolak" && !alasan.trim()) {
      setGagal("Alasan penolakan wajib diisi supaya pemohon tahu apa yang harus diperbaiki.");
      return;
    }
    setIsWorking(true);
    try {
      await persetujuanService.putuskan(workspaceSlug, projectId, baris.id, aksi, alasan.trim());
      setelStatus(baris.tugas.id, aksi === "setujui" ? "disetujui" : "ditolak");
      onSelesai();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: aksi === "setujui" ? "Disetujui" : "Ditolak",
        message:
          aksi === "setujui"
            ? `Tugas ${baris.tugas.nomor ?? ""} disetujui.`
            : `Tugas ${baris.tugas.nomor ?? ""} kembali ke draft pemohon.`,
      });
    } catch (err) {
      // Pesan dari API ditampilkan apa adanya (mis. "Anda bukan atasan pembuat
      // di divisi ini") — kegagalan senyap adalah kelas bug termahal di sini.
      const pesan = pesanGagal(err, "Gagal menyimpan keputusan.");
      setGagal(pesan);
      setToast({ type: TOAST_TYPE.ERROR, title: "Gagal menyimpan", message: pesan });
    } finally {
      setIsWorking(false);
    }
  };

  if (!baris.boleh_saya_putuskan) return <></>;

  return (
    <div className="flex flex-col gap-2 rounded-md border border-subtle bg-layer-1 p-3">
      <textarea
        value={alasan}
        rows={2}
        maxLength={2000}
        onChange={(e) => setAlasan(e.target.value)}
        placeholder="Alasan (wajib kalau menolak, opsional kalau menyetujui)"
        className={inputClass}
      />
      {gagal && <p className="border-red-500/30 bg-red-500/5 text-xs text-red-600 rounded border px-2 py-1">{gagal}</p>}
      <div className="flex items-center gap-2">
        <Button
          variant="primary"
          size="sm"
          loading={isWorking}
          onClick={() => void putuskan("setujui")}
          prependIcon={<CheckCircle2 className="size-3.5" />}
        >
          Setujui
        </Button>
        <Button
          variant="error-outline"
          size="sm"
          loading={isWorking}
          onClick={() => void putuskan("tolak")}
          prependIcon={<XCircle className="size-3.5" />}
        >
          Tolak
        </Button>
      </div>
    </div>
  );
}
function TombolAjukanUlang({
  baris,
  workspaceSlug,
  onSelesai,
}: {
  baris: TBarisAntrean;
  workspaceSlug: string;
  onSelesai: () => void;
}) {
  const [isWorking, setIsWorking] = useState(false);
  const [gagal, setGagal] = useState<string | null>(null);
  const setelStatus = useSetelStatusPersetujuan();

  const ajukan = async () => {
    setGagal(null);
    setIsWorking(true);
    try {
      const hasil = await persetujuanService.putuskan(workspaceSlug, baris.projectId, baris.id, "ajukan-ulang");
      setelStatus(baris.tugas.id, hasil?.status ?? "menunggu");
      onSelesai();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: "Diajukan ulang",
        message: `Tugas ${baris.tugas.nomor ?? ""} kembali ke antrean atasan.`,
      });
    } catch (err) {
      const pesan = pesanGagal(err, "Gagal mengajukan ulang.");
      setGagal(pesan);
      setToast({ type: TOAST_TYPE.ERROR, title: "Gagal mengajukan", message: pesan });
    } finally {
      setIsWorking(false);
    }
  };

  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-[11px] text-tertiary">
        Tugas ini kembali ke draft pribadimu (tidak di papan). Perbaiki dulu sesuai alasan di atas, lalu ajukan ulang.
      </p>
      {gagal && <p className="border-red-500/30 bg-red-500/5 text-xs text-red-600 rounded border px-2 py-1">{gagal}</p>}
      <div>
        <Button
          variant="secondary"
          size="sm"
          loading={isWorking}
          onClick={() => void ajukan()}
          prependIcon={<Send className="size-3.5" />}
        >
          Ajukan ulang
        </Button>
      </div>
    </div>
  );
}

export type TAntreanPersetujuanProps = {
  workspaceSlug: string;
  /** Tetap = tab per divisi. Kosong = pemanggil memilih divisi sendiri. */
  projectId?: string;
};

export const AntreanPersetujuan = observer(function AntreanPersetujuan(props: TAntreanPersetujuanProps) {
  const { workspaceSlug, projectId: projectTetap } = props;
  const { joinedProjectIds, getProjectById } = useProject();
  // sudut: antrean yang perlu SAYA putuskan vs pengajuan SAYA sendiri
  const [sudut, setSudut] = useState<"penyetuju" | "pemohon">("penyetuju");
  const [divisiDipilih, setDivisiDipilih] = useState("");
  const [baris, setBaris] = useState<TBarisAntrean[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [gagalMuat, setGagalMuat] = useState<string | null>(null);
  const [gerbangMati, setGerbangMati] = useState(false);

  const divisiSaya = useMemo(() => {
    const daftar: { id: string; identifier: string; name: string }[] = [];
    for (const projectId of joinedProjectIds ?? []) {
      const proyek = getProjectById(projectId);
      if (proyek) daftar.push({ id: proyek.id, identifier: proyek.identifier, name: proyek.name });
    }
    return daftar;
  }, [joinedProjectIds, getProjectById]);

  const muatSemua = useCallback(async () => {
    if (!workspaceSlug) return;
    // Tab per divisi: tepat satu panggilan. Halaman lama: satu per divisi.
    const aktif = projectTetap
      ? [projectTetap]
      : sudut === "penyetuju" && divisiDipilih
        ? [divisiDipilih]
        : divisiSaya.map((d) => d.id);
    if (aktif.length === 0) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setGagalMuat(null);
    try {
      const respons: TDaftarPersetujuan[] = await Promise.all(
        aktif.map((pid) => persetujuanService.daftar(workspaceSlug, pid, { peran: sudut }))
      );
      const mati = respons.some((res) => !res?.gerbang_aktif);
      setGerbangMati(mati);
      // Yang menunggu di atas, sisanya di bawah — TANPA `sort`: lib TS web
      // pra-ES2023 (tak ada `toSorted`) dan aturan lint menolak `sort` di
      // variabel. Urutan dalam grup = urutan server (backend tanpa ORDER BY;
      // kalau riwayat perlu "terbaru dulu", itu `order_by` di endpoint).
      const semua: TBarisAntrean[] = respons.flatMap((res, i) => {
        const pid = aktif[i];
        const nama = getProjectById(pid)?.name ?? pid;
        // `Object.assign`, bukan spread: aturan `no-map-spread` (copy-on-write
        // tetap terjaga — respons axios tidak dimutasi).
        return (res?.hasil ?? []).map((item) => Object.assign({}, item, { divisi: nama, projectId: pid }));
      });
      setBaris([...semua.filter((b) => b.status === "menunggu"), ...semua.filter((b) => b.status !== "menunggu")]);
    } catch (err) {
      setGagalMuat(pesanGagal(err, "Gagal memuat antrean persetujuan. Coba muat ulang halaman."));
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug, projectTetap, divisiSaya, sudut, divisiDipilih, getProjectById]);

  useEffect(() => {
    void muatSemua();
  }, [muatSemua]);

  const menunggu = baris.filter((b) => b.status === "menunggu");
  // Tidak ada saring di klien: `muatSemua` sudah mengambil tepat divisi yang
  // dipilih, jadi `baris` SELALU yang tampil. Menyaring lagi berarti dua
  // kebenaran tentang "yang tampil".

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <p className="text-xs text-tertiary">
        Staf hanya bisa menugaskan pekerjaan ke dirinya sendiri, dan penugasan itu menunggu persetujuan atasan di
        divisinya (supervisor, manager, atau direktur). Tugas yang ditolak kembali ke draft pemohon — yang menandai
        statusnya adalah daftar ini.
      </p>

      {!projectTetap && divisiSaya.length === 0 ? (
        <p className="text-sm text-tertiary">
          Kamu belum menjadi anggota divisi mana pun di workspace ini. Minta admin menambahkanmu ke divisimu dulu.
        </p>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 rounded-md border border-subtle p-0.5">
              <button
                type="button"
                onClick={() => setSudut("penyetuju")}
                className={`text-xs rounded px-2.5 py-1 font-medium ${sudut === "penyetuju" ? "bg-layer-3 text-primary" : "text-tertiary"}`}
              >
                Perlu saya putuskan ({sudut === "penyetuju" ? menunggu.length : "…"})
              </button>
              <button
                type="button"
                onClick={() => setSudut("pemohon")}
                className={`text-xs rounded px-2.5 py-1 font-medium ${sudut === "pemohon" ? "bg-layer-3 text-primary" : "text-tertiary"}`}
              >
                Pengajuan saya
              </button>
            </div>
            {!projectTetap && sudut === "penyetuju" && (
              <select value={divisiDipilih} onChange={(e) => setDivisiDipilih(e.target.value)} className={inputClass}>
                <option value="">Semua divisi saya</option>
                {divisiSaya.map((divisi) => (
                  <option key={divisi.id} value={divisi.id}>
                    {divisi.name} ({divisi.identifier})
                  </option>
                ))}
              </select>
            )}
            <Button variant="secondary" size="sm" onClick={() => void muatSemua()}>
              Muat ulang
            </Button>
          </div>

          {gerbangMati && (
            <div className="text-xs flex items-start gap-2 rounded-md border border-subtle bg-layer-1 px-3 py-2 text-secondary">
              <Inbox className="mt-0.5 size-4 shrink-0 text-tertiary" />
              <span>
                Gerbang persetujuan di server sedang <span className="font-medium">mati</span>, jadi antrean ini kosong
                bukan karena tidak ada yang menunggu — belum ada penugasan yang dicatat. Nyalakan gerbangnya dulu
                (setelah jenjang diisi lewat God Mode), lalu muat ulang.
              </span>
            </div>
          )}

          {gagalMuat ? (
            <div className="border-red-500/30 bg-red-500/5 text-xs text-red-600 flex items-start gap-2 rounded-md border px-3 py-2">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              <div className="flex flex-col gap-1">
                <span>{gagalMuat}</span>
                <Button variant="secondary" size="sm" onClick={() => void muatSemua()} className="self-start">
                  Coba lagi
                </Button>
              </div>
            </div>
          ) : isLoading ? (
            <Loader className="space-y-2">
              {[1, 2, 3].map((k) => (
                <Loader.Item key={k} height="72px" />
              ))}
            </Loader>
          ) : baris.length === 0 ? (
            <EmptyStateCompact
              assetKey="intake"
              title={sudut === "penyetuju" ? "Tidak ada yang menunggu keputusan" : "Belum ada pengajuan"}
              description={
                sudut === "penyetuju"
                  ? "Kalau staf divisimu menugaskan pekerjaan ke dirinya sendiri, barisnya muncul di sini."
                  : "Tugas yang kamu buat untuk dirimu sendiri muncul di sini beserta status persetujuannya."
              }
            />
          ) : (
            <div className="flex flex-col gap-3">
              {baris.map((item) => (
                <div key={item.id} className="flex flex-col gap-2 rounded-md border border-subtle bg-layer-1 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge status={item.status} />
                    <span className="text-xs font-medium text-primary">
                      {item.tugas.nomor ?? "—"} · {item.tugas.judul ?? "(tanpa judul)"}
                    </span>
                  </div>
                  <p className="text-[11px] text-tertiary">
                    {projectTetap ? null : <>Divisi {item.divisi} · </>}diajukan oleh{" "}
                    {item.pemohon.nama ?? item.pemohon.email ?? "—"} · {formatTanggal(item.created_at)}
                    {item.status !== "menunggu" && <> · diputuskan {formatTanggal(item.diputuskan_pada)}</>}
                  </p>
                  {item.status === "ditolak" && item.alasan && (
                    <p className="border-red-500/30 bg-red-500/5 text-xs text-red-600 rounded border px-2 py-1">
                      Alasan penolakan: {item.alasan}
                    </p>
                  )}
                  {item.status === "ditolak" && item.peran_saya === "pemohon" && (
                    <TombolAjukanUlang baris={item} workspaceSlug={workspaceSlug} onSelesai={() => void muatSemua()} />
                  )}
                  {item.status === "menunggu" && item.penyetuju_di_divisi.length === 0 && (
                    <p className="flex items-center gap-1 text-[11px] text-tertiary">
                      <Clock className="size-3.5" /> Belum ada atasan di divisi ini — jenjangnya perlu diisi lewat God
                      Mode.
                    </p>
                  )}
                  {item.status === "menunggu" && (
                    <KartuKeputusan
                      baris={item}
                      workspaceSlug={workspaceSlug}
                      projectId={item.projectId}
                      onSelesai={() => void muatSemua()}
                    />
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
});
