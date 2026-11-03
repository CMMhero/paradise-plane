/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: layar pilih departemen untuk akun yang belum ditempatkan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { useParams } from "react-router";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { RadioGroup } from "@plane/propel/radio-group";
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
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString();
  const [ditunda, setDitunda] = useState(sudahDitunda);
  const [terpilih, setTerpilih] = useState<string | null>(null);
  const [menyimpan, setMenyimpan] = useState(false);

  const { data, mutate } = useSWR(slug ? `PENEMPATAN_SAYA:${slug}` : null, () =>
    penempatanService.saya(slug as string)
  );

  const tampil = !!slug && !!data?.perlu_pilih && !ditunda;

  // Escape = "Nanti saja", sama seperti tombolnya; layar ini tidak boleh jadi
  // jalan buntu bagi yang memakai papan ketik.
  useEffect(() => {
    if (!tampil) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      try {
        sessionStorage.setItem(KUNCI_NANTI, "1");
      } catch {
        // sessionStorage bisa diblokir; penundaan cukup untuk layar ini.
      }
      setDitunda(true);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [tampil]);

  if (!tampil || !slug || !data) return null;

  const simpan = async () => {
    if (!terpilih) return;
    setMenyimpan(true);
    try {
      await penempatanService.pilih(slug, terpilih);
      await mutate({ perlu_pilih: false, departemen: [] }, { revalidate: false });
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("department_picker_ui.saved_title"),
        message: t("department_picker_ui.saved_message"),
      });
    } catch (e) {
      const galat = (e as { error?: string } | undefined)?.error;
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("department_picker_ui.save_failed"),
        message: galat ?? t("chat_ui.try_again_shortly"),
      });
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
      // oxlint-disable-next-line jsx-a11y/prefer-tag-over-role -- native <dialog> needs open/showModal and changes default styling
      role="dialog"
      aria-modal="true"
      aria-labelledby="pilih-departemen-judul"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    >
      <div className="flex max-h-[85vh] w-full max-w-md flex-col gap-4 rounded-overlay border border-subtle bg-surface-1 p-5">
        <div>
          <h2 id="pilih-departemen-judul" className="text-16 font-semibold">
            {t("department_picker_ui.title")}
          </h2>
          <p className="mt-1 text-13 text-secondary">{t("department_picker_ui.description")}</p>
        </div>
        {/* Satu grup untuk semua divisi supaya tombol panah berpindah lintas divisi. */}
        <RadioGroup
          name="departemen"
          aria-labelledby="pilih-departemen-judul"
          className="gap-3 overflow-y-auto"
          value={terpilih}
          onValueChange={setTerpilih}
        >
          {Object.entries(perDivisi).map(([divisi, daftar]) => (
            <fieldset key={divisi} className="flex flex-col gap-1">
              <legend className="mb-1 text-12 font-medium tracking-wide text-tertiary uppercase">{divisi}</legend>
              {daftar.map((d) => (
                <RadioGroup.Item
                  key={d.id}
                  value={d.id}
                  label={d.nama}
                  className="border border-subtle px-3 py-2 has-[[data-checked]]:border-accent-strong has-[[data-checked]]:bg-accent-subtle"
                />
              ))}
            </fieldset>
          ))}
        </RadioGroup>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={nanti} disabled={menyimpan}>
            {t("notification_ui.later")}
          </Button>
          <Button variant="primary" onClick={() => void simpan()} disabled={!terpilih || menyimpan}>
            {menyimpan ? t("saving") : t("save")}
          </Button>
        </div>
      </div>
    </div>
  );
}
