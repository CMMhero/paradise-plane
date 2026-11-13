/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: strings of the God Mode settings tabs
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Menu and tab names, the help line of every setting, and the labels of the
 * registry-driven controls. English only (KEP-46). Defaults, ranges and choice
 * lists are NOT here: they come from GET /api/instances/settings/ (KEP-83).
 * Each help line says what the setting does and who it affects.
 */

const tab = (title: string, description: string) => ({ title, description });

// KEP-85 permission keys. Content has an owner; project structure goes by level.
const PERM_CONTENT_KEYS = [
  "PERM_MODULE_EDIT",
  "PERM_MODULE_ARCHIVE",
  "PERM_MODULE_DELETE",
  "PERM_PAGE_EDIT",
  "PERM_PAGE_ARCHIVE",
  "PERM_PAGE_DELETE",
  "PERM_VIEW_EDIT",
  "PERM_VIEW_DELETE",
  "PERM_COMMENT_EDIT",
  "PERM_COMMENT_DELETE",
  "PERM_WIKI_EDIT",
  "PERM_WIKI_DELETE",
] as const;
const PERM_STRUCTURE_KEYS = [
  "PERM_PROJECT_EDIT",
  "PERM_PROJECT_WORKFLOW",
  "PERM_PROJECT_ARCHIVE",
  "PERM_PROJECT_DELETE",
  "PERM_TRASH_RESTORE",
  "PERM_TRASH_PURGE",
] as const;
const PERM_CONTENT_CHOICES: Record<number, string> = {
  0: "Owner and their superiors",
  1: "Owner only",
  2: "Any department member",
};
const PERM_STRUCTURE_CHOICES: Record<number, string> = {
  20: "Supervisor and above, in their departments",
  30: "Manager and above, in their divisions",
  40: "Directors only",
  90: "Admins only",
};
const permissionChoices: Record<string, Record<number, string>> = Object.fromEntries([
  ...PERM_CONTENT_KEYS.map((key) => [key, PERM_CONTENT_CHOICES]),
  ...PERM_STRUCTURE_KEYS.map((key) => [key, PERM_STRUCTURE_CHOICES]),
]);

