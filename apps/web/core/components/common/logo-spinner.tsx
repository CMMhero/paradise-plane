/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// assets
import ParadiseLogo from "@/app/assets/images/paradise-logo.png?url";

export function LogoSpinner() {
  return (
    <div className="flex items-center justify-center">
      <div className="relative flex size-12 items-center justify-center sm:size-16">
        <span
          className="absolute inset-0 animate-spin rounded-full border-2 border-[#ED1F24]/20 border-t-[#ED1F24]"
          style={{ animationDuration: "0.9s" }}
        />
        <img src={ParadiseLogo} alt="Paradise Perkasa" className="size-6 animate-pulse object-contain sm:size-9" />
      </div>
    </div>
  );
}
