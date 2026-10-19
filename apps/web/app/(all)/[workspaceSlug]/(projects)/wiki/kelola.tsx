/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kelola folder Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { Trash2 } from "lucide-react";
import { Button } from "@plane/propel/button";
import { EmojiIconPickerTypes, EmojiPicker, Logo } from "@plane/propel/emoji-icon-picker";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TLogoProps, TPage } from "@plane/types";
import { EModalPosition, EModalWidth, ModalCore } from "@plane/ui";
import { getPageName } from "@plane/utils";
// services
import { ProjectPageService } from "@/services/page";
import { WikiAccessService, type TWikiPermissions } from "@/services/wiki_access.service";
import { WikiFolderService } from "@/services/wiki_material.service";

const layananFolder = new WikiFolderService();
const layananHalaman = new ProjectPageService();
const layananAkses = new WikiAccessService();

type TProps = {
  workspaceSlug: string;
  projectId: string;
  folder: TPage;
  izin: TWikiPermissions | undefined;
  isOpen: boolean;
  onClose: () => void;
  /** Dipanggil sesudah ada yang berubah, supaya pemanggilnya memuat ulang. */
  onBerubah: () => void | Promise<unknown>;
  /** Dipanggil sesudah folder benar-benar dihapus. */
  onTerhapus: () => void;
};

/**
 * Satu tempat untuk mengurus sebuah folder Wiki: nama, ikon, siapa
 * pengelolanya, dan menghapusnya.
 *
 * Sebelum ini pengaturan divisi pemilik HANYA ada di Setelan project Wiki, dan
 * begitu Wiki punya rutenya sendiri, tidak ada lagi jalan ke sana. Jadi Super
 * Admin sekalipun tidak bisa mengubah akses walau izinnya memang ada. Itu bukan
 * bug izin, itu jalan yang saya putus sendiri, dan panel inilah gantinya.
 */
