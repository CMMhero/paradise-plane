/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pratinjau teks polos dan Markdown di Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";

/** Kotak gulir yang sama untuk semua pratinjau yang dibaca server. */
export function KotakPratinjau({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cn("overflow-auto rounded-card border border-subtle bg-layer-1 p-4", className)}>{children}</div>
  );
}

/** Keterangan di bawah pratinjau: dipotong, tampilan sederhana, dan sejenisnya. */
export function CatatanPratinjau({ children }: { children: ReactNode }) {
  return <p className="mt-2 text-12 text-tertiary">{children}</p>;
}

type TPropsIsi = { text: string; truncated?: boolean; className?: string };

/**
 * Teks polos. Dirender sebagai teks (`<pre>`), tidak pernah sebagai HTML, jadi
 * berkas .html atau .xml yang diunggah tampil sebagai kodenya, bukan dijalankan.
 */
export function PratinjauTeks({ text, truncated, className }: TPropsIsi) {
  const { t } = useTranslation();
  return (
    <>
      <KotakPratinjau className={className}>
        {text ? (
          <pre className="font-mono text-12 leading-relaxed break-words whitespace-pre-wrap text-primary">{text}</pre>
        ) : (
          <p className="text-13 text-tertiary">{t("wiki_ui.viewer.empty_text")}</p>
        )}
      </KotakPratinjau>
      {truncated && <CatatanPratinjau>{t("wiki_ui.viewer.truncated_text")}</CatatanPratinjau>}
    </>
  );
}

// Di luar komponen supaya identitasnya tetap: komponen yang dibuat ulang tiap
// render membuat seluruh dokumen Markdown dipasang ulang.
const KOMPONEN_MARKDOWN: Components = {
  h1: ({ children }) => <h1 className="mt-6 mb-2 text-20 font-semibold text-primary">{children}</h1>,
  h2: ({ children }) => <h2 className="mt-5 mb-2 text-16 font-semibold text-primary">{children}</h2>,
  h3: ({ children }) => <h3 className="mt-4 mb-1.5 text-14 font-semibold text-primary">{children}</h3>,
  h4: ({ children }) => <h4 className="mt-3 mb-1 text-13 font-semibold text-primary">{children}</h4>,
  p: ({ children }) => <p className="my-2">{children}</p>,
  ul: ({ children }) => <ul className="my-2 list-disc pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="my-2 list-decimal pl-5">{children}</ol>,
  li: ({ children }) => <li className="my-0.5">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="my-3 border-l-2 border-strong pl-3 text-tertiary">{children}</blockquote>
  ),
  hr: () => <hr className="my-4 border-subtle" />,
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="text-accent-primary underline">
      {children}
    </a>
  ),
  pre: ({ children }) => (
    <pre className="my-3 overflow-auto rounded-item bg-layer-3 p-3 font-mono text-12">{children}</pre>
  ),
  code: ({ className, children }) => (
    <code className={cn("rounded-sm bg-layer-3 px-1 font-mono text-12", className)}>{children}</code>
  ),
};

/**
 * Markdown lewat react-markdown, yang tidak merender HTML mentah. Gambar
 * dibuang: alamatnya dari unggahan orang dan akan memuat sumber luar saat
 * dibuka. Tautan dibuka di tab baru tanpa `opener`.
 */
export function PratinjauMarkdown({ text, truncated, className }: TPropsIsi) {
  const { t } = useTranslation();
  return (
    <>
      <KotakPratinjau className={className}>
        {text ? (
          <div className="mx-auto max-w-3xl text-13 leading-relaxed text-secondary">
            <ReactMarkdown disallowedElements={["img"]} components={KOMPONEN_MARKDOWN}>
              {text}
            </ReactMarkdown>
          </div>
        ) : (
          <p className="text-13 text-tertiary">{t("wiki_ui.viewer.empty_text")}</p>
        )}
      </KotakPratinjau>
      {truncated && <CatatanPratinjau>{t("wiki_ui.viewer.truncated_text")}</CatatanPratinjau>}
    </>
  );
}
