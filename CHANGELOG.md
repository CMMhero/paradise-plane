# Changelog, Paradise Task Tracker

Build history of the system, compiled from the commit log. Newest entries first.

Date format: YYYY-MM-DD. Commit references point to this repository.

---

## 2026-11-26

### Version 2.15.0

- **2.14.0 to 2.15.0, minor.** A new position level, a new export feature, one
  choices-only migration (`0187_tingkat_asisten_manager`) and one new API
  dependency (`markdown-it-py==4.2.0`, so the API image must be rebuilt). No
  data is rewritten. Operator step, only if wanted: give people the new position
  in God Mode > Members or Organization.
- **Assistant manager.** Level 25, between Supervisor (20) and Manager (30). It
  is placed in departments like a supervisor and outranks supervisors there.
  Rule defaults did not change, so an assistant manager's finished work still
  waits for approval (`APPROVAL_REQUIRED_BELOW_LEVEL` is 30), and directors'
  Needs attention does not list their items. God Mode rules that offered
  Supervisor and Manager now also offer Assistant manager.
- **Export to Excel.** Project, workspace view, Your work, module and project
  view lists download an `.xlsx` with the list's filters and order. List and
  export share one scoping function, so the export never holds rows the list
  would not show. Workspace guests cannot export. Above 10,000 rows the export
  is refused with a message.
- **Announcements.** Authors edit and delete their own posts on the
  Announcements page. The 24 hour chat window no longer applies to an author who
  may still post there. Admins cannot change other people's posts.
- **Announcement email.** The body was sent as raw Markdown. It is now rendered,
  the button opens `/pengumuman`, and God Mode > Email > Preview has a sample.
  The author still receives no copy.
- **Markdown in chat.** All text messages render Markdown. Mentions, references
  and bare links keep working. Previews, reply quotes and notification text show
  plain text. A `*` between digits stays an asterisk, and a plain line after a
  list leaves the list.
- **File cards.** Non-image files in descriptions and comments are cards. The
  sanitizer keeps a card only when it points at this app's own files. The
  attachment endpoint serves safe types inline for previews.
- **Mentions.** Cards inside the work item panel no longer close it, work item
  and channel chips open their target, and a mention added in a follow-up
  autosave of a description now creates its notification (the task crashed).

- **2.13.1 to 2.14.0, minor.** Notification housekeeping: a new daily job
  that touches existing inbox rows (it archives everything older than 7 days on
  its first run) and a changed default for what directors see in Needs
  attention. Old accounts keep working. No Django migration, no operator step.
  To keep every old notification, set God Mode > Work rules > Notifications >
  "Clean up inbox notifications older than" to 0 before the first 02:00 UTC run.
- **Dismiss all.** Needs attention has a Dismiss all button on the widget and on
  every group with more than one card. Mention cards are marked read in the
  inbox, the rest are hidden on this device like the single Dismiss. Only the
  cards on screen are dismissed; more cards behind the "+N more" line appear
  after the next refresh.
- **Directors in Needs attention.** The overdue team list of secretaries and
  directors now only holds work items created by managers and above, so work
  created by supervisors, leaders and staff is skipped. New rule in God Mode >
  Work rules > What each level sees: "Needs attention for directors: lowest
  creator level" (Manager by default, Supervisor gives the old list, Member
  lists everything). Supervisors and managers still see their whole team, and
  dashboards and the director report keep their own rule
  (`ORG_VIEW_LEADER_CREATED_ONLY`).
- **Inbox reads itself.** Opening the inbox, in the full view or the bell
  popover, marks the notifications of the current tab and filters as read after
  2.5 seconds. Closing it sooner cancels that. Mentions that become read leave
  Needs attention, as they always did.
- **Inbox cleanup.** A daily job (02:00 UTC) archives, or deletes, notifications
  older than N days, read or not. Snoozed ones wait for the snooze to end. Two
  new rules under God Mode > Work rules > Notifications and digests:
  "Clean up inbox notifications older than (days)" (7, 0 turns it off) and
  "What the inbox cleanup does" (Archive by default, Delete removes the rows).

---

### Version 2.13.1

- **2.13.0 to 2.13.1, patch.** Two fixes to what 2.13.0 shipped. No migration and
  no operator step.
- **Announcements page.** Leaving the page through a sidebar link changed the
  URL but kept the page on screen. The format buttons kept their state in the
  editor's parent, so every editor transaction re-rendered the whole editor.
  They now live in their own component and skip updates that change nothing.
  The write box also keeps the comment box padding (a bordered editor inside
  the card) instead of stripping it. Not reproduced in a browser: found by
  reading the code.
- **Home widget order.** New widget rows for members who already had Home
  widgets were numbered like fresh accounts, so Announcements landed above older
  widgets and Changelog tied with Quick links. They now go below every existing
  widget, Changelog last.

---

## 2026-11-22

### Version 2.13.0

- **2.12.1 to 2.13.0, minor.** A substantial new feature (the announcement
  editor), a data reshaping on production, and a role rename. Old accounts keep
  working. No Django migration. Operator step, already done on `space` on
  2026-11-22 before this release: `pecah_divisi` ran with
  `paradise/rencana/pecah-plant-cilegon.json`, with every manager seat left
  vacant. LOG, ENG, QAQC and HRL still need a manager: re-run the command with
  the original plan and `--manager KODE=<user>`.
- **Announcements.** The write box is now the comment editor: Markdown
  shortcuts, toolbar (bold, italic, underline, strikethrough, lists, quote,
  code), links and mentions. Enter starts a new paragraph, Ctrl or Cmd plus
  Enter publishes. Files and images are attached through the Attach file
  button, paste, or drag and drop, and travel as chat attachments (same count,
  size and type limits as chat, images open in the full screen viewer). The
  text is stored as Markdown in the message body, so Chat and email still read
  it as plain text. Old announcements are rendered the same way, with single
  line breaks and bare links preserved. Inline images are not supported.
  Announcement cards use the same card style as the other pages.
- **Home widgets.** Changelog is now a normal widget in Manage widgets (it used
  to be pinned under the list), and there is a new Announcements widget that
  shows the three latest announcements with a link to the page. Both can be
  switched off and reordered per person. They are new `WorkspaceHomePreference`
  keys (`announcements`, `changelog`) created on the next Home load, at the
  bottom, enabled by default; the God Mode rule "Home widgets and their order"
  lists them too. Show more in the Changelog widget now loads every release back
  to the oldest (the endpoint cap went from 50 to 1000). The Announcements
  widget follows the Chat module switch.
- **Sidebar.** "Show department list" and "Show limited departments" are gone
  from Customize navigation: the list always shows every department, and only
  the Super Admin's switch in God Mode can hide it. Pinning and unpinning
  Workspace group items is gone: every menu the person is allowed to use
  shows, and Customize navigation only reorders them. The "More" button and the
  panel behind it are removed (the Workspace extended sidebar was dead code
  after that; the project extended sidebar stays).
- **Branch Manager.** The Branch Director level (33) is renamed Branch Manager
  in God Mode, notification and visibility settings, API messages, the
  `jadikan_cabang` command and email. The stored level number and the
  `Direktur Cabang` choice label in the model are unchanged, so there is no
  migration.
- **Approval hold.** When staff move a work item to Done and it goes to
  approval, the item now waits in the In Progress group (the group set by the
  "return rejected work items to" rule, first state of that group) instead of
  staying in its old state. A new item created in Backlog and moved straight to
  Done used to sit in Backlog while waiting. An item already in a started state,
  for example In Review, stays where it is. Reject still returns to In Progress.
- **Org chart.** Department boxes in the God Mode chart list each supervisor by
  name with an avatar, the same way division boxes list their managers.
- **Plant Cilegon.** Division `PC` is split into Logistics (LOG, PPC),
  Engineering (ENG-ENG, RND-RND), Production (PRO, PO), QA QC (QQ), Maintenance
  (MTC), GA and HSE (GA, HSE) and HR and Legal (HR-CLG). 11 departments, 11
  boards and 295 work items kept their ids.

---

## 2026-11-21

### Version 2.12.1

- **2.12.0 to 2.12.1, patch.** Small display and flow fixes on touch screens
  and in the sidebar. No migration and no operator step.
- **Home on phones.** Sticky notes and the Changelog no longer stack on top of
  each other. The sticky masonry measured its container height once, but the
  sticky editor only grew afterwards, so the container came out too short and
  the release card was drawn under the sticky notes. The layout is now
  recalculated every time a sticky changes size.
- **Department requests.** The page has a "New request" button that always
  shows in the page header. The form opens from that button. When there is no
  target department yet (a department only counts when its Intake is on and
  you are not a member of it), the explanation appears inside the form instead
  of replacing the whole form with no button.
- **Sidebar.** Chat and Announcements moved to the top group (with Home and
  Drafts), above the Workspace group. They no longer appear in the Workspace
  group, the "More" panel, or the pinned list in Customize navigation. The
  "Departments" item inside the Workspace group is removed because it
  duplicated the department list below it. The department list itself is
  untouched.
- **Refresh button.** The button in the breadcrumb bar is removed. Both called
  `segarkanSemua()`, so one is enough: the one in the top navigation, since it
  is on every page and the breadcrumb bar is already crowded on phones.
- **Work item detail on phones.** The 36px horizontal padding on each side was
  too wide on narrow screens. It is now 16px on phones, 24px on small tablets,
  and 36px from md up. The overview peek and the properties panel shrink to
  match.
- **Images in the editor, touch screens.** Tapping an image opens it full
  screen, like the "full" button on desktop, instead of highlighting it in
  blue.

### Version 2.12.0

- **2.11.0 to 2.12.0, minor.** One new screen in God Mode (Work rules > All
  rules), and 89 product rules that used to be locked in code can now be
  changed from there, including permission rules. Every rule's default matches
  the 2.11.0 behavior exactly, so nothing changes until a Super Admin changes
  it. No migration and no operator step.
- **Rule registry.** `plane/utils/aturan/` declares each rule once (key, type,
  default, limits, label, help text, risk, when it applies). Values are stored
  in `InstanceConfiguration` and read through `aturan.get_*` with a 5-second
  per-process cache. A corrupt value falls back to the default. Rules that the
  UI uses are sent in `paradise_rules` on `/api/instances/`. Endpoints are
  `GET/PATCH /api/instances/rules/` and `POST .../reset/`. High-risk rules only
  change with the phrase `CHANGE RULES`, and every change is recorded in the
  audit log as `Rule: KEY`. The guide for adding a rule is in
  `paradise/god-mode-rules.md`. The old registries (`SAKLAR_BAWAAN`,
  `SETELAN_ANGKA`, `SETELAN_TEKS`) are untouched. The new screen shows them
  read-only with links to their own tabs.
- **What can be changed, by area.** Visibility: private work items, KPI scope,
  leadership statistics, who gets mention notifications, private wiki pages,
  the Director menu, the KPI tab. Actions: staff assignment rules, no assigning
  a superior, recipients must be placed, auto-assigning the creator, who can
  edit and comment, **which fields are locked for staff or opened to all
  members**, the Done lock and the level that can reopen, approval levels, new
  projects, overdue rule. Display: activity timeline order, filters, comment
  box position, work item list grouping and order, Home widgets and their
  order, KPI period. Notifications: notification groups per level, Director
  report, daily digest, reminder days, Announcements email, @all. Chat, wiki,
  quick links: who can write Announcements, create channels, use @all, make
  calls, upload to the wiki, manage shared links. Security: blocked file types,
  password strength, limits on login and API attempts, lifetime of sign-in
  codes and reset links, God Mode session. Display defaults apply to new
  accounts. The "Apply to existing members" button applies them to all members.
- **Security guardrails.** Every numeric rule in the security area has a lower
  and an upper bound, so it cannot be zeroed or made unlimited. Password
  strength cannot go below a score of 3. The file type list can only block
  (the deny list for scripts and executables is locked in code). The env
  settings `AUTHENTICATION_RATE_LIMIT`, `API_KEY_RATE_LIMIT`,
  `ADMIN_SESSION_COOKIE_AGE` and `SESSION_SAVE_EVERY_REQUEST` now only set the
  initial value, and are clamped to a safe range.
- **Deliberately not moved yet.** The organization-wide reach (35 or 40) and
  the oversight scope per level: the Secretary is added to every project as an
  admin and never removed, so changing the number would not narrow anything.
  That membership needs a decision first. Who may invite stays workspace admin.
  Limits that cannot be zeroed, data-leak disputes (the cross-division request
  projection), and data invariants (one project per department, overdue
  deadlines are not shifted) stay in code.
- **Old gaps found, not changed.** Work item changes through an API token
  (`api/views/issue.py`) bypass the work item edit rule. The email change code
  has no limit on wrong attempts. Data Analytics and the Division Dashboard are
  still served by the API to all members. The KPI tab rule only hides the tab.
- **Not tested in a browser.** The All rules screen, the sort buttons, and the
  web consumers of the rules were checked only with types and unit tests. After
  release, check the All rules screen, change one high-risk rule with the
  phrase, and reset it.

### Version 2.11.0

- **2.10.0 to 2.11.0, minor.** Many visible changes and two data migrations
  (0185, 0186), plus one operator command to split Plant Cilegon. Old accounts
  keep working. Operator steps:
  - Run the migrations. **0185 turns on Intake in all projects** (including
    ones an admin turned off on purpose) and creates their default inbox.
    **0186 fills empty assignees on staff-created work items with their
    creator**, including done and cancelled work items, except work items that
    ever had an assignee. Past KPI and workload numbers may shift. Preview
    first with `python manage.py isi_assignee_staf` (dry run).
  - Split Plant Cilegon: `pecah_divisi`, with the plan in
    `paradise/rencana/pecah-plant-cilegon.json` (seven divisions per the
    organization chart). **Back up the database first**, run the dry run, then
    `--apply`. This command does not run automatically on deploy.
- **Intake and cross-department requests.** Departments created in God Mode
  never got an Intake inbox, so the Intake list failed with "Intake not found"
  and the request target list was empty. The Intake inbox is now created in
  every project creation path and recreated if it goes missing. The target list
  only contains projects that are mapped to a department, have Intake on, are
  not archived, are not Wiki, and are not visible to guests. Supervisors and
  managers of the target department see incoming requests, with the sender's
  note. The Intake page explains the cause of an error (no access, Intake off,
  server error).