export const settingsStrings = {
  menus: {
    general: tab("General", "Identify your instance and set the office timezone."),
    access: tab("Sign-in & access", "Who can sign in, how, and for how long."),
    people: tab("People", "Accounts, organization, and what new members start with."),
    rules: tab("Work rules", "Approvals, permissions, dates, and archiving."),
    notifications: tab("Notifications", "Email server, sending rules, schedule, and defaults by role."),
    modules: tab("Modules", "Which modules exist and the limits inside them."),
    integrations: tab("Integrations", "Google, AI, and the image library."),
    logs: tab("Data & logs", "Activity, audit log, trash, and how long they are kept."),
  },

  tabs: {
    general_instance: tab(
      "Instance",
      "Change the name of your instance and instance admin e-mail addresses. Enable or disable telemetry in your instance."
    ),
    general_company: tab("Company", "Details that apply to the whole office."),
    general_workspaces: tab("Workspaces", "See all workspaces on this instance."),
    access_methods: tab("Methods", "Choose how people sign up and sign in, and who may create workspaces."),
    access_providers: tab("Providers", "Sign in with an outside account. Each provider needs its own credentials."),
    access_sessions: tab("Sessions & invites", "How long a sign-in lasts and how long an invitation stays valid."),
    people_accounts: tab(
      "Accounts",
      "Create, deactivate, and manage accounts. Self sign-up is off, so accounts are only created here."
    ),
    people_organization: tab("Organization", "Departments, divisions, and who sits where."),
    people_defaults: tab(
      "New member defaults",
      "Settings every new account starts with. Existing accounts are set per person on the Accounts tab."
    ),
    rules_approvals: tab(
      "Approvals & ownership",
      "Who approves finished work and who may delete, archive, reassign, or re-date a work item."
    ),
    rules_dates: tab(
      "Dates & overdue",
      "How start and due dates fill themselves in as work items move, and when a work item counts as overdue."
    ),
    rules_permissions: tab(
      "Permissions",
      "Who else may change, archive, or delete modules, pages, views, comments, Wiki files, departments, and trash."
    ),
    rules_archiving: tab(
      "Archiving",
      "When finished work items move to the archive, and how departments can go sooner."
    ),
    rules_projects: tab(
      "New department defaults",
      "Settings every new department starts with. They are applied when a department is created in Organization."
    ),
    notifications_email: tab("Email server", "Configure your SMTP controls."),
    notifications_sending: tab("Sending rules", "Which emails go out, how they are grouped, and who receives them."),
    notifications_schedule: tab(
      "Schedule",
      "When reminders and daily summaries are sent. All times use the office timezone."
    ),
    notifications_roles: tab(
      "Defaults by role",
      "Which notifications each position starts with. Staff and leaders are copied to an account when it is created; the director row applies to every director and secretary at once."
    ),
    notifications_preview: tab("Preview", "Every email the app sends, rendered with sample data. Nothing is sent."),
    modules_visibility: tab(
      "Visibility",
      "Turning a module off hides its menus and blocks its pages for everyone. Data stays intact and returns when it is turned back on."
    ),
    modules_chat: tab("Chat", "Limits for direct messages and group channels."),
    modules_dashboards: tab(
      "Dashboards",
      "When a division is flagged on the Division Dashboard and how long items stay on Needs attention."
    ),
    modules_files: tab("Files", "How large an uploaded file may be."),
    integrations_google: tab(
      "Google",
      "Sign in with Google and the Google Calendar sync, with their credentials, on one page."
    ),
    integrations_ai: tab("Artificial intelligence", "Credentials for the AI features every workspace uses."),
    integrations_image: tab("Image library", "Let people search and pick images from third-party libraries."),
    logs_activity: tab("Activity", "Who is using the app right now and how often people sign in and out."),
    logs_audit: tab("Audit log", "Who changed what in God Mode and in the app."),
    logs_trash: tab("Trash", "Deleted items waiting to be removed for good."),
    logs_retention: tab("Retention", "How long deleted items and sign-in history are kept before they are removed."),
  },

  sections: {
    company: { title: "Office", hint: "One timezone for the whole office." },
    sessions: { title: "Sign-in sessions" },
    invites: { title: "Invitations" },
    approvals: { title: "Approvals", hint: "Applies to work items finished by staff." },
    ownership: {
      title: "Ownership",
      hint: "Who may act on a work item that belongs to someone else. Modules, pages, comments, and departments are on the Permissions tab.",
    },
    hierarchy: { title: "Hierarchy" },
    dates_fill: { title: "Filling dates" },
    dates_overdue: { title: "Overdue" },
    perm_modules: { title: "Modules", hint: "The owners are whoever created the module, its lead, and its members." },
    perm_pages: { title: "Pages", hint: "The owner is the person who created the page." },
    perm_views: { title: "Views", hint: "Saved work item views. The owner is the person who saved it." },
    perm_comments: { title: "Comments", hint: "Comments on work items. The owner is the author." },
    perm_wiki: { title: "Wiki files", hint: "Files in the company library. The owner is the uploader." },
    perm_projects: {
      title: "Departments",
      hint: "Departments have no single owner. Supervisors act on their own department, managers in their divisions, directors on everything they oversee.",
    },
    perm_trash: {
      title: "Trash",
      hint: "Work items, pages, and modules waiting in a department's trash after someone deleted them.",
    },
    archive_instance: { title: "Instance ceiling" },
    archive_projects: { title: "New departments" },
    sending_reminders: { title: "Reminders" },
    sending_chat: { title: "Chat" },
    sending_work: { title: "Work item email" },
    sending_assign: { title: "Assignments" },
    sending_admin: {
      title: "Super Admin emails",
      hint: "Emails that only Super Admins receive, such as warnings about logs. They go to every active Super Admin, whatever their position.",
    },
    schedule_reminders: { title: "Due date reminders" },
    schedule_summaries: { title: "Daily summaries" },
    schedule_content: { title: "What summaries show" },
    modules_sidebar: { title: "Main sidebar" },
    modules_workspace: { title: "Workspace menu" },
    modules_project: {
      title: "Department menu",
      hint: "Department admins can still turn these on or off per department. A module that is off here is hidden in every department.",
    },
    modules_work_item: { title: "Work item features" },
    chat_limits: { title: "Messages" },
    dashboards_status: {
      title: "Division status",
      hint: "Each division gets a status from the share of its active work items that are past due.",
    },
    dashboards_attention: { title: "Needs attention", hint: "The widget on Home that lists work waiting on a person." },
    files: { title: "Uploads" },
    google_signin: { title: "Sign in with Google" },
    google_calendar: { title: "Google Calendar" },
    retention: { title: "Retention" },
  },

  fields: {
    OFFICE_TIMEZONE: {
      name: "Office timezone",
      help: "The one timezone for every reminder and summary time below. Affects when emails go out and what counts as today in them.",
    },
    SESSION_DAYS: {
      name: "Stay signed in for",
      help: "How long a sign-in lasts before people have to sign in again. Applies to everyone; shorter is safer. Changes apply from the next sign-in; people already signed in keep their current session length.",
    },
    INVITE_EXPIRY_DAYS: {
      name: "Invitations expire after",
      help: "Days before an unused invitation stops working. 0 means invitations never expire.",
    },
    APPROVAL_REQUIRED_BELOW_LEVEL: {
      name: "Who needs approval to finish work",
      help: "Work items finished by people below this level wait for a superior to approve. Affects the approval queue.",
    },
    APPROVAL_REJECT_REASON_REQUIRED: {
      name: "Require a reason to reject",
      help: "A superior must write why when sending finished work back. Staff see the reason on the work item.",
    },
    APPROVAL_FINISH_TIME: {
      name: "Finish time for approved work",
      help: "When a work item that went through approval counts as done. The finish date and an automatically filled due date use this time, so a slow approval does not make staff look late. A resubmission uses the latest request.",
    },
    APPROVAL_PENDING_NOT_LATE: {
      name: "Waiting for approval is not late",
      help: "Work items waiting for approval are left out of overdue counts, red due dates, deadline reminders, daily summaries and Needs attention. They still show as waiting for approval. Once the due date passes, the people who can approve get the reminder instead of the staff member.",
    },
    TASK_DELETE_RULE: {
      name: "Who can delete or archive a work item",
      help: "Applies to every work item in every department.",
    },
    DUE_DATE_CHANGE_RULE: {
      name: "Who can change a due date",
      help: "Overdue work items never get their due date moved, whatever this says.",
    },
    PERM_MODULE_EDIT: {
      name: "Edit a module",
      help: "Who can rename a module or change its dates, lead, members, and description. Its creator, lead, and members can always edit it.",
    },
    PERM_MODULE_ARCHIVE: {
      name: "Archive a module",
      help: "Who can archive or restore another person's module. Its creator, lead, and members can always archive it.",
    },
    PERM_MODULE_DELETE: {
      name: "Delete a module",
      help: "Who can delete another person's module. Its work items stay in the department. Its creator, lead, and members can always delete it.",
    },
    PERM_PAGE_EDIT: {
      name: "Edit a page",
      help: "Who can change the title or content of another person's page. Authors can always edit their own.",
    },
    PERM_PAGE_ARCHIVE: {
      name: "Archive a page",
      help: "Who can archive or restore another person's page. Authors can always archive their own.",
    },
    PERM_PAGE_DELETE: {
      name: "Delete a page",
      help: "Who can delete another person's page. Authors can always delete their own.",
    },
    PERM_VIEW_EDIT: {
      name: "Edit a view",
      help: "Who can change the filters, layout, or name of a view someone else saved. The person who saved it can always edit it.",
    },
    PERM_VIEW_DELETE: {
      name: "Delete a view",
      help: "Who can delete a view someone else saved. The person who saved it can always delete it.",
    },
    PERM_COMMENT_EDIT: {
      name: "Edit a comment",
      help: "Who can change another person's comment. Authors can always edit their own.",
    },
    PERM_COMMENT_DELETE: {
      name: "Delete a comment",
      help: "Who can remove another person's comment. Authors can always delete their own.",
    },
    PERM_WIKI_EDIT: {
      name: "Edit a Wiki file",
      help: "Who can change a file someone else uploaded. Uploaders can always edit their own.",
    },
    PERM_WIKI_DELETE: {
      name: "Delete a Wiki file",
      help: "Who can delete a file someone else uploaded. Uploaders can always delete their own.",
    },
    PERM_PROJECT_EDIT: {
      name: "Department details and settings",
      help: "Who can change a department's name, identifier, cover, features, and automation.",
    },
    PERM_PROJECT_WORKFLOW: {
      name: "Department workflow",
      help: "Who can add, change, or remove a department's states, labels, estimates, and intake.",
    },
    PERM_PROJECT_ARCHIVE: {
      name: "Archive a department",
      help: "Who can archive a department or bring it back.",
    },
    PERM_PROJECT_DELETE: {
      name: "Delete a department",
      help: "Who can delete a whole department, with all its work items, modules, and pages.",
    },
    PERM_TRASH_RESTORE: {
      name: "Restore from trash",
      help: "Who can bring back something another person deleted in a department.",
    },
    PERM_TRASH_PURGE: {
      name: "Delete for good",
      help: "Who can remove something from a department's trash before the retention period ends. This cannot be undone.",
    },
    ASSIGN_DOWN_ONLY: {
      name: "Assign to lower levels only",
      help: "People can only assign work to someone on a lower level than themselves. Off lets anyone assign to anyone.",
    },
    HIERARKI_GERBANG_TUGAS: {
      name: "Hierarchy gate",
      help: "Staff can only assign themselves and their work items wait for a superior's approval. Off keeps the previous behavior.",
    },
    AUTO_START_DATE_ON_START: {
      name: "Fill start date when work starts",
      help: "Moving a work item to an In Progress state sets an empty start date to today. Skipped when the due date has already passed.",
    },
    AUTO_DUE_DATE_ON_DONE: {
      name: "Fill due date when work is done",
      help: "Moving a work item to Done sets an empty due date to the day it was finished. With the hierarchy gate on, it is filled when a superior approves, using the finish time set under Approvals & ownership.",
    },
    DUE_DATE_ON_EARLY_DONE: {
      name: "Due date when finished early",
      help: "Moving the due date records the planned date in the activity log. Late work never moves its due date, so reports keep showing it as late.",
    },
    OVERDUE_GRACE_DAYS: {
      name: "Overdue grace period",
      help: "Days after the due date before a work item turns red and counts as overdue on dashboards. Reminder emails and summaries still count calendar days.",
    },
    AUTO_ARCHIVE_DONE_DAYS: {
      name: "Archive done work items after",
      help: "The ceiling for every department: done work items are archived once they have been done this long. A department can archive sooner, never later than this. Checked once a day.",
    },
    ENABLE_DEADLINE_REMINDER: {
      name: "Due date reminders",
      help: "Emails the assignee and assigner around the due date, with a calendar attachment. Off stops the emails; inbox reminders follow the Schedule tab.",
    },
    ENABLE_CHAT_EMAIL: {
      name: "Unread message email",
      help: "Emails people about chat messages they have not read.",
    },
    CHAT_EMAIL_QUIET_MINUTES: {
      name: "Wait before emailing",
      help: "How long a message stays unread before it is emailed.",
    },
    CHAT_EMAIL_INTERVAL_MINUTES: {
      name: "Minimum gap between emails",
      help: "At most one unread-message email per person within this window.",
    },
    ENABLE_EMAIL_BATCH: {
      name: "Collect work item emails",
      help: "Updates, comments, mentions and approvals for one person are held and sent as one email. Off sends each as it happens.",
    },
    EMAIL_BATCH_DELAY_MINUTES: {
      name: "Collect for",
      help: "Counted from the oldest unsent update for each person. Everything that arrives meanwhile goes into the same email.",
    },
    ENABLE_EMAIL_THREADING: {
      name: "One email thread per work item",
      help: "Emails about the same work item share a subject like [PROJ-12] Title, so Gmail and Outlook stack them in one conversation.",
    },
    ENABLE_EMAIL_ACTIVE_ONLY: {
      name: "Email active members only",
      help: "Skip work item, approval, assignment, due date and chat emails for people who have not opened the app recently. Sign-in codes, password resets and invites are always sent.",
    },
    EMAIL_ACTIVE_DAYS: {
      name: "Active within",
      help: "People who last used the app longer ago than this get no work item emails.",
    },
    ENABLE_ADMIN_RETENTION_EMAIL: {
      name: "Warn before login history is deleted",
      help: "Email every Super Admin a few days before the oldest sign-in history is deleted, so it can be exported first. The warning on the Retention tab always shows, and cleanup keeps running.",
    },
    ENABLE_TUGAS_KE_DM: {
      name: "Assignments to DM",
      help: "New work item details are posted in the direct message between assigner and assignee.",
    },
    DEADLINE_REMINDER_EMAIL_DAYS: {
      name: "Reminder email days",
      help: "Days around the due date when a reminder email goes out. Negative is before, 0 is the due day, positive is after.",
    },
    DEADLINE_REMINDER_INBOX_DAYS: {
      name: "Reminder inbox days",
      help: "The same idea for the in-app inbox reminder. Affects assignees and assigners.",
    },
    DEADLINE_REMINDER_TIME: {
      name: "Reminder time",
      help: "When the day's reminders are sent. Use 5-minute steps, no later than 23:50.",
    },
    DIGEST_MORNING_TIME: {
      name: "Morning summary time",
      help: "When people who chose the morning summary receive it. Use 5-minute steps, no later than 23:50.",
    },
    DIGEST_EVENING_TIME: {
      name: "Evening summary time",
      help: "When people who chose the evening summary receive it. Use 5-minute steps, no later than 23:50.",
    },
    DIRECTOR_DIGEST_TIME: {
      name: "Director summary time",
      help: "When directors receive their division summary. Directors cannot turn it off. Use 5-minute steps, no later than 23:50.",
    },
    DIGEST_WEEKDAYS: {
      name: "Summary days",
      help: "Days of the week the daily summaries are sent. Applies to every summary.",
    },
    DIGEST_LOOKAHEAD_DAYS: {
      name: "Look ahead",
      help: "How many days of upcoming due dates a summary lists.",
    },
    STUCK_AFTER_DAYS: {
      name: "Stuck after",
      help: "A work item with no activity for this long is listed as stuck in summaries.",
    },
    CHAT_DELETE_WINDOW_HOURS: {
      name: "Delete window for messages",
      help: "People can delete their own messages only within this many hours after sending. 0 removes the limit.",
    },
    CHAT_EDIT_WINDOW_HOURS: {
      name: "Edit window for messages",
      help: "People can edit their own messages only within this many hours after sending. 0 removes the limit.",
    },
    CHAT_MESSAGE_MAX_LENGTH: {
      name: "Longest message",
      help: "Characters allowed in one chat message.",
    },
    CHAT_ATTACHMENTS_MAX: {
      name: "Attachments per message",
      help: "Files allowed on one chat message.",
    },
    DASHBOARD_PERHATIAN_PERSEN: {
      name: "Needs attention from",
      help: "A division is marked Needs attention once this share of its active work items is overdue.",
    },
    DASHBOARD_KRITIS_PERSEN: {
      name: "Critical from",
      help: "A division is marked Critical once this share is overdue. Keep it above Needs attention.",
    },
    DASHBOARD_ON_TIME_WINDOW_DAYS: {
      name: "On-time window",
      help: "Done on time counts work items with a due date that were finished in this many past days.",
    },
    ATTENTION_REJECTED_DAYS: {
      name: "Rejected work stays listed for",
      help: "How long a rejected work item stays on the assignee's Needs attention widget.",
    },
    ATTENTION_MENTION_DAYS: {
      name: "Mentions stay listed for",
      help: "How long an unanswered mention stays on the Needs attention widget.",
    },
    UPLOAD_MAX_MB: {
      name: "Largest upload",
      help: "The biggest file anyone can attach, in MB. Applies to every upload in the app and in chat.",
    },
    ENABLE_GOOGLE_CALENDAR_SYNC: {
      name: "Google Calendar sync",
      help: "Work item due dates are written to the Google calendar of everyone who connects their account.",
    },
    TRASH_RETENTION_DAYS: {
      name: "Trash retention",
      help: "Deleted work items, pages, and modules are removed for good after this many days.",
    },
    LOGIN_HISTORY_RETENTION_DAYS: {
      name: "Sign-in history retention",
      help: "Sign-in and sign-out events older than this are removed. Super Admins get an email a week before.",
    },
  } as Record<string, { name: string; help: string }>,

  modules: {
    inbox: { name: "Inbox", desc: "Notifications for mentions, assignments, and updates." },
    your_work: {
      name: "Your work",
      desc: "Personal overview of assigned and created work items. Also hides profile pages.",
    },
    stickies: { name: "Stickies", desc: "Personal sticky notes." },
    drafts: { name: "Drafts", desc: "Work items saved as drafts before they are created." },
    quick_links: { name: "Quick links", desc: "Personal bookmarks to pages inside and outside the app." },
    dashboards: { name: "Dashboards", desc: "Division dashboards with progress and workload per department." },
    initiatives: { name: "Initiatives", desc: "Cross-project goals that group related work." },
    views: { name: "Views", desc: "Saved work item views, at workspace and department level." },
    analytics: { name: "Analytics", desc: "Workspace analytics and insight charts." },
    chat: { name: "Chat", desc: "Direct messages, group channels, and voice or video calls." },
    wiki: { name: "Wiki", desc: "Company file library, plus the per-folder access setting in departments." },
    archives: { name: "Archives", desc: "Archived departments, work items, and modules." },
    work_items: {
      name: "Work items",
      desc: "Department work item lists and detail pages. Turning this off leaves departments with almost nothing to show.",
    },
    modules: { name: "Modules", desc: "Groups of related work items inside a department." },
    pages: { name: "Pages", desc: "Department documents written in the editor." },
    intake: { name: "Intake", desc: "Requests from outside the department that wait for triage." },
    approvals: {
      name: "Approvals",
      desc: "Approval queue per division. With the hierarchy gate on, keep this on so superiors can approve staff work.",
    },
    time_tracking: { name: "Time tracking", desc: "Worklogs on work items and logged hours on division dashboards." },
    estimates: { name: "Estimates", desc: "Story points or time estimates on work items, per department." },
  },

  /** Labels for choice values. A value the server adds later falls back to "Option N". */
  choices: {
    ...permissionChoices,
    APPROVAL_REQUIRED_BELOW_LEVEL: {
      20: "Staff only",
      30: "Staff and supervisors",
      40: "Everyone below director",
    },
    TASK_DELETE_RULE: {
      0: "Creator, department admins and Super Admin",
      1: "Creator and Super Admin only",
      2: "Anyone who may edit the work item",
    },
    DUE_DATE_CHANGE_RULE: {
      0: "Creator and Super Admin",
      1: "Creator, department admins and Super Admin",
      2: "Anyone who may edit the work item",
    },
    DUE_DATE_ON_EARLY_DONE: {
      0: "Keep the planned date",
      1: "Move to the finish date",
    },
    APPROVAL_FINISH_TIME: {
      0: "When the staff member requests approval",
      1: "When a superior approves",
    },
  } as Record<string, Record<number, string>>,

  controls: {
    on: "On",
    off: "Off",
    default_prefix: "Default: {value}",
    option: "Option {n}",
    never: "never",
    archive_off: "Off",
    archive_after: "After {count} days",
    choose_timezone: "Choose a timezone",
    day_list_placeholder: "-3, -1, 0, 3",
    day_list_summary_before: "{n}d before",
    day_list_summary_on: "on the day",
    day_list_summary_after: "{n}d after",
    time_in_zone: "{zone} time",
  },

  units: {
    minutes: "minutes",
    hours: "hours",
    days: "days",
    percent: "%",
    mb: "MB",
    chars: "characters",
    files: "files",
  } as Record<string, string>,

  weekdays: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],

  validation: {
    number: "Enter a whole number from {min} to {max}.",
    number_plain: "Enter a whole number.",
    time: "Enter a time like 08:30.",
    day_list: "Enter 1 to 12 different whole numbers from -30 to 30, separated by commas.",
    weekday_set: "Pick at least one day.",
    choice: "Pick one of the options.",
    timezone: "Choose a timezone.",
    fix_first: "Fix the highlighted values first.",
  },

  form: {
    load_failed: "Could not load the settings.",
    not_available: "This setting is not available on this server version.",
    reset: "Reset to defaults",
    reset_confirm_hint: "Puts every value on this tab back to its default. Nothing is saved until you press Save.",
    saved_title: "Saved",
    saved_message: "{tab} updated.",
    save_failed_title: "Could not save",
    save_failed_message: "The server rejected one or more values.",
    sensitive_note: "Rules on this tab are sensitive. Saving asks you to type {phrase} first.",
    audit_note: "Every change is written to the audit log.",
  },

  confirm: {
    title: "Change sensitive rules?",
    intro:
      "These rules change who may approve, edit, delete, or reassign work for everyone. The change is written to the audit log.",
    changes_title: "You are changing",
    from_to: "{from} to {to}",
    instruction: "Type {phrase} to continue.",
    confirm: "Save changes",
    cancel: "Keep editing",
    wrong_phrase: "The phrase does not match.",
    required: "The server wants the confirmation phrase. Type it and save again.",
  },

  smtp: {
    title: "Email is not set up",
    body: "Nothing on this tab is delivered until an email server is configured and turned on.",
    link: "Open Email server",
  },

  permissions: {
    intro:
      "Super Admins and workspace admins can always do everything, and owners can always change their own things. These rules decide who else can. Work items keep their own rules on the Approvals & ownership tab.",
  },

  company: {
    timezone_note: "Times on the Schedule tab are entered in this timezone.",
    workspace_note: "Workspaces no longer have their own timezone setting.",
  },

  access: {
    signup_name: "Allow anyone to sign up",
    signup_help: "Off means people can only join when an admin invites them or creates their account.",
    workspace_name: "Allow members to create workspaces",
    workspace_help:
      "Off means only instance admins can create workspaces. Everyone else is invited to the ones that exist.",
    section_open: { title: "Who can join" },
    methods_title: "Available authentication modes",
    providers_title: "Sign-in providers",
    google_link: "Google credentials and sign-in live under Integrations.",
    google_open: "Open Google",
    saved: "Saved",
    save_failed: "Could not save",
    saving: "Saving",
  },

  archiving: {
    ceiling_hint:
      "The instance ceiling applies to every department. A department can archive sooner, never later than this.",
    projects_title: "New department archive and close timing",
    projects_hint:
      "What a new department starts with. A department can archive sooner, never later than the instance ceiling above: a longer value here is capped to the ceiling when the check runs.",
    archive_in: "Archive completed work items after",
    close_in: "Close stale work items after",
    months: "{count} months",
    off: "Off",
    projects_help: "Months. 0 turns it off for new departments. Existing departments are not changed.",
    load_failed: "Could not load the department defaults.",
    reset: "Reset to defaults",
    saved: "Archiving saved",
    save_failed: "Could not save",
    label: "New department archiving",
  },

  google: {
    signin_help:
      "The OAuth client people use to sign in with Google. It has its own credentials, separate from Calendar.",
    signin_enabled: "Sign in with Google",
    signin_enabled_help: "Lets people sign in or sign up with their Google accounts.",
    calendar_client_id: "Client ID",
    calendar_client_secret: "Client secret",
    calendar_hint:
      "A Web OAuth client with the Google Calendar API enabled. Redirect URI must be exactly https://<host>/api/google-calendar/callback/",
    calendar_missing: "Fill in the Calendar Client ID and secret before turning sync on.",
    saved: "Saved",
    save_failed: "Could not save",
    saving: "Saving",
    save_credentials: "Save credentials",
    calendar_credentials: "Calendar credentials",
    signin_credentials: "Sign-in credentials",
  },

  roles: {
    load_failed: "Could not load the defaults.",
    saved: "Defaults by role saved",
    save_failed: "Could not save",
    reset: "Reset to defaults",
    label: "Defaults by role",
    col_staf: "Staff (or no position)",
    col_pimpinan: "Leaders (supervisor, manager)",
    col_direktur: "Directors and secretaries",
    direktur_note:
      "Also a hard limit: anything off here is off for every director and secretary right away, whatever their own settings. Keep it to mentions, chat, and summaries.",
    admin_note:
      "A switch turned off on Sending rules or Schedule cannot be turned on by anyone; people see it greyed out as turned off by admin.",
  },
};
