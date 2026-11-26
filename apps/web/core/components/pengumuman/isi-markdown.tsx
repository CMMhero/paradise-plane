/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: isi pengumuman dan pesan obrolan (Markdown)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu perender untuk halaman Pengumuman, widget Home, dan gelembung Obrolan.
 * `isi` disimpan sebagai Markdown (teks biasa, jadi pesan lama tetap terbaca):
 * satu baris baru tetap baris baru, tautan telanjang jadi tautan, HTML yang
 * diketik tetap tampil sebagai teks (lib/markdown/pesan.ts).
 *
 * react-markdown tidak pernah merender HTML mentah. Gambar tidak dimuat (alamatnya
 * bisa dari mana saja; berkas dilampirkan terpisah), dan hanya http, https, serta
 * mailto yang bisa diklik.
 */

import { createContext, memo, useContext, useMemo } from "react";
import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
// plane imports
import { cn } from "@plane/utils";
// components
import { MemberProfileTrigger } from "@/components/member-profile";
import { KOMPONEN_MARKDOWN } from "@/components/wiki/pratinjau/teks";
// lib
import { PLUGIN_DIALEK, bolehDiklik, lindungiKali, remarkBarisBaru } from "@/lib/markdown/pesan";
// pages
import { remarkRujukan } from "@/app/(all)/[workspaceSlug]/(projects)/chat/rujukan-markdown";
import type { TPil } from "@/app/(all)/[workspaceSlug]/(projects)/chat/rujukan-markdown";
import type { TSumberRujukan } from "@/app/(all)/[workspaceSlug]/(projects)/chat/sebut";

/** `kartu` = pengumuman; `gelembung` = pesan masuk; `terang` = gelembung saya, di atas warna aksen. */
export type TNadaMarkdown = "kartu" | "gelembung" | "terang";

const pilBawaan = (pil: TPil): ReactNode =>
  pil.jenis === "sebut" ? (
    <MemberProfileTrigger userId={pil.id} className="align-baseline" openOnHover>
      <span className="rounded-sm bg-accent-subtle px-1 font-semibold text-accent-primary hover:opacity-85">
        {pil.isi}
      </span>
    </MemberProfileTrigger>
  ) : (
    pil.isi
  );

const KonteksPil = createContext<(pil: TPil) => ReactNode>(pilBawaan);

/** Pil sebutan dan rujukan dari `remarkRujukan`; `span` lain lewat apa adanya. */
const Rentang: NonNullable<Components["span"]> = ({ node, children, className }) => {
  const render = useContext(KonteksPil);
  const jenis = node?.properties.dataRujukan as TPil["jenis"] | undefined;
  if (!jenis) return <span className={className}>{children}</span>;
  return render({ jenis, id: String(node?.properties.dataId ?? ""), isi: String(children) } as TPil);
};

const tautan = (className: string): NonNullable<Components["a"]> =>
  function Tautan({ href, children }) {
    // Skema lain (javascript:, data:, alamat relatif) tidak pernah jadi href.
    if (!bolehDiklik(href))
      return (
        <span>
          {children}
          {href ? ` (${href})` : null}
        </span>
      );
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        onClick={(e) => e.stopPropagation()}
        className={className}
      >
        {children}
      </a>
    );
  };

/** Judul di gelembung hanya tebal: pesan obrolan bukan bagian dari susunan judul halaman. */
const Judul = ({ children }: { children?: ReactNode }) => <p className="text-14 font-semibold">{children}</p>;