- **Division splitter.** `pecah_divisi` creates the new divisions in the same
  branch, moves departments (id and work board stay), sets managers through the
  same helper as God Mode, then deletes the empty source division. The old
  division's wiki folder is detached (not deleted). Shared quick links that
  were only for the old division become invisible to everyone, and their titles
  are printed.
- **Director sees Your work again.** Archives stay hidden.
- **The Department menu can be turned off.** An admin turns it off for everyone
  in God Mode > Modules > Visibility, and each member can hide it for
  themselves in Customize navigation. Announcements can now be pinned and
  unpinned, and are pinned by default.
- **Image viewer.** Images in descriptions, comments, work item attachments,
  and chat can be browsed with arrows, buttons, or swipe, without closing the
  viewer. The shared component `@plane/propel/image-gallery` replaces the
  editor lightbox.
- **Quick link icons from a URL.** The server downloads an https image (PNG,
  JPEG, WebP, GIF, 150 KB max, 8 seconds) and stores a copy as a data URI.
  `emoji.url` must now be https or `data:image`.
- **God Mode.** Retention for API, webhook, and email logs and the Wiki preview
  limit are now God Mode settings. One menu registry (`paradise-navigation.ts`)
  drives the sidebar, module defaults, Power-K, and the God Mode menu, with a
  test that fails if any of them drift apart. Organization layout: the
  statistics cards wrap, the Levels board has two rows, and the chart supports
  two-finger pinch.
- **Phones.** Below 768px the text size goes up one step, and buttons, tabs,
  and input fields have a 40 to 44px tap area, in the app and in God Mode.
  Notifications appear at the top so they do not cover the Add and Cancel
  buttons. The cross-department requests, Announcements, and Quick links pages
  now have a page title through `PageShell`.
- **Other fixes.** The `pengumuman_ui.title` and `other` texts showed up raw
  because the keys never existed. A new test compares all static keys against
  en and id. Guests are no longer asked to pick a department. The Power-K
  command for Announcements is named "Go to announcements". The Approvals page
  filter no longer overlaps the button on phones.
- **Not tested on a real phone or a production build.** Browser testing used
  Chromium on a copy of the dev database. Open question: an Announcements item
  removed from Customize navigation still shows in the sidebar (Paradise menus
  always show). Either the unpin button should be hidden or it should be
  honored.

---

## 2026-11-20

### Version 2.10.0

- **2.9.0 to 2.10.0, minor.** A new page (Announcements), a KPI menu that
  merges three menus, a change in who sees what (Director), and a changed
  overdue rule. No migration and no required database step. One operator step
  on the server, see the God Mode item.
- **God Mode can be opened from anywhere.** After signing in through
  `space.paradiseperkasa.com/god-mode/`, the browser used to be thrown to a
  local IP address because `ADMIN_BASE_URL` on the server holds an IP. The
  redirect now returns to the address the browser is currently using (from the
  `Origin` header, then the request host), and only if that address is already
  registered in `WEB_URL`, `APP_BASE_URL`, `ADMIN_BASE_URL`, `SPACE_BASE_URL`,
  or `CORS_ALLOWED_ORIGINS`, so it cannot become an open redirect. Signing in
  by IP on the LAN still lands on the IP. A new tenant is no longer redirected
  to `/god-mode/god-mode/`. `deploy.sh` now warns when `ADMIN_BASE_URL` or
  `SPACE_BASE_URL` differs from `WEB_URL`. Recommended operator step: in
  `~/paradise-app/apps/api/.env` and `~/paradise-app/.env`, change
  `ADMIN_BASE_URL` and `SPACE_BASE_URL` to `https://space.paradiseperkasa.com`,
  then recreate the `api` container. Leave `CORS_ALLOWED_ORIGINS` and
  `SITE_ADDRESS` alone. Code: `plane/utils/host.py`.
- **One KPI menu.** Analytics, Dashboards, and KPI are merged into one KPI menu
  with KPI, Analytics, and Dashboards tabs. The Analytics and Dashboards tabs
  only show for admins who are not a Director. The old addresses `/analytics`,
  `/dashboard-divisi`, and `/dashboards` redirect to the matching tab.
- **Director no longer sees Your work and Archives.** The Director (level 40)
  does not see "Your work" and "Archives", and opening them by direct address
  redirects to home. Other levels are unchanged. Code: `use-is-direktur.ts`,
  `isDirektur()` in `hierarki.service.ts`.
- **Changelog moved to Home, Announcements got its own page.** The Changelog is
  now a widget at the bottom of Home and no longer shows up in Chat: members
  are no longer auto-subscribed to the Changelog channel, and the channel is
  hidden from the list, search, and badges. Old cards stay in the database and
  the widget reads them through `GET /api/workspaces/<slug>/changelog/`. The
  new page `/<slug>/pengumuman` shows announcements, with a write box for
  people allowed to broadcast. The author rule and the Announcements email are
  unchanged.
- **Overdue is counted from when the work item was recorded.** A work item
  created today with a deadline last week, then submitted for approval right
  away today, used to count as overdue. New rule: the effective deadline is the
  later of the deadline and the office date when the work item was recorded. It
  is overdue if it was completed after that effective deadline. Work items
  recorded before their deadline are unchanged. One function,
  `utils/ketepatan_waktu.py`, is used by the completion report, KPI, and the
  Division Dashboard. No new column. Undecided question: a work item recorded
  on Friday night and submitted on Monday is still three days overdue. If a
  grace period is needed, change it in that one place.
- **Scroll.** `h-screen` is replaced with `h-dvh` in about 13 full-screen
  shells so the bottom is not covered by the browser bar on phones. Settings
  pages are no longer cut off below the navigation on small screens. Popovers
  and right-click menus have a capped height and can scroll. The loader and
  error states of the peek panel use `h-full`. Not tested in a real browser.
  After release, check settings, tall filters, and right-click menus on a
  phone.

### Version 2.9.0

- **2.8.0 to 2.9.0, minor.** Many new features (KPI, the Approvals page,
  private work items, the Leader level, branches and Branch Director,
  Announcements authors, the wiki folder editor), permission changes (Done work
  items locked, cannot assign a superior), and eight migrations (0177 to 0181,
  0183, 0184). Operator steps:
  - Run the migrations. **0181 permanently deletes** all "Paradise" chat rooms
    (`kabar:<user>`) along with their messages. It cannot be undone. Back up the
    database first.
  - Restart the Celery workers after deploy. Chat cards and Announcements
    emails are created in the worker, and old workers keep running old code.
  - Set up SMTP in God Mode if you have not. Without SMTP, Announcements emails
    are only logged as "SMTP not set".
  - In Announcements > settings > "Who can write", add the HR department (or
    whoever may broadcast).
  - Place Leaders through the Organization board in God Mode.
  - Migration 0184 adds branches. To make Plant Cilegon a branch:
    `python manage.py jadikan_cabang --divisi PC --kode CLG --nama "Plant Cilegon"
    [--direktur-cabang <email>] --dry-run`, check the plan, then run it without
    `--dry-run`. The counts of departments, projects, work items, and people in
    PC must be the same before and after. Running it again must print "Nothing
    to change". After that, split PC into the branch divisions in God Mode.
- **Branches and Branch Director (33).** A new Branch > Division > Department
  structure. A division without a branch is head office. The Branch Director
  sits between Manager (30) and Secretary (35): they see, approve, assign, and
  get KPI only in their branch. The Director and Secretary still reach all
  branches. Head office Managers and Supervisors do not see branches. God Mode
  can create branches, move divisions into a branch, and place the Branch
  Director. Each branch has its own chat channel. Code: `utils/cabang.py`, the
  `jadikan_cabang` command.
- **Cannot assign a superior.** Anyone with a level cannot make a person of a
  higher level an assignee, including workspace admins who have a level, when
  the gate is off, when `ASSIGN_DOWN_ONLY` is off, through sub-items promoted to
  the parent, and through a project's default assignee. Peers at the same level
  work as before. Only Super Admins and admins without a level are exempt. The
  assignee picker no longer offers superiors. This reverses the first-round
  rule that an admin placed as Staff is still a full admin outside their
  department. Code: `utils/atasan.py`.
- **No refresh when switching tabs or windows.** Window focus no longer
  triggers a refetch. Returning to a tab after less than 5 minutes only pulls
  what changed according to that time signal. After more than 5 minutes there
  is one silent refresh, with no loading screen and no scroll back to the top.
  Polling stops when the window is not focused. The fallback when the socket
  drops is now every 120 seconds, and only while the window is focused.
- **Instant chat read markers.** Opening a chat immediately lowers the badge
  and the unread count, and the sender sees the double check in about one
  second through the `baca` event on the socket. A hidden tab no longer marks
  messages as read.
- **API Lint CI is green.** The ruff exclusion pattern for test files was
  written wrong (`tests/*` never matched `plane/tests/...`). Overlong lines were
  tidied without changing behavior.
- **Leader level (12).** Between Staff and Supervisor, placed per department. A
  Leader may assign Staff in their department and edit their work items. A
  Leader's own work item completion still needs Supervisor approval, and a
  Leader does not approve. The value is 12, not 15, so the `_SALAH_KAPAL` guard
  (15 is a project role) stays intact.
- **Done work items are locked.** Nobody can change the content of a work item
  in Done status, including admins and Super Admins: fields, description,
  comments, reactions, links, attachments, sub-items, relations. The only thing
  allowed is reopening (moving it out of Done), by the superior of all
  assignees, a workspace admin, or a Super Admin. The approval flow keeps
  working. Code: `utils/kunci_selesai.py`.
- **Admins with a Staff level follow Staff rules in their department.** The
  create work item form fills in themselves as assignee right away, and they
  must stay in the list. In other departments the admin is still free. This
  reverses the 12 Nov rule that a Super Admin placed as Staff may assign
  anyone.
- **Private work items.** Only visible to the assignee, the creator, the
  assignee's direct superior (including Leader), and Super Admins. Hidden from
  lists, detail (404), search, notifications, chat cards, export, API v1, and
  space. Still counted in KPI numbers and the Division Dashboard. Code:
  `utils/akses_privat.py`.
- **Workspace Approvals page.** One page for everything awaiting a decision
  from Supervisors, Managers, Secretaries, and Directors across all the
  departments and divisions they oversee: completion approvals and
  cross-department requests. Grouped by division, then department. Staff do
  not see the menu. This reverses the 2026-10-16 decision that moved the queue
  to a per-division tab (that tab stays).
- **Cross-department requests are back in the sidebar.** Anyone can request a
  work item from another department. The request goes into the target Intake
  and shows up on the Approvals page. Once accepted, it becomes a normal work
  item. The requester sees the status and rejection reason under "My requests",
  and gets notified in the inbox. This page used to load repeatedly without end
  because `t` from `useTranslation` changed on every render. `t` is now
  memoized in the hook.
- **Director numbers only from work items created by Supervisor and above.**
  The Director and Secretary no longer count work items created by Staff or
  Leader in the Division Dashboard, Needs Attention, Reports, and the director
  email digest. Supervisors and Managers still see the full numbers. Code:
  `utils/statistik_pimpinan.py`.
- **KPI dashboard for everyone.** Completed, on-time rate, overdue, open
  workload, cycle time, approval outcomes, working hours, and the trend per
  period. Staff see themselves, Leaders and Supervisors their department,
  Managers their division, and Secretaries, Directors, and admins the whole
  organization. Code: `utils/kinerja.py`.
- **The "Paradise" room is removed.** Cards from human actors still go to DMs.
  Cards without a human actor, channel mentions, and "added to project" no
  longer go to chat, but stay in the Inbox and email.
- **Chat cards show text, not HTML.** Comments, mentions, and descriptions show
  as plain text with `@Name`. Old cards that still contain HTML are cleaned up
  when displayed. Code: `utils/teks_html.py`.
- **Announcements with email.** An admin picks the departments (or people) who
  may write. Every new post is emailed to all members except the author. There
  is a per-user switch "Announcements email", on by default.
- **Wiki folder editors.** An admin can give a folder (for example QMS) a list
  of editors. In that folder only editors and admins can write, and others can
  only view. Subfolders inherit. "New folder" now asks for a name first.
- **Activity order is now an account preference**, newest on top by default.
  Change it in Profile > Preferences or with the order button in the timeline.
- **Delete confirmation** for comments and replies, personal quick links, work
  item and module links, removing a sub-item, removing a relation, the
  workspace logo, time entries, and removing an integration.
- **Needs Attention cards on Home are actionable.** Approve or reject, change
  state, quick reply to mentions, open, and mark as read.
- **Chat:** the message list can no longer scroll below the write box.
- **Tested.** Full pytest suite: 2616 passed (355 more than `main`), 44 failed,
  exactly the same as `main` before the changes. 58 live scenarios (desktop and
  phone) were run in the browser with screenshots.

## 2026-11-17

### Version 2.8.0

- **2.7.1 to 2.8.0, minor.** The rules for who may assign, comment, and be
  notified changed (a permission change), plus one migration without DDL
  (0176). No data was reshaped and there are no new env variables. Operator
  step: check the project visibility default in God Mode. A new department is
  now always private regardless of the default.
- **The work item creator automatically becomes the assignee.** Anyone who
  creates a work item without picking an assignee becomes its assignee,
  including admins and Super Admins, and this no longer depends on the approval
  gate switch. It applies in web, quick-add, sub-work item, draft, intake, and
  API v1. A creator who is not placed in that department gets no assignee and
  no error.
- **Comments and reactions follow edit rights.** Only the assignee, the
  creator, and the supervisor, manager, secretary, and director above them (and
  admins) may comment, reply, or react on someone else's work item. The rule is
  the same function as the edit rule (`galat_percakapan_tugas`), so the two
  cannot differ. On the web the comment box and the reaction button are hidden.
- **Assignees are only people actually placed in that department.** An admin or
  Super Admin who merely has access cannot be assigned. Staff through director
  can, and assignment only goes to levels below the assigner. Checked on the
  server (`galat_penugasan`, `galat_tambah_rekan`) and in the assignee picker
  list. Existing assignees on existing work items are not rechecked.
- **Update notices are merged into one per window.** Consecutive changes by the
  same person on the same work item now become one inbox row, one chat card,
  and one email per `EMAIL_BATCH_DELAY_MINUTES` window, not just for
  single-value fields. Consecutive comments become "N new comments". Still
  immediate: @mentions, assignment to a recipient, new work items, replies, and
  approvals. Code: `utils/gabung_kabar.py`.
