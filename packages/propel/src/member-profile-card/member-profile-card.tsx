/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu profil anggota (bagian bersama)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Bagian murni tampilan dari kartu profil anggota, dipakai apps/web (data dari
 * API workspace) dan apps/admin (data dari API instance admin) supaya kedua
 * kartu tidak pernah berbeda rupa. Tidak ada i18n, store, atau fetch di sini:
 * semua teks masuk lewat props.
 */

import { useState } from "react";
import type { ReactNode } from "react";
import { Building2, Mail, Phone } from "lucide-react";
import { Popover } from "../popover";
import { Tooltip } from "../tooltip";
import { cn } from "../utils/classname";

export type TMemberProfileUnit = { id: string; nama: string };

export type TMemberProfilePlacement = {
  key: string;
  /** Divisi tempat orang ini berada. */
  division: TMemberProfileUnit | null;
  /** Departemen di bawah divisi itu, kalau penempatannya sampai tingkat departemen. */
  department: TMemberProfileUnit | null;
  /** Nama jenjang yang sudah diterjemahkan (Staff, Manager, ...), atau null. */
  levelLabel: string | null;
};

export type TMemberProfileFieldLabels = {
  /** Tooltip ikon baris penempatan. */
  placement: string;
  /** Teks tombol "+N lagi" untuk `count` penempatan yang masih tersembunyi. */
  morePlacements: (count: number) => string;
  email: string;
  phoneExtension: string;
  notSet: string;
};

const POPOVER_PANEL_CLASS = "w-72 rounded-popover border-[0.5px] border-strong bg-surface-1 p-4 shadow-raised-200";

/** Satu baris data profil. Nama datanya jadi tooltip ikon, bukan teks. */
export function MemberProfileDetailRow({
  icon: Icon,
  label,
  children,
}: {
  icon: typeof Mail;
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="flex items-start gap-2.5 text-13">
      <Tooltip tooltipContent={label} position="left">
        <span className="mt-0.5 shrink-0 cursor-help text-tertiary">
          <Icon className="size-3.5" aria-hidden />
          <span className="sr-only">{label}</span>
        </span>
      </Tooltip>
      <div className="min-w-0 flex-1 break-words">{children}</div>
    </div>
  );
}

/** Penempatan yang langsung tampil; sisanya dilipat di balik "+N lagi". */
const PLACEMENT_VISIBLE_LIMIT = 3;

/** Satu baris unit. Tanpa label jenjang: ikon gedung di baris induk sudah menandai penempatan. */
function PlacementUnitRow({ name, isPrimary }: { name: string; isPrimary: boolean }) {
  return (
    <span className={cn("min-w-0 break-words", isPrimary ? "font-medium text-primary" : "text-secondary")}>{name}</span>
  );
}

/** Satu penempatan, teks polos: divisi, departemen, lalu jenjang sebagai teks redup. Tanpa kotak atau lencana. */
function PlacementBlock({ placement }: { placement: TMemberProfilePlacement }) {
  const { division, department, levelLabel } = placement;
  return (
    <div className="flex min-w-0 flex-col">
      {division ? <PlacementUnitRow name={division.nama} isPrimary /> : null}
      {department ? <PlacementUnitRow name={department.nama} isPrimary={!division} /> : null}
      {levelLabel ? <span className="text-12 text-tertiary">{levelLabel}</span> : null}
    </div>
  );
}

