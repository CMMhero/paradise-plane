/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pratinjau semua email di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Daftar email di kiri, isinya di kanan dalam iframe ber-sandbox (tanpa skrip,
 * tautan dibuka di tab baru). Server merender lewat fungsi yang SAMA dengan
 * pengirim sungguhan dan tidak pernah membuka SMTP, jadi halaman ini aman
 * dibuka kapan saja. Lebar 600/375 px meniru kotak masuk desktop dan ponsel.
 */

import { useState } from "react";
import { ExternalLink, Paperclip } from "lucide-react";
import useSWR from "swr";
// plane imports
import { Button } from "@plane/propel/button";
import { InstanceEmailPreviewService, type TEmailPreviewLang } from "@plane/services";
import { Loader } from "@plane/ui";
import { cn } from "@plane/utils";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
import { StateBox } from "@/components/common/paradise";
import { EmailTabs } from "@/components/common/section-tabs";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
// types
import type { Route } from "./+types/page";

const service = new InstanceEmailPreviewService();

type TTampilan = "html" | "text";
type TLebar = "desktop" | "mobile";

const LEBAR_PX: Record<TLebar, number> = { desktop: 640, mobile: 375 };
const SKELETON = ["a", "b", "c", "d", "e", "f", "g", "h"];

type TPilihan<T extends string> = { value: T; label: string };

/** Pilihan kecil bergaya pil, sama dengan pilihan di menu Display tabel. */
function Pilihan<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: TPilihan<T>[];
  onChange: (v: T) => void;
}) {
  return (
    <fieldset className="m-0 flex items-center gap-1 border-0 p-0">
      <legend className="sr-only">{label}</legend>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={value === o.value}
          onClick={() => onChange(o.value)}
          className={cn("rounded-control border px-2.5 py-1 text-12 font-medium transition-colors", {
            "border-accent-strong bg-accent-primary text-on-color": value === o.value,
            "border-subtle text-secondary hover:bg-layer-1": value !== o.value,
          })}
        >
          {o.label}
        </button>
      ))}
    </fieldset>
  );
}

