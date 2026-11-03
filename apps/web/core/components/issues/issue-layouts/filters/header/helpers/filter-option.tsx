/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Checkbox } from "@plane/ui";

type Props = {
  icon?: React.ReactNode;
  isChecked: boolean;
  title: React.ReactNode;
  onClick?: () => void;
  multiple?: boolean;
  activePulse?: boolean;
};

export function FilterOption(props: Props) {
  const { icon, isChecked, multiple = true, onClick, title, activePulse = false } = props;

  return (
    <button
      type="button"
      className="flex w-full items-center gap-2 rounded-item p-1.5 hover:bg-layer-transparent-hover"
      onClick={onClick}
    >
      {/* Paradise (KEP-64): indikator memakai Checkbox bersama; klik ditangani tombol induk. */}
      <Checkbox
        checked={isChecked}
        shape={multiple ? "square" : "circle"}
        readOnly
        tabIndex={-1}
        aria-hidden
        containerClassName="pointer-events-none"
      />
      <div className="flex items-center gap-2 truncate">
        {icon && <div className="grid w-5 flex-shrink-0 place-items-center">{icon}</div>}
        <div className="flex-grow truncate text-caption-sm-regular text-secondary">{title}</div>
      </div>
      {activePulse && (
        <div className="ml-auto h-2 w-2 flex-shrink-0 animate-pulse rounded-full bg-accent-primary text-caption-sm-regular" />
      )}
    </button>
  );
}
