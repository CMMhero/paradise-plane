/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: project Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Wiki disimpan sebagai project biasa ber-identifier `WIKI`, tapi bagi pengguna
 * ia bukan project: ia punya rute `/wiki` sendiri di sidebar workspace. Jadi
 * project ini disembunyikan dari daftar project di sidebar dan halaman Projects.
 * UUID-nya berbeda di tiap instance, karena itu dikenali lewat identifier.
 */
export const WIKI_PROJECT_IDENTIFIER = "WIKI";

export const isWikiProject = (project: { identifier?: string } | undefined | null): boolean =>
  project?.identifier === WIKI_PROJECT_IDENTIFIER;