export function KelolaFolder({
  workspaceSlug,
  projectId,
  folder,
  izin,
  isOpen,
  onClose,
  onBerubah,
  onTerhapus,
}: TProps) {
  const [nama, setNama] = useState(getPageName(folder.name));
  const [sedangSimpan, setSedangSimpan] = useState(false);
  const [sedangHapus, setSedangHapus] = useState(false);
  const [konfirmasiHapus, setKonfirmasiHapus] = useState(false);
  const [ikonTerbuka, setIkonTerbuka] = useState(false);

  const adalahDivisi = !folder.parent;
  const bolehAturDivisi = adalahDivisi && !!izin?.is_project_admin;
  const izinFolder = izin?.folders.find((f) => f.id === folder.id);
  const pemilikSekarang = new Set((izinFolder?.divisions ?? []).map((d) => d.id));
  const terbuka = !!izinFolder?.is_general;

  const galat = (error: unknown, cadangan: string) =>
    setToast({
      type: TOAST_TYPE.ERROR,
      title: "Gagal",
      message: (error as { error?: string })?.error || cadangan,
    });

  const simpanNama = async () => {
    const bersih = nama.trim();
    if (!bersih || bersih === getPageName(folder.name) || !folder.id) return;
    setSedangSimpan(true);
    try {
      await layananFolder.rename(workspaceSlug, projectId, folder.id, bersih);
      await onBerubah();
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Nama diganti", message: bersih });
    } catch (error) {
      galat(error, "Nama folder gagal diganti.");
    } finally {
      setSedangSimpan(false);
    }
  };

  const gantiIkon = async (nilai: {
    type: (typeof EmojiIconPickerTypes)[keyof typeof EmojiIconPickerTypes];
    value: unknown;
  }) => {
    if (!folder.id) return;
    const isi = nilai.type === EmojiIconPickerTypes.EMOJI ? { value: nilai.value, url: undefined } : nilai.value;
    const logoProps = { in_use: nilai.type, [nilai.type]: isi } as TLogoProps;
    try {
      await layananFolder.setLogo(workspaceSlug, projectId, folder.id, logoProps);
      await onBerubah();
    } catch (error) {
      galat(error, "Ikon gagal diganti.");
    }
  };

  const aturPemilik = async (divisionId: string, dicentang: boolean) => {
    if (!folder.id) return;
    // Endpoint ini MENGGANTI seluruh daftar, bukan menambah satu per satu, jadi
    // yang dikirim harus keadaan akhir yang diinginkan. Mengirim satu id saja
    // akan mencabut semua pemilik lainnya.
    const berikutnya = dicentang
      ? [...pemilikSekarang, divisionId]
      : [...pemilikSekarang].filter((id) => id !== divisionId);
    try {
      await layananAkses.setFolderDivisions(workspaceSlug, projectId, folder.id, berikutnya);
      await onBerubah();
    } catch (error) {
      galat(error, "Divisi pengelola gagal disimpan.");
    }
  };

  const hapus = async () => {
    if (!folder.id || sedangHapus) return;
    setSedangHapus(true);
    try {
      // Dua langkah lewat endpoint halaman yang sudah ada, BUKAN jalan pintas
      // sendiri. Di situlah ketiga penjaga struktur hidup: folder berisi materi
      // orang lain tidak boleh diarsipkan sembarangan, dan folder yang masih
      // berisi tidak boleh dihapus sama sekali.
      await layananHalaman.archive(workspaceSlug, projectId, folder.id);
      await layananHalaman.remove(workspaceSlug, projectId, folder.id);
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Folder dihapus", message: getPageName(folder.name) });
      onTerhapus();
    } catch (error) {
      galat(error, "Folder gagal dihapus.");
    } finally {
      setSedangHapus(false);
      setKonfirmasiHapus(false);
    }
  };

  return (
    <ModalCore isOpen={isOpen} handleClose={onClose} position={EModalPosition.CENTER} width={EModalWidth.XXL}>
      <div className="space-y-6 p-6">
        <div>
          <h2 className="text-lg font-semibold text-primary">Kelola {adalahDivisi ? "divisi" : "topik"}</h2>
          <p className="mt-1 text-12 text-tertiary">
            Perubahan di sini langsung berlaku untuk semua orang yang membuka Wiki.
          </p>
        </div>

        {/* Nama dan ikon */}
        <div className="space-y-2">
          <label htmlFor="wiki-nama-folder" className="text-12 font-medium text-secondary">
            Nama dan ikon
          </label>
          <div className="flex items-center gap-2">
            <EmojiPicker
              isOpen={ikonTerbuka}
              handleToggle={setIkonTerbuka}
              closeOnSelect
              label={
                <span className="grid size-9 shrink-0 place-items-center rounded-md border border-subtle bg-layer-2">
                  {folder.logo_props?.in_use ? (
                    <Logo logo={folder.logo_props} size={18} type="lucide" />
                  ) : (
                    <span className="text-12 text-tertiary">ikon</span>
                  )}
                </span>
              }
              onChange={(nilai) => void gantiIkon(nilai)}
              defaultOpen={EmojiIconPickerTypes.EMOJI}
            />
            <input
              id="wiki-nama-folder"
              type="text"
              value={nama}
              onChange={(e) => setNama(e.target.value)}
              className="flex-1 rounded-md border border-subtle bg-layer-2 px-3 py-2 text-13 text-primary outline-none focus:border-accent-strong"
            />
            <Button variant="primary" size="sm" onClick={simpanNama} loading={sedangSimpan}>
              Simpan
            </Button>
          </div>
        </div>

        {/* Siapa yang boleh mengisi */}
        {adalahDivisi && (
          <div className="space-y-2">
            <p className="text-12 font-medium text-secondary">Siapa yang boleh menaruh materi</p>
            {bolehAturDivisi ? (
              <div className="space-y-2 rounded-md border border-subtle p-3">
                <label className="flex items-center gap-2 text-12 font-medium text-secondary">
                  <input
                    type="checkbox"
                    checked={terbuka}
                    onChange={(e) =>
                      izin?.general_division_id && void aturPemilik(izin.general_division_id, e.target.checked)
                    }
                    className="size-3.5"
                  />
                  Terbuka untuk semua karyawan (General)
                </label>
                <div className="flex flex-wrap gap-x-4 gap-y-1.5 border-t border-subtle pt-2">
                  {(izin?.available_divisions ?? []).map((d) => (
                    <label
                      key={d.id}
                      title={d.name}
                      className={`flex items-center gap-1.5 text-11 ${terbuka ? "text-placeholder" : "text-secondary"}`}
                    >
                      <input
                        type="checkbox"
                        checked={pemilikSekarang.has(d.id)}
                        onChange={(e) => void aturPemilik(d.id, e.target.checked)}
                        className="size-3.5"
                      />
                      {d.identifier}
                    </label>
                  ))}
                </div>
                <p className="text-11 text-tertiary">
                  Membaca tetap terbuka untuk semua orang. Yang diatur di sini hanya siapa yang boleh menaruh materi
                  baru. Materi yang sudah ada tetap hanya bisa diubah atau dihapus pengunggahnya, kepala divisi
                  pengelola, atau Super Admin.
                </p>
              </div>
            ) : (
              <p className="rounded-md border border-subtle px-3 py-2 text-12 text-tertiary">
                {izinFolder?.is_general
                  ? "Terbuka untuk semua karyawan."
                  : izinFolder?.divisions.length
                    ? `Dikelola ${izinFolder.divisions.map((d) => d.name).join(", ")}.`
                    : "Belum ada divisi pengelola, jadi folder ini terkunci."}{" "}
                Hanya admin project Wiki dan Super Admin yang bisa mengubahnya.
              </p>
            )}
          </div>
        )}

        {/* Hapus */}
        <div className="space-y-2 border-t border-subtle pt-4">
          {konfirmasiHapus ? (
            <div className="rounded-md border border-danger-strong bg-danger-subtle p-3">
              <p className="text-12 text-primary">
                Hapus <span className="font-semibold">{getPageName(folder.name)}</span>? Folder yang masih berisi tidak
                bisa dihapus, jadi pindahkan atau hapus isinya dulu.
              </p>
              <div className="mt-3 flex gap-2">
                <Button variant="error-fill" size="sm" onClick={hapus} loading={sedangHapus}>
                  Ya, hapus
                </Button>
                <Button variant="secondary" size="sm" onClick={() => setKonfirmasiHapus(false)}>
                  Batal
                </Button>
              </div>
            </div>
          ) : (
            <Button variant="error-outline" size="sm" onClick={() => setKonfirmasiHapus(true)}>
              <Trash2 className="size-3.5" />
              Hapus {adalahDivisi ? "divisi" : "topik"} ini
            </Button>
          )}
        </div>
      </div>
    </ModalCore>
  );
}
