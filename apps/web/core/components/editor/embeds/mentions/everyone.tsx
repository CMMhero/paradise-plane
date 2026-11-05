/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Paradise (KEP-91): chip @all, memberi tahu semua anggota project/percakapan.
export function EditorEveryoneMention() {
  return (
    <span className="not-prose inline rounded-sm bg-label-yellow-bg px-1 py-0.5 text-label-yellow-text no-underline">
      @all
    </span>
  );
}
