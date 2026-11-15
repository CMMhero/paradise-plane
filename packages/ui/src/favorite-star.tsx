/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Star } from "lucide-react";
import React from "react";
// helpers
import { cn } from "./utils";

type Props = {
  /** Wajib: tombolnya hanya ikon bintang. Status terpilih dibacakan lewat aria-pressed. */
  ariaLabel: string;
  buttonClassName?: string;
  iconClassName?: string;
  onClick: (e: React.MouseEvent<HTMLButtonElement>) => void;
  selected: boolean;
};

export function FavoriteStar(props: Props) {
  const { ariaLabel, buttonClassName, iconClassName, onClick, selected } = props;

  return (
    <button
      type="button"
      // size-6 -m-1: sasaran 24px (WCAG 2.5.8) tanpa menggeser tata letak ikon 16px
      className={cn("-m-1 grid size-6 place-items-center", buttonClassName)}
      onClick={onClick}
      aria-label={ariaLabel}
      aria-pressed={selected}
    >
      <Star
        className={cn(
          "h-4 w-4 text-tertiary transition-all",
          {
            "fill-(--color-label-yellow-icon) stroke-(--color-label-yellow-icon)": selected,
          },
          iconClassName
        )}
      />
    </button>
  );
}
