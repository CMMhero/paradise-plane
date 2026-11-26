/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu berkas untuk lampiran work item
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

const escapeHtml = (value: string) =>
  value.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

/** `<file-component>` HTML for an attachment, the same shape the editor's file node renders. */
export const attachmentCardHtml = (file: { url: string; name: string; size: number | null; type: string | null }) => {
  const attrs = [
    `src="${escapeHtml(file.url)}"`,
    `name="${escapeHtml(file.name)}"`,
    file.size !== null ? `size="${file.size}"` : "",
    file.type ? `type="${escapeHtml(file.type)}"` : "",
  ].filter(Boolean);
  return `<file-component ${attrs.join(" ")}>${escapeHtml(file.name)}</file-component>`;
};
