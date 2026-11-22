/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: penyunting pengumuman
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Penyunting yang sama dengan kotak komentar (LiteTextEditor: pintasan
 * Markdown, daftar, kutipan, kode, tautan, sebutan), ditambah lampiran berkas.
 * Isinya disimpan sebagai Markdown di pesan kanal Announcements; berkas dan
 * gambar naik sebagai lampiran Obrolan (batas jumlah, ukuran, dan tipe dijaga
 * server), jadi tidak ada gambar sebaris. Enter = paragraf baru, Ctrl/Cmd+Enter
 * = terbitkan: pengumuman biasanya lebih dari satu baris.
 */

import { useEffect, useRef, useState } from "react";
import type { RefObject } from "react";
import { observer } from "mobx-react";
import { Paperclip, X } from "lucide-react";
// plane imports
import { TOOLBAR_ITEMS } from "@plane/editor";
import type { EditorRefApi, ToolbarMenuItem, TExtensions } from "@plane/editor";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { cn, isCommentEmpty } from "@plane/utils";
// components
import { LiteTextEditor } from "@/components/editor/lite-text";
// hooks
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUploadFailureText } from "@/hooks/use-upload-error-reporter";
// local imports
import { ukuranTerbaca } from "../chat/lampiran";
import { berkasDariTempel, seretBerkas, useUnggahLampiran } from "../chat/unggah-lampiran";

type Props = {
  slug: string;
  /** Lempar galat bila gagal; penyunting tetap berisi supaya tulisan tidak hilang. */
  onTerbit: (isi: string, lampiran: string[]) => Promise<void>;
};

// Tanpa perataan teks dan tanpa gambar sebaris: Markdown tidak punya perataan, dan
// gambar naik lewat lampiran.
const KELOMPOK_TOMBOL: ToolbarMenuItem[][] = [
  TOOLBAR_ITEMS.lite.basic,
  TOOLBAR_ITEMS.lite.list,
  TOOLBAR_ITEMS.lite.userAction,
];

// Gambar sebaris dimatikan, dan Enter dibiarkan membuat paragraf. Konstanta di luar
// komponen supaya identitasnya tetap.
const EKSTENSI_MATI: TExtensions[] = ["image", "enter-key"];
const TAMPILAN_EDITOR = { fontSize: "small-font" } as const;

const tolakUnggahSebaris = async (): Promise<never> => {
  throw new Error("inline uploads are disabled in announcements");
};

/**
 * Bilah tombol format. Hidup di komponennya sendiri: status tombol berubah di tiap
 * transaksi editor, dan kalau disimpan di penyunting induk ia merender ulang
 * LiteTextEditor tiap transaksi, yang memicu transaksi berikutnya (putaran render
 * tak berujung yang membuat halaman macet). Sama seperti IssueCommentToolbar.
 */
