/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: terapkan bawaan ke member lama
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tombol terpisah dari Simpan: menimpa pilihan puluhan orang harus disengaja.
 * Server hanya menerima `navigasi` dan `work_items` (lihat
 * InstanceMemberDefaultsApplyEndpoint); bahasa dan email tetap pilihan pribadi.
 */

import { useState } from "react";
import { Button } from "@plane/propel/button";
import { setPromiseToast } from "@plane/propel/toast";
import { InstanceMemberService, type TMemberDefaultsSection } from "@plane/services";
import { AlertModalCore } from "@plane/ui";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";

const memberService = new InstanceMemberService();

type Props = {
  /** Ada draf yang belum disimpan: terapkan memakai nilai TERSIMPAN, jadi kunci dulu. */
  isDirty: boolean;
};

export function TerapkanKeSemua({ isDirty }: Props) {
  const { s, fill } = useGodmodeStrings();
  const t = s.bawaan;
  const [bagian, setBagian] = useState<TMemberDefaultsSection | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const terapkan = async () => {
    if (!bagian) return;
    setIsSubmitting(true);
    const janji = memberService.terapkanBawaan([bagian]);
    setPromiseToast(janji, {
      loading: t.applying,
      success: {
        title: t.applied,
        message: (r) => fill(t.applied_message, { count: Object.values(r.updated).reduce((a, b) => a + b, 0) }),
      },
      error: { title: t.apply_failed, message: (e) => (e as { error?: string })?.error ?? t.apply_failed },
    });
    try {
      await janji;
      setBagian(null);
    } catch {
      // Toast sudah memberi tahu; modal dibiarkan terbuka supaya bisa dicoba lagi.
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="space-y-2">
      <div className="space-y-0.5">
        <h3 className="text-11 font-medium tracking-wide text-secondary uppercase">{t.apply_title}</h3>
        <p className="text-12 text-tertiary">{isDirty ? t.apply_unsaved : t.apply_note}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" size="sm" disabled={isDirty} onClick={() => setBagian("navigasi")}>
          {t.apply_navigation}
        </Button>
        <Button variant="secondary" size="sm" disabled={isDirty} onClick={() => setBagian("work_items")}>
          {t.apply_work_items}
        </Button>
      </div>
      <AlertModalCore
        isOpen={bagian !== null}
        variant="primary"
        title={bagian === "navigasi" ? t.apply_navigation : t.apply_work_items}
        content={bagian === "navigasi" ? t.apply_confirm_navigation : t.apply_confirm_work_items}
        isSubmitting={isSubmitting}
        primaryButtonText={{ default: t.apply_yes, loading: t.applying }}
        secondaryButtonText={s.common.cancel}
        handleClose={() => setBagian(null)}
        handleSubmit={() => void terapkan()}
      />
    </section>
  );
}