- **Anyone can be mentioned, notices only go to those concerned.** Anyone can
  be @-mentioned in comments and descriptions, but only active members of that
  project (and the director or secretary) receive a notification, email, or chat
  card, or are auto-subscribed. The @ picker shows a hint "will not be
  notified". Code: `utils/jangkauan_sebutan.py`.
- **New departments and projects are always private.** A project created from a
  department sends private explicitly, so a God Mode default that was stored as
  Public no longer opens it. The model column default and the web form are also
  private. Existing projects are unchanged.
- **Not tested.** The pytest suite could not be run on the author's machine (no
  Docker/Django). Run the full suite before release.

## 2026-11-15

### Version 2.7.1

- **2.7.0 to 2.7.1, patch.** An audit of display, layout, accessibility, and
  performance. All small fixes and refinements, with no migration and no new
  env variables. Operator step: none.
- **Tablets no longer open with the sidebar covering the content.** The sidebar
  floats below 1024px, but its backdrop still used a 768px threshold, so at
  768-1023px the sidebar opened over the content and then collapsed after the
  first render. The threshold is now consistent, and the initial state is
  computed from the first render. Median layout shift (CLS) on tablets dropped
  from 0.20 to 0. Pages with CLS above 0.1 dropped from 28 to 1 (out of 186
  captures).
- **Input fields no longer trigger auto-zoom on iOS** (16px font on touch
  devices). Enter in the chat box adds a new line on phones (send with the
  button) and does not send while an IME is still composing.
- **The unhandled `undefined` error in all work item views is gone.** List
  requests cancelled by a newer request were rethrown as a rejection with no
  reason. They are now skipped. Real errors are still thrown.
- **Accessibility, zero axe violations.** From 151 of 155 page loads with
  serious or critical violations to 0 across 31 pages, mobile and desktop,
  light and dark. This covers names for icon buttons (`IconButton` now requires
  `aria-label`), three-dot menus, menus no longer nested inside buttons, form
  labels, 24px touch targets, the department picker dialog and call screen
  with focus traps, the combobox pattern for the @ picker, `aria-pressed` on
  the mic and camera, and pop-up notifications that stop closing themselves
  while focused.
- **Color contrast.** Danger, success, and warning text in the dark theme used
  step 900, which flips to pale pink in Plane's dark palette, so overdue dates
  looked white. It now uses step 700 (contrast 5:1 or more). Tertiary text and
  placeholders in the light theme are slightly darker. In the division
  dashboard the progress bars follow the status, the summary banner uses one
  token pair in both themes, and the "Updated" clock uses the profile time zone.
  The chat unread badge uses solid red.
- **Responsive.** Work item list rows on tablets stack the title above the
  chips (the title used to be cut to "Dok..."). Empty kanban columns narrow
  (80vw with scroll-snap on phones). The phone calendar marks days and picks
  the nearest working day. Three toolbars on phones become one. Project tabs
  have a fade hint at the edge. The profile form, Initiatives, and
  cross-division page padding fit at 390px. Work item detail on phones puts
  Properties right after the description. Intake and Notifications use separate
  panels from tablet up. `vh` is replaced with `dvh`.
- **Performance (production build, 4x CPU and Fast 4G).** First-load JS on the
  work item page dropped from 1978 to 1386 KB gzip (about 28 percent across
  all workspace routes): the rich text editor loads when used, the chart
  library no longer comes along on the work item and module pages, and the chat
  image viewer and `file-type` load when needed. Chat bubbles are memoized so
  the 5-second polling does not rerender the whole conversation, and the call
  UI is lazy-loaded.
- **Text:** the "Initiatives" and "Dashboard Divisi" titles now go through
  i18n. The @ picker translates "loading" and "no results". "Add Module" and
  "Add quick Link" become lowercase inside sentences.
- **Screenshots:** `docs/ui-audit/` holds 186 before and after captures (31
  pages x 3 sizes x light/dark) with axe and performance metrics. The capture
  scripts are in `scripts/ui-audit/`.

## 2026-11-13

### Version 2.7.0

- **2.6.1 to 2.7.0, minor.** New user-visible features (live screens, comment
  replies, the Secretary level) and one additive migration
  (`0175_tingkat_sekretaris`, which only changes column choices and leaves old
  data untouched). Operator step: none. `apps/live` is rebuilt too because it
  forwards the new signal, and the existing Redis is used as is.
- **Live screens without F5 (KEP-102).** Lists, boards, calendars, work item
  detail, notifications, and project membership refresh themselves when someone
  else changes them. Django publishes a small hint (id only) to Redis,
  `apps/live` forwards it only to people who may see it, and the browser
  refetches through the normal API. There is a refresh button in the top bar
  that refreshes the screen content without reloading the page. When the socket
  drops, a refresh runs every 45 seconds.
- **Comment replies (KEP-103).** Comments can be replied to, replies nest under
  the parent comment, the parent author is notified once (not twice if also
  mentioned), and deleting the parent deletes its replies.
- **Secretary level (KEP-101).** Level 35 between Manager and Director:
  organization-wide reach like the Director, but cannot assign the Director.
  The profile card now shows the level even if the person is not placed in a
  department.
- **More reliable attachments (KEP-104).** File type no longer depends on the
  user's OS registry, upload failures show as a translated toast instead of
  staying silent, transient failures are retried, cancelled uploads are not
  counted as successful, and picking the same file twice works again.
- **Fully i18n onboarding (KEP-105).** All onboarding steps, the tour, the
  greeting, and the password fields use translation keys in 19 languages. New
  workspaces are filled with sample projects in the owner's language. The
  `check:onboarding` guard script fails if any onboarding text is hardcoded.

## 2026-11-12

### Version 2.6.1

- **2.6.0 to 2.6.1, patch.** Small fixes and refinements, with no migration and
  no new env variables. Operator step: none. At the same time the version
  scheme was changed (see the next item), so old release numbers were
  renumbered.
- **Version scheme fixed and history renumbered.** Patch (x.y.Z) for small
  changes, minor (x.Y.0) for big changes, major (X.0.0) only for major
  overhauls. The releases that used to be numbered 3.0.0, 4.0.0, 4.1.0, and
  4.2.0 are now 2.3.0, 2.4.0, 2.5.0, and 2.6.0 (the old 2.3.0 never shipped on
  its own and merged into 3.0.0). Changelog cards already published in each
  workspace were renumbered too by `catatan_rilis.terbitkan` when the API
  starts, with no duplicate cards. The git tags `p3.0.0`..`p4.2.0` were
  replaced by `p2.4.0`..`p2.6.0`. The new rule is in AGENTS.md > Versioning.
- **Approvals no longer leave duplicate status rows.** When a superior approves,
  the activity log only records "approved". The "set state to Done" row, the
  chat card "updated your work item", and the inbox notification that repeated
  the same thing are no longer created. A rejection still records the state
  move.
- **Approval decisions reach all assignees.** Before, only the requester got
  the "approved"/"rejected" email and card, and fellow assignees did not. Now
  the requester and all assignees of that work item get it (except the one who
  decided).
- **The @ picker shows people outside the department.** They appear grayed out
  in the "Outside this department" section and cannot be picked, so the names
  of colleagues from other departments no longer look missing. Only shows after
  typing.
- **The parent picker prefers work items that already have sub-items.** Applies
  in the create work item form and in work item detail.
- **Super Admins can set assignees on any work item** without being rejected
  with "Staff may only invite peers", and the failed-edit toast shows the
  reason from the server.

### Version 2.6.0

- **2.5.0 to 2.6.0, minor (formerly numbered 4.2.0).** New user-visible
  features and rules, plus one data migration (0174, no schema). No data was
  reshaped and there are no new env variables, so not a major. Operator step:
  not required. One thing to check: a project visibility default in God Mode
  (Defaults > Project) that HAS been saved before still wins over the new
  factory default. If it is saved as "Public", change it to "Private" once.
- **Child assignees go up to the parent and module (KEP-98).** A person
  assigned on a sub-work item automatically becomes an assignee of its parent
  (chained up to the grandparent) and a member of the module those work items
  are in, including the parent's module. Add-only: removing an assignee from
  the child does not remove them from the parent. Called from the create/edit
  work item serializers (web and API v1), add sub-work item, and add work item
  to module. It does not go through the assignment gate because it derives from
  the child's assignment, which already passed. Code:
  `plane/utils/naik_assignee.py`. Old data is not backfilled.
- **Adding sub-work items to someone else's parent.** Staff who is the creator
  or assignee of one of a work item's children may now add sub-work items to
  its parent. Before, `POST .../sub-issues/` was rejected with 403 because the
  parent was not theirs by creation or assignment, so people had to create a
  new work item and then set the parent through the form. It only adds
  children: the parent's title, description, and assignees stay view-only, and
  a work item made into a child must still be one's own. Server:
  `terlibat_di_anak` in `utils/task_access.py`; web: `useTerlibatDiAnak` and
  the `subIssueDisabled` prop in the work item widget.
- **New projects and departments are private.** The factory default for
  project visibility is now Private, and projects created from a department
  (God Mode) follow that default, no longer Public from the column default.
- **Director only for work items created by manager and above.** Completion
  approval requests for ordinary work items (created by a supervisor, staff, or
  with no creator) no longer show up for the director: not in the queue, the
  Needs attention widget, the Division Dashboard, notifications, or deadline
  reminders, and a director's POST approve/reject is rejected with 403. It is
  the creator of the WORK ITEM that counts, not the requester. One rule in
  `saring_penyetuju` and `pengajuan_boleh_diputuskan` (the request key is now
  `(project, pemohon, pembuat)`). A division with no superior at all still
  falls to the Super Admin, not the director.
- **Department, project, and Wiki folder are one unit.** Renaming a department
  in God Mode now renames its project, and the department's Wiki folder carries
  its project's icon (a hand-picked icon on that folder is no longer saved). A
  name already used by another project is rejected with 400 before saving. The
  project identifier (the code in work item numbers) deliberately does not
  follow the department code. Migration 0174 aligns existing data; conflicting
  names are skipped.

## 2026-11-09

### Version 2.5.0

- **Bump from 2.4.0 to 2.5.0, minor (previously numbered 4.1.0).** There are new user-visible features
  (department pages and content search in the Wiki, file preview, the
  workspace Views page, an approval column) and one additive migration (0172, two
  columns with default values, the `pg_trgm` extension, two indexes). No data
  is reshaped and there are no new env variables, so this is not a major.
  Operator step: not required. Existing Wiki material only joins content search
  after `docker exec api python manage.py wiki_indeks_ulang` has been run
  once; new uploads index themselves.
- **Follow-ups in the same version (Nov 9).** After the initial 4.1.0 release, the changes
  below went into 4.1.0 at the user's decision (version not bumped). No
  migration, no new env variables, no operator step.
- **Refresh button.** In the header of every page. One click re-runs
  all SWR data the screen is currently using (work item lists, approval
  queue, badges) without reloading the page. Component:
  `core/components/common/refresh-button.tsx`.
- **The retention warning email is no longer daily, and the interval is set by the Super
  Admin.** After the third month there is always a row in the 7-day window, so
  the warning fired every day forever. The interval is now the God Mode setting
  `ADMIN_RETENTION_EMAIL_INTERVAL_DAYS` (Notifications > Sending, default 7
  days, 1 to 365; **0 = follow the login history retention period**, so a 90-day
  retention means one email every 90 days). A count that jumps to double
  or more (for example when retention is shortened) is sent sooner, but not
  twice a day. The last-sent marker is in the cache and is only written if the
  email was actually sent, so a dead SMTP server does not block tomorrow's attempt. Trash
  retention has no warning email, so this setting only concerns login
  history.
- **Rejected label.** "Rejected - needs revision" becomes "Rejected" (Indonesian:
  "Ditolak") in 19 locales.
- **The Module picker height in work item detail** now matches the State picker.
- **The parent of a work item is clickable** from the Parent property, including for other
  people's work items that are view-only (the link used to sit inside a disabled
  button, so it was dead). Opens in the same tab.

- **Django 4.2 to 5.2 and DRF 3.18.** Support for 4.2 has ended. Migration 0173
  only changes state (`through_fields` on three M2Ms), no SQL. Needs
  PostgreSQL 14 or newer; the production server runs 15.7. This code can no longer run
  on Django 4.2, so rolling back means reinstalling the old image.
- **Moved to Vite+.** Package scripts now call `vp lint`, `vp fmt`,
  `vp pack`, `vp test`; Turbo, the Dockerfile, and CI are unchanged.
- **Seven fixes from upstream Plane.** Date range filters on created_at
  and updated_at, recovery from stale asset errors, the drop zone in Kanban,
  per-layout error boundaries, notification service fixes, and the click-outside
  hook and dropdown.
- **Wiki.** Department folders show the department's project pages
  (read-only, permission enforced on the server). Search forgives typos
  and searches the contents of files and pages. Text, Markdown, CSV, Excel, and
  Word files are previewed in the app without PDF conversion, as structured
  JSON blocks (never HTML).
- **Views.** The workspace Views page lists the department views that person is allowed
  to open; filtering happens on the server. The view form and the view list were reworked.
- **Chat.** The conversation list is sorted: unread first, then online,
  then the rest. Work item cards use the work item title.

---

## 2026-11-05

### Version 2.4.0

- **Bump from 2.3.0 to 2.4.0, minor (previously numbered 4.0.0).** 3.1.0 was never
  released; per-place roles (KEP-93) became a release of their own because migration 0169 reshapes
  existing placement rows and the meaning of permissions changes. Operator step:
  nothing manual (deploy.sh runs 0169), but after deploy check
  the Organization board: a manager who used to sit in a department of another division is now
  recorded as Supervisor there, and their row in their own division's department
  is revoked. `PengawasanDivisi` data and explicit project memberships are NOT
  deleted.
- **Per-place roles (KEP-93).** A department row carries the person's role in that
  department (Staff/Supervisor, never Manager). Every authority decision on a project
  uses the role in the place that reaches that project
  (`tingkat_anggota(..., project_id)`, `peta_tingkat(..., project_id)`), so a
  manager of division A who sits as Staff in a department of division B is only staff in
  B. The person's level = their highest role; a manager without a division keeps their
  level in a row with no place.
- **No department managers.** Adding a manager to a department in a division
  they lead is rejected (400 `sudah-memimpin-divisi`); leading a division releases the
  departments inside it (`departemen_dilepas`). For a department in another division:
  the board asks for the role (Staff/Supervisor) through a dialog.
