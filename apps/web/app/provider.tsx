/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { lazy, Suspense } from "react";
import { useTheme } from "next-themes";
import { SWRConfig } from "swr";
// Plane Imports
import { WEB_SWR_CONFIG } from "@plane/constants";
import { TranslationProvider } from "@plane/i18n";
import { Toast } from "@plane/propel/toast";
// helpers
import { resolveGeneralTheme } from "@plane/utils";
// components
import { ImageGalleryI18nProvider } from "@/components/common/image-gallery/provider";
// mobx store provider
import { StoreProvider } from "@/lib/store-context";

// lazy imports
const AppProgressBar = lazy(function AppProgressBar() {
  return import("@/lib/b-progress/AppProgressBar");
});

const StoreWrapper = lazy(function StoreWrapper() {
  return import("@/lib/wrappers/store-wrapper");
});

const InstanceWrapper = lazy(function InstanceWrapper() {
  return import("@/lib/wrappers/instance-wrapper");
});

/**
 * Jendela dianggap "terlihat" hanya saat tab tampak DAN jendelanya berfokus.
 * SWR memakai ini untuk menunda `refreshInterval`, jadi polling berhenti saat
 * orang beralih ke aplikasi lain, bukan hanya saat tab tersembunyi. Tinggal di
 * sini, bukan di `@plane/constants`, karena paket itu tidak memuat tipe DOM.
 */
const SWR_CONFIG = {
  ...WEB_SWR_CONFIG,
  isVisible: () => document.visibilityState !== "hidden" && document.hasFocus(),
};

export interface IAppProvider {
  children: React.ReactNode;
}

export function AppProvider(props: IAppProvider) {
  const { children } = props;
  // themes
  const { resolvedTheme } = useTheme();

  return (
    <StoreProvider>
      <>
        <AppProgressBar />
        <TranslationProvider>
          <Toast theme={resolveGeneralTheme(resolvedTheme)} />
          <ImageGalleryI18nProvider>
            <StoreWrapper>
              <InstanceWrapper>
                <Suspense>
                  <SWRConfig value={SWR_CONFIG}>{children}</SWRConfig>
                </Suspense>
              </InstanceWrapper>
            </StoreWrapper>
          </ImageGalleryI18nProvider>
        </TranslationProvider>
      </>
    </StoreProvider>
  );
}
