/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu berkas untuk lampiran work item
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

const UUID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
const ATTACHMENT_PATH = new RegExp(
  `^/api/assets/v2/workspaces/[^/]+/projects/${UUID}/issues/${UUID}/attachments/${UUID}/?$`,
  "i"
);

/**
 * `src` for a file card when `href` is a work item attachment served by this
 * app's API, else null. Only the API origin (or the page's own, when the API
 * sits behind the same host) counts: a look-alike path on another site stays a
 * plain link and is never loaded into a preview frame.
 */
export const resolveAttachmentLink = (href: string, origins: { apiBaseUrl: string; pageOrigin: string }) => {
  let url: URL;
  try {
    url = new URL(href, origins.pageOrigin);
  } catch {
    return null;
  }
  const apiOrigin = origins.apiBaseUrl ? new URL(origins.apiBaseUrl, origins.pageOrigin).origin : origins.pageOrigin;
  if (url.origin !== apiOrigin && url.origin !== origins.pageOrigin) return null;
  if (url.search || url.hash || !ATTACHMENT_PATH.test(url.pathname)) return null;
  return `${origins.apiBaseUrl}${url.pathname}`;
};

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
