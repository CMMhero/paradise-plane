/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { combine } from "@atlaskit/pragmatic-drag-and-drop/combine";
import type {
  DragLocationHistory,
  DropTargetRecord,
  ElementDragPayload,
} from "@atlaskit/pragmatic-drag-and-drop/dist/types/internal-types";
import { dropTargetForElements } from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import { orderBy } from "lodash-es";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { Disclosure, Transition } from "@headlessui/react";
import { IS_FAVORITE_MENU_OPEN } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { ChevronRightIcon } from "@plane/propel/icons";
// ui
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { IFavorite } from "@plane/types";
// helpers
import { cn } from "@plane/utils";
// hooks
import { useFavorite } from "@/hooks/store/use-favorite";
import useLocalStorage from "@/hooks/use-local-storage";
// plane web components
import { FavoriteRoot } from "./favorite-items";
import type { TargetData } from "./favorites.helpers";
import { getInstructionFromPayload } from "./favorites.helpers";

export const SidebarFavoritesMenu = observer(function SidebarFavoritesMenu() {
  // states
  const [isDragging, setIsDragging] = useState(false);
  // navigation
  const { workspaceSlug } = useParams();
  // store hooks
  const { groupedFavorites, deleteFavorite, reOrderFavorite } = useFavorite();
  // translation
  const { t } = useTranslation();
  // local storage
  const { setValue: toggleFavoriteMenu, storedValue } = useLocalStorage<boolean>(IS_FAVORITE_MENU_OPEN, false);
  // derived values
  const isFavoriteMenuOpen = !!storedValue;
  // Semua favorit selain folder, satu tingkat, termasuk yang dulu ada di dalam folder.
  const favoritRata = orderBy(Object.values(groupedFavorites), "sequence", "desc").filter((fav) => !fav.is_folder);
  // refs
  const containerRef = useRef<HTMLDivElement>(null);
  const elementRef = useRef<HTMLDivElement>(null);

  // Kustomisasi Paradise: folder favorit dicabut (permintaan user 5 Nov 2026).
  // Seret-lepas cuma mengurutkan ulang; tidak ada lagi yang bisa jadi anak folder.
  const handleDrop = (_self: DropTargetRecord, source: ElementDragPayload, location: DragLocationHistory) => {
    const dropTargets = location?.current?.dropTargets ?? [];
    if (!dropTargets || dropTargets.length <= 0) return;
    const dropTarget =
      dropTargets.length > 1 ? dropTargets.find((target: DropTargetRecord) => target?.data?.isChild) : dropTargets[0];

    const dropTargetData = dropTarget?.data as TargetData;

    if (!dropTarget || !dropTargetData) return;
    const instruction = getInstructionFromPayload(dropTarget, source, location);
    const sourceData = source.data as TargetData;
    if (!sourceData.id || instruction === "make-child") return;
    handleReorder(sourceData.id, dropTargetData.id, instruction);
  };

  const handleRemoveFromFavorites = (favorite: IFavorite) => {
    deleteFavorite(workspaceSlug.toString(), favorite.id)
      .then(() => {
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: t("success"),
          message: t("favorite_removed_successfully"),
        });
        return;
      })
      .catch(() => {
        setToast({
          type: TOAST_TYPE.ERROR,
          title: t("error"),
          message: t("something_went_wrong"),
        });
      });
  };

  const handleReorder = useCallback(
    (favoriteId: string, droppedFavId: string, edge: string | undefined) => {
      reOrderFavorite(workspaceSlug.toString(), favoriteId, droppedFavId, edge).catch(() => {
        setToast({
          type: TOAST_TYPE.ERROR,
          title: t("error"),
          message: t("failed_to_reorder_favorite"),
        });
      });
    },
    [workspaceSlug, reOrderFavorite, t]
  );

  useEffect(() => {
    const element = elementRef.current;

    if (!element) return;

    return combine(
      dropTargetForElements({
        element,
        onDragEnter: () => {
          setIsDragging(true);
        },
        onDragLeave: () => {
          setIsDragging(false);
        },
        onDragStart: () => {
          setIsDragging(true);
        },
        onDrop: ({ source }) => {
          setIsDragging(false);
          const sourceId = source?.data?.id as string | undefined;
          console.log({ sourceId });
          if (!sourceId || !groupedFavorites[sourceId].parent) return;
        },
      })
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [elementRef.current, isDragging]);

  return (
    <>
      <Disclosure as="div" defaultOpen ref={containerRef}>
        <div
          ref={elementRef}
          className={cn(
            "group/favorites-button flex w-full items-center justify-between rounded-sm px-2 py-1.5 text-placeholder hover:bg-layer-transparent-hover"
          )}
        >
          <Disclosure.Button
            as="button"
            type="button"
            className={cn(
              "flex w-full items-center gap-1 text-left text-13 font-semibold whitespace-nowrap text-placeholder",
              {
                "bg-layer-1 opacity-60": isDragging,
              }
            )}
            onClick={() => toggleFavoriteMenu(!isFavoriteMenuOpen)}
            aria-label={t(
              isFavoriteMenuOpen
                ? "aria_labels.projects_sidebar.close_favorites_menu"
                : "aria_labels.projects_sidebar.open_favorites_menu"
            )}
          >
            <span className="text-13 font-semibold">{t("favorites")}</span>
          </Disclosure.Button>
          <div className="pointer-events-none flex items-center opacity-0 group-hover/favorites-button:pointer-events-auto group-hover/favorites-button:opacity-100">
            <Disclosure.Button
              as="button"
              type="button"
              className="grid flex-shrink-0 place-items-center rounded-sm p-0.5 hover:bg-layer-transparent-hover"
              onClick={() => toggleFavoriteMenu(!isFavoriteMenuOpen)}
              aria-label={t(
                isFavoriteMenuOpen
                  ? "aria_labels.projects_sidebar.close_favorites_menu"
                  : "aria_labels.projects_sidebar.open_favorites_menu"
              )}
            >
              <ChevronRightIcon
                className={cn("size-3 flex-shrink-0 transition-all", {
                  "rotate-90": isFavoriteMenuOpen,
                })}
              />
            </Disclosure.Button>
          </div>
        </div>
        <Transition
          show={isFavoriteMenuOpen}
          enter="transition duration-100 ease-out"
          enterFrom="transform scale-95 opacity-0"
          enterTo="transform scale-100 opacity-100"
          leave="transition duration-75 ease-out"
          leaveFrom="transform scale-100 opacity-100"
          leaveTo="transform scale-95 opacity-0"
        >
          {isFavoriteMenuOpen && (
            <Disclosure.Panel as="div" className="mt-0.5 flex flex-col gap-0.5" static>
              {/* Folder lama di database tidak dihapus, hanya tidak ditampilkan;
                  favorit yang dulu di dalamnya naik ke daftar utama supaya tidak hilang. */}
              {favoritRata.length === 0 ? (
                <span className="px-8 py-1.5 text-11 font-medium text-placeholder">{t("no_favorites_yet")}</span>
              ) : (
                favoritRata.map((fav, index, { length }) => (
                  <FavoriteRoot
                    key={fav.id}
                    workspaceSlug={workspaceSlug.toString()}
                    favorite={fav}
                    isLastChild={index === length - 1}
                    parentId={undefined}
                    handleRemoveFromFavorites={handleRemoveFromFavorites}
                    handleDrop={handleDrop}
                  />
                ))
              )}
            </Disclosure.Panel>
          )}
        </Transition>
      </Disclosure>
    </>
  );
});