- **Organization board.** The Levels lane shows its members (fixed box,
  scrollable) and they can be dragged. Only the Director lane accepts drops;
  Staff/Supervisor are managed in the department lane, Manager through the division. The
  "Managers" lane on the department card is removed. Drag from People = add, from the
  structure = move (now also across types); a manager dragged FROM THE STRUCTURE to
  their own division's department = demoted (leaves the division, `pertahankan_peran`),
  from People it stays locked. A director dragged to People = drops to Staff. The People
  panel is sticky from md, the Managers zone is styled like a lane, department cards have no
  frame, the New division button is at the end of the list.
- **Removed: Other project access and Supervised divisions** in the member
  editor. Placements are shown read-only; change them on the board. The resolver no longer
  reads `PengawasanDivisi`, and a POST to `pengawasan` is rejected with 400.
- **Previously prepared as 3.1.0 (minor):** new chat features plus
  one additive migration (0167, a new nullable column, runs by itself on
  deploy).
- **Migrations and the changelog are no longer run by hand.** Production:
  `deploy.sh` makes sure there are zero pending migrations from inside the new `api` and
  publishes the changelog, with errors that fail the deploy; `rilis.sh`
  refuses a commit without `release_notes/<version>.json` or a CHANGELOG entry.
  Local: `api` applies migrations on its own at start (no longer stuck
  waiting for the migrator), then `plane/db/sinkron_lokal.py` applies new
  migrations and the changelog a few seconds after the file is saved. Migration 0168
  aligns the `user_timezone` choices with the pinned pytz (SQL no-op),
  so `makemigrations --check` is clean and can serve as a gate.
- **The 3.0.0 release notes are dated 2026-11-04**, not 05 (the file was written
  a day after the release). A Changelog card that has already been published now follows
  its file when the file is corrected (`selaraskan()`), with no new card
  and no unread badge; production corrects itself on deploy.
- **Automatic local gates.** pre-commit: ruff rejects new errors in staged `.py`
  files (compared to HEAD) and runs `makemigrations --check` when models
  change. pre-push: `turbo check:format check:lint check:types --affected`
  like CI, plus the release notes. Emergency bypass: `PARADISE_LEWATI_CEK=1`.
- **@all, self, #channel, and #work item mentions (KEP-91).** In chat,
  descriptions, and comments: `@` offers people, yourself, and `@all`;
  `#` offers channels and work items. The server filters to what the sender is allowed to see
  (private channels: members only; work items: projects they belong to),
  then masks a private channel's name as `#private-channel` for readers
  who are not members, in the bubble, quote, pin, search, card, inbox,
  and email. `@all` in a channel sends a mention card to all members; in a
  description/comment it sends a mention notification to all project members
  without making them subscribers. New endpoints `chat/rujukan/` and
  `chat/rujukan/info/`. The hint `@ mention · # channel or work item` shows in the
  placeholder of the chat, comment, and description input while it is empty.
  Hover a mention for a preview card: person = the existing profile card (now
  opens on hover), channel = name, public/private, topic, member count, work item = number, project, title, state, priority, due date,
  assignee. `chat/rujukan/info/` also carries the card's data
  (new `HoverCard` component in `@plane/propel/popover`, Base UI PreviewCard).
  The profile card no longer prints the "Division"/"Department" label on each unit;
  the building icon already marks the placement.
  No migration. Also fixed: description mention emails used to be
  addressed to a leftover loop variable (`subscriber`), not the person mentioned.
- **Pin, copy, and quick reactions in chat (KEP-87).** Members who can write in a room
  can pin anyone's message (Announcements: admin only,
  Changelog: not possible), at most 20 per room, shown in the top bar of the
  conversation. Columns `disematkan_pada`/`disematkan_oleh` on `PesanLangsung`
  (migration 0167), endpoints `chat/pesan/<id>/sematkan/` and
  `chat/ruang/<id>/sematan/`, WebSocket broadcast `sematan`. The message menu gets
  Copy, plus a quick reaction row and the full emoji picker; on
  touch screens via long press.
- **Tighter chat bubbles.** The wide spacing between messages turned out to come from an
  invisible action bar (`opacity-0`) that still took up ~30px below each
  message. That bar is removed: the actions (quick reaction, Reply, Copy, Pin,
  Edit, Delete) moved to the right-click / long-press / Shift+F10 menu, plus a
  floating emoji button and "..." beside the bubble on hover.
  All bubbles, including call/work item/release cards, use one small radius
  (`rounded-item`). Reactions sit on the bottom edge of the bubble.
- **Activity cards go to the actor's DM (KEP-90).** Approvals, comments,
  mentions, and work item updates are now sent to the DM between the person
  who acted and each affected person (notification recipients: assignee,
  approver, creator), with the actor as the sender. System actions, bots, and
  actions on one's own work item still go to the "Paradise" room. Same switch
  as assignments to DM (`ENABLE_TUGAS_KE_DM`); when it is off, all cards go back to the
  "Paradise" room. No migration; old cards stay where they are.
- **Own cards use the own-bubble color.** Call, work item, and approval
  cards that I trigger show in the accent color like outgoing messages;
  the Approve/Reject buttons do not appear on my own submission card.
- **Chat fixes, Nov 5 afternoon.** The emoji/"..." button beside the bubble
  no longer disappears on hover (4px gap outside the hover area), and is now bottom-aligned and
  sticky for long messages. Duplicate reactions / reactions that could not be
  added: the Base UI context menu click fired twice on Windows (filtered in
  `chat/reaksi.ts`), the reaction toggle on the server is now atomic (message row locked,
  old duplicates cleaned up), and reactions on old history now show. The
  right-click menu is no longer covered by the reaction chip (`z-50` moved to the Positioner
  in propel). Link previews got 12px of bottom spacing.
- **Typing feels lighter.** The chat input is now its own component
  (`chat/kotak-tulis.tsx`), so typing no longer re-renders the whole
  message list. The work item description and new comment no longer re-render
  the Tiptap editor on every keystroke (react-hook-form Controller replaced with
  `setValue`).
- **Member profile card.** Division and department on separate lines, the role
  is its own badge; multiple placements show per block (first 3, the rest
  "+N more").
- **Empty state illustration centered.** `EmptyStateDetailed` in propel now
  defaults to `align="center"`; all empty/not-found pages follow.
- **Favorite folders removed.** The create-folder button in the Favorites sidebar
  is removed and folders are no longer shown. Favorites that used to be inside a folder
  move up to the main list, so nothing is lost; old folder rows stay in the
  database, no migration.
- **"Jump to latest message" button in chat.** Appears when scrolled up, with a
  dot if a message came in. Incoming messages no longer pull the screen down
  while you read history; a newly opened conversation and your own sent messages
  still go straight to the bottom.
- **Your Work no longer shows blank rows.** `ActivityMessage` only
  knew some `field` values; reaction, vote, draft, comment, approval, `intake`
  (the web uses the key `inbox`) and `estimate_points` fell through to empty, so all that
  showed was "You, 1 day ago". Now there is a message for all of them and an unknown field gets a
  generic sentence. No data was deleted.
- **God Mode audit log fully labeled.** The object type was empty because the label on the
  web only knew five models, while settings changes were recorded as
  `instanceconfiguration`. All God Mode write endpoints now record through
  `plane/license/audit_godmode.py` with the object type and name; old empty
  rows get a fallback label.
- **Chat images open in the work item viewer (KEP-88).** Clicking a chat attachment image
  opens the same lightbox as the work item description (zoom, pan,
  Esc/Back), not a new tab. `ImageFullScreenModal` is now exported
  from `@plane/editor`.
- **Links and images in descriptions/comments also show in Links and
  Attachments (KEP-88).** Not stored as new rows: the `issue-links/` and
  `attachments/` lists append items derived from the text
  (`plane/utils/turunan_konten.py`) tagged with `sumber`, read-only on the web.
  Delete it from the text = gone from the list. Description images can no longer be
  deleted through the attachment endpoint. The count badge in the work item list still
  counts manual ones only.
- **Link preview cards (KEP-88).** New endpoint
  `workspaces/<slug>/link-preview/?url=` fetches the title, summary, and Open Graph image
  through `safe_get` (IP pinned on every hop), cached 24 hours (on failure: 1
  hour), 120 requests/minute per person. The card shows under descriptions,
  comments, chat messages, and above the chat input while typing. No
  migration, no new setting, goes into the unreleased 3.1.0.
- **Projects are called departments everywhere (KEP-92).** Each department already has
  exactly one project (0146), so only the name changes: 19
  locales, hardcoded web text, and God Mode. The "create project" button, modal, palette command,
  and shortcut on the web are removed; `ProjectViewSet.create` answers 403
  "Departments are created in God Mode." API v1 is unchanged. Department cards
  on the Organization board no longer repeat their project's name, and the
  `uppercase` class is removed from all text labels.
- **Wiki separated from projects (KEP-94), major.** Migration 0170 creates
  `wiki_folder` and `wiki_material`; 0171 moves each WIKI project page
  into a folder with the same id and each material into a `WikiMaterial` with the same id
  as its file (old links stay alive), then soft-deletes the WIKI project, its memberships,
  its old pages, and its old ACL rows with a single timestamp. MinIO objects are not touched.
  Every Division and Department automatically has a folder. Upload rights are read from the
  organization placement, not project membership. New endpoints under `/api/workspaces/<slug>/wiki/`,
  the old Wiki endpoints under `projects/` are removed, and the Wiki has its own trash. Operator
  step: nothing manual (deploy runs 0170/0171), but after deploy open /wiki and check
  that the old folders still have their contents; the migrations can be rolled back (`migrate db 0170`) as long as the WIKI project
  has not been permanently deleted by the daily task (see `TRASH_RETENTION_DAYS`).

## 2026-11-04

### Version 2.3.0

- **Bump from 2.2.0 to 2.3.0, minor (previously numbered 3.0.0).** A merge of two
  old numbers: 2.3.0, which was never released on its own, and 3.0.0. Permission semantics
  change and people lose rights they had yesterday (KEP-85), there are new
  endpoints, and one tidy-up data migration (0163, runs by itself on
  deploy). No operator step.

