/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Nomaden: Owner Panel, daftar pelanggan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { AlertTriangle, ExternalLink, ReceiptText, RefreshCw } from "lucide-react";
import useSWR from "swr";
// plane internal packages
import { Button } from "@plane/propel/button";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import { ControlPlaneService, type TCompany, type TCompanyStatus, type TTier } from "@plane/services";
import { Loader } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";

const layanan = new ControlPlaneService();

const TINGKATAN: TTier[] = ["FREE", "PRO", "EXPERT", "ENTERPRISE"];

/**
 * Warna dipakai SEMANTIS, bukan dekoratif: hijau berarti tidak perlu ditindak,
 * kuning berarti menunggu tindakan, merah berarti sudah dihentikan. Orang yang
 * membuka halaman ini biasanya sedang mencari satu hal, yaitu siapa yang perlu
 * ditagih hari ini.
 */
const WARNA_STATUS: Record<TCompanyStatus, string> = {
  ACTIVE: "bg-green-500/10 text-green-600 ring-green-500/20",
  TRIAL: "bg-blue-500/10 text-blue-600 ring-blue-500/20",
  PAST_DUE: "bg-amber-500/10 text-amber-700 ring-amber-500/25",
  SUSPENDED: "bg-red-500/10 text-red-600 ring-red-500/20",
  CHURNED: "bg-neutral-500/10 text-tertiary ring-neutral-500/20",
};

const LABEL_STATUS: Record<TCompanyStatus, string> = {
  ACTIVE: "Aktif",
  TRIAL: "Percobaan",
  PAST_DUE: "Menunggak",
  SUSPENDED: "Ditangguhkan",
  CHURNED: "Berhenti",
};

const SKELETON = ["s1", "s2", "s3"];

const kelasSelect =
  "rounded border border-subtle bg-layer-1 px-2 py-1 text-body-sm-regular text-primary outline-none " +
  "transition-colors hover:border-strong focus:border-accent-primary";