/** Daftar penempatan, dibatasi `PLACEMENT_VISIBLE_LIMIT` dengan tombol "+N lagi" untuk membukanya. */
function PlacementList({
  placements,
  labels,
}: {
  placements: TMemberProfilePlacement[];
  labels: TMemberProfileFieldLabels;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const hiddenCount = placements.length - PLACEMENT_VISIBLE_LIMIT;
  const visible = isExpanded || hiddenCount <= 0 ? placements : placements.slice(0, PLACEMENT_VISIBLE_LIMIT);
  return (
    <div className="flex flex-col gap-2">
      {visible.map((p) => (
        <PlacementBlock key={p.key} placement={p} />
      ))}
      {!isExpanded && hiddenCount > 0 ? (
        <button
          type="button"
          className="self-start rounded-control px-1 text-12 text-secondary outline-none hover:text-primary focus-visible:text-primary"
          onClick={() => setIsExpanded(true)}
        >
          {labels.morePlacements(hiddenCount)}
        </button>
      ) : null}
    </div>
  );
}

/**
 * Baris penempatan, email, dan ekstensi.
 * `email`/`phoneExtension`: null = peminta tidak berhak melihat kontak (baris
 * disembunyikan); ekstensi kosong "" tetap tampil sebagai "Not set".
 */
export function MemberProfileFields({
  labels,
  placements,
  email,
  phoneExtension,
}: {
  labels: TMemberProfileFieldLabels;
  placements: TMemberProfilePlacement[];
  email: string | null;
  phoneExtension: string | null;
}) {
  const notSet = <span className="block truncate text-tertiary">{labels.notSet}</span>;
  return (
    <div className="flex flex-col gap-2">
      <MemberProfileDetailRow icon={Building2} label={labels.placement}>
        {placements.length > 0 ? <PlacementList placements={placements} labels={labels} /> : notSet}
      </MemberProfileDetailRow>
      {email ? (
        <MemberProfileDetailRow icon={Mail} label={labels.email}>
          <a href={`mailto:${email}`} className="text-primary hover:underline">
            {email}
          </a>
        </MemberProfileDetailRow>
      ) : null}
      {phoneExtension !== null ? (
        <MemberProfileDetailRow icon={Phone} label={labels.phoneExtension}>
          {phoneExtension ? (
            <a href={`tel:${phoneExtension.replace(/\s/g, "")}`} className="text-primary hover:underline">
              {phoneExtension}
            </a>
          ) : (
            notSet
          )}
        </MemberProfileDetailRow>
      ) : null}
    </div>
  );
}

/** Kerangka pemuatan kartu. */
export function MemberProfileSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn("space-y-2", className)} aria-busy>
      <div className="h-3 w-3/4 animate-pulse rounded-sm bg-layer-1" />
      <div className="h-3 w-1/2 animate-pulse rounded-sm bg-layer-1" />
    </div>
  );
}

/** Avatar (slot) + nama lengkap + @handle + lencana (slot). */
export function MemberProfileHeader({
  avatar,
  fullName,
  handle,
  badges,
}: {
  avatar: ReactNode;
  fullName: string;
  handle: string;
  badges?: ReactNode;
}) {
  return (
    <div className="flex items-center gap-3">
      {avatar}
      <div className="min-w-0">
        <p className="truncate text-14 font-semibold text-primary">{fullName}</p>
        <p className="flex items-center gap-1.5 truncate text-12 text-secondary">
          <span className="truncate">@{handle}</span>
          {badges}
        </p>
      </div>
    </div>
  );
}

/** Lencana kecil di sebelah handle ("You", "Deactivated", ...). */
export function MemberProfileBadge({
  tone = "neutral",
  children,
}: {
  tone?: "neutral" | "danger";
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "rounded-sm px-1 text-11",
        tone === "danger" ? "bg-danger-subtle text-danger-primary" : "bg-layer-1 text-tertiary"
      )}
    >
      {children}
    </span>
  );
}

/**
 * Popover kartu: pemicu membungkus `children`, klik tidak bocor ke induk
 * (kartu kanban, baris tabel, tautan), isi kartu = `card`.
 */
export function MemberProfilePopover({
  open,
  onOpenChange,
  ariaLabel,
  triggerClassName,
  side = "bottom",
  align = "start",
  hoverHandlers,
  card,
  children,
}: {
  /** Pointer masuk/keluar pemicu DAN kartu; dipakai untuk membuka kartu saat hover. */
  hoverHandlers?: { onMouseEnter: () => void; onMouseLeave: () => void };
  open: boolean;
  onOpenChange: (open: boolean) => void;
  ariaLabel: string;
  triggerClassName?: string;
  side?: "top" | "bottom" | "left" | "right";
  align?: "start" | "center" | "end";
  card: ReactNode;
  children: ReactNode;
}) {
  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <Popover.Button
        nativeButton={false}
        render={<span />}
        // base-ui memberi role="button" + tabIndex sendiri saat nativeButton=false.
        aria-label={ariaLabel}
        className={cn("inline-flex max-w-full cursor-pointer items-center rounded-sm outline-none", triggerClassName)}
        onMouseEnter={hoverHandlers?.onMouseEnter}
        onMouseLeave={hoverHandlers?.onMouseLeave}
        onClick={(e) => {
          // Jangan biarkan klik membuka kartu work item / mengikuti tautan induk.
          e.stopPropagation();
          e.preventDefault();
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") e.stopPropagation();
        }}
      >
        {children}
      </Popover.Button>
      <Popover.Panel
        side={side}
        align={align}
        // z-index harus di positioner (elemen yang benar-benar diposisikan), bukan
        // di popup: dengan z di popup, kartu tertutup peek overview work item (z-25).
        positionerClassName="z-40"
        className={POPOVER_PANEL_CLASS}
        onMouseEnter={hoverHandlers?.onMouseEnter}
        onMouseLeave={hoverHandlers?.onMouseLeave}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex flex-col gap-3">{card}</div>
      </Popover.Panel>
    </Popover>
  );
}
