/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: jaring pengaman pustaka Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Component, type ErrorInfo, type ReactNode } from "react";
import { Link } from "react-router";
import { useTranslation } from "@plane/i18n";

type TProps = {
  children: ReactNode;
  /** Jalan pulang ke tampilan daftar lama, yang tidak bergantung pada kode ini sama sekali. */
  tautanDaftar: string;
};

type TState = { galat: Error | null };

/**
 * Kalau pustaka Wiki jatuh, Wiki-nya jangan ikut jatuh.
 *
 * Tanpa batas ini, satu galat render di grid kartu akan naik ke batas galat
 * root dan menjatuhkan seluruh rute, sehingga 83 orang kehilangan akses ke
 * seluruh Wiki hanya karena satu kartu. Dengan batas ini, yang gagal cuma
 * susunan kartunya, dan orang tetap punya satu klik menuju tampilan daftar
 * lama yang tidak menyentuh kode baru ini sama sekali.
 *
 * Harus Class Component: React belum punya padanan fungsional untuk
 * componentDidCatch.
 */
export class BatasGalatWiki extends Component<TProps, TState> {
  state: TState = { galat: null };

  static getDerivedStateFromError(galat: Error): TState {
    return { galat };
  }

  componentDidCatch(galat: Error, info: ErrorInfo) {
    // Sengaja dicetak: tanpa ini, satu-satunya jejaknya adalah layar kosong,
    // dan laporan "Wiki-nya rusak" tanpa pesan mustahil ditelusuri.
    // oxlint-disable-next-line no-console
    console.error("Pustaka Wiki gagal dirender", galat, info.componentStack);
  }

  render() {
    if (!this.state.galat) return this.props.children;

    return <TampilanGalat tautanDaftar={this.props.tautanDaftar} />;
  }
}

// Kelas tidak bisa memakai hook, jadi teksnya diambil di komponen fungsi terpisah.
function TampilanGalat({ tautanDaftar }: { tautanDaftar: string }) {
  const { t } = useTranslation();
  return (
    <div className="flex h-full w-full items-center justify-center p-8">
      <div className="max-w-md text-center">
        <h2 className="text-15 font-semibold text-primary">{t("wiki_ui.error.title")}</h2>
        <p className="mt-1 text-13 text-tertiary">{t("wiki_ui.error.message")}</p>
        <Link
          to={tautanDaftar}
          className="mt-4 inline-block rounded-md border border-subtle px-3 py-1.5 text-12 font-medium text-secondary transition-colors hover:border-strong hover:text-primary"
        >
          {t("wiki_ui.error.open_list")}
        </Link>
      </div>
    </div>
  );
}
