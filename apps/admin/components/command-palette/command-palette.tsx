/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: God Mode command palette (Ctrl/Cmd + K)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Same shape as Power K in the web app (cmdk inside a dialog, search on top,
 * list below), but the list is ours: menus, tabs and every registry setting,
 * ranked by fuzzy.ts over title, help text, keywords and breadcrumb. Picking a
 * setting opens its tab and scrolls to the row (use-setting-anchor.ts).
 */

import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { observer } from "mobx-react";
import { useRouter } from "next/navigation";
import { ChevronRight, CornerDownLeft, Search } from "lucide-react";
import { Dialog, Transition } from "@headlessui/react";
import { Command } from "@plane/propel/command";
import { cn } from "@plane/utils";
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { coreSidebarMenuLinks } from "@/hooks/use-sidebar-menu/core";
import { useInstanceSettings } from "@/hooks/use-instance-settings";
import { buildPaletteEntries, searchPalette } from "./entries";
import type { TPaletteEntry } from "./entries";

const isMac = (): boolean => typeof navigator !== "undefined" && /mac|iphone|ipad/i.test(navigator.platform);

/** Ctrl/Cmd + K toggles the palette from anywhere in God Mode. */
export function useCommandPaletteShortcut(onToggle: () => void): void {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && !e.altKey && !e.shiftKey && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onToggle();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onToggle]);
}

function ShortcutKeys({ className }: { className?: string }) {
  return (
    <kbd className={cn("font-sans rounded-sm border border-subtle bg-layer-1 px-1.5 text-11 text-tertiary", className)}>
      {isMac() ? "⌘" : "Ctrl"} K
    </kbd>
  );
}

function EntryRow({ entry, onSelect }: { entry: TPaletteEntry; onSelect: (entry: TPaletteEntry) => void }) {
  const { s } = useGodmodeStrings();
  const Icon = coreSidebarMenuLinks[entry.menu].Icon;
  return (
    <Command.Item
      value={entry.id}
      onSelect={() => onSelect(entry)}
      className="group flex cursor-pointer items-start gap-3 rounded-md px-2 py-2 text-left outline-none data-[selected=true]:bg-layer-transparent-active sentuh:min-h-11"
    >
      <Icon className="mt-0.5 size-4 shrink-0 text-tertiary" />
      <div className="min-w-0 flex-1 space-y-0.5">
        <div className="flex min-w-0 items-center gap-2">
          <span className="truncate text-13 font-medium text-primary">{entry.title}</span>
          <span className="shrink-0 rounded-sm bg-layer-1 px-1.5 text-11 text-tertiary">
            {s.palette.kind[entry.kind]}
          </span>
        </div>
        {entry.path.length > 0 && (
          <div className="flex min-w-0 flex-wrap items-center gap-0.5 text-11 text-tertiary">
            {entry.path.map((part, i) => (
              <Fragment key={entry.path.slice(0, i + 1).join("/")}>
                {i > 0 && <ChevronRight className="size-3 shrink-0" />}
                <span>{part}</span>
              </Fragment>
            ))}
          </div>
        )}
        {entry.description && <p className="line-clamp-2 text-11 leading-5 text-secondary">{entry.description}</p>}
      </div>
      <CornerDownLeft className="mt-0.5 size-3.5 shrink-0 text-tertiary opacity-0 group-data-[selected=true]:opacity-100" />
    </Command.Item>
  );
}

type Props = { isOpen: boolean; onClose: () => void };

