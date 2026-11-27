/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: jenis berkas untuk ikon kartu lampiran
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { LucideIcon } from "lucide-react";
import {
  File,
  FileArchive,
  FileCode,
  FileImage,
  FileMusic,
  FileSpreadsheet,
  FileText,
  FileVideo,
  Presentation,
} from "lucide-react";

export type TFileKind =
  | "pdf"
  | "word"
  | "excel"
  | "powerpoint"
  | "image"
  | "video"
  | "audio"
  | "archive"
  | "text"
  | "code"
  | "other";

type TFileKindSpec = {
  icon: LucideIcon;
  /** Tailwind classes, written out in full so the class scanner sees them. */
  tone: string;
  extensions: readonly string[];
  mimeTypes: readonly string[];
  mimePrefixes?: readonly string[];
};

const GREY = "bg-label-grey-bg text-label-grey-text";

/**
 * The one place that knows what a file looks like. Order matters: the first
 * spec whose extension or MIME type matches wins, so specific kinds come
 * before general ones (an SVG is an image, not code; JSON is code, not text).
 */
const FILE_KIND_SPECS: Record<Exclude<TFileKind, "other">, TFileKindSpec> = {
  pdf: {
    icon: FileText,
    tone: "bg-label-crimson-bg text-label-crimson-text",
    extensions: ["pdf"],
    mimeTypes: ["application/pdf"],
  },
  word: {
    icon: FileText,
    tone: "bg-label-indigo-bg text-label-indigo-text",
    extensions: ["doc", "docx", "odt", "rtf"],
    mimeTypes: [
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "application/vnd.oasis.opendocument.text",
      "application/rtf",
    ],
  },
  excel: {
    icon: FileSpreadsheet,
    tone: "bg-label-emerald-bg text-label-emerald-text",
    extensions: ["xls", "xlsx", "ods", "csv"],
    mimeTypes: [
      "application/vnd.ms-excel",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "application/vnd.oasis.opendocument.spreadsheet",
      "text/csv",
    ],
  },
  powerpoint: {
    icon: Presentation,
    tone: "bg-label-orange-bg text-label-orange-text",
    extensions: ["ppt", "pptx", "odp", "key"],
    mimeTypes: [
      "application/vnd.ms-powerpoint",
      "application/vnd.openxmlformats-officedocument.presentationml.presentation",
      "application/vnd.oasis.opendocument.presentation",
    ],
  },
  image: {
    icon: FileImage,
    tone: "bg-label-pink-bg text-label-pink-text",
    extensions: ["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "heic", "avif"],
    mimeTypes: [],
    mimePrefixes: ["image/"],
  },
  video: {
    icon: FileVideo,
    tone: "bg-label-purple-bg text-label-purple-text",
    extensions: ["mp4", "webm", "mov", "mkv", "avi", "ogv", "m4v"],
    mimeTypes: [],
    mimePrefixes: ["video/"],
  },
  audio: {
    icon: FileMusic,
    tone: "bg-label-purple-bg text-label-purple-text",
    extensions: ["mp3", "wav", "m4a", "flac", "ogg", "aac", "opus"],
    mimeTypes: [],
    mimePrefixes: ["audio/"],
  },
  archive: {
    icon: FileArchive,
    tone: "bg-label-yellow-bg text-label-yellow-text",
    extensions: ["zip", "rar", "7z", "tar", "gz", "tgz", "bz2", "xz"],
    mimeTypes: [
      "application/zip",
      "application/x-zip-compressed",
      "application/vnd.rar",
      "application/x-rar-compressed",
      "application/x-7z-compressed",
      "application/x-tar",
      "application/gzip",
      "application/x-gzip",
    ],
  },
  code: {
    icon: FileCode,
    tone: GREY,
    extensions: ["json", "xml", "yaml", "yml", "js", "ts", "tsx", "jsx", "py", "html", "css", "sql", "sh"],
    mimeTypes: ["application/json", "application/xml", "text/xml", "text/javascript", "text/css", "application/x-sql"],
  },
  text: {
    icon: FileText,
    tone: GREY,
    extensions: ["txt", "md", "log"],
    mimeTypes: ["text/plain", "text/markdown"],
  },
};

const OTHER_SPEC: Pick<TFileKindSpec, "icon" | "tone"> = { icon: File, tone: GREY };

const extensionOf = (name: string | null | undefined): string => {
  const base = name?.split(/[?#]/)[0] ?? "";
  return base.includes(".") ? (base.split(".").pop() ?? "").toLowerCase() : "";
};

const SPEC_ENTRIES = Object.entries(FILE_KIND_SPECS) as [Exclude<TFileKind, "other">, TFileKindSpec][];

/**
 * The extension decides first: browsers often send office files as
 * application/octet-stream, and old attachment links carry only a file name.
 */
export const getFileKind = (file: { name?: string | null; type?: string | null }): TFileKind => {
  const extension = extensionOf(file.name);
  if (extension) {
    const byExtension = SPEC_ENTRIES.find(([, spec]) => spec.extensions.includes(extension));
    if (byExtension) return byExtension[0];
  }
  const mime = (file.type ?? "").split(";")[0].trim().toLowerCase();
  if (!mime) return "other";
  const byMime = SPEC_ENTRIES.find(
    ([, spec]) => spec.mimeTypes.includes(mime) || spec.mimePrefixes?.some((prefix) => mime.startsWith(prefix))
  );
  return byMime?.[0] ?? "other";
};

export const getFileKindStyle = (kind: TFileKind): Pick<TFileKindSpec, "icon" | "tone"> =>
  kind === "other" ? OTHER_SPEC : FILE_KIND_SPECS[kind];