function BilahTombol({ editorRef, siap }: { editorRef: RefObject<EditorRefApi | null>; siap: boolean }) {
  const [aktif, setAktif] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const editor = editorRef.current;
    if (!siap || !editor) return;
    const perbarui = () => {
      const baru: Record<string, boolean> = {};
      for (const item of KELOMPOK_TOMBOL.flat()) {
        // @ts-expect-error type mismatch between toolbar item variants, same as the comment toolbar
        baru[item.renderKey] = editor.isMenuItemActive({ itemKey: item.itemKey, ...item.extraProps });
      }
      // Tanpa perubahan: jangan merender ulang.
      setAktif((lama) =>
        KELOMPOK_TOMBOL.flat().every((item) => lama[item.renderKey] === baru[item.renderKey]) ? lama : baru
      );
    };
    const lepas = editor.onStateChange(perbarui);
    perbarui();
    return () => lepas();
  }, [editorRef, siap]);

  return (
    <div className="flex flex-wrap items-center gap-0.5 rounded-sm border-[0.5px] border-subtle bg-surface-2 p-1">
      {KELOMPOK_TOMBOL.map((kelompok, i) => (
        <div
          key={kelompok[0]?.renderKey ?? "kelompok"}
          className={cn("flex items-center gap-0.5", i > 0 && "border-l border-subtle pl-1.5")}
        >
          {kelompok.map((item) => (
            <button
              key={item.renderKey}
              type="button"
              aria-label={item.name}
              aria-pressed={!!aktif[item.renderKey]}
              onClick={() =>
                // @ts-expect-error type mismatch between toolbar item variants, same as the comment toolbar
                editorRef.current?.executeMenuItemCommand({ itemKey: item.itemKey, ...item.extraProps })
              }
              className={cn(
                "grid aspect-square place-items-center rounded-xs p-1 text-placeholder hover:bg-layer-1 sentuh:p-1.5",
                aktif[item.renderKey] && "bg-layer-1 text-primary"
              )}
            >
              <item.icon className="size-3.5" strokeWidth={2.5} />
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}

export const PenyuntingPengumuman = observer(function PenyuntingPengumuman({ slug, onTerbit }: Props) {
  const { t } = useTranslation();
  const editorRef = useRef<EditorRefApi>(null);
  const berkasRef = useRef<HTMLInputElement>(null);
  const [kosong, setKosong] = useState(true);
  const [mengirim, setMengirim] = useState(false);
  // Boolean, bukan objek editornya: nilai yang sama tidak merender ulang penyunting.
  const [editorSiap, setEditorSiap] = useState(false);
  const workspaceId = useWorkspace().getWorkspaceBySlug(slug)?.id as string;
  const describeUploadFailure = useUploadFailureText();

  const { siap, naik, mengunggah, tambah, buang, kosongkan, maksJumlah } = useUnggahLampiran({
    slug,
    onTolak: (tolak, maks) => {
      const terlaluBesar = tolak.filter((x) => x.jenis === "terlalu-besar");
      setToast({
        type: TOAST_TYPE.ERROR,
        title:
          terlaluBesar.length > 0
            ? t("chatux_kelola_ui.file_too_large", { name: terlaluBesar[0].nama, size: Math.round(maks / 1024 / 1024) })
            : t("chatux_kelola_ui.too_many_files", { count: maksJumlah }),
      });
    },
    onGagal: (gagal, total, alasan) => {
      const teks = describeUploadFailure(alasan);
      if (teks.isCancelled && gagal === total) return;
      setToast({
        type: TOAST_TYPE.ERROR,
        title: gagal === total ? t("chat_ui.upload_failed_all") : t("chat_ui.upload_failed_some", { count: gagal }),
        message: teks.message || t("chat_ui.upload_failed_hint"),
      });
    },
  });

  const bisaTerbit = (!kosong || siap.length > 0) && !mengirim && !mengunggah;

  const terbitkan = async () => {
    if (!bisaTerbit) return;
    const isi = (editorRef.current?.getMarkDown() ?? "").trim();
    setMengirim(true);
    try {
      await onTerbit(
        isi,
        siap.map((l) => l.id)
      );
      editorRef.current?.clearEditor();
      setKosong(true);
      kosongkan();
    } catch {
      // Pemanggil sudah menampilkan galatnya; tulisan dan lampiran tetap ada.
    } finally {
      setMengirim(false);
    }
  };

  const pilihBerkas = (berkas: FileList | null) => {
    // Salin dulu: mengosongkan input juga mengosongkan FileList miliknya.
    const daftar = berkas ? Array.from(berkas) : null;
    if (berkasRef.current) berkasRef.current.value = "";
    void tambah(daftar);
  };

  return (
    <div
      className="flex flex-col gap-3 rounded-card border border-subtle bg-layer-1 p-3"
      // Tempel dan seret berkas = lampiran, termasuk gambar. Fase tangkap supaya
      // penyunting tidak memasangnya sebaris.
      role="presentation"
      onPasteCapture={(e) => {
        const berkas = berkasDariTempel(e.clipboardData);
        if (berkas.length === 0) return;
        e.preventDefault();
        e.stopPropagation();
        void tambah(berkas);
      }}
      onDragOverCapture={(e) => {
        if (!seretBerkas(e.dataTransfer)) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = "copy";
      }}
      onDropCapture={(e) => {
        if (!seretBerkas(e.dataTransfer)) return;
        e.preventDefault();
        e.stopPropagation();
        void tambah(e.dataTransfer.files);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
          e.preventDefault();
          void terbitkan();
        }
      }}
    >
      <BilahTombol editorRef={editorRef} siap={editorSiap} />

      <LiteTextEditor
        editable
        variant="none"
        workspaceId={workspaceId}
        workspaceSlug={slug}
        id={`pengumuman_${slug}`}
        ref={editorRef}
        handleEditorReady={setEditorSiap}
        value="<p></p>"
        initialValue="<p></p>"
        isEmpty={kosong}
        disabledExtensions={EKSTENSI_MATI}
        placeholder={t("pengumuman_ui.placeholder")}
        containerClassName="min-h-24"
        parentClassName="p-2"
        onChange={(_json, html) => setKosong(isCommentEmpty(html))}
        uploadFile={tolakUnggahSebaris}
        duplicateFile={tolakUnggahSebaris}
        displayConfig={TAMPILAN_EDITOR}
      />

      {siap.length > 0 || naik.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2">
          {siap.map((l) => (
            <span
              key={l.id}
              className="flex items-center gap-1.5 rounded-control border border-subtle px-2 py-1 text-12 text-secondary"
            >
              <span className="max-w-40 truncate">{l.nama}</span>
              <span className="text-tertiary">{ukuranTerbaca(l.ukuran)}</span>
              <button
                type="button"
                data-sentuh-lega
                onClick={() => buang(l.id)}
                aria-label={t("chat_ui.remove_named", { name: l.nama })}
                className="-m-1.5 rounded-button p-1.5 text-tertiary hover:text-primary"
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
          {naik.map((n) => (
            <span
              key={n.kunci}
              className="relative flex items-center gap-1.5 overflow-hidden rounded-control border border-subtle px-2 py-1 text-12 text-tertiary"
            >
              <span
                aria-hidden
                className="absolute inset-y-0 left-0 bg-accent-primary/10 transition-[width]"
                style={{ width: `${n.persen}%` }}
              />
              <span className="relative max-w-40 truncate">{n.nama}</span>
              <span className="relative tabular-nums">{n.persen}%</span>
              <progress
                className="sr-only"
                max={100}
                value={n.persen}
                aria-label={t("chatux_kelola_ui.uploading_named", { name: n.nama })}
              />
            </span>
          ))}
        </div>
      ) : null}

      <div className="flex items-center justify-between gap-2">
        <input ref={berkasRef} type="file" multiple hidden onChange={(e) => pilihBerkas(e.target.files)} />
        <Button
          type="button"
          variant="ghost"
          size="base"
          onClick={() => berkasRef.current?.click()}
          disabled={mengunggah}
          prependIcon={<Paperclip className="size-3.5" />}
        >
          {t("chat_ui.attach_file")}
        </Button>
        <Button
          variant="primary"
          size="base"
          onClick={() => void terbitkan()}
          disabled={!bisaTerbit}
          loading={mengirim}
        >
          {t("pengumuman_ui.send")}
        </Button>
      </div>
    </div>
  );
});