const komponen = (nada: TNadaMarkdown): Components => {
  const terang = nada === "terang";
  // Jarak antar blok: kartu memakai margin sendiri, gelembung memakai `space-y` wadahnya.
  const jarak = nada === "kartu" ? "my-2" : undefined;
  const garis = terang ? "border-white/50" : "border-strong";
  const latarKode = terang ? "bg-black/20" : "bg-layer-1";
  const Tautan = tautan(
    nada === "kartu" ? "text-accent-primary underline" : "underline underline-offset-2 hover:opacity-80"
  );
  const bersama: Components = {
    span: Rentang,
    a: Tautan,
    img: ({ src, alt }) => <Tautan href={src}>{alt || src}</Tautan>,
    ul: ({ children, className }) => (
      <ul className={cn(jarak, "list-disc pl-5", className?.includes("contains-task-list") && "list-none pl-0")}>
        {children}
      </ul>
    ),
    ol: ({ children, start }) => (
      <ol start={start} className={cn(jarak, "list-decimal pl-5")}>
        {children}
      </ol>
    ),
    table: ({ children }) => (
      <div className={cn(jarak, "max-w-full overflow-x-auto")}>
        <table className="border-collapse text-12 [overflow-wrap:normal]">{children}</table>
      </div>
    ),
    th: ({ children, style }) => (
      <th style={style} className={cn("border px-2 py-0.5 text-left font-semibold", garis)}>
        {children}
      </th>
    ),
    td: ({ children, style }) => (
      <td style={style} className={cn("border px-2 py-0.5 align-top", garis)}>
        {children}
      </td>
    ),
  };
  if (nada === "kartu") return { ...KOMPONEN_MARKDOWN, ...bersama };

  return {
    ...bersama,
    h1: Judul,
    h2: Judul,
    h3: Judul,
    h4: Judul,
    h5: Judul,
    h6: Judul,
    blockquote: ({ children }) => (
      <blockquote className={cn("space-y-1.5 border-l-2 pl-2", garis)}>{children}</blockquote>
    ),
    hr: () => <hr className="border-current opacity-30" />,
    code: ({ children }) => <code className={cn("rounded-sm px-1 font-mono text-12", latarKode)}>{children}</code>,
    pre: ({ children }) => (
      <pre
        className={cn(
          "max-w-full overflow-x-auto rounded-item p-2 font-mono text-12 [overflow-wrap:normal]",
          "[&>code]:bg-transparent [&>code]:p-0",
          latarKode
        )}
      >
        {children}
      </pre>
    ),
  };
};

// Di luar komponen supaya identitasnya tetap: komponen yang dibuat ulang tiap
// render membuat seluruh pesan dipasang ulang (kartu melayang ikut tertutup).
const KOMPONEN: Record<TNadaMarkdown, Components> = {
  kartu: komponen("kartu"),
  gelembung: komponen("gelembung"),
  terang: komponen("terang"),
};

type TProps = {
  teks: string;
  nada?: TNadaMarkdown;
  /** Yang boleh disorot sebagai sebutan atau rujukan (`muatan` pesan). */
  sumber?: TSumberRujukan;
  /** Cara menggambar pil; bawaan: sebutan membuka profil, sisanya teks. */
  renderPil?: (pil: TPil) => ReactNode;
};

export const IsiMarkdown = memo(function IsiMarkdown({ teks, nada = "kartu", sumber, renderPil }: TProps) {
  const plugin = useMemo(() => {
    // Tautan profil baru jadi pil bila menunjuk aplikasi ini; dari situs lain tetap tautan biasa.
    const asal = typeof window === "undefined" ? undefined : window.location.origin;
    const rujukan = [remarkRujukan, { ...sumber, asal }] as [typeof remarkRujukan, TSumberRujukan?];
    return [...PLUGIN_DIALEK, rujukan, remarkBarisBaru];
  }, [sumber]);
  return (
    <div
      className={cn(
        "text-13 [overflow-wrap:anywhere]",
        nada === "kartu" ? "leading-relaxed text-secondary" : "space-y-1.5"
      )}
    >
      <KonteksPil.Provider value={renderPil ?? pilBawaan}>
        <ReactMarkdown remarkPlugins={plugin} components={KOMPONEN[nada]}>
          {lindungiKali(teks)}
        </ReactMarkdown>
      </KonteksPil.Provider>
    </div>
  );
});
