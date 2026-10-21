/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

type Props = {
  isSignUp?: boolean;
};

// Sama seperti versi web: tautan syarat layanan & privasi plane.so dibuang.
// Karyawan bukan pelanggan Plane; menyuruh menyetujui syarat vendor yang tidak
// melayani mereka justru menyesatkan.
export function TermsAndConditions(_props: Props) {
  return (
    <span className="flex items-center justify-center py-6">
      <p className="text-center text-13 whitespace-pre-line text-secondary">
        Sistem internal PT Paradise Perkasa.{"\n"}Penggunaan tunduk pada kebijakan perusahaan.
      </p>
    </span>
  );
}