export function CommandPaletteDialog({ isOpen, onClose }: Props) {
  const { s, fill } = useGodmodeStrings();
  const router = useRouter();
  const { settings } = useInstanceSettings();
  const [query, setQuery] = useState("");

  const entries = useMemo(
    () => buildPaletteEntries(s.settings, settings ? new Set(Object.keys(settings)) : undefined),
    [s.settings, settings]
  );
  const trimmed = query.trim();
  const matches = useMemo(() => (trimmed ? searchPalette(entries, trimmed) : []), [entries, trimmed]);
  const menus = useMemo(() => entries.filter((e) => e.kind === "menu"), [entries]);

  const handleSelect = useCallback(
    (entry: TPaletteEntry) => {
      onClose();
      router.push(entry.href);
    },
    [onClose, router]
  );

  // Start fresh each time, after the close transition so the list does not flash.
  useEffect(() => {
    if (isOpen) return;
    const timer = setTimeout(() => setQuery(""), 200);
    return () => clearTimeout(timer);
  }, [isOpen]);

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-backdrop transition-opacity" />
        </Transition.Child>
        <div className="fixed inset-0 z-30 overflow-y-auto">
          <div className="flex items-start justify-center p-2 pt-[8dvh] sm:p-6 md:pt-[12dvh]">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-200"
              enterFrom="opacity-0 translate-y-2 sm:translate-y-0 sm:scale-[0.98]"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-150"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-2 sm:translate-y-0 sm:scale-[0.98]"
            >
              <Dialog.Panel className="relative flex w-full max-w-2xl flex-col rounded-overlay border border-subtle bg-surface-1 shadow-raised-200">
                <Dialog.Title className="sr-only">{s.palette.label}</Dialog.Title>
                <Command
                  shouldFilter={false}
                  loop
                  label={s.palette.label}
                  className="w-full"
                  onKeyDown={(e) => {
                    if (e.key === "Escape" && query) {
                      // First Escape clears the search, the second closes.
                      e.preventDefault();
                      e.stopPropagation();
                      setQuery("");
                    }
                  }}
                >
                  <div className="flex items-center gap-2 border-b border-subtle px-4 py-3">
                    <Search className="size-4 shrink-0 text-placeholder" />
                    {/* Primitive input: propel's Command.Input brings its own search box frame. */}
                    <CommandInput value={query} onChange={setQuery} placeholder={s.palette.placeholder} />
                  </div>
                  <Command.List className="vertical-scrollbar scrollbar-sm max-h-[min(28rem,calc(100dvh-14rem))] overflow-y-auto overscroll-contain p-2 outline-none">
                    {trimmed ? (
                      <>
                        <Command.Empty className="px-2 py-8 text-center text-13 text-tertiary">
                          {fill(s.palette.empty, { query: trimmed })}
                        </Command.Empty>
                        {matches.map(({ entry }) => (
                          <EntryRow key={entry.id} entry={entry} onSelect={handleSelect} />
                        ))}
                      </>
                    ) : (
                      <>
                        <div className="px-2 pt-1 pb-2 text-12 font-medium text-tertiary">{s.palette.group_menus}</div>
                        {menus.map((entry) => (
                          <EntryRow key={entry.id} entry={entry} onSelect={handleSelect} />
                        ))}
                      </>
                    )}
                  </Command.List>
                  <div className="flex items-center gap-4 rounded-b-overlay border-t border-subtle bg-surface-2 px-4 py-2 text-11 text-tertiary">
                    <span>
                      <kbd className="font-sans">↑↓</kbd> {s.palette.hint_navigate}
                    </span>
                    <span>
                      <kbd className="font-sans">↵</kbd> {s.palette.hint_open}
                    </span>
                    <span>
                      <kbd className="font-sans">Esc</kbd> {s.palette.hint_close}
                    </span>
                  </div>
                </Command>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  );
}

function CommandInput({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      aria-label={placeholder}
      className="flex-1 bg-transparent text-13 text-primary placeholder-(--text-color-placeholder) outline-none sentuh:text-16"
    />
  );
}

/** Header button + global shortcut + dialog. */
export const CommandPalette = observer(function CommandPalette() {
  const { s } = useGodmodeStrings();
  const [isOpen, setIsOpen] = useState(false);
  const toggle = useCallback(() => setIsOpen((open) => !open), []);
  const close = useCallback(() => setIsOpen(false), []);
  useCommandPaletteShortcut(toggle);

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        aria-label={s.palette.trigger}
        className="flex shrink-0 items-center gap-2 rounded-field border-[0.5px] border-subtle-1 bg-layer-2 px-2.5 py-1.5 text-left text-13 text-tertiary transition-colors hover:bg-layer-transparent-hover hover:text-secondary focus-visible:ring-1 focus-visible:ring-accent-strong focus-visible:outline-none sm:w-60"
      >
        <Search className="size-3.5 shrink-0" />
        <span className="hidden flex-1 truncate sm:inline">{s.palette.trigger}</span>
        <ShortcutKeys className="hidden sm:inline" />
      </button>
      <CommandPaletteDialog isOpen={isOpen} onClose={close} />
    </>
  );
});
