/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: ikon aksi baris orang di Struktur organisasi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { ArrowDownToLine, ArrowUpToLine, UserMinus } from "lucide-react";

/** Satu ikon per aksi, supaya naik/turun/cabut terlihat sama di semua panel. */
export const IKON_AKSI = { naik: ArrowUpToLine, turun: ArrowDownToLine, cabut: UserMinus };
