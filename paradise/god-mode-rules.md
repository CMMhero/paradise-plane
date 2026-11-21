# God Mode rules: how to add one rule

The contract for anyone (human or agent) moving a rule that is still hardcoded
into God Mode > Work rules > All rules. The inventory is in
`.rules-inventory.local.md` (local, not committed), areas A through G.

## How it is built

- **Registry**: `apps/api/plane/utils/aturan/`. One `Rule` per rule, declared in
  `area_<name>.py` inside the `ATURAN` tuple. Area files are discovered
  automatically (the loader scans for `area_*` module names), so there is no
  shared list to edit.
- **Area -> file**: A `area_visibilitas.py`, B `area_tugas.py`, C
  `area_tampilan.py`, D `area_notifikasi.py`, E `area_obrolan.py`, F
  `area_keamanan.py`, G `area_keputusan.py`. The web mirror lives in
  `packages/constants/src/aturan/area-<name>.ts` with the same names.
- **Storage**: an `InstanceConfiguration` row whose key equals the rule's `key`.
  Display defaults for new accounts (`member_default="tampilan.<column>"`) are
  stored in PARADISE_BAWAAN_MEMBER, under the `tampilan` section.
- **Readers**: `aturan.get(key)`, `aturan.get_bool`, `aturan.get_int` (int and
  level), `aturan.get_choice`, `aturan.get_list`. A corrupt value in the database
  falls back to `default` and never raises. An unregistered key raises
  `KeyError`.
- **Cache**: a snapshot of all registry rows per process, one query, 5 second
  lifetime. A process that writes drops it immediately (`post_save`/`post_delete`
  signals). `applies="live"` means the change takes effect within 5 seconds in
  every process.
- **Endpoints**: `GET/PATCH /api/instances/rules/`, `POST /api/instances/rules/reset/`.
  A `risk="high"` rule only changes (and only returns to its default) with the
  phrase `CHANGE RULES`. Every change is recorded in Logs > Audit log as
  `Rule: KEY`. `PATCH /api/instances/configurations/` rejects registry keys.
- **Web**: rules with `web=True` are sent in `config.paradise_rules` on
  `/api/instances/`. apps/web reads them with `useAturan().get("KEY")`, typed,
  with defaults from `@plane/constants`.
- **The God Mode screen** reads everything from the API. A new rule needs no row
  in apps/admin: label, help, choices, bounds, and risk all come from the `Rule`.

## Six steps

1. **Declare** it in your area file. The key constant goes at the top, then the
   `Rule` in `ATURAN`. Import only from `plane.utils.aturan.jenis` (not from
   `plane.utils.aturan`: that package is still loading when the area files are
   imported).

   ```python
   from plane.utils.aturan.jenis import LEVEL, TINGGI, Rule

   APPROVER_MIN_LEVEL = "APPROVER_MIN_LEVEL"

   ATURAN = (
       Rule(
           key=APPROVER_MIN_LEVEL,
           kind=LEVEL,
           default=20,
           choices=(20, 30),
           group="approvals",
           label="Lowest level that can approve",
           help="Finished work waits for someone at this level or above ...",
           risk=TINGGI,
           kep="P29",
       ),
   )
   ```

   - `key`: UPPER_SNAKE, stable forever (it is the row key in the database). It
     must not equal a key in the old registries (`saklar_instance.py`,
     `setelan_instance.py`); the import fails on a clash.
   - `kind`: `BOOL`, `INT` (requires `min`, `max`), `CHOICE` (`choices` holds
     `(value, "Label")`), `TEXT` (`max_length`, default 200), `LEVEL` (`choices`
     holds level numbers; labels are generated), `KEY_LIST` (`choices` holds
     `(key, "Label")`; the value is a tuple of keys).
   - `default`: **exactly today's behavior.** This is not the place to fix
     behavior; a fix is a separate owner decision.
   - `group`: one of the topics in `aturan/grup.py`. The topics already cover all
     seven areas; adding a new topic means one line in that shared file, so avoid
     it if you can.
   - `label` and `help`: English (KEP-46), short sentences, no em dashes. `help`
     says who is affected and what does not change.
   - `risk`: `high` if a wrong value exposes data or opens up edit permission;
     `medium` if it changes who is notified, what is counted, or what data is
     written; `low` if it only affects display. Follow the Risk column in the
     inventory.
   - `applies`: `LIVE` (default), `NEXT_RUN` (read by a scheduled task), or
     `RESTART` (read once at process start; avoid).
   - `web=True` only if apps/web needs the value for DISPLAY. Never for secrets.
     For web rules, write `key=` and `default=<literal>` each on its own single
     line (the TS test reads the Python source).
   - `kep`: the decision reference (`"KEP-83"`) if there is one.

2. **Use it on the server, in one place.** Replace the hardcoded constant or
   comparison with `aturan.get_*` in the function that actually decides
   (resolver, permission gate, task). For permission and data-scope rules,
   **enforcement must live in the API.** The web may hide a button, but it is
   never the only guard, and it never recomputes permissions from a rule value:
   per-person permissions still come from the API (`boleh_*`, `bisa_*`).