const EmailPreviewPage = function EmailPreviewPage(_props: Route.ComponentProps) {
  const { s, fill } = useGodmodeStrings();
  const t = s.email_preview;
  const [lang, setLang] = useState<TEmailPreviewLang>("id");
  const [kunci, setKunci] = useState<string | null>(null);
  const [tampilan, setTampilan] = useState<TTampilan>("html");
  const [lebar, setLebar] = useState<TLebar>("desktop");

  const daftar = useSWR(["EMAIL_PREVIEW_LIST", lang], () => service.list(lang), { revalidateOnFocus: false });
  const pilihan = kunci ?? daftar.data?.results[0]?.key ?? null;
  const isi = useSWR(
    pilihan ? ["EMAIL_PREVIEW", pilihan, lang] : null,
    ([, k, l]: [string, string, TEmailPreviewLang]) => service.retrieve(k, l),
    {
      revalidateOnFocus: false,
      keepPreviousData: true,
    }
  );

  const bukaTab = () => {
    if (!isi.data) return;
    const url = URL.createObjectURL(new Blob([isi.data.html], { type: "text/html" }));
    window.open(url, "_blank", "noopener");
    // Beri waktu tab baru memuat sebelum URL dilepas.
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  };

  return (
    <PageWrapper header={{ title: t.title, description: t.description }}>
      <EmailTabs />
      <div className="mb-4 flex flex-wrap items-center gap-x-6 gap-y-3">
        <Pilihan
          label={t.language}
          value={lang}
          onChange={setLang}
          options={[
            { value: "id", label: t.lang_id },
            { value: "en", label: t.lang_en },
          ]}
        />
        <Pilihan
          label={t.view_html}
          value={tampilan}
          onChange={setTampilan}
          options={[
            { value: "html", label: t.view_html },
            { value: "text", label: t.view_text },
          ]}
        />
        {tampilan === "html" && (
          <Pilihan
            label={t.width}
            value={lebar}
            onChange={setLebar}
            options={[
              { value: "desktop", label: t.width_desktop },
              { value: "mobile", label: t.width_mobile },
            ]}
          />
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
        <nav aria-label={t.templates} className="rounded-card border border-subtle">
          <div className="border-b border-subtle px-3 py-2 text-11 font-medium text-tertiary">
            {daftar.data ? fill(t.count, { n: daftar.data.results.length }) : t.templates}
          </div>
          {daftar.error ? (
            <div className="p-3">
              <StateBox tone="danger">{t.list_failed}</StateBox>
            </div>
          ) : !daftar.data ? (
            <Loader className="space-y-2 p-3">
              {SKELETON.map((k) => (
                <Loader.Item key={k} height="36px" />
              ))}
            </Loader>
          ) : (
            <ul className="max-h-[70vh] overflow-y-auto p-1">
              {daftar.data.results.map((item) => (
                <li key={item.key}>
                  <button
                    type="button"
                    aria-current={item.key === pilihan ? "true" : undefined}
                    onClick={() => setKunci(item.key)}
                    className={cn("w-full rounded-control px-2.5 py-2 text-left transition-colors", {
                      "bg-layer-1 text-primary": item.key === pilihan,
                      "text-secondary hover:bg-layer-1": item.key !== pilihan,
                    })}
                  >
                    <span className="font-mono block text-11 text-tertiary">{item.key}</span>
                    <span className={cn("block truncate text-13", { "text-danger-primary": item.error })}>
                      {item.subject}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </nav>

        <section className="min-w-0 rounded-card border border-subtle">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-subtle px-4 py-2.5">
            <div className="min-w-0">
              <div className="text-11 text-tertiary">{t.subject}</div>
              <div className="truncate text-13 font-medium text-primary">{isi.data?.subject ?? " "}</div>
            </div>
            <div className="flex items-center gap-3">
              {isi.data && isi.data.attachments.length > 0 && (
                <span className="flex items-center gap-1 text-12 text-tertiary" title={t.attachments}>
                  <Paperclip className="size-3.5" aria-hidden />
                  {isi.data.attachments.join(", ")}
                </span>
              )}
              <Button variant="secondary" size="sm" onClick={bukaTab} disabled={!isi.data}>
                <ExternalLink className="size-3.5" aria-hidden />
                {t.open_tab}
              </Button>
            </div>
          </div>

          <div className="bg-layer-1 p-4">
            {!pilihan ? (
              <StateBox>{t.empty}</StateBox>
            ) : isi.error ? (
              <StateBox tone="danger">{t.render_failed}</StateBox>
            ) : !isi.data ? (
              <Loader>
                <Loader.Item height="70vh" />
              </Loader>
            ) : tampilan === "text" ? (
              <pre className="font-mono mx-auto max-w-[640px] overflow-x-auto rounded-card border border-subtle bg-surface-1 p-4 text-12 whitespace-pre-wrap text-primary">
                {isi.data.text}
              </pre>
            ) : (
              <iframe
                key={`${isi.data.key}-${isi.data.lang}`}
                title={isi.data.subject}
                srcDoc={isi.data.html}
                // Tanpa allow-scripts: HTML email tidak boleh menjalankan apa pun di God Mode.
                sandbox="allow-popups allow-popups-to-escape-sandbox"
                className={cn("mx-auto block h-[70vh] w-full rounded-card border border-subtle bg-white", {
                  "opacity-60": isi.isValidating,
                })}
                style={{ maxWidth: LEBAR_PX[lebar] }}
              />
            )}
          </div>
        </section>
      </div>
    </PageWrapper>
  );
};

export const meta: Route.MetaFunction = () => [{ title: "Email Preview - God Mode" }];

export default EmailPreviewPage;
