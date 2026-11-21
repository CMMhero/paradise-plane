/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: satu galeri per work item
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode, RefObject } from "react";
import { observer } from "mobx-react";
import { ImageGallery } from "@plane/propel/image-gallery";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// local imports
import { attachmentGalleryEntries } from "./attachment-items";

type Props = {
  issueId: string;
  /** the element holding the description, the widgets and the activity */
  rootRef: RefObject<HTMLElement | null>;
  children: ReactNode;
};

/**
 * Every image of one work item in reading order: the description, then the
 * comments top to bottom (both read from the page), then image attachments
 * from the store, so they count even while the Attachments section is closed.
 */
export const WorkItemImageGalleryScope = observer(function WorkItemImageGalleryScope(props: Props) {
  const { issueId, rootRef, children } = props;
  const {
    attachment: { getAttachmentsByIssueId, getAttachmentById },
  } = useIssueDetail();
  const attachments = (getAttachmentsByIssueId(issueId) ?? []).map((id) => getAttachmentById(id));
  // observer: re-renders only when the attachments change, and the scope ignores lists that did not
  const extraItems = attachmentGalleryEntries(attachments);

  return (
    <ImageGallery.Scope rootRef={rootRef} extraItems={extraItems} resetKey={issueId}>
      {children}
    </ImageGallery.Scope>
  );
});
