/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";

type TPageWrapperProps = {
  children: ReactNode;
  header?: {
    title: string;
    description: string | ReactNode;
    actions?: ReactNode;
  };
  customHeader?: ReactNode;
};

// Paradise: one width for every God Mode page. Pages under the same menu
// switch tabs without the layout jumping; wide tables scroll inside their own
// wrapper instead of widening the page.
export const PageWrapper = (props: TPageWrapperProps) => {
  const { children, header, customHeader } = props;

  return (
    <div className="mx-auto h-full w-full max-w-[1200px] space-y-6 py-4 md:px-4">
      {customHeader ? (
        <div className="mx-4 shrink-0 space-y-1 border-b border-subtle py-4">{customHeader}</div>
      ) : (
        header && (
          <div className="mx-4 flex shrink-0 items-center justify-between gap-4 space-y-1 border-b border-subtle py-4">
            <div className={header.actions ? "flex flex-col gap-1" : "space-y-1"}>
              <div className="text-h5-semibold text-primary">{header.title}</div>
              <div className="text-body-sm-regular text-secondary">{header.description}</div>
            </div>
            {header.actions && <div className="shrink-0">{header.actions}</div>}
          </div>
        )
      )}
      {/* Paradise: BUKAN wadah gulir. Tingginya tidak dibatasi, jadi ia tak pernah
          menggulir sendiri (yang menggulir wadah di layout dashboard), tapi
          overflow-y-scroll tetap menjadikannya induk gulir terdekat dan membunuh
          `position: sticky` di dalamnya (panel People papan Organization).
          overflow-x-clip tetap memotong konten lebar tanpa jadi wadah gulir. */}
      <div className="overflow-x-clip px-4 pb-4">{children}</div>
    </div>
  );
};
