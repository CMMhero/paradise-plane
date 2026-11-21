# Wiki plan, Paradise Task Tracker

Status: **PLAN** (not yet executed). Written 2026-07-24.

Target: one company Wiki with a folder per division, where **the owning division
can edit and everyone else can only view**, and uploads of almost any file type up
to **100 MB**.

---

## The requested concept

Two layers of documentation:

| Layer                    | Who sees it                                  | Who edits it                           | Contents             |
| ------------------------ | -------------------------------------------- | -------------------------------------- | -------------------- |
| **Private per division** | only that division (or those granted access) | that division                          | division secrets     |
| **Public**               | all employees                                | only the division that owns the folder | general guides, SOPs |

Inside Public there is a "folder" per division. Example, the HR folder: **HR
uploads/edits/deletes, everyone else views**. Allowed files: jpg, png, mp4, mp3,
docx, xlsx, pdf, ppt, and so on.

The user's decision: **1 big Wiki with a folder per division** (not 1 project per
division), and **all file types including video, 100 MB limit**.

---

## Investigation findings (real code)

- **Private per division = ALREADY POSSIBLE without code.** Plane's private
  projects (`network=0`, "Secret") can only be seen by their members. The 16
  division projects are already private, so the Pages inside them are the
  division's secret wiki. Nothing to build.
- **Page permissions attach to the whole project, not per folder.**
  `ProjectPagePermission` (`apps/api/plane/app/permissions/page.py`): you must be
  a project member to get access; Guest=view, Member=edit, Admin=delete. Within
  one project, every member has the same edit rights, so "the HR folder is
  editable only by HR" is NOT supported natively.
- **The editor has no non-image file node.** `packages/editor` only has
  `image`/`custom-image`, and the slash command only offers "Image". Uploading
  pdf/docx/mp4 into a page means BUILDING a new editor node.
- **Page upload is image-only (hardcoded).** `apps/api/.../asset/v2.py` around
  line 342 (`WorkspaceFileAssetEndpoint`) and 544 (`ProjectAssetEndpoint`):
  `allowed_types` has only 5 image types. The full `ATTACHMENT_MIME_TYPES` list
  EXISTS in `settings/common.py` (pdf/docx/xlsx/ppt/mp4/mp3/zip) BUT is only used
  for Issue attachments (`issue/attachment.py:105`), not pages.
- **The size limit is 5 MB.** `FILE_SIZE_LIMIT=5242880`. The Caddy proxy uses the
  same env (`apps/proxy/Caddyfile.ce`: `max_size {$FILE_SIZE_LIMIT}`), so one knob
  controls both Caddy and Django's `DATA_UPLOAD_MAX_MEMORY_SIZE`.
- **Sub-pages are hidden in the UI.** The list filters `parent__isnull=True`
  (`apps/api/plane/app/views/page/base.py:97`), so a nested folder tree doesn't
  show without frontend work.
- **There is a hook to override permissions.** `page.py` provides
  `_check_access_and_get_role` and `_has_private_page_action_access` ("Override
  for feature flag logic"), an official extension point (used by the EE edition).

---

## Phase A, File upload (all types, 100 MB)

Needed whatever the wiki structure ends up being. Stands on its own.

| #   | Work                              | File                                                                                                                        | Size         | Risk   |
| --- | --------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------ | ------ |
| A1  | Open non-image types for pages    | `asset/v2.py` ~342 & ~544 → use `ATTACHMENT_MIME_TYPES` when `entity_type=PAGE_DESCRIPTION` (don't touch avatar/cover ~128) | small        | low    |
| A2  | 100 MB limit                      | `.env`: `FILE_SIZE_LIMIT=104857600` (applies to both Caddy and Django)                                                      | trivial      | low    |
| A3  | **New "File" node in the editor** | `packages/editor/.../extensions/custom-file/` (new) + a "File" slash command                                                | medium-large | medium |

A3 = an upload component, a file card (icon + name + download), an inline
mp4/mp3 player, and Yjs sync. The editor is shared by Issue/Page/Comment, so
don't break the others. **Lazy version:** file card + download only for now;
preview/inline player later.

## Phase B, Per-folder permissions (SECURITY SENSITIVE)

| #   | Work                  | How                                                                                                                                                                            | Risk     |
| --- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------- |
| B1  | Mark the folder owner | A new small model `page → owning division project` (borrow the 16 division projects, no new group concept) + a migration                                                       | low      |
| B2  | Enforce permissions   | Override `ProjectPagePermission` via the hook. Edit/delete: walk up to the parent folder, then check the user is a member of the owning division's project. View = all members | **high** |
| B3  | Set the folder owner  | A small endpoint, admin only                                                                                                                                                   | low      |

Required tests: a non-owner can't edit/delete another folder; sub-pages inherit
their parent's owner; moving a page between folders recalculates the owner;
creating a page under folder X checks folder X's owner (not just the project
role).

## Phase C, Folder tree in the UI

| #   | Work                                | How                                                                                      | Risk   |
| --- | ----------------------------------- | ---------------------------------------------------------------------------------------- | ------ |
| C1  | Show nested pages                   | Build a children endpoint + a tree sidebar (get around the `parent__isnull=True` filter) | medium |
| C2  | Edit/delete disabled for non-owners | The backend already refuses; the UI just stops offering the actions                      | small  |
| C3  | UI to set the folder owner          | admin only (pairs with B3)                                                               | small  |

---

## Important notes

- **This is a fork.** Phases B and C diverge from the original Plane code, so
  every Plane upgrade has to be reapplied and retested. Document it.
- **Everything goes through the CI pipeline** (`paradise-build` → GHCR →
  `deploy.sh`): every change = commit → ~7 minute build → deploy. Not instant.
- **Disk:** 100 MB × many people adds up to GBs fast. The production server (not
  yet in place) needs roomy SSD and disk monitoring.
- **Suggested order:** Phase A first (useful immediately, low risk, still needed
  even if the structure changes), then B, then C.

## A saving worth weighing

Before building the editor node (A3) and the ACL (B) from scratch, check whether
the paid Plane edition (EE) already has both so they can be ported, which would be
cheaper and better tested. The `upstream` repo we have is community only, so we'd
need to look at an EE reference.
