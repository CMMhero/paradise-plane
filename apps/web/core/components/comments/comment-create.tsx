/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useRef, useState } from "react";
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
  } = props;
  // states
  const [uploadedAssetIds, setUploadedAssetIds] = useState<string[]>([]);
  // refs
  const editorRef = useRef<EditorRefApi>(null);
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
      comment_html: "<p></p>",
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
      const comment = await activityOperations.createComment(formData);
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
      className={cn("sticky bottom-0 z-[4] bg-surface-1 sm:static")}
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
      <Controller
        name="access"
        control={control}
        render={({ field: { onChange: onAccessChange, value: accessValue } }) => (
          <LiteTextEditor
            editable
            workspaceId={workspaceId}
            id={"add_comment_" + entityId}
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
            initialValue="<p></p>"
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
