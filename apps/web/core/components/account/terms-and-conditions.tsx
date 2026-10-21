/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
import type { EAuthModes } from "@plane/constants";

interface TermsAndConditionsProps {
  authType?: EAuthModes;
}

// Dulu menautkan ke syarat layanan & kebijakan privasi plane.so. Itu keliru di
// sini: karyawan PT Paradise Perkasa bukan pelanggan Plane, jadi menyuruh mereka
// menyetujui syarat vendor yang tidak melayani mereka justru menyesatkan.
// Diganti pernyataan internal, tanpa tautan keluar.
export function TermsAndConditions({ authType: _authType }: TermsAndConditionsProps) {
  return (
    <div className="flex items-center justify-center">
      <p className="text-center text-13 whitespace-pre-line text-tertiary">
        Sistem internal PT Paradise Perkasa.{"\n"}Penggunaan tunduk pada kebijakan perusahaan.
      </p>
    </div>
  );
}
