/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Paradise (KEP-91): label kanal (#umum) dan work item (#PRJ-12) yang sudah pernah terlihat.
// Dipakai editor untuk renderText/markdown yang sinkron; kalau belum ada, jatuh ke id.
const labels = new Map<string, string>();

const keyOf = (entityName: string, id: string) => `${entityName}:${id}`;

export const setRujukanLabel = (entityName: string, id: string, label: string) => {
  labels.set(keyOf(entityName, id), label);
};

export const getRujukanLabel = (entityName: string, id: string): string | undefined =>
  labels.get(keyOf(entityName, id));
