/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { observer } from "mobx-react";
import { useForm, Controller } from "react-hook-form";
// plane imports
import { EIssueCommentAccessSpecifier } from "@plane/constants";
import type { EditorRefApi, TFileHandler } from "@plane/editor";
import type { TIssueComment, TCommentsOperations } from "@plane/types";
import { cn, isCommentEmpty } from "@plane/utils";
// components
import { LiteTextEditor } from "@/components/editor/lite-text";
// hooks
import { useWorkspace } from "@/hooks/store/use-workspace";
// services
import { FileService } from "@/services/file.service";

type TCommentCreate = {
  entityId: string;
  workspaceSlug: string;
  activityOperations: TCommentsOperations;
  showToolbarInitially?: boolean;
  projectId?: string;
  onSubmitCallback?: (elementId: string) => void;
  /** pasted/dropped non-image files become attachments of the entity */
  attachFiles?: TFileHandler["attachFiles"];
  /** rendered under the editor, e.g. attachment upload progress and errors */
  attachmentStatus?: ReactNode;
  /** reply mode: id of the thread root the new comment attaches to */
  parentId?: string;
  /** editor content on mount, e.g. a mention when replying to a reply */
  initialHtml?: string;
  /** focus the editor (cursor at the end) once it is ready */
  focusOnMount?: boolean;
  /** rendered above the editor, e.g. who the reply is for */
  header?: ReactNode;
};

// services
const fileService = new FileService();

export const CommentCreate = observer(function CommentCreate(props: TCommentCreate) {
  const {
    workspaceSlug,
    entityId,
    activityOperations,
    showToolbarInitially = false,
    projectId,
    onSubmitCallback,
    attachFiles,
    attachmentStatus,
    parentId,
    initialHtml = "<p></p>",
    focusOnMount = false,
    header,
  } = props;
  // states
  const [uploadedAssetIds, setUploadedAssetIds] = useState<string[]>([]);
  // refs
  const editorRef = useRef<EditorRefApi>(null);

  useEffect(() => {
    if (!focusOnMount) return;
    // the editor mounts a tick after this component
    const timeout = setTimeout(() => editorRef.current?.focus("end"), 50);
    return () => clearTimeout(timeout);
  }, [focusOnMount]);
  // store hooks
  const workspaceStore = useWorkspace();
  // derived values
  const workspaceId = workspaceStore.getWorkspaceBySlug(workspaceSlug)?.id as string;
  // form info
  const {
    handleSubmit,
    control,
    setValue,
    formState: { isSubmitting },
    reset,
  } = useForm<Partial<TIssueComment>>({
    defaultValues: {
      comment_html: initialHtml,
    },
  });
  // Paradise: dulu `watch("comment_html")` + Controller, jadi tiap huruf
  // merender ulang komponen ini, LiteTextEditor, dan editornya (useEditor
  // membangun ulang extension lalu setOptions menghitung ulang dekorasi
  // dokumen), plus dua kali sanitize-html atas seluruh komentar. Sekarang
  // nilainya cuma disimpan ke form; yang memicu render hanya saat status
  // kosong/berisi berbalik.
  const [isEmpty, setIsEmpty] = useState(true);

  const onSubmit = async (formData: Partial<TIssueComment>) => {
    try {
      const comment = await activityOperations.createComment(parentId ? { ...formData, parent: parentId } : formData);
      if (comment?.id) onSubmitCallback?.(comment.id);
      if (uploadedAssetIds.length > 0) {
        if (projectId) {
          await fileService.updateBulkProjectAssetsUploadStatus(workspaceSlug, projectId.toString(), entityId, {
            asset_ids: uploadedAssetIds,
          });
        } else {
          await fileService.updateBulkWorkspaceAssetsUploadStatus(workspaceSlug, entityId, {
            asset_ids: uploadedAssetIds,
          });
        }
        setUploadedAssetIds([]);
      }
    } catch (error) {
      console.error(error);
    } finally {
      reset({
        comment_html: "<p></p>",
      });
      setIsEmpty(true);
      editorRef.current?.clearEditor();
    }
  };

  return (
    <div
      className={cn({ "sticky bottom-0 z-[4] bg-surface-1 sm:static": !parentId })}
      role="presentation"
      onKeyDown={(e) => {
        if (
          e.key === "Enter" &&
          !e.shiftKey &&
          !e.ctrlKey &&
          !e.metaKey &&
          !isEmpty &&
          !isSubmitting &&
          editorRef.current?.isEditorReadyToDiscard()
        )
          handleSubmit(onSubmit)(e);
      }}
    >
      {header}
      <Controller
        name="access"
        control={control}
        render={({ field: { onChange: onAccessChange, value: accessValue } }) => (
          <LiteTextEditor
            editable
            workspaceId={workspaceId}
            id={"add_comment_" + entityId + (parentId ? "_reply_" + parentId : "")}
            value={"<p></p>"}
            workspaceSlug={workspaceSlug}
            projectId={projectId}
            onEnterKeyPress={(e) => {
              if (!isEmpty && !isSubmitting) {
                handleSubmit(onSubmit)(e);
              }
            }}
            ref={editorRef}
            // Isi awal editor saja; editor hanya membacanya saat dibuat.
            initialValue={initialHtml}
            isEmpty={isEmpty}
            containerClassName="min-h-min"
            onChange={(_comment_json, comment_html) => {
              setValue("comment_html", comment_html);
              setIsEmpty(isCommentEmpty(comment_html));
            }}
            accessSpecifier={accessValue ?? EIssueCommentAccessSpecifier.INTERNAL}
            handleAccessChange={onAccessChange}
            isSubmitting={isSubmitting}
            uploadFile={async (blockId, file) => {
              const { asset_id } = await activityOperations.uploadCommentAsset(blockId, file);
              setUploadedAssetIds((prev) => [...prev, asset_id]);
              return asset_id;
            }}
            duplicateFile={async (assetId: string) => {
              const { asset_id } = await activityOperations.duplicateCommentAsset(assetId);
              setUploadedAssetIds((prev) => [...prev, asset_id]);
              return asset_id;
            }}
            attachFiles={attachFiles}
            showToolbarInitially={showToolbarInitially}
            parentClassName="p-2"
            displayConfig={{
              fontSize: "small-font",
            }}
          />
        )}
      />
      {attachmentStatus}
    </div>
  );
});