- **Per-resource permissions follow ownership and hierarchy (KEP-85).** Modules, pages,
  views, comments, and Wiki material can only be changed, archived, or deleted by
  their owner (creator/owner, plus the module's lead and members), their superior in the
  hierarchy, workspace admins, and Super Admins. Project structure (details and
  settings, state, label, estimate, intake, archive/delete project, restore/purge
  trash) is the authority of supervisors and above in the project they oversee. Plane's own
  "project admin" role no longer grants rights over other people's things. All 18
  rules can be set in God Mode > Work rules > Permissions (phrase
  `CHANGE RULES`, recorded in the Audit log). New endpoint
  `GET workspaces/<slug>/izin-saya/` is used by the web to hide actions that
  would certainly be rejected.
- **Gaps closed:** API tokens could change/delete anyone's comments
  (including guests); every member could change and archive other people's modules,
  archive projects, and change states; guests could change states;
  API tokens could archive projects without being admin; anyone could change the
  title of someone else's Wiki material through the asset endpoint; project admins could permanently
  purge other people's pages, views, modules, and material from Trash.
- **What people will notice:** staff can no longer put work items into a module that
  is not theirs (not the creator, lead, or member). Managing states, including their
  order, now needs workflow authority.

- **Mobile layout cleaned up across the app.** Tested with screenshots at
  390/360/768/1280 px. Names in the Members table no longer break one letter per
  line (on desktop too). Top bar: search becomes an icon that opens the command
  palette, bell/help/avatar are no longer pushed off screen. Project
  tabs can be swiped, breadcrumbs have no dangling arrow and no double row in
  Settings, the work item toolbar has a Filter button and layout icon. Filter
  ribbon: the button moves to its own row on mobile, chips are larger on touch
  screens, filters no longer vanish in dev (StrictMode). The Members toolbar, profile padding,
  command palette, modals, dropdowns, sidebar drawer, Pages, Views, Division Dashboard,
  and Recents were tidied too. Part of the unreleased 2.3.0, with no
  further version bump.
- **God Mode reorganized, work rules are configurable (KEP-83).** Eight menus
  (General, Sign-in & access, People, Work rules, Notifications, Modules,
  Integrations, Data & logs); old URLs redirect. One source of settings:
  `GET/PATCH /api/instances/settings/`, God Mode no longer copies defaults.
  Newly configurable: digest and reminder hours & days in the office time zone,
  reminder points, approval rules, delete/archive, change due date, assign
  downward only, upload limit, session age, invitation validity,
  chat limits (length, attachments, edit window), the Needs attention window. All defaults =
  the old behavior; sensitive rules ask for the phrase `CHANGE RULES` and are recorded in the
  Audit log. Personal switches whose parent was turned off by an admin show as locked.
  The instance's auto-archive becomes a ceiling for per-project settings. People >
  Organization is now one page: the structure chart on top, a drag-and-drop Board
  below (the Chart & details tab and the old project panel are removed, KEP-86);
  dragging a person back to People = revoke from that place; supervisor/manager
  drop to Staff only if no department or division is left at all; the member edit button is in the first column;
  the technical Audit log columns always show. Migration 0165 only adds a
  schedule marker table. Still minor: no new env and no operator step.
  Operator note: `FILE_SIZE_LIMIT` and `SESSION_COOKIE_AGE` are now only
  seeds. After the first deploy, raising the env no longer raises the limit;
  change it in God Mode (Modules > Files, Sign-in & access > Sessions). Migration 0165
  depends on 0163 and 0164, so all three must be in the same commit.
- **God Mode settings search (Ctrl/Cmd + K).** A Power K style command palette
  in the God Mode header: fuzzy search for menus, tabs, and every registry setting
  by title, help text, option labels, setting key, and menu path
  (a one-letter typo still finds it). Selecting a setting opens its tab,
  scrolls to its row, and briefly highlights it. Select dropdowns
  (`CustomSelect`, `CustomSearchSelect`) are now left-aligned when the label
  wraps to two lines; before, the second line was centered.
- **Settings defaults reviewed + completion time = time of submission (KEP-84).**
  New defaults: hierarchy gate, due date reminder email, one email thread per
  work item, and email only to LIVE active members; invitations expire after 7 days,
  chat edit window 24 hours, Trash 30 days, new members get the Asia/Jakarta time zone.
  A work item submitted by staff counts as done when submitted, not when the superior
  approves, and is not counted as late while waiting; overdue reminders
  move to the approver. Both are God Mode > Work rules settings.
  Immediate effects on deploy (the keys are new in this release): people who
  have not opened the app in 30 days stop receiving work news emails (inbox stays),
  invitations older than 7 days expire immediately, chat messages older than
  24 hours can no longer be edited.
- **DM calls ring on any page, video works again.**
  Call invitations used to go through the PER-ROOM socket, so the callee only rang
  if they happened to have that conversation open, and whoever answered
  entered the LiveKit room of the conversation open on their screen, not the call's
  own. Now DM signaling goes through the presence socket (one per tab,
  `tipe: "panggilan"`, room membership checked by `apps/live`), and
  the call lives at workspace level (`penyedia-panggilan.tsx`) so it does not
  drop when changing pages. There is an incoming call card + ringtone +
  browser notification, a 45-second ring limit (caller: "No answer", callee:
  "Missed call"), cancel, decline, busy, and sync between
  tabs. Video: `adaptiveStream` was removed because we do not use
  `track.attach()`, which made the server stop forwarding video (audio worked,
  video 0 KB); the self preview is rebuilt after the camera is turned on again,
  and the other party's camera being off shows as an avatar.
- **Staff is the default level, staff cannot create projects (KEP-79).**
  People without a level automatically become Staff; a manager/supervisor who loses their
  last place drops to Staff. Creating projects is only for Super Admin, workspace Admin,
  and Supervisor and above. Levels can be set directly in God Mode
  > Members > Organization.
- **Shared quick links + automatic title & favicon (KEP-82).** Super Admin and
  workspace admins can set quick links for everyone or for specific divisions
  and departments. One modal for all links: the admin chooses
  Visibility Private (only themselves) or Public (everyone / selected units);
  regular members only manage their own Private links. Changing visibility
  moves the link. These links show at the top of Home and the Quick links page of
  everyone in their target. Title and favicon are fetched automatically from
  the site; the icon is picked from the built-in emoji/icons like a project icon (not
  an image URL), and can be reset to the site's favicon. Quick link text that
  used to show as a raw key now reads properly. Migration 0164 adds a table;
  migration 0166 imports 23 links from the one.paradiseperkasa.com portal as
  global quick links for everyone (idempotent, installed on deploy).
- **Inbox becomes a popover on the bell (KEP-80).** Can be expanded to a full page.
  The full page was tidied: header aligned, wider list column, the sound button
  now works (z-index was in the wrong place) and is the same size as the other buttons.
- **Chat: deleted messages show "Message deleted" (KEP-81)**, the people list is
  sorted with online/away first, status badge also on yourself.
- **Theme switching without reloading the page.** The theme is applied immediately, saved
  in the background, and reverted if that fails.
- **Wiki is no longer counted** in the Division Dashboard, Reports, analytics, and
  the list of projects without a department.
- **Member profile card across all of God Mode**, "View work" for admins only,
  and long names/emails in the member table no longer overflow.
- **Emails with the same content are sent once, all addresses in To (KEP-78).**
  The login history deletion warning (to all admins), assignment emails to
  co-assignees, and due date reminders for one work item used to be sent one by one;
  now one email `To: a; b; c`, so each recipient knows who else
  received it. The greeting names everyone and the footer lists all addresses.
  Split only by recipient language and position in the email thread, at most 50
  addresses per message.
- **Stickies and the editor follow the app font.** The editor (stickies, descriptions,
  comments, pages) used to use a pinned Inter; now the "Sans serif" choice
  follows the interface font in Preferences. The code font (code blocks,
  `<code>`, `<kbd>`, the `font-code`/`font-mono` classes, the "Mono" choice in the editor)
  is always Geist Mono, also when the interface font is changed to JetBrains Mono. Code
  blocks used to point to a "JetBrainsMono" family that was never loaded, and
  `font-mono` was a dead class that quietly used the interface font.
- **"Deleted account" no longer sticks in God Mode departments.** Deleting an
  account used to not revoke its organization placement, so the account still
  showed (in R&D as Manager) and its revoke button did nothing because the member list
  hides deleted accounts. Now deleting an account revokes its
  placement (soft delete), restoring from Trash brings it back, the organization
  tree never shows deleted accounts, and migration 0163
  cleans up the old leftovers. Production rows were cleaned directly on Nov 4.
- **God Mode > Email > Preview:** language defaults to English, the
  "Send to me" button sends the currently open sample to the signed-in admin's email
  (`POST /api/instances/email-preview/<key>/send/`), and the iframe frame no
  longer adds corners/lines that are not part of the email.
- **Email sender is named "Space Paradise Perkasa"** (`pengirim()` in
  `email_merek.py`); the address still comes from the God Mode SMTP configuration.
- **The thin line inside email cards (classic Outlook) is gone.** The card frame
  used to be a cell with the border color as background holding a white cell inside; Word at
  125/150% display scaling leaves a gap between blocks so the border color shows
  through as a line across the card. Now one shared frame
  (`partials/bingkai_buka.html` / `bingkai_tutup.html`): classic Outlook uses a
  1px border cell on all four sides, other clients a normal `border`.
- **Email font = a system stack starting with Segoe UI**, the Google Fonts link
  removed, so the God Mode preview matches what shows in Outlook. The HTML button
  height matches the Outlook VML button (40px).
- **Work item & approval emails are batched into one digest per person.**
  `EmailNotificationLog` queue + a 5-minute sweep, default delay 15 minutes;
  approval requests go on top. Three new settings in God Mode `/features`:
  `ENABLE_EMAIL_BATCH` (+ `EMAIL_BATCH_DELAY_MINUTES`), `ENABLE_EMAIL_THREADING`
  (replies in the same thread per work item, off by default because the subject becomes
  `[PROJ-12] Title`), `ENABLE_EMAIL_ACTIVE_ONLY` (+ `EMAIL_ACTIVE_DAYS`, 30).
- **"Needs attention" widget on Home** (`GET .../paradise/attention/`): overdue
  work items, due within 7 days, rejected, waiting for approval, mentions; superiors
  also get the decision queue and their team's overdue work items.
- **The approval queue is only for those who may decide** (same predicate as
  the approve/reject action); rejected then resubmitted now shows once
  as waiting. The Approval column in the table view has a filter dropdown
  (including "None").
- **Activity:** duplicate entries are gone (project membership join replaced with `Exists`,
  the store filters duplicate ids); unknown fields no longer show blank.
- **Mobile:** the sidebar no longer opens by itself and is no longer covered by the header,
  profile settings use mobile navigation, activity text wraps, IDs in the
  approval queue are no longer clipped, dropdown menu touch targets are taller.
  The Module dropdown in work item detail matches the height of other rows.

## 2026-11-03

### Version 2.2.0

- **2.1.0 to 2.2.0, minor.** It started as 2.1.1 (a patch for email copy), then
  moved up to minor because the same release adds a new display property. It
  stays minor after the 3 Nov afternoon wave (system channels, chat cards,
  profile, branded email): two additive migrations (`0159_obrolan_kartu_sistem`,
  `0160_profil_kontak`) with default values, so old data keeps working. Old
  display filters keep working (the new property is on by default).
  - **Old assignment DMs become cards too.** Migration `0161_kartu_tugas_lama`
    turns the text-only "📋 Tugas baru untuk Anda" DMs from before 2.2.0 into
    work item cards with buttons. Only `jenis`/`muatan` change, `isi` stays
    as it is. Work items that were already deleted are left as text. It is
    reversible and needs no operator step, so it stays minor. Other card types
    (mention, comment, update, approval, project) were never sent to chat
    before 2.2.0.
  - **Placement: add, don't move (KEP-76).** One person = one level + one list
    of places. Staff and supervisors can be in many departments; a manager can
    lead many divisions and also sit in a department outside their divisions.
    The errors "Only supervisors can hold multiple departments", "Lowering the
    level requires a single department first", and "Set a level before placing
    this person" are gone: dropping below Manager releases their divisions
    automatically (the editor shows this before Save), and their departments
    stay. Four write paths that used to overwrite the FIRST placement row (the
    level editor, "Make department from project", picking your own department)
    now go through one writer, `plane/db/penempatan.py`. Member editor: one
    "Departments & divisions" picker; "Other project access" only shows
    projects that are not already granted automatically. Organization page: the
    "Multi-department supervisors" panel is merged into Members, and the
    candidate label "moved from" becomes "also in". Still minor: no migration,
    old data stays valid. **Check before deploy:** manager rows attached to a
    department used to be ignored and now give access to that department's
    projects. Count them in production first:
    `JabatanOrganisasi.objects.filter(tingkat__gte=30, tingkat__lt=40, departemen__isnull=False).count()`.
  - **Check before deploy.** Email language now follows `Profile.language`,
    and the default is `en`. Check that value in production first, otherwise
    the whole office gets English emails. The online indicator needs
    `apps/live` and Redis.
  - **Link preview image follows the Bara look.** `og-image.png` (the image
    shown when a link is shared on WhatsApp, Slack, Teams) now uses the warm
    charcoal panel from the sign-in screen, Plus Jakarta Sans + Geist Mono, and
    the same project board crop as `AuthShowcase`. The generator moved from
    Pillow to `paradise/bin/buat-og-image.mjs` + `og-image.html` (captured by
    headless Chrome), so fonts and colors match the app exactly.
    `og:description` now says "tugas" instead of "issue".
  - **@ mentions in chat and division/department channels (KEP-74).** Type `@`
    in the compose box to mention people in that conversation (DM: the other
    person; channel: its members). The browser sends IDs (`sebut`), the server
    filters them to the room's members, stores them in `muatan.sebut`, and for
    channels sends a "mentioned you in #channel" card to that person's
    Paradise room (the `inbox_mention` toggle). Every division and department
    automatically has a private channel (`kunci_sistem` `divisi:<id>` /
    `departemen:<id>`); its members follow the God Mode placements through
    `plane/db/jangkauan.py`, with no invite/leave buttons. No migration.
    Mentions of yourself are now highlighted and clickable like the mentions
    you send. Before, the matching name was "Anda" instead of the real display
    name, so `@MyName` in other people's messages stayed plain text.
  - **Reply quotes are clickable.** Clicking a quote in a bubble jumps to the
    original message and briefly highlights it. If that message is not loaded
    yet, older history is fetched up to 10 pages; if it was deleted, the
    notice "the original message is no longer available" appears.
  - **Profile card: empty data is just "Not set".** The "Job title:" prefix and
    similar are dropped; the row icon already shows what the data is.
  - **Browser notifications for chat and inbox.** The operating system card
    used to appear only for hidden tabs, so Paradise open behind another app
    only made a sound. Now every chat message and inbox notification is also
    sent through the browser (if allowed), next to the in-app card. A toggle +
    test button in the sound popup (Chat and the Notifications panel), saved
    per browser (`notif_peramban_nyala`). A failure in Chrome Android (`new
    Notification` throws) falls back to the in-app card. A closed browser still
    receives nothing (that needs Web Push).
  - **Fix: sound when opening a system channel.** The last-message marker on
    the Chat page was not keyed per conversation, so switching to a
    conversation already in the SWR cache read as a new message and played a
    sound.
  - **Fix: comment/mention/update cards were never sent.**
    `notification_task` built the Notification in memory with a string id,
    while `_muat_tugas` used UUID keys, so every card from the Celery path was
    silently skipped. The key is now a string, and a guard test covers it.
  - **Names are clickable (KEP-73).** Assignee in the sidebar and peek, Created
    by in the peek, the sender name on chat bubbles, reply quotes, and
    `@mentions` open the profile card. Chat mentions have three styles (I am
    mentioned, I mention, someone else). Empty profile data shows a single
    "Not set" line. The assignee avatar in the table (spreadsheet), list/kanban
    cards, sub-issues, relations, inbox, and the approval queue also opens the
    profile card; the rest of the cell still opens the assignee picker.
    Read-only cells are rendered without a `disabled` button, because that
    button swallowed clicks on the avatar inside it.
  - **Command palette (Power K) follows the features that exist.** New
    commands: Chat (`gc`), Wiki (`gw`), Division Dashboard (`gb`), Stickies
    (`gt`), Quick links (`gl`), project Approvals (`gq`), Initiatives, Your Work
    calendar, and "Open an account setting" (`oa`, the profile modal tabs
    including Connections). All of them follow the God Mode module toggles and
    the same access as the sidebar. Removed: all Cycles commands (KEP-53; `gc`
    now belongs to Chat), Billing in the workspace settings list (it has no
    page), the "Documentation" command (replaced by `gw`), and "Go to account
    settings", which pointed at a nonexistent `/settings/account` and now opens
    the profile modal.
  - **Chat message delete limit.** A sender can only delete their own message
    within 24 hours; after that the server answers 403 and the delete button
    disappears. The number is a new setting `CHAT_DELETE_WINDOW_HOURS` in God
    Mode > Features > Chat (0 = no limit), seeded automatically by
    `configure_instance`, no migration.
  - **Job title from the department list.** Profile > General uses a
    department picker (`GET penempatan-saya/?daftar=1`) instead of a free-text
    field. Old entries that are not a department name stay visible and are not
    deleted.
  - **WhatsApp-style chat.** Reply quotes have a faint background with a left
    accent line that follows the box corners, the sender name shows in incoming
    bubbles, and the avatar in channels now belongs to each message's sender
    (before, it was always the DM counterpart, so it was empty in channels).
  - **Phone extension on the member profile card** always shows with a label,
    or "Not set" if it has not been filled in.
  - **Sound popup in Chat and the Notifications panel.** The speaker button is
    no longer just a mute switch: clicking it opens a popup with a volume
    slider, a mute toggle, and a Preview button. The logic is shared with
    Profile > Preferences (`useVolumeSuara`), so both save to the same account.
  - **Avatar on the call screen.** The propel `Avatar` ignored numeric sizes,
    so the avatar shrank to a small cropped letter. Numeric sizes are now set
    inline, and the call screen shows the real profile photo (the other person
    in a DM, each participant from the LiveKit identity).
  - **New sign-in screen (web and God Mode).** One framed card: the left panel
    cycles through four app images (board, division dashboard, work item
    detail, chat) with a one-line caption, and the right panel is the sign-in
    form. The numbered feature list, tagline, dot texture, and copyright line
    are removed; the brand shows as "Space Paradise Perkasa", and the form
    title is in English ("Sign in"). The "Sistem internal PT Paradise Perkasa"
    statement under the form is gone too. There is one component,
    `AuthShowcase` in `@plane/propel/auth-showcase`; its colors are the
    `--pamer-*` tokens in `paradise-tampilan.css`. The `login_ui.*` i18n keys
    are replaced in 19 languages.
  - **No double label in the sidebar.** Project groups in the sidebar only use
    the division name; the department label above each project is removed
    because projects are already specific to a department and carry the same
    name.
  - **Departments always have a project (KEP-32 reinforced).** Codes whose
    identifier collides are no longer rejected: the new project gets a numeric
    suffix (`P1` -> `P3`). Moving a project to another department immediately
    creates a replacement project for the department it came from, and an
    empty `project_ids` is rejected. Old data is caught up with
    `manage.py lengkapi_project_departemen [--dry-run]` (manual, idempotent).
  - **Old changelogs show up too.** `release_notes/` now contains 1.5.0, 1.6.0,
    2.0.0, and 2.1.0. The older releases being backfilled are dated with their
    release date, so the channel stays in version order and does not light the
    unread badge. In production they are all published automatically when the
    2.2.0 API container first starts.
  - **Email style.** The callout accent line and the card note follow the
    card's corner radius (nested cells, not `border-left`). Buttons are no
    longer underlined in clients that strip inline `!important`.
  - **Fully round toggles.** The track and knob of toggles (`@plane/ui`
    ToggleSwitch, `@plane/propel` Switch, the Slack channel toggle) are
    `rounded-full` again. This is the second exception to the "nothing is fully
    round except avatars" rule in KEP-64.
  - **God Mode breadcrumbs no longer all caps.** Segments without a label used
    to show `PROJECT-DEFAULTS`; they now have labels ("New project defaults",
    "Preview", "Workspaces"), and the fallback is a plain sentence, not capitals.
  - **Toasts without an accent line.** The 2px colored strip per type on the
    top edge of the toast (`toast-garis`) is removed. The toast type is clear
    enough from its icon.
  - **Approval column in the table view.** Approval status has its own column
    in the spreadsheet, instead of a chip riding in the title cell. Deciders
    still see the Approve/Reject buttons in that cell. Work items that never
    needed approval show a dash.
  - **Display properties follow what exists.** The new `Approval` property can
    be turned off per view and applies in list, kanban, and table. With the
    Approvals module off in God Mode, the approval chip, column, and row color
    are gone. The Approve/Reject menu in the three-dot menu stays on purpose so
    work items that are still waiting are not locked forever. Estimate is not
    offered in projects without estimates. Created on/Updated on can now be
    turned off, but are only offered in the table because list and kanban never
    drew them.
  - **Completed work item report in the Division Dashboard (KEP-62).** A third
    mode, "Report", next to Summary and Detail. Pick a period (7 days, 30 days,
    this month, last month), then see four numbers (done with a comparison to
    the previous period, percent on time, done late, new work items), a bar of
    done per division, and the title of every completed work item per division >
    project with assignee, completion date, and an on time/late/no due date
    label. Days are counted in WIB. The on-screen list is capped at the latest
    500 rows; the CSV (`?unduh=csv`) has everything. Scope is the same as the
    dashboard: only projects the user is a member of. New endpoint
    `GET /api/workspaces/<slug>/divisi-dashboard/laporan/?periode=`, no
    migration.
  - **Auto-archive Done work items (God Mode > Features > Work items).** Super
    Admin picks Off / 7 / 14 / 30 / 60 / 90 / 180 / 365 days; default 90. A
    daily task at 01:00 UTC archives work items in the completed group that
    have been done for that long, in all projects. The count is from
    `completed_at`; old rows without `completed_at` use `updated_at`. Cancelled
    is excluded, and undecided intake is excluded. Activity is recorded without
    notifications. The upstream per-project "Auto-archive" setting keeps working
    alongside it. New key `AUTO_ARCHIVE_DONE_DAYS`; PATCH rejects values outside
    the list. No migration. **Deploy note:** because the default is 90 days, the
    first run after deploy immediately archives every Done work item that
    finished more than 90 days ago. Set it to Off in God Mode before 01:00 UTC
    if that is not wanted. Everything can be restored from Archives.
- Approval email copy fixes (the 2.1.1 plan):
  - Approval emails no longer mix up the supervisor and the staff member. The
    subject for the supervisor starts with "Needs your approval: Andi marked
    ... done", the subject for staff starts with "Your work was
    approved/rejected". The body, button, and email footer name the recipient's
    role.
  - The email copy still used the old KEP-28 flow ("no longer locked", "back to
    your private draft"). It now follows KEP-55: approved = Done, rejected =
    back to In Progress, then move to Done again to submit again.
  - Inbox cards are clearer too ("needs your approval to mark this work item
    done", "approved your work"), and the notification setting "Assignment
    approvals" is renamed "Done approvals".
  - A Super Admin placed in a department or division (God Mode > Organization)
    now shows up in that department's/division's projects: the Created by,
    Assignees, and Mentions filters, the assignee dropdown, the mention picker,
    and the member list. In other projects they stay hidden. One fix in
    `plane/db/superadmin.py`, so all five member list endpoints follow (KEP-61).
- Performance and touch-screen use (part of 2.2.0, no further version bump; all
  of these are fixes with no migration and no operator step):
  - **Lighter board for supervisors.** `_bawahan_ids` and `rekan_staf_ids` used
    to fire one membership query per person (`bisa-ditugaskan/`, every board
    open, and every property change). Now it is one query. The
    `bisa-ditugaskan` endpoint also drops the second membership check per
    subordinate.
  - **Changing a work item property no longer checks permissions twice.** The
    PATCH view marks the serializer context, so `galat_ubah_tugas` only runs
    once. Other write paths (bulk, API token, intake) are still checked in the
    serializer.
  - **Initiatives list**: two aggregate queries for the whole list, instead of
    three queries per initiative.
  - **Per-card access rights are not refetched constantly.** `bisa-ditugaskan`
    and Super Admin status are no longer reloaded every time a card scrolls back
    into view or every time the tab is focused; changes to a position show up
    after a reload.
  - **Chat**: the call SDK (LiveKit) is only downloaded on the first call, not
    every time a chat opens. The socket echo from your own tab's actions does
    not trigger a second refetch. Attachment images and videos have a fixed
    height, so the conversation stays at the latest message when images finish
    loading.
  - **Actions that used to appear only on hover are now reachable on
    phones/tablets** and by keyboard: chat message buttons, rename/delete Wiki
    material, the Quick Links menu, closing the notification popup, the God Mode
    org chart menu. A new Tailwind variant `sentuh:` (= `pointer: coarse`, same
    as `isMobile`) in `paradise.css`.
  - **Confirmation before deleting** a chat message, leaving a channel, and
    deleting Wiki material (the `useKonfirmasi` hook). Before, one stray touch
    deleted immediately.
  - **Approvals**: the rejection reason and the "no approver yet" warning show
    below the queue row, not only in a tooltip that never appears on touch
    screens. The Approve/Reject buttons on kanban cards are larger and spaced
    out on touch screens.
  - Phone layout: long channel/DM names are truncated cleanly instead of
    pushing the call button off screen, long URLs in chat bubbles are broken,
    the Wiki sub-topic title controls become icon-only below `sm`, the project
    Trash table leaves room for item names, the notification matrix toggles are
    larger on touch screens, and the division header in the sidebar has more
    contrast.
  - The Connections page tells "loading" apart from "failed to load" and adds a
    retry button. Three dead classes in God Mode (`text-sm`, `text-lg`,
    `text-custom-text-300`) are replaced with theme tokens.
  - **Display system (KEP-64).** Every visual value becomes a token in
    `packages/tailwind-config/paradise-tampilan.css`; components only use token
    classes and component props (`variant`, `size`), and do not write their own
    colors, radii, or padding.
    - Tinted backgrounds per color scheme, not plain white/black. Five schemes:
      Ember (default, red brand accent), Dusk (purple), Ink (indigo),
      Forest (green), Neutral (Plane's default gray, blue accent). The primary
      and secondary accents follow the scheme; the `--brand-*` ladder is built
      from three knobs per scheme.
    - Plus Jakarta Sans font (default) and Geist Mono for code, loaded locally
      from fontsource.
    - Named radii, also registered in tailwind-merge: `control`,
      `button`, `field`, `item` 0.375 to 0.5rem, `card`/`popover`
      0.75rem, `overlay` 1rem. Nothing is fully round except profile photos,
      spinners, and small status dots.
    - Buttons in sizes 24/28/32/36px, icon buttons as tall as regular buttons,
      and a `chip` size (20px, 11px text) for properties on work item cards.
    - The approval badge uses the propel `Badge` with a variant per status.
    - One motion curve for all transitions; the work item table view is striped
      (`bg-zebra`); the toast accent line sits on the top edge.
    - 3D effects, shine, and glow were tried and then removed at the user's
      request; the look is flat again.
  - **Per-person display preferences.** Profile > Preferences: color scheme,
    font (Plus Jakarta Sans, Inter, Geist, Figtree, Bricolage Grotesque,
    Archivo, Sora, Shantell Sans, JetBrains Mono, Source Serif 4, system font),
    and animation (smooth/reduced). Saved in `Profile.theme`, no migration.
    Follows KEP-57: defaults for new accounts in God Mode > Members > Defaults,
    per-person values in the member panel.
  - **Standard components across the app.** The browser's native `<select>`,
    handmade buttons, and home-made color badges on the Paradise and God Mode
    pages are replaced with `Button`/`IconButton`/`Badge`/`CustomSelect`.
    `CustomSelect` looks the same as `Input`; `CustomMenu.MenuItem` has a
    `danger` variant. God Mode pagination uses `Button`. The unread badge in
    Chat uses the same `CountChip` as Inbox. Division and department names in
    the sidebar are no longer all caps.
  - The Filters/Display buttons sometimes changed size and sometimes did not
    open the panel: two buttons (full and icon-only) were swapped by a
    container query inside a `<div>` that was acting as a button. It is now one
    real button.
  - **System channels Announcements and Changelog.** Present in every
    workspace, and all members join automatically (a migration fills in existing
    members; a signal and a check when the chat list opens handle new ones).
    They cannot be left, renamed, or deleted. Only Super Admin and workspace
    admins can post to Announcements; Changelog is read-only.
  - **Automatic changelog on deploy.** Release notes per version in
    `apps/api/plane/release_notes/<versi>.json` (Added/Changed/Fixed).
    `terbitkan_changelog` runs in the API entrypoint after migrations, never
    posts twice, does not post versions above `apps/api/package.json`, and its
    failure does not hold up gunicorn.
  - **Cards in chat, not links.** Everyone has a personal "Paradise" room with
    cards that have buttons: approval (Approve/Reject right there, the buttons
    disappear once a decision is made), mention, comment, work item update,
    added to a project. The trigger is the existing Notification row, so inbox
    rules and settings still apply. Assignments stay in the assigner's DM, now
    as a card.
  - **Voice/video call log** shows in the conversation (connected with
    duration, or missed) with a Call back button.
  - **Manage channels**: a channel directory with search and preview, and a
    settings panel (rename, topic, members, invite, remove, leave, delete).
    Invites to a private channel are now only by managers.
  - **Online/away/offline indicator** in the DM list, the DM header, and the
    channel member list, over the `apps/live` WebSocket (not polling).
  - **Paste or drag files** into chat to attach them (max 5 per message). In
    work item comments and descriptions, non-image files become work item
    attachments; images stay inside the text.
  - **Notification volume**: slider, mute, and a Preview button in Profile >
    Preferences; the default for new accounts is in God Mode.
  - **Member profile.** Clicking a name/avatar in mentions, activity, comments,
    the member list, and chat opens a card: job title, department/division,
    email, phone extension, online status, a Send message button. New fields
    `job_title` and `phone_extension`, filled in by the person or through God
    Mode. Guests do not see the email and extension.
  - **Super Admin can be mentioned and chosen in filters** when placed in a
    department (KEP-61). Mention search now finds full names (before, "Budi
    Santoso" matched no one). Deleted accounts are no longer offered.
  - **Branded email.** All 26 email types use one layout: the Paradise Perkasa
    logo (embedded, because the server is LAN-only), the app's colors and font,
    app-style buttons, and a plain text version. Profile photos in email are
    fixed (`http://hostNone` and expired MinIO links), with an initials
    fallback. Language follows the recipient's profile. The
    `kirim_contoh_email` command sends all the samples, only to
    it.ai1@itechmandiri.com. God Mode > Email > Preview shows all templates
    (ID/EN, desktop/phone) without sending anything.
  - **Dates and overdue in God Mode > Features.** Auto-fill start date on In
    Progress, auto-fill due date on Done, how to treat the due date when done
    early (keep, or move back to the completion day; late work items are never
    shifted), the overdue grace period (days), and the Division Dashboard "on
    time" window. Defaults match the old behavior.
  - **God Mode**: an "Unsaved changes" bar with Save/Discard that is always
    visible on every form, plus a warning before leaving the page. Leftover
    Indonesian text in God Mode is now English.
  - **Sign-in screen redone** (app and God Mode): a brand panel on the left for
    desktop, one column on phones. The authentication flow is unchanged.
  - **There is always a way back.** The image viewer has a close button, Esc,
    click on the backdrop, browser Back, and zoom controls (including pinch).
    Back closes the work item peek, the Gantt fullscreen, and the Wiki viewer,
    instead of leaving the page.
  - Reactions on other people's channel messages used to be rejected (checked
    only against the sender or recipient); they are now checked against channel
    membership.
  - **No more native browser controls.** The month/year pickers in all calendars
    (work item dates, date ranges, filters, snooze) used to be a real `<select>`
    with an OS-drawn list; they are now a propel `Combobox`. Native checkboxes
    become the `@plane/ui` `Checkbox`; radios become a new propel `RadioGroup`
    (a dot, not a check; arrows move the selection; the whole row is
    clickable), for example the Accordion/Tabbed navigation mode. Date fields in
    the God Mode filters become a `Calendar` in a `Popover`, and raw
    input/textarea become `Input`/`TextArea`. The volume slider stays an
    `<input type="range">` because there is no slider component yet.
  - **Faster build and deploy.** CI uses the GitHub Actions layer cache per
    image, and the web/admin/space/live Dockerfiles install dependencies before
    copying source, so a commit that only changes code does not redownload
    packages. A release is now one command from the laptop,
    `paradise/bin/rilis.sh`. `deploy.sh` fails if the migration fails; before,
    it still ended HEALTHY because a stopped migrator container does not show up
    in `compose ps`.
  - **Email language decided: English.** All 100 production profiles have
    `language=en`, so email goes out in English, the same as the UI. No data
    changes; anyone can pick Indonesian in Profile.

## 2026-11-02

### Version 2.1.0

- **2.0.0 to 2.1.0, minor.** 2.0.0 is already running in production. This
  release adds a new tab and fixes approvals, with no migration and no operator
  step.
  - An **Approval** tab appears in the project tabbed navigation, the same as
    the sidebar menu. It can be turned off from God Mode through the `approvals`
    module.
  - After a supervisor approves, the card moves straight to the Done column
    without a reload. Reject moves it to In Progress. The decision response now
    carries `tugas.state_id`.
  - Approval status uses one `ApprovalStatusChip` component on the Approval
    page, kanban/list/spreadsheet cards, the detail sidebar, and the peek.
  - The Approval page was slow: every row recomputed the approver list (1,085
    queries for 6 rows). It is now computed once per request, 93 queries and
    241 ms on local data. Decided history is capped at the latest 200 rows;
    pending items are not capped. This is also why "the division manager cannot
    approve": the Approve button only appeared after a response that could
    exceed the gunicorn timeout (BUG-11).
  - The board no longer refetches the approval queue for every card that newly
    comes into view.

## 2026-10-30

### Version 2.0.0

- **Bump 1.6.0 → 2.0.0, major.** Since 1.6.0 (26 Oct), some changes force an
  operator step or remove a feature:
  - KEP-29: divisions and departments became records, and projects moved under
    departments. Existing organization data needs migrating.
  - KEP-46: the Customers menu in God Mode is gone, God Mode is English-only,
    and the custom menus were merged.
  - KEP-40/46: settings moved from `.env` to God Mode. The env file is now only
    a seed.
  - New migrations `0150_email_bawaan_jabatan` and `0151_potret_bawaan_email`
    (the email defaults for new members in God Mode no longer change existing
    accounts), plus changes to `apps/api/.env.example` and
    `docker-compose-local.yml`.
  - Due dates through intake: intake triage can change the due date of other
    people's work items.
  - KEP-59 (2 Nov): directors only receive mentions, chat, and digests.
    Approvals, property/status changes, work items, and comments are off for
    every director, including those who had turned them on themselves. The
    notification defaults in God Mode (`/members/defaults`) now have three
    columns: Staff, Leaders (supervisor, manager), Directors. The Directors
    column applies immediately as an upper limit.
  - Chat fix (2 Nov): attachments on channel messages could only be opened by
    the sender (the old "sender/recipient" rule, while channel messages have no
    recipient). Now the rule is the same as for room content: room members can
    open them. The workspace owner still can't, unless a member.
  - Demo data `manage.py seed_demo_data` (a local tool, not a feature): a
    made-up company with a full hierarchy, work items, approvals, chat,
    attachments, Wiki, and login history, with the Super Admin account included.
    Local only: it requires `--settings=plane.settings.local`, it refuses to run
    on an instance with more than 5 real accounts, and its files are excluded
    from the production image through the new `apps/api/.dockerignore`. Not a
    data migration. See the README.
  - KEP-25 strengthened (2 Nov): other people's work items are now truly
    view-only. The peek overview, kanban/list cards, table cells, and the quick
    action menu use one rule (`useBolehUbahTugas`): the creator, an assignee, the
    supervisor of ALL of its assignees, or a Super Admin. On the server, links,
    attachments, sub-issues, relations, cycle/module, worklogs, versions, and
    date dragging are also guarded by `KepemilikanTugasMixin`. Comments stay
    open. No migration.
    Follow-up: sub-issue rows in the detail view are judged per child (they used
    to follow the parent's rights), and other people's Gantt blocks can't be
    dragged or resized.
  - Granular notifications (2 Nov): each kind of update (assigned, mentioned,
    comment, approval, due & overdue, work item completed, status, other
    changes, chat) has its own INBOX and EMAIL switch in Profile >
    Notifications, and the daily digest can be chosen per section (overdue,
    today, 7 days, what you gave out, team). The same matrix shows in God Mode
    (per-member preferences and role defaults). New in the inbox: due/overdue
    reminders (D-1, D, D+1, D+3, D+7, without waiting for
    `ENABLE_DEADLINE_REMINDER` because they don't send email) and unread DMs
    (one row per conversation). Additive migration `0155_notifikasi_granular`,
    every new column starts on = the old behavior.
  - KEP-57 (2 Nov): all personal settings can be set from God Mode, both as
    defaults for new accounts (Members > New member defaults) and per person
    (member panel). Newly covered: sidebar navigation (pinned menus, project
    list style, project limit) and the work item layout. **The default layout is
    now Board** (it was List) for every new member+project; existing members
    are aligned only through the "Apply ... to everyone" button, which asks for
    confirmation. New menu Workspaces > New project defaults: visibility, time
    zone, auto-archive/close, and guest access for new projects (the Create
    project form is prefilled with these values; API v1 now accepts `network`).
    Chat, Wiki, Division dashboard, and Initiatives can finally be pinned in
    Customize navigation. No migration.
  - KEP-55 (2 Nov): when staff drag their work item to Done, they only request
    approval. The status doesn't move, a "Requested for approval" toast
    appears, and the work item only enters Done when the supervisor approves.
    Rejected = the work item goes back to In Progress, then the staff member
    works on it and drags it to Done again to resubmit. Work item properties
    (full sidebar and peek) have an "Approval" row with one chip, the same as
    the card badge ("Awaiting approval", "Approved by <name>", "Rejected"; no
    request "-"). A log of every request/decision (with the rejection reason) is
    in Activity (`IssueActivity field="approval"`). The approval badge on cards
    is now as wide as its content. Replaces the 26 Oct rule (the work item stays
    Done while waiting). Data migration `0157_log_persetujuan_lama` writes logs
    for old requests (idempotent, reversing it deletes them); old requests still
    waiting in the Done status can be decided as usual.
  - End-of-day digest (2 Nov): besides the start-of-day digest Monday-Friday at
    08:30 WIB, there is a second email at 17:30 WIB (`kirim_ringkasan_sore`,
    beat `ringkasan-sore`) to close the day. It contains: work items completed
    today, those due today but not done, overdue ones, and those due the next
    working day (Friday = through Monday). For supervisors and managers, the
    team section gets a Done column. It has its own switch, `daily_digest_sore`,
    in Profile > Notifications and in God Mode (per member and role defaults).
    The default is on for all roles, the same as the morning digest. The
    sections included follow the same section choice. The morning digest
    subject now starts with `[Ringkasan pagi]`. "Today" is counted by WIB, not
    UTC. Additive migration `0158_ringkasan_sore`: people who already froze
    their choices inherit their morning digest switch.
  - KEP-60 (2 Nov): Division Dashboard for leaders. The default is **Summary**
    mode: one sentence (how many divisions are on track, which one has the most
    problems), four numbers compared with the previous 7 days (completed on
    time, completed in 7 days, overdue, awaiting your approval), a health card
    per division (On track / Needs attention / Critical), and at most five
    things to look at with direct links. **Detail** mode has a table per
    division > department and a CSV download. The mode choice is remembered per
    browser. Status thresholds are set in God Mode > Features > Division
    dashboard (`DASHBOARD_PERHATIAN_PERSEN` 5%, `DASHBOARD_KRITIS_PERSEN` 15%).
    The `divisi-dashboard` endpoint was rewritten with aggregate queries: it
    used to run ~6 queries per project, now it runs 12 queries no matter how
    many projects there are (93 ms on local data). Approval authority is
    computed in bulk through `project_boleh_diputuskan`, equal to
    `boleh_memutuskan` for 57 of 57 local accounts. Old fields are still there.
    No migration.
  - Sub work items in the detail view no longer flash and then disappear: two
    racing fetches (StrictMode/remount) toggled visibility on and then off. It
    is now set, not toggled (`sub-issues/content.tsx`).
  - KEP-56 (2 Nov): default navigation changed. Projects use tabs (not an
    accordion), all projects show in the sidebar ("Show limited projects" is
    off), and all sidebar menus are pinned. Admin-only menus (Analytics, Views,
    Archives, Division dashboard) are still filtered by permission, so regular
    members don't see them. Migration `0156_navigasi_bawaan_tab` also aligns old
    accounts: the "Show limited projects" switch used to seem impossible to turn
    off (a failed save was silently reverted by the store), so the stored limit
    of 10 wasn't anyone's choice. A failed save in the Customize navigation
    dialog now shows a toast.
  - Chat: notes to self. You appear at the top of the people list with the
    label "(You)", a DM to yourself is no longer rejected with 400, the room has
    only one subscription, its messages are born already read (no badge or
    email), and the call buttons are hidden. No migration.
  - Module lead & members: the logged-in user can always pick themselves. The
    Super Admin is filtered out of the project member list (`sembunyikan()`), so
    they never showed up in this picker; the same went for supervisors who enter
    through hierarchy reach. New prop `sertakanDiriSendiri` on `MemberDropdown`.
  - The organization structure in God Mode is easier to manage (2 Nov). The
    overview chart is now a canvas: drag to pan, Ctrl + scroll or buttons to
    zoom, "fit to screen", and full-screen mode (keyboard: arrows, + / -, 0).
    The left tree panel can be collapsed into an icon rail (remembered per
    browser), and divisions are collapsed by default with an expand/collapse all
    button. Each chart box and tree row has a "..." menu to rename & change the
    code, delete, add a department, add a manager/member, and move a division
    or change the project, without opening the detail panel first. All manage
    modals are consolidated in `organisasi/kelola.tsx`. No migration, no new
    endpoint.
  - The sidebar no longer shows division/department codes: the project sidebar
    on the web and the organization tree in God Mode use only the name. The
    code is still in the God Mode detail panel and is still searchable.
  - Disabled modules (or removed ones, KEP-50) no longer leak into the app.
    Estimate, Cycle, Module, and Work item type are gone from Display
    properties, spreadsheet columns, list/kanban chips, Group by, and Order by,
    including old saved filters (group by cycle becomes state, order by
    estimate becomes Last created). Power K follows: commands, key shortcuts,
    the Keyboard shortcuts modal, the project settings submenu, and search
    result groups. Also the Analytics button in the work item/module header,
    the Total cycles/intake cards and the Cycle/Module/Estimate axes in
    Analytics, the "Save to Drafts" offer, Archive actions (work item, module,
    project, auto-archive), Pages in Home Recents, Cycle/Module in the intake
    form, the Chat/Inbox pop-ups, and the Help > Documentation (Wiki) menu.
    There is one gate map: `paradise-features.ts` and
    `power-k/core/paradise-gates.ts`. No migration, data is untouched.
  - Flatter Wiki (2 Nov): sub-topics no longer show as cards you have to click
    first. On a folder page, each sub-topic becomes a section that opens and
    closes right in the Materials list, complete with its materials, its own
    upload button, and the sub-topics below it. It is open by default; closed
    sections are remembered per browser (`localStorage`) and don't fetch their
    materials. The sub-topic page still exists through the "Open" link. The
    material count in the list header now includes sub-topics. No migration.
  - The last Plane logos are gone: the "Projects" icon in the app rail
    (`PlaneNewIcon`) is now a single-color Paradise house glyph, and the web
    `apple-touch-icon` (`app/assets/icons/icon-180x180.png`, `icon-512x512.png`,
    which are also used for link previews on iOS/WhatsApp/Slack) was replaced
    with the Paradise logo.
  - Quick links get their own sidebar menu and page at
    `/:workspace/quick-links`, like Stickies. The widget is still on Home; both
    read the same data. No migration.
  - KEP-49: all menus can be turned off from God Mode > Features. The main
    sidebar (Inbox, Your work, Stickies, Drafts, Quick links), workspace menus
    (add Chat & Wiki), project tabs (Work items, Cycles, Modules, Pages, Intake,
    Approvals), and work item features (Time tracking, Estimates, Work item
    types, Templates). The last group used to be turned off in code through
    `PARADISE_FEATURES` and the routes were dropped at build time; now the routes
    are always registered and guarded at runtime. **Watch out for Cycles:** it is
    off by default, so projects that had turned Cycles on won't see the tab until
    a Super Admin turns it on. No migration: new switch rows are created by
    `configure_instance` with the default value.
  - Deleted accounts & complete Trash (KEP-50). An account deleted from God Mode
    disappears from the Accounts list, the workspace/project member lists, and
    all pickers (assignee, mention). Old references stay and show as "Deleted
    account" (`is_deleted` in `UserLiteSerializer`). The original identity is
    kept in the new `akun_terhapus` table (migration `0152_akun_terhapus`,
    additive, plus renaming the old "Akun dihapus" accounts to "Deleted
    account"), so an account can be restored from Logs > Trash; Super Admin
    status deliberately does not come back. Trash also holds projects, Wiki
    materials, views, labels, templates, and initiatives. A restore that
    conflicts (email, project identifier, label name) is rejected with 409
    before anything is restored.
  - KEP-53 (2 Nov): **Cycles, Work item types, and Templates & Recurring were
    removed.** The routes, settings pages, the custom properties panel, the God
    Mode switches (`ENABLE_CYCLES`, `ENABLE_WORK_ITEM_TYPES`,
    `ENABLE_TEMPLATES`, `ENABLE_RECURRING_ISSUES`), the `issue-types`,
    `properties`, `issue-templates`, and `recurring-issues` endpoints, and the
    `create-recurring-issues` beat task are gone. Old tables & data are
    untouched.
  - KEP-53: **all project features are on**, including department projects and
    old projects. Migration `0154_fitur_project_nyala` changes the column
    defaults (`module_view`, `issue_views_view`, `intake_view`,
    `is_time_tracking_enabled` become `True`) and turns all five on in every
    project. The previous per-project values were not saved.
  - **Trash reworked** (Logs > Trash in God Mode and Settings > Trash in a
    project): the standard God Mode list page layout. Search by name or
    deleter, a type filter derived from the contents of the trash (with
    counts), a table, deleter avatars, icon actions, and a confirmation modal
    replacing `window.confirm`. Type labels in the project Trash are now really
    translated (before, raw i18n keys showed).
  - **God Mode lists look like the work item view** (2 Nov): Accounts, Logs >
    Activity (login history), Audit log, and Trash use one kit
    (`apps/admin/components/common/data-view`). Search, a Filters button that
    adds `property | operator | value` chips (is / is not, date range with
    presets, text), a Display menu (order, visible columns, rows per page), and
    clickable table headers for sorting. Choices are saved per page in the
    browser. Accounts can now be filtered by status, Super Admin, role,
    department, division, access, session, active/login/logout/created date,
    sign-in method, IP, and email. Audit log by actor (including scripts),
    action, object type, changed column, date, and IP. Login history by person,
    event, source, method, date, and IP. Backend: `/api/instances/audit-logs/`
    and `/api/instances/login-history/` accept multiple values (`a,b`), negation
    (`*_not`), and `?sort=`; login history also sends `pilihan` (the existing
    sources & methods). No migration.
- **Not 2.0.1.** A patch is only for fixing a version that has already been
  released, and 2.0.0 was never released.
- **Versions unified.** Before, the root was 1.6.0 while 19 workspaces lagged
  at 1.5.0, so the "Version" label in the sidebar (read from
  `apps/api/package.json`) showed the wrong number. Now everything is managed
  through `pnpm version:bump` (`scripts/bump-version.mjs`). The rules are in
  `AGENTS.md` → Versioning (KEP-48).

### Navigation: no more dead-end pages (2 Nov)

Included in 2.0.0 without a version bump: 2.0.0 isn't released yet. On its own,
this would be a patch (fixes, no migration or setting).

- **Inbox (Notifications).** Upstream hides the main sidebar in Inbox because
  it relies on the app rail, but the app rail is off here. As a result Inbox had
  no way out except the browser Back button. The sidebar is now hidden only if
  the app rail is actually shown, and the Inbox header gets an open-sidebar
  button like other pages (narrow screens/collapsed sidebar).
- **Account settings (`/settings/profile/*`).** These pages sit outside the
  workspace layout, so no main sidebar and no top bar. Added a "Back to
  workspace" arrow above the settings sidebar, mirroring the Workspace settings
  header.
- **Create workspace.** The "Go back" button used `router.back()`, which does
  nothing when the page is opened directly. It now falls back to the last
  workspace when there is no previous app page.
- Audited and already fine: all pages under `(projects)` (sidebar + toggle +
  breadcrumb), Workspace/Project settings (back arrow), disabled module pages,
  404/error, invitations, God Mode.

### Approvals: standard filter, one click, consistent page

Included in 2.0.0 without another version bump: 2.0.0 isn't released yet and is
already major. On its own, this would be minor (new filter, no migration or
setting).

- **"Approval" filter in the work item filters.** The "Awaiting approval" pill
  button next to the filter row is gone. In its place is the `approval_status`
  property in the standard filter (Add filter > Approval > Awaiting approval /
  Approved), so it can be combined with other filters, saved to views, and
  carried in the URL. It is filtered on the server (`IssueFilterSet`, the latest
  approval row per work item), not hidden on the client as before: group counts
  and pagination are now correct.
- **One-click approve for supervisors.** In list, kanban, and spreadsheet, a
  waiting work item that I can decide carries an Approve button (immediate) and
  a Reject button (reason dialog) next to the badge. One request per project,
  not per card. The work item sidebar and the "..." menu use the same button
  and dialog.
- **Approvals page consistent with Pages.** A secondary header with tabs (Needs
  my decision + count / My requests, tab in `?tab=`), page-wide `ListItem`
  rows, a `Banner` for disabled gates and load errors, and the default loader
  and empty state. The hand-made cards, `max-w-3xl`, and textarea are gone.

### Wiki: access settings removed, built-in rules (KEP-51, 2 Nov)

Included in 2.0.0 without another version bump: 2.0.0 isn't released yet and is
already major. The change itself is major (a settings page and two endpoints
removed, the meaning of permissions changed), so the rule "don't bump twice at
the same level" applies.

- **The Project settings > Wiki access page is removed**, along with the
  `wiki-access/` and `wiki-access/folders/<id>/` endpoints. The owner checkbox
  in the Manage panel inside Wiki is also gone; the panel now only shows who
  can contribute.
- **Governance is always on** for projects with the WIKI identifier, without a
  `WikiGovernedProject` row. Local and production now behave the same.
- **New rights matrix:** read = all Wiki members; upload = an admin or a member
  (member/admin, not guest) of a department project under that folder's
  division; edit/delete materials = an admin or the uploader; folders and
  sub-topics = admin only. "Admin" = workspace admin or Super Admin.
- **Folder defaults:** division folders follow the God Mode organization
  structure (`pastikan_folder_divisi`). A division without departments = only
  admins upload. Any other top-level folder without an owner = General, and all
  Wiki members can upload. Warning: leftover trial folders in production that
  used to be locked also become General; delete them through the Manage panel
  if they aren't used.
- No migration. Old `WikiFolderAccess` rows are still read.

### God Mode look: Audit log, Accounts, Organization

Included in 2.0.0 without a version bump: 2.0.0 isn't released yet, and this is a
visual change with no behavior change (no new endpoint, migration, or setting).

- **Audit log.** Entries are grouped by day (Today, Yesterday, dates), actors
  show with avatars, actions use badges with icons, and a new "Changes" column
  summarizes the changed columns. A row opens into a Field / Before / After
  table with readable column names (`state_id` becomes State, `True` becomes
  Yes, UUIDs are shortened, description HTML becomes text). Technical columns
  (timestamp, order) are hidden behind a button at first. There is a Clear
  filters button.
- **Accounts.** Columns are tightened: avatar + name + email, a Super Admin /
  You / Deactivated badge, level + placement (department name), workspace
  access, relative time ("3h ago") with the exact time in a tooltip. The editor
  moved from an in-place expanding row to a stepped modal (Account,
  Organization, Preferences, Super Admin, Danger zone) with Save/Cancel stuck at
  the bottom. New accounts also go through a modal.
- **Organization.** The page is now master-detail: the organization tree on the
  left (company > division > department, plus Not placed yet and Projects
  without a department), the selected node's panel on the right. The company
  overview is a top-down chart (director > division + manager > department).
  Editing/deleting divisions & departments goes through a modal and
  AlertModalCore, and people show as uniform rows with promote/demote and remove
  actions.
- **Create division/department: name first, code follows automatically.** The
  code is filled from the name (Finance becomes FIN, Human Resources becomes
  HR), with a number added on a clash (FIN2). The code can still be edited;
  clearing it returns to the automatic code. When editing, the old code doesn't
  change along with the name.
- **Object column in the Audit log.** The upstream `__str__` text has the form
  `A <B>` (e.g. `email <New division>` for a Wiki page) and is split into a bold
  name + dim context ("by email", "in Project"). Cleaned up in the view because
  that text is frozen when the entry is written.
- **The Connections tab is hidden without Google credentials.** `/api/instances/`
  sends `has_google_calendar_configured` (client ID AND secret filled, from God
  Mode or env). When False, the Connections tab disappears from profile settings
  (page & modal) and `/settings/profile/connections` redirects to General. An
  old server without this field: the tab still shows.
- **Upstream components, not hand-made ones.** Native selects were replaced with
  `CustomSelect`/`CustomSearchSelect`, inputs with `Input`, switches with
  `ToggleSwitch`, checkboxes with `Checkbox`, badges with `Badge`, avatars with
  `Avatar`, icon buttons with `IconButton`, and modals with `ModalCore`. The
  remaining shared blocks are in `apps/admin/components/common/paradise-ui.tsx`.
- **Dead classes cleaned up:** `font-mono` (not in the theme, replaced with
  `font-code`), `bg-placeholder` on the session status dot (the "Signed out" dot
  used to be invisible), `border-l-warning-primary`, `shadow-lg`.

## 2026-10-22

### Approval notifications (inbox + email)

- **Three new triggers.** A request (new & resubmitted) → inbox + email to the
  supervisor who can decide; a decision (approve/reject, reason included) →
  inbox + email to the requester. Assignment to me & status changes still go
  through the old path (already working: the assignee automatically becomes a
  subscriber + the `property_change` switch).
- **Email language follows the recipient** (`Profile.language`, id/en); new
  template `emails/notifications/approval.html`.
- **New switch** `approval` in `UserNotificationPreference` (default on)
  - a toggle in Profile → Notifications; the inbox is always written, the
    switch only controls email.
- Without SMTP, the row is marked done (it doesn't get stuck in the queue).

### Version 1.5.0

- **Bump 1.4.0 → 1.5.0** in 20 workspace `package.json` files (new features
  since 14 Oct: approval queue, God Mode members & organization, the awaiting
  approval filter).
- **i18n for all new feature strings.** The web uses `issue.approval.*` keys
  (52 keys, 19 locales in sync); dates follow the active language. God Mode uses
  the typed dictionary `apps/admin/app/i18n/godmode.ts` + an ID/EN toggle.
- **Super Admin confirmation without a passphrase.** Granting uses retyping
  "jadikan superadmin" / "make superadmin" (validated by the server); the env
  `SUPER_ADMIN_GRANT_PASSPHRASE` was removed.
- **Design system cleanup:** `danger-subtle`/`warning-subtle` tokens replace the
  hardcoded `red-500`/`amber-500`, and `aria-pressed`/`aria-label` on the
  approval controls.

## 2026-07-31

### Branding

- **Finishing the removal of upstream branding** (`07a6fe2`). The earlier pass
  removed links, components, and routes, but **didn't touch the locale text**.
  1,712 lines in 19 locales were fixed. The two most-seen surfaces still wrote
  the vendor name until today: the `Ctrl+K` command palette and the sign-in
  screen.
- `SUPPORT_EMAIL` and `WEBSITE_URL` lost their vendor defaults. The first had
  the most impact: its value is inserted into the real message _"User account
  deactivated. Please contact …"_ on web, space, **and** admin, so employees
  whose accounts were deactivated were pointed to the vendor's inbox.
- Three upgrade-prompt surfaces that were missed before were cleaned up: the
  banner that appears when selecting several work items, the whole
  `/active-cycles` page, and "Powered by …" on public pages.

## 2026-07-30

### Navigation

- **Wiki enters the workspace sidebar** (`9ea16c2`). It also fixes an old bug:
  `Dashboards` and `Initiatives` **were never visible in anyone's sidebar since
  they were created**, because dynamic nav items are hidden if not pinned, and
  the default was not pinned.
- Removal of upstream product branding from the interface (`a407ce0`):
  promotional buttons, tier badges, the vendor help menu, the command palette,
  the Billing tab along with its route, and the terms of service link on the
  sign-in screen.

### Operations

- Backup waits for Postgres to be ready instead of failing instantly when
  Docker isn't up yet (`8468112`).
- The healthcheck stops logging `HTTP 000000` (`0134346`), and its schedule is
  registered disabled until the production server actually exists (`cef2a20`).

### Wiki

- The seed stops writing duplicate titles into the page body (`ecbc4e8`).

## 2026-07-29

- **File node in the editor with in-place preview** (`84e6638`), completing
  Phase A: the backend already accepted pdf/docx/mp4/zip, but the editor only
  offered images.
- **Nested page tree** (`8e6e2fc`), Phase C. Sub-pages weren't just invisible
  before, they **returned 404 when opened**: the filter sat in `get_queryset()`,
  which `retrieve`/`update`/`destroy` also use.
- The scheduled task registration script was fixed until it could actually run
  (`d03ef68`).

## 2026-07-28

### Wiki, Phase B complete (per-folder access control)

- Attachments of all file types, upload limit 100 MB (`7a85899`).
- **Edit permission enforcement on the real-time collaboration server**
  (`e9e73ea`). Without it, members outside the folder owner's division saw the
  page as editable, typed, and then lost their writing on reload.
- Admin API for managing folder ownership (`3685b5e`).
- Folder access settings UI, and the editor respects the read-only state
  (`4149011`).

### Fixes

- **Recurring issues finally actually run** (`5f1cb37`). The task was registered
  in the scheduler but not in the worker's import list, so every 15 minutes the
  message was sent and silently discarded.

## 2026-07-24

- **Audit Logs**, recording the actor on access & content models (`cc2888b`),
  then an admin-only read API with filters and pagination (`352422c`).
- **Per-folder Wiki ACL, backend** (`886303d`): model, resolver, and permission
  enforcement. Built without a new dependency; division membership is dynamic,
  so static grants easily drift from the real state.
- **CI/CD to GHCR** (`1a681fb`), image build per push, deploy by pulling the
  image on the server. Two fixes followed: the env file is created before
  compose validation (`1c36246`) and bake uses the root compose (`f2f5736`).
- The MinIO endpoint the browser sees can be overridden (`15ff66e`).

## 2026-07-13

### The first eight days of building features

- **Time Tracking**, model & API with per-user permissions (`cc82b12`), then a
  sidebar UI to record, view totals, and delete your own worklogs (`0b24b07`).
- **Work Item Types**, work item types per project, admin only (`cdeb15e`).
- **Custom Properties**, a property/option/value model with 6 field types
  (`9354fe7`), cascading cleanup when deleting a type + typed value validation
  (`461ce37`), and a frontend type selector + dynamic fields (`8205b9b`).
- **Templates & Recurring**, work item templates + automatic repetition via
  Celery beat (`7364fc7`), and a settings page to manage them (`ee54c30`).
- **Workspace Wiki**, seed of the company Wiki project with a root page per
  division (`09b925f`).
- **Division Dashboard**, a recap per division with worklog totals and CSV
  export of the time report (`0b68e8a`).
- **Initiatives**, cross-division workspace goals with progress rollup
  (`0e0f417`).

### Identity & environment

- The logo and loading spinner were replaced with the Paradise Perkasa identity
  (`f3aa2d2`).
- Embedded creator attribution along with a tamper-evident check (`a03a842`).
- The dev server binds to all interfaces for LAN access (`f36753f`).
- The `packages/i18n/locales` junction was restored as a symlink in the git
  index (`ebf0314`), a recurring problem on Windows.

## 2026-07-10, foundation

- Vendoring **Plane Community Edition v0.24.0 (AGPL-3.0)** as the base
  (`1d503d3`), and a NOTICE with upstream attribution (`7d8ac1f`).
- A read-only architecture audit of the codebase (`2433208`).
- The office operations layer: environment template (`1d62838`), self-host guide
  (`20fd63b`), production deploy guide (`c4b29d3`), pre-production security
  checklist (`81253c8`), upstream sync guide (`0429966`).
- Scripts: dev helper (`0c81898`), PostgreSQL backup with retention & integrity
  check (`b215cb2`), service healthcheck (`7da2b7a`), scheduled task
  registration (`f10842a`).
- Build & deploy workflow skeleton (`180c6cc`), operations Makefile
  (`1cdaec2`), `.gitignore` tightened for secrets & backups (`248fe06`).
- Package identity and app title changed to Paradise Task Tracker (`a5763d7`,
  `0330de0`).
