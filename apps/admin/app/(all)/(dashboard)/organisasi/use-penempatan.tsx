/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: penempatan optimis untuk papan organisasi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu jalan untuk semua seretan dan pilihan menu papan:
 * 1. cache pohon + hierarki diperbarui optimis (papan langsung berubah);
 * 2. POST /api/instances/hierarki/;
 * 3. gagal = kembalikan potret cache (kalau tidak ada operasi lain yang masih
 *    berjalan; kalau ada, biar revalidasi yang membetulkan) + toast galat server;
 * 4. selalu muat ulang SEMUA kunci terkait (Jebakan L4), bukan cuma dua kunci ini.
 * Toast sukses membawa tombol Undo yang mengirim posisi lama orang itu.
 */

import { useRef } from "react";
import type { KeyedMutator } from "swr";
// plane imports
import { Button } from "@plane/propel/button";
import { dismissToast, setToast, TOAST_TYPE, updateToast } from "@plane/propel/toast";
import {
  InstanceHierarkiService,
  TINGKAT_MEMBER,
  type TAnggotaHierarki,
  type THierarkiResponse,
  type TPohonOrganisasi,
} from "@plane/services";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import {
  badanPulihkan,
  namaJenjang,
  posisiDari,
  terapkanKeHierarki,
  terapkanKePohon,
  type TRencana,
} from "./papan-logika";
import { pesanGagalSimpan } from "./util";

const hierarkiService = new InstanceHierarkiService();

type TKirim = Extract<TRencana, { hasil: "kirim" }>;

export function usePenempatanOptimis({
  mutatePohon,
  mutateHierarki,
  muatUlangSemua,
}: {
  mutatePohon: KeyedMutator<TPohonOrganisasi>;
  mutateHierarki: KeyedMutator<THierarkiResponse>;
  /** Revalidasi semua kunci SWR yang membawa penempatan/jenjang. */
  muatUlangSemua: () => Promise<unknown>;
}) {
  const { s, fill } = useGodmodeStrings();
  const berjalan = useRef(0);
  /** Sesudah cabut: jenjangnya tetap, atau jatuh ke Staf karena tak ada tempat tersisa (KEP-86). */
  const pesanCabut = (akhir: number) =>
    akhir === TINGKAT_MEMBER
      ? s.org.board.level_dropped
      : fill(s.org.board.level_kept, { level: namaJenjang(akhir, s) });

  const jalankan = async (o: TAnggotaHierarki, rencana: TKirim, judul: string, bisaUndo = true): Promise<boolean> => {
    let potretPohon: TPohonOrganisasi | undefined;
    let potretHierarki: THierarkiResponse | undefined;
    berjalan.current += 1;
    await Promise.all([
      mutatePohon(
        (kini) => {
          potretPohon = kini;
          return kini ? terapkanKePohon(kini, o, rencana.sesudah) : kini;
        },
        { revalidate: false }
      ),
      mutateHierarki(
        (kini) => {
          potretHierarki = kini;
          return kini ? terapkanKeHierarki(kini, o.id, rencana.sesudah) : kini;
        },
        { revalidate: false }
      ),
    ]);
    try {
      const hasil = await hierarkiService.setel({ member_id: o.id, ...rencana.badan });
      const pesan =
        hasil.member.divisi_dilepas.length > 0
          ? s.org.level_saved_divisions_released
          : (hasil.member.departemen_dilepas?.length ?? 0) > 0
            ? s.org.board.departments_released
            : rencana.mode === "lepas"
              ? pesanCabut(hasil.member.tingkat ?? rencana.sesudah.tingkat)
              : undefined;
      const id = setToast({ type: TOAST_TYPE.SUCCESS, title: judul, message: pesan });
      // Tombol Undo dipasang sesudah id toast diketahui, supaya bisa menutup toastnya sendiri.
      if (bisaUndo && id)
        updateToast(id, {
          type: TOAST_TYPE.SUCCESS,
          title: judul,
          message: pesan,
          actionItems: (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                dismissToast(id);
                void jalankan(
                  o,
                  { hasil: "kirim", mode: "pindah", badan: badanPulihkan(o), sesudah: posisiDari(o) },
                  s.org.board.undone,
                  false
                );
              }}
            >
              {s.org.board.undo}
            </Button>
          ),
        });
      return true;
    } catch (err) {
      if (berjalan.current === 1) {
        await Promise.all([
          mutatePohon(potretPohon, { revalidate: false }),
          mutateHierarki(potretHierarki, { revalidate: false }),
        ]);
      }
      setToast({
        type: TOAST_TYPE.ERROR,
        title: s.org.failed,
        message: pesanGagalSimpan(err, s.org.save_failed_message, s.org.session_expired),
      });
      return false;
    } finally {
      berjalan.current -= 1;
      await muatUlangSemua();
    }
  };

  return jalankan;
}