function ukuran(bytes: number) {
  if (!bytes) return "0 MB";
  const mb = bytes / (1024 * 1024);
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb.toFixed(0)} MB`;
}

/**
 * "3 jam lalu" mengalahkan stempel waktu penuh di sini. Yang ditanyakan orang
 * bukan kapan tepatnya sebuah instance berdenyut, melainkan apakah ia masih
 * hidup, dan jarak menjawab itu tanpa perlu dihitung di kepala.
 */
function jarakWaktu(iso: string | null) {
  if (!iso) return "belum pernah";
  const detik = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (detik < 90) return "baru saja";
  const menit = Math.floor(detik / 60);
  if (menit < 60) return `${menit} menit lalu`;
  const jam = Math.floor(menit / 60);
  if (jam < 48) return `${jam} jam lalu`;
  return `${Math.floor(jam / 24)} hari lalu`;
}

/** Denyut per jam, jadi lewat tiga jam berarti ada yang perlu dilihat. */
const AMBANG_SENYAP_JAM = 3;

function instanceSenyap(iso: string | null) {
  if (!iso) return true;
  return Date.now() - new Date(iso).getTime() > AMBANG_SENYAP_JAM * 3600 * 1000;
}

const BarisPerusahaan = function BarisPerusahaan({ perusahaan, onUbah }: { perusahaan: TCompany; onUbah: () => void }) {
  const [sibuk, setSibuk] = useState(false);
  const instansi = perusahaan.instances[0];
  const pakai = instansi?.usage;

  const jalankan = async (aksi: () => Promise<unknown>, pesanSukses: string) => {
    setSibuk(true);
    try {
      await aksi();
      onUbah();
      setToast({ type: TOAST_TYPE.SUCCESS, title: pesanSukses });
    } catch (e) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Gagal",
        message: (e as { error?: string })?.error ?? "Coba lagi.",
      });
    } finally {
      setSibuk(false);
    }
  };

  const terbitkanTagihan = () =>
    jalankan(async () => {
      const hasil = await layanan.createInvoice(perusahaan.slug);
      // Tautannya dibuka langsung, bukan cuma diberitahukan ada. Halaman bayar
      // yang harus dicari sendiri di daftar tagihan adalah satu langkah lagi
      // sebelum pelanggan bisa membayar.
      if (hasil?.invoice_url) window.open(hasil.invoice_url, "_blank", "noopener");
    }, "Tagihan diterbitkan");

  return (
    <tr className="border-b border-subtle transition-colors last:border-0 hover:bg-layer-transparent-hover">
      <td className="px-4 py-3 align-top">
        <div className="text-body-sm-medium text-primary">{perusahaan.name}</div>
        <div className="text-caption-sm-regular text-tertiary">{perusahaan.contact_email}</div>
      </td>

      <td className="px-4 py-3 align-top">
        <span
          className={`inline-flex rounded-full px-2 py-0.5 text-caption-sm-medium ring-1 ring-inset ${
            WARNA_STATUS[perusahaan.status]
          }`}
        >
          {LABEL_STATUS[perusahaan.status]}
        </span>
      </td>

      <td className="px-4 py-3 align-top">
        <select
          value={perusahaan.tier}
          disabled={sibuk}
          onChange={(e) =>
            jalankan(
              () => layanan.updateCompany(perusahaan.slug, { tier: e.target.value as TTier }),
              "Tingkatan diubah"
            )
          }
          className={kelasSelect}
        >
          {TINGKATAN.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </td>

      <td className="px-4 py-3 align-top">
        {instansi ? (
          <>
            <div className="font-mono text-caption-sm-regular text-secondary">{instansi.subdomain}</div>
            <div
              className={`text-caption-sm-regular ${
                instanceSenyap(instansi.last_seen_at) ? "text-amber-600" : "text-tertiary"
              }`}
            >
              {instanceSenyap(instansi.last_seen_at) && <AlertTriangle className="mr-1 inline size-3" aria-hidden />}
              {jarakWaktu(instansi.last_seen_at)}
            </div>
          </>
        ) : (
          <span className="text-caption-sm-regular text-tertiary">belum ada instance</span>
        )}
      </td>

      <td className="px-4 py-3 align-top text-caption-sm-regular text-secondary">
        {pakai ? (
          <>
            <div>{pakai.members} anggota</div>
            <div className="text-tertiary">{ukuran(pakai.storage_bytes)}</div>
          </>
        ) : (
          <span className="text-tertiary">belum melapor</span>
        )}
      </td>

      <td className="px-4 py-3 align-top">
        <div className="flex flex-wrap justify-end gap-2">
          {perusahaan.tier !== "FREE" && perusahaan.tier !== "ENTERPRISE" && (
            <Button variant="secondary" size="sm" disabled={sibuk} onClick={terbitkanTagihan}>
              <ReceiptText className="size-3.5" />
              Tagih
            </Button>
          )}
          {perusahaan.status === "SUSPENDED" ? (
            <Button
              variant="primary"
              size="sm"
              disabled={sibuk}
              onClick={() =>
                jalankan(() => layanan.updateCompany(perusahaan.slug, { status: "ACTIVE" }), "Diaktifkan kembali")
              }
            >
              Aktifkan
            </Button>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              disabled={sibuk || perusahaan.status === "CHURNED"}
              onClick={() =>
                jalankan(() => layanan.updateCompany(perusahaan.slug, { status: "SUSPENDED" }), "Ditangguhkan")
              }
            >
              Tangguhkan
            </Button>
          )}
        </div>
      </td>
    </tr>
  );
};

const CompaniesPage = function CompaniesPage() {
  const { data, isLoading, error, mutate } = useSWR("CONTROL_COMPANIES", () => layanan.companies(), {
    revalidateOnFocus: false,
  });

  const perusahaan = data?.companies ?? [];
  const perluDitindak = perusahaan.filter((c: TCompany) => c.status === "PAST_DUE" || c.status === "SUSPENDED").length;

  return (
    <PageWrapper
      size="lg"
      header={{
        title: "Pelanggan",
        description:
          "Perusahaan berlangganan, pemakaian terakhir yang mereka laporkan, dan tagihannya. " +
          "Halaman ini hanya ada di deployment pemilik produk.",
      }}
    >
      <div className="mx-4">
        {/* Ringkasan didahulukan karena pertanyaan pertama yang dibawa orang ke
            halaman ini hampir selalu "ada yang perlu ditindak hari ini?" */}
        <div className="mb-4 flex flex-wrap items-center gap-4">
          <div>
            <div className="text-h3-medium text-primary">{perusahaan.length}</div>
            <div className="text-caption-sm-regular text-tertiary">perusahaan</div>
          </div>
          <div>
            <div className={`text-h3-medium ${perluDitindak > 0 ? "text-amber-600" : "text-primary"}`}>
              {perluDitindak}
            </div>
            <div className="text-caption-sm-regular text-tertiary">perlu ditindak</div>
          </div>
          <button
            type="button"
            onClick={() => mutate()}
            className="ml-auto flex items-center gap-1.5 rounded px-2 py-1 text-caption-sm-regular text-secondary transition-colors hover:bg-layer-transparent-hover hover:text-primary"
          >
            <RefreshCw className="size-3.5" aria-hidden />
            Muat ulang
          </button>
        </div>

        {isLoading && (
          <Loader className="space-y-2">
            {SKELETON.map((k) => (
              <Loader.Item key={k} height="56px" />
            ))}
          </Loader>
        )}

        {!isLoading && error && (
          <div className="rounded-md border border-subtle bg-layer-1 p-8 text-center">
            <h2 className="text-body-md-medium text-primary">Bidang kendali tidak aktif di sini</h2>
            <p className="mt-1 text-body-sm-regular text-tertiary">
              Halaman ini menuntut <span className="font-mono">ENABLE_CONTROL_PLANE=1</span>, dan itu hanya disetel di
              deployment milik pemilik produk. Di instance pelanggan maupun instance pasang-sendiri, tabelnya memang
              tidak pernah dibuat.
            </p>
          </div>
        )}

        {!isLoading && !error && perusahaan.length === 0 && (
          <div className="rounded-md border border-subtle bg-layer-1 p-8 text-center">
            <h2 className="text-body-md-medium text-primary">Belum ada pelanggan</h2>
            <p className="mt-1 text-body-sm-regular text-tertiary">
              Daftarkan yang pertama lewat <span className="font-mono">manage.py provision_tenant</span>. Perintah itu
              sekaligus menerbitkan rahasia denyut dan berkas env-nya.
            </p>
          </div>
        )}

        {!isLoading && !error && perusahaan.length > 0 && (
          <div className="overflow-x-auto rounded-md border border-subtle bg-layer-1">
            <table className="w-full min-w-[860px] border-collapse">
              <thead>
                <tr className="border-b border-subtle text-left">
                  <th className="px-4 py-2 text-caption-sm-medium text-tertiary">Perusahaan</th>
                  <th className="px-4 py-2 text-caption-sm-medium text-tertiary">Status</th>
                  <th className="px-4 py-2 text-caption-sm-medium text-tertiary">Tingkatan</th>
                  <th className="px-4 py-2 text-caption-sm-medium text-tertiary">Instance</th>
                  <th className="px-4 py-2 text-caption-sm-medium text-tertiary">Pemakaian</th>
                  <th className="px-4 py-2 text-right text-caption-sm-medium text-tertiary">Aksi</th>
                </tr>
              </thead>
              <tbody>
                {perusahaan.map((c: TCompany) => (
                  <BarisPerusahaan key={c.slug} perusahaan={c} onUbah={() => mutate()} />
                ))}
              </tbody>
            </table>
          </div>
        )}

        <p className="mt-3 flex items-center gap-1.5 text-caption-sm-regular text-tertiary">
          <ExternalLink className="size-3" aria-hidden />
          Tombol Tagih membuka halaman bayar Xendit di tab baru. FREE tidak ditagih, ENTERPRISE ditagih lewat
          kesepakatan.
        </p>
      </div>
    </PageWrapper>
  );
};

export default CompaniesPage;