3. **Web mirror** (only if `web=True`): add the same key to
   `ATURAN_WEB_<AREA>` in `packages/constants/src/aturan/area-<name>.ts` using
   `boolWeb`, `angkaWeb`, `teksWeb`, `pilihanWeb`, or `daftarWeb`. Use it in an
   `observer` component:

   ```ts
   const { get } = useAturan();
   const hidden = get("DIRECTOR_SIDEBAR_HIDES"); // typed, default applies before config arrives
   ```

   The `index.ts` in that folder already registers all seven areas; don't edit
   it.

4. **Display defaults for new accounts** (area C): use
   `member_default="tampilan.<column>"`. If the value lives in `Profile.theme`,
   also fill in `profile_theme_key` and `profile_values` (a map from each rule
   value to the value stored on the profile). A new account gets the value only
   when it differs from `default` (a missing key is read by the web as the
   default), and the existing "Apply to existing members" button (the `tampilan`
   section) writes it to all accounts. A value that lives in localStorage needs
   its own application in the web; say so in the PR rather than building a second
   defaults path. The All rules screen already shows these rules with an "Apply
   to all members" button. A row in People > New member defaults is optional
   (see ACTIVITY_NEWEST_FIRST for an example); adding one touches a shared file.

5. **Tests, the same pattern for every rule:**
   - _Default unchanged_: with no database row, the behavior under test matches
     what it was before the rule existed (run the existing tests that touch that
     behavior, and add one explicit test).
   - _Other value applies_: write an `InstanceConfiguration` row (or PATCH through
     the endpoint) and prove the API response changes. Examples:
     `tests/contract/app/test_aturan_penyetuju_app.py`,
     `tests/unit/views/test_chat_sematan.py::test_batas_sematan_dari_god_mode`.
   - The registry guard (`tests/unit/utils/test_aturan_registri.py`) and the
     endpoint tests (`tests/contract/app/test_aturan_god_mode.py`) cover new rules
     automatically: complete metadata, defaults pass the validator, `high` rules
     need the phrase, `paradise_rules` contains only web rules.
   - Web: `packages/constants/src/aturan/aturan.test.ts` fails if a web key,
     default, or choice differs from Python. The admin screen has a test that
     reads `area_*.py` and checks that every rule is shown.
   - Don't use `monkeypatch.setattr` on the old constant; write the row. The
     autouse fixture in `plane/tests/conftest.py` clears the cache between tests.

6. **Clean up and record**: delete the old constant it replaces (never leave two
   sources), update the comments where it was used, and run the checks for each
   package you touched. A new rule needs no migration (its row is only created
   when a Super Admin changes it). No new env var (KEP-48).

## Area A: deliberately not moved

- **A1 organization-wide reach threshold (35 or 40): deferred.** The number 35 is
  not a single comparison, it is a shape of the data. `db/direktur.py` makes
  everyone at level 35 and above a role 20 member of ALL projects (never
  revoked), and `db/penempatan.py` and the God Mode editor
  (`menjangkauSeluruhOrganisasi` in apps/admin) refuse to give a secretary a
  placement. Choosing 40 would leave secretaries as admins in every project,
  with no authority to supervise and no way to place them: a widening disguised
  as a narrowing. It needs an owner decision on what happens to those memberships
  (revoke? keep?) and an editor change first.
- **A2 supervision scope per level: deferred.** `divisi_diawasi` already comes
  from placement (department, division, branch); the only level lever with a real
  alternative is A1 (above) and the approver level (APPROVER_MIN_LEVEL, area B).
  A differently named choice would either do nothing or grant cross-unit
  authority that does not exist in the data. This resolver also belongs to the
  area B gate.
- **A8 "director" is 40 on the web and 35 and above in the API:** both
  definitions stay. Each rule's help text states its level as a number, and
  DIRECTOR_MENUS_APPLY_TO chooses whether the menu rules also apply to
  secretaries.
- **A11** follows the approver rule (no key of its own), **A12** the
  cross-division request projection stays in code (a data-leak boundary, KEP-02),
  **A14** already exists in Rules > Projects.
- **A7** is tabs only: the Analytics and Division dashboard endpoints still serve
  any member. If the owner wants that to be access control, the API has to guard
  it first.

## Not moved yet

The old registries (`SAKLAR_BAWAAN`/`_MODUL_BAWAAN`, `SETELAN_ANGKA`/`SETELAN_PILIHAN`,
`SETELAN_TEKS`) stay in place with their old readers and endpoint
(`/api/instances/settings/`). The All rules screen shows them read-only with
links to their own tabs. Moving them into this registry is a separate job for one
person after the area migration is done: their keys and readers (`saklar_aktif`,
`setelan_angka`, `setelan_teks`) are used in dozens of places and carry env
seeds, so don't touch them in parallel. Area agents only ADD rules.
