/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { pull, concat, update, uniq, set } from "lodash-es";
import { action, makeObservable, observable, runInAction } from "mobx";
// Plane Imports
import type { TIssueComment, TIssueCommentMap, TIssueCommentIdMap, TIssueServiceType } from "@plane/types";
// services
import { IssueCommentService } from "@/services/issue";
// types
import type { IIssueDetail } from "./root.store";

export type TCommentLoader = "fetch" | "create" | "update" | "delete" | "mutate" | undefined;

export interface IIssueCommentStoreActions {
  fetchComments: (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    loaderType?: TCommentLoader
  ) => Promise<TIssueComment[]>;
  createComment: (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    data: Partial<TIssueComment>
  ) => Promise<any>;
  updateComment: (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    commentId: string,
    data: Partial<TIssueComment>
  ) => Promise<any>;
  removeComment: (workspaceSlug: string, projectId: string, issueId: string, commentId: string) => Promise<any>;
}

export interface IIssueCommentStore extends IIssueCommentStoreActions {
  // observables
  loader: TCommentLoader;
  comments: TIssueCommentIdMap;
  commentMap: TIssueCommentMap;
  // helper methods
  getCommentsByIssueId: (issueId: string) => string[] | undefined;
  getCommentById: (activityId: string) => TIssueComment | undefined;
}

export class IssueCommentStore implements IIssueCommentStore {
  // observables
  loader: TCommentLoader = "fetch";
  comments: TIssueCommentIdMap = {};
  commentMap: TIssueCommentMap = {};
  serviceType;
  // newest created_at seen in a server response, per issue (not observable)
  private newestFetchedAt: Record<string, string> = {};
  // root store
  rootIssueDetail: IIssueDetail;
  // services
  issueCommentService;

  constructor(rootStore: IIssueDetail, serviceType: TIssueServiceType) {
    makeObservable(this, {
      // observables
      loader: observable.ref,
      comments: observable,
      commentMap: observable,
      // actions
      fetchComments: action,
      createComment: action,
      updateComment: action,
      removeComment: action,
    });
    // root store
    this.serviceType = serviceType;
    this.rootIssueDetail = rootStore;
    // services
    this.issueCommentService = new IssueCommentService(serviceType);
  }

  // helper methods
  getCommentsByIssueId = (issueId: string) => {
    if (!issueId) return undefined;
    return this.comments[issueId] ?? undefined;
  };

  getCommentById = (commentId: string) => {
    if (!commentId) return undefined;
    return this.commentMap[commentId] ?? undefined;
  };

  fetchComments = async (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    loaderType: TCommentLoader = "fetch"
  ) => {
    this.loader = loaderType;

    // Pull only what is newer than the last SERVER response, not than the last id in the list: a
    // comment or reply created from this tab is appended locally and can be newer than one by
    // someone else that has not been pulled yet; the list is deduplicated by id, so overlap is safe.
    const props = this.newestFetchedAt[issueId] ? { created_at__gt: this.newestFetchedAt[issueId] } : {};

    const comments = await this.issueCommentService.getIssueComments(workspaceSlug, projectId, issueId, props);

    const commentIds = comments.map((comment) => comment.id);
    comments.forEach((comment) => {
      const newest = this.newestFetchedAt[issueId];
      if (!newest || new Date(comment.created_at) > new Date(newest))
        this.newestFetchedAt[issueId] = comment.created_at;
    });
    runInAction(() => {
      update(this.comments, issueId, (_commentIds) => {
        if (!_commentIds) return commentIds;
        return uniq(concat(_commentIds, commentIds));
      });
      comments.forEach((comment) => {
        this.rootIssueDetail.commentReaction.applyCommentReactions(comment.id, comment?.comment_reactions || []);
        set(this.commentMap, comment.id, comment);
      });
      this.loader = undefined;
    });

    return comments;
  };

  createComment = async (workspaceSlug: string, projectId: string, issueId: string, data: Partial<TIssueComment>) => {
    const response = await this.issueCommentService.createIssueComment(workspaceSlug, projectId, issueId, data);

    runInAction(() => {
      update(this.comments, issueId, (_commentIds) => {
        if (!_commentIds) return [response.id];
        return uniq(concat(_commentIds, [response.id]));
      });
      set(this.commentMap, response.id, response);
    });

    return response;
  };

  updateComment = async (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    commentId: string,
    data: Partial<TIssueComment>
  ) => {
    try {
      runInAction(() => {
        Object.keys(data).forEach((key) => {
          set(this.commentMap, [commentId, key], data[key as keyof TIssueComment]);
        });
      });

      const response = await this.issueCommentService.patchIssueComment(
        workspaceSlug,
        projectId,
        issueId,
        commentId,
        data
      );

      runInAction(() => {
        set(this.commentMap, [commentId, "updated_at"], response.updated_at);
        set(this.commentMap, [commentId, "edited_at"], response.edited_at);
      });

      return response;
    } catch (error) {
      this.rootIssueDetail.activity.fetchActivities(workspaceSlug, projectId, issueId);
      throw error;
    }
  };

  removeComment = async (workspaceSlug: string, projectId: string, issueId: string, commentId: string) => {
    const response = await this.issueCommentService.deleteIssueComment(workspaceSlug, projectId, issueId, commentId);

    runInAction(() => {
      // The server deletes a comment together with its replies, so drop them here too.
      const replyIds = (this.comments[issueId] ?? []).filter((id) => this.commentMap[id]?.parent === commentId);
      pull(this.comments[issueId], commentId, ...replyIds);
      delete this.commentMap[commentId];
      replyIds.forEach((replyId) => delete this.commentMap[replyId]);
    });

    return response;
  };
}
