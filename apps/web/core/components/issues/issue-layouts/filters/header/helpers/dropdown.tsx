/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React, { Fragment, useState } from "react";
import type { Placement } from "@popperjs/core";
import { usePopper } from "react-popper";
// headless ui
import { Popover, Transition } from "@headlessui/react";
// ui
import { Button } from "@plane/propel/button";

type Props = {
  children: React.ReactNode;
  icon?: React.ReactElement;
  /** Tidak dipakai lagi (KEP-64: tombol selalu ikon + judul); dibiarkan supaya pemanggil lama tetap valid. */
  miniIcon?: React.ReactNode;
  title?: string;
  placement?: Placement;
  disabled?: boolean;
  tabIndex?: number;
  menuButton?: React.ReactNode;
  isFiltersApplied?: boolean;
};

export function FiltersDropdown(props: Props) {
  const {
    children,
    icon,
    title = "Dropdown",
    placement,
    disabled = false,
    tabIndex,
    menuButton,
    isFiltersApplied = false,
  } = props;

  const [referenceElement, setReferenceElement] = useState<HTMLButtonElement | HTMLDivElement | null>(null);
  const [popperElement, setPopperElement] = useState<HTMLDivElement | null>(null);

  const { styles, attributes } = usePopper(referenceElement, popperElement, {
    placement: placement ?? "auto",
  });

  return (
    // flex: tanpa ini <div> blok membungkus tombol inline-flex dan ikut tinggi baris teks,
    // jadi lebih tinggi dari tombol dan tergeser dari tetangganya di header.
    <Popover as="div" className="flex items-center">
      {({ open }) => (
        <>
          {menuButton ? (
            <Popover.Button as={React.Fragment}>
              <button type="button" ref={setReferenceElement} className="flex items-center rounded-button">
                {menuButton}
              </button>
            </Popover.Button>
          ) : (
            // Paradise (KEP-64): SATU tombol nyata sebagai Popover.Button. Versi lama
            // membungkus dua tombol (penuh dan ikon saja, ditukar container query
            // @4xl) di dalam <div> yang dijadikan tombol. Akibatnya ukurannya
            // berganti setiap lebar header berubah (sidebar/peek dibuka), dan klik
            // kadang tidak membuka panel karena jangkar popper bisa menunjuk ke
            // varian yang sedang tersembunyi.
            <Popover.Button
              as={Button}
              ref={setReferenceElement}
              disabled={disabled}
              variant="secondary"
              size="lg"
              prependIcon={icon}
              tabIndex={tabIndex}
              className="relative"
            >
              <span className={open ? "text-primary" : "text-secondary"}>{title}</span>
              {isFiltersApplied && (
                <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-accent-primary" />
              )}
            </Popover.Button>
          )}
          <Transition
            as={Fragment}
            enter="transition ease-out duration-200"
            enterFrom="opacity-0 translate-y-1"
            enterTo="opacity-100 translate-y-0"
            leave="transition ease-in duration-150"
            leaveFrom="opacity-100 translate-y-0"
            leaveTo="opacity-0 translate-y-1"
          >
            {/** translate-y-0 is a hack to create new stacking context. Required for safari  */}
            <Popover.Panel className="fixed z-10 translate-y-0">
              <div
                className="my-1 overflow-hidden rounded-popover border border-subtle bg-surface-1 shadow-raised-200"
                ref={setPopperElement}
                style={styles.popper}
                {...attributes.popper}
              >
                <div className="flex max-h-[min(30rem,calc(100dvh-8rem))] w-[18.75rem] max-w-[calc(100vw-1rem)] flex-col overflow-hidden lg:max-h-[min(37.5rem,calc(100dvh-8rem))]">
                  {children}
                </div>
              </div>
            </Popover.Panel>
          </Transition>
        </>
      )}
    </Popover>
  );
}
