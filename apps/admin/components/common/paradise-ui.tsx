/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: balok orang, field, panel, modal God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Pendamping paradise.tsx. Sengaja tipis: tiap balok membungkus komponen
 * upstream yang sudah ada (Propel Avatar/IconButton/Tooltip, ModalCore
 * @plane/ui) dan hanya menambah susunan yang berulang di Accounts,
 * Organization, dan Audit log. Label status pakai `Badge` Propel langsung.
 */

import type { ReactNode } from "react";
import { X } from "lucide-react";
import { Avatar } from "@plane/propel/avatar";
import { IconButton } from "@plane/propel/icon-button";
import { Tooltip } from "@plane/propel/tooltip";
import { EModalPosition, EModalWidth, ModalCore } from "@plane/ui";
import { cn } from "@plane/utils";
import { MemberProfileTrigger } from "./member-profile";
import { avatarTone } from "./paradise-styles";

type TUkuranOrang = "sm" | "md" | "lg";
const UKURAN_AVATAR = { sm: "md", md: "base", lg: "lg" } as const;

/** Propel Avatar with a fallback hue picked from the name, so one person keeps one colour everywhere. */
export function PersonAvatar({ name, size = "md" }: { name: string; size?: TUkuranOrang }) {
  const rona = avatarTone(name);
  return (
    <Avatar
      name={name}
      size={UKURAN_AVATAR[size]}
      showTooltip={false}
      fallbackBackgroundColor={rona.bg}
      fallbackTextColor={rona.text}
    />
  );
}

/** Avatar + name + email, the one way a person is shown in every God Mode list. */
export function PersonCell({
  userId,
  name,
  email,
  badges,
  size = "md",
  muted = false,
}: {
  /** When set, clicking the avatar or name opens the member profile card. */
  userId?: string | null;
  name: string;
  email?: string;
  badges?: ReactNode;
  size?: TUkuranOrang;
  muted?: boolean;
}) {
  const label = name || email || "?";
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <MemberProfileTrigger userId={userId} name={label} className="shrink-0">
        <PersonAvatar name={label} size={size} />
      </MemberProfileTrigger>
      <div className="min-w-0">
        <div className="flex min-w-0 flex-wrap items-center gap-1.5">
          <MemberProfileTrigger userId={userId} name={label} className="min-w-0">
            <span
              className={cn("truncate font-medium", muted ? "text-tertiary" : "text-primary")}
              title={name || email}
            >
              {name || email}
            </span>
          </MemberProfileTrigger>
          {badges}
        </div>
        {email && name && (
          <div className="truncate text-11 text-tertiary" title={email}>
            {email}
          </div>
        )}
      </div>
    </div>
  );
}

/** Label + control + optional hint/error. Wraps every form control in custom God Mode pages. */
export function Field({
  label,
  hint,
  error,
  className,
  children,
}: {
  label: string;
  hint?: ReactNode;
  error?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={cn("space-y-1", className)}>
      <span className="block text-12 font-medium text-secondary">{label}</span>
      {children}
      {error ? (
        <span className="block text-11 text-danger-primary">{error}</span>
      ) : (
        hint && <span className="block text-11 leading-4 text-tertiary">{hint}</span>
      )}
    </div>
  );
}

/** Bordered card with a header row. Used by modal sections and organization detail. */
export function Panel({
  title,
  description,
  icon,
  actions,
  tone = "neutral",
  children,
  flush = false,
}: {
  title: ReactNode;
  description?: ReactNode;
  icon?: ReactNode;
  actions?: ReactNode;
  tone?: "neutral" | "warning" | "danger";
  children?: ReactNode;
  /** Children touch the border (lists that draw their own dividers). */
  flush?: boolean;
}) {
  return (
    <section
      className={cn("overflow-hidden rounded-card border bg-layer-1", {
        "border-subtle": tone === "neutral",
        "border-warning-subtle": tone === "warning",
        "border-danger-subtle": tone === "danger",
      })}
    >
      <div
        className={cn("flex flex-wrap items-start justify-between gap-3 px-4 py-3", {
          "border-b border-subtle": Boolean(children),
          "bg-warning-subtle": tone === "warning",
          "bg-danger-subtle": tone === "danger",
        })}
      >
        <div className="flex min-w-0 items-start gap-2.5">
          {icon && (
            <span
              className={cn("mt-0.5 shrink-0", {
                "text-tertiary": tone === "neutral",
                "text-warning-primary": tone === "warning",
                "text-danger-primary": tone === "danger",
              })}
            >
              {icon}
            </span>
          )}
          <div className="min-w-0 space-y-0.5">
            <h3 className="text-13 font-semibold text-primary">{title}</h3>
            {description && <p className="text-11 leading-4 text-tertiary">{description}</p>}
          </div>
        </div>
        {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {children && <div className={flush ? "" : "p-4"}>{children}</div>}
    </section>
  );
}

/** Propel ghost IconButton with a tooltip. The label doubles as the accessible name. */
export function IconAction({
  label,
  icon,
  onClick,
  disabled,
  variant = "ghost",
}: {
  label: string;
  icon: React.FC<{ className?: string }>;
  onClick: () => void;
  disabled?: boolean;
  variant?: "ghost" | "error-outline" | "secondary";
}) {
  return (
    <Tooltip tooltipContent={label}>
      <IconButton variant={variant} size="lg" icon={icon} aria-label={label} disabled={disabled} onClick={onClick} />
    </Tooltip>
  );
}

/** ModalCore with a header (title + close), a body that scrolls on its own, and a sticky footer. */
export function ParadiseModal({
  isOpen,
  onClose,
  title,
  leading,
  subtitle,
  footer,
  footerNote,
  width = EModalWidth.XXL,
  closeLabel = "Close",
  children,
}: {
  isOpen: boolean;
  onClose: () => void;
  title: ReactNode;
  /** Sits left of the title (avatar, icon). */
  leading?: ReactNode;
  subtitle?: ReactNode;
  footer?: ReactNode;
  /** Left side of the footer (hints, warnings). */
  footerNote?: ReactNode;
  width?: EModalWidth;
  closeLabel?: string;
  children: ReactNode;
}) {
  return (
    <ModalCore isOpen={isOpen} handleClose={onClose} position={EModalPosition.CENTER} width={width}>
      <div className="flex max-h-[88vh] flex-col">
        <div className="flex items-center gap-3 border-b border-subtle px-5 py-4">
          {leading}
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-16 font-semibold text-primary">{title}</h2>
            {subtitle && <div className="mt-0.5 truncate text-12 text-tertiary">{subtitle}</div>}
          </div>
          <IconButton variant="ghost" size="lg" icon={X} aria-label={closeLabel} onClick={onClose} />
        </div>
        <div className="vertical-scrollbar scrollbar-sm flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-b-overlay border-t border-subtle bg-layer-1 px-5 py-3">
            <div className="min-w-0 flex-1 text-11 text-tertiary">{footerNote}</div>
            <div className="flex shrink-0 items-center gap-2">{footer}</div>
          </div>
        )}
      </div>
    </ModalCore>
  );
}

export { EModalWidth };
