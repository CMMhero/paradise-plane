/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { memo, useMemo } from "react";
import { Popover as BasePopover } from "@base-ui-components/react/popover";
import { PreviewCard as BasePreviewCard } from "@base-ui-components/react/preview-card";
import type { TPlacement, TSide, TAlign } from "../utils/placement";
import { convertPlacementToSideAndAlign } from "../utils/placement";

export interface PopoverContentProps extends React.ComponentProps<typeof BasePopover.Popup> {
  placement?: TPlacement;
  align?: TAlign;
  sideOffset?: BasePopover.Positioner.Props["sideOffset"];
  side?: TSide;
  containerRef?: React.RefObject<HTMLElement>;
  positionerClassName?: string;
}

// PopoverContent component
const PopoverContent = memo(function PopoverContent({
  children,
  className,
  placement,
  side = "bottom",
  align = "center",
  sideOffset = 8,
  containerRef,
  positionerClassName,
  ...props
}: PopoverContentProps) {
  // side and align calculations
  const { finalSide, finalAlign } = useMemo(() => {
    if (placement) {
      const converted = convertPlacementToSideAndAlign(placement);
      return { finalSide: converted.side, finalAlign: converted.align };
    }
    return { finalSide: side, finalAlign: align };
  }, [placement, side, align]);

  return (
    // oxlint-disable-next-line react/refs -- container must be resolved on first render so the portal mounts in the right node; a state/effect copy would mount it in the default container first
    <PopoverPortal container={containerRef?.current}>
      <PopoverPositioner side={finalSide} sideOffset={sideOffset} align={finalAlign} className={positionerClassName}>
        <BasePopover.Popup data-slot="popover-content" className={className} {...props}>
          {children}
        </BasePopover.Popup>
      </PopoverPositioner>
    </PopoverPortal>
  );
});

// wrapper components
const PopoverTrigger = memo(function PopoverTrigger(props: React.ComponentProps<typeof BasePopover.Trigger>) {
  return <BasePopover.Trigger data-slot="popover-trigger" {...props} />;
});

const PopoverPortal = memo(function PopoverPortal(props: React.ComponentProps<typeof BasePopover.Portal>) {
  return <BasePopover.Portal data-slot="popover-portal" {...props} />;
});

const PopoverPositioner = memo(function PopoverPositioner(props: React.ComponentProps<typeof BasePopover.Positioner>) {
  return <BasePopover.Positioner data-slot="popover-positioner" {...props} />;
});

// compound components
const Popover = Object.assign(
  memo(function Popover(props: React.ComponentProps<typeof BasePopover.Root>) {
    return <BasePopover.Root data-slot="popover" {...props} />;
  }),
  {
    Button: PopoverTrigger,
    Panel: PopoverContent,
  }
);

// display names
PopoverContent.displayName = "PopoverContent";
Popover.displayName = "Popover";
PopoverPortal.displayName = "PopoverPortal";
PopoverTrigger.displayName = "PopoverTrigger";
PopoverPositioner.displayName = "PopoverPositioner";

// Paradise (KEP-91): kartu pratinjau saat hover/fokus (mention orang, kanal, work item).
// Lain dengan Popover: tidak butuh klik, dan tertutup sendiri saat pointer pergi.
export type HoverCardProps = {
  /** Pemicu: satu elemen yang menerima ref dan props hover. */
  children: React.ReactElement;
  /** Isi kartu. */
  content: React.ReactNode;
  side?: TSide;
  align?: TAlign;
  delay?: number;
  closeDelay?: number;
  /** Mati = hanya anak yang dirender, tanpa kartu. */
  disabled?: boolean;
  className?: string;
};

const HOVER_CARD_CLASS =
  "w-64 max-w-[calc(100vw-2rem)] rounded-popover border-[0.5px] border-strong bg-surface-1 p-3 shadow-raised-200";

const HoverCard = memo(function HoverCard({
  children,
  content,
  side = "bottom",
  align = "start",
  delay = 350,
  closeDelay = 120,
  disabled = false,
  className,
}: HoverCardProps) {
  if (disabled) return children;
  return (
    <BasePreviewCard.Root delay={delay} closeDelay={closeDelay}>
      <BasePreviewCard.Trigger render={children} />
      <BasePreviewCard.Portal>
        {/* z-index di positioner, sama alasannya dengan kartu profil: tanpa itu tertutup peek overview. */}
        <BasePreviewCard.Positioner side={side} align={align} sideOffset={6} className="z-40">
          <BasePreviewCard.Popup
            data-slot="hover-card-content"
            className={className ?? HOVER_CARD_CLASS}
            onClick={(e) => e.stopPropagation()}
          >
            {content}
          </BasePreviewCard.Popup>
        </BasePreviewCard.Positioner>
      </BasePreviewCard.Portal>
    </BasePreviewCard.Root>
  );
});
HoverCard.displayName = "HoverCard";

export { Popover, HoverCard };
