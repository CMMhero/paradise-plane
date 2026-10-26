/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: layar pilih departemen untuk akun yang belum ditempatkan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { useParams } from "react-router";
import useSWR from "swr";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
// services
import { penempatanService } from "@/services/penempatan.service";

const KUNCI_NANTI = "pilih-departemen-nanti";

const sudahDitunda = (): boolean => {
  try {
    return sessionStorage.getItem(KUNCI_NANTI) === "1";
  } catch {
    return false;
  }
};

/**
 * Muncul sekali untuk akun (baru atau lama) yang belum punya departemen.
 * Yang disimpan selalu jenjang staf; naik jenjang atau pindah tetap lewat admin.
 */
export function PilihDepartemen() {
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString();
  const [ditunda, setDitunda] = useState(sudahDitunda);
  const [terpilih, setTerpilih] = useState<string | null>(null);
  const [menyimpan, setMenyimpan] = useState(false);

  const { data, mutate } = useSWR(slug ? `PENEMPATAN_SAYA:${slug}` : null, () =>
    penempatanService.saya(slug as string)
  );

  if (!slug || !data?.perlu_pilih || ditunda) return null;

  const simpan = async () => {
    if (!terpilih) return;
    setMenyimpan(true);
    try {
      await penempatanService.pilih(slug, terpilih);
      await mutate({ perlu_pilih: false, departemen: [] }, { revalidate: false });
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Departemen tersimpan", message: "Anda terdaftar sebagai staf." });
    } catch (e) {
      const galat = (e as { error?: string } | undefined)?.error;
      setToast({ type: TOAST_TYPE.ERROR, title: "Gagal menyimpan", message: galat ?? "Coba lagi sebentar." });
    } finally {
      setMenyimpan(false);
    }
  };

  const nanti = () => {
    try {
      sessionStorage.setItem(KUNCI_NANTI, "1");
    } catch {
      // sessionStorage bisa diblokir; penundaan cukup untuk layar ini.
    }
    setDitunda(true);
  };

  // Dikelompokkan per divisi supaya daftar panjang tetap terbaca.
  const perDivisi = data.departemen.reduce<Record<string, typeof data.departemen>>((acc, d) => {
    (acc[d.divisi] ??= []).push(d);
    return acc;
  }, {});

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="pilih-departemen-judul"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    >
      <div className="shadow-xl flex max-h-[85vh] w-full max-w-md flex-col gap-4 rounded-lg border border-subtle bg-surface-1 p-5">
        <div>
          <h2 id="pilih-departemen-judul" className="text-lg font-semibold">
            Pilih departemen Anda
          </h2>
          <p className="text-sm mt-1 text-secondary">
            Akun Anda belum ditempatkan. Pilih departemen tempat Anda bekerja; Anda terdaftar sebagai staf. Perubahan
            jabatan atau pindah departemen dilakukan admin.
          </p>
        </div>
        <div className="flex flex-col gap-3 overflow-y-auto">
          {Object.entries(perDivisi).map(([divisi, daftar]) => (
            <fieldset key={divisi} className="flex flex-col gap-1">
              <legend className="text-xs mb-1 font-medium tracking-wide text-tertiary uppercase">{divisi}</legend>
              {daftar.map((d) => (
                <label
                  key={d.id}
                  className={`text-sm flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 ${
                    terpilih === d.id ? "border-accent-strong bg-accent-subtle" : "border-subtle hover:bg-layer-1"
                  }`}
                >
                  <input
                    type="radio"
                    name="departemen"
                    value={d.id}
                    checked={terpilih === d.id}
                    onChange={() => setTerpilih(d.id)}
                  />
                  <span>{d.nama}</span>
                </label>
              ))}
            </fieldset>
          ))}
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={nanti} disabled={menyimpan}>
            Nanti saja
          </Button>
          <Button variant="primary" onClick={() => void simpan()} disabled={!terpilih || menyimpan}>
            {menyimpan ? "Menyimpan…" : "Simpan"}
          </Button>
        </div>
      </div>
    </div>
  );
}
