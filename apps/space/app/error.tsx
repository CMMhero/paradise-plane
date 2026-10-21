/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// ui
import { Button } from "@plane/propel/button";

// Di luar komponen: tidak menangkap variabel apa pun dari scope induk, jadi
// tidak perlu dibuat ulang tiap render.
const handleRetry = () => {
  window.location.reload();
};

function ErrorPage() {
  return (
    <div className="grid h-screen place-items-center bg-surface-1 p-4">
      <div className="space-y-8 text-center">
        <div className="space-y-2">
          <h3 className="text-16 font-semibold">Terjadi kesalahan</h3>
          <p className="mx-auto text-13 text-secondary md:w-1/2">
            Coba muat ulang halaman. Kalau masalahnya terus berulang, hubungi tim IT internal.
          </p>
        </div>
        <div className="flex items-center justify-center gap-2">
          <Button variant="primary" size="lg" onClick={handleRetry}>
            Refresh
          </Button>
          {/* <Button variant="secondary" size="lg" onClick={() => {}}>
            Sign out
          </Button> */}
        </div>
      </div>
    </div>
  );
}

export default ErrorPage;
