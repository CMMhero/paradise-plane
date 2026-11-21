/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: God Mode > Work rules > All rules
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Every rule of the registry by topic, plus the older settings read-only with a
 * link to their own tab. Edits stay local until Save in the shared unsaved bar
 * (components/common/unsaved-changes.tsx). A high-risk rule asks for the typed
 * phrase first, on save and on reset. The server is all-or-nothing: a 400 with
 * `errors` marks the rules and nothing is saved. The logic lives in
 * rules-model.ts; this file renders it.
 */

import { useCallback, useMemo, useState, useSyncExternalStore } from "react";
import { useLocation } from "react-router";
import { ChevronDown, ChevronRight, Search } from "lucide-react";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setPromiseToast, setToast } from "@plane/propel/toast";
import { InstanceMemberService } from "@plane/services";
import type { TMemberDefaultsSection } from "@plane/services";
import type { TParadiseRuleValue, TRegistryRule } from "@plane/types";
import { AlertModalCore, Loader } from "@plane/ui";
import { cn } from "@plane/utils";
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { settingAnchor } from "@/components/command-palette/entries";
import { StateBox } from "@/components/common/paradise";
import { inputClass } from "@/components/common/paradise-styles";
import { useUnsavedChanges } from "@/components/common/unsaved-changes";
import { ConfirmRulesModal } from "@/components/settings/confirm-rules-modal";
import type { TRuleChange } from "@/components/settings/confirm-rules-modal";
import { useInstanceRules } from "@/hooks/use-instance-rules";
import { RuleRow } from "./rule-row";
import {
  buildRuleSections,
  countEntries,
  effectiveValue,
  filterSections,
  formatRuleValue,
  isRuleChanged,
  needsConfirm,
  pendingChanges,
  pendingValues,
  pruneDraft,
  sectionAnchor,
  validateRuleValue,
} from "./rules-model";
import type { TDraft, TRuleEntry, TRuleSection } from "./rules-model";

const memberService = new InstanceMemberService();

type TConfirm = { type: "save" } | { type: "reset"; rule: TRegistryRule };
type TErrorBody = { errors?: Record<string, string>; error?: string };

const DESKTOP_QUERY = "(min-width: 1024px)";
const subscribeDesktop = (notify: () => void) => {
  const query = window.matchMedia(DESKTOP_QUERY);
  query.addEventListener("change", notify);
  return () => query.removeEventListener("change", notify);
};
/** True from the lg breakpoint up: sections stay open and the topic nav shows. */
const useIsDesktop = (): boolean =>
  useSyncExternalStore(
    subscribeDesktop,
    () => window.matchMedia(DESKTOP_QUERY).matches,
    () => false
  );

const scrollToId = (id: string) => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.getElementById(id)?.scrollIntoView({ block: "start", behavior: reduceMotion ? "auto" : "smooth" });
};

const failToast = (title: string, message: string) => setToast({ type: TOAST_TYPE.ERROR, title, message });

const focusRing = "focus-visible:ring-2 focus-visible:ring-accent-strong focus-visible:outline-none";

export function RulesScreen() {
  const { s, fill } = useGodmodeStrings();
  const t = s.settings;
  const a = t.allRules;
  const { data, error, update, reset, reload } = useInstanceRules();
  const { hash } = useLocation();
  const isDesktop = useIsDesktop();

  const [draft, setDraft] = useState<TDraft>({});
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  const [query, setQuery] = useState("");
  const [changedOnly, setChangedOnly] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [confirm, setConfirm] = useState<TConfirm | null>(null);
  const [applyRule, setApplyRule] = useState<TRegistryRule | null>(null);
  const [isApplying, setIsApplying] = useState(false);
  // null = nobody touched an accordion yet: the first section is open on small screens.
  const [openIds, setOpenIds] = useState<Set<string> | null>(null);

  const rules = useMemo(() => data?.rules ?? [], [data]);
  const sections = useMemo(() => (data ? buildRuleSections(data, t) : []), [data, t]);
  const isFiltering = query.trim() !== "" || changedOnly;

  const isChanged = useCallback((entry: TRuleEntry) => isRuleChanged(entry.rule, draft), [draft]);
  const visible = useMemo(
    () => filterSections(sections, { query, changedOnly }, isChanged),
    [sections, query, changedOnly, isChanged]
  );
  const total = countEntries(sections);
  const changedTotal = sections.reduce((n, sec) => n + sec.entries.filter(isChanged).length, 0);

  const changes = useMemo(() => pendingChanges(rules, draft), [rules, draft]);
  const clientErrors = useMemo(() => {
    const out: Record<string, string> = {};
    for (const rule of changes) {
      const message = validateRuleValue(rule, draft[rule.key], a);
      if (message) out[rule.key] = message;
    }
    return out;
  }, [changes, draft, a]);
  const hasClientErrors = Object.keys(clientErrors).length > 0;

  const openSet = useMemo(() => openIds ?? new Set(sections[0] ? [sections[0].id] : []), [openIds, sections]);

  // A palette link (#setting-KEY) must find its row even inside a closed accordion.
  // Adjusted while rendering (not in an effect), once per hash after the rules have loaded.
  const [openedForHash, setOpenedForHash] = useState("");
  if (sections.length > 0 && hash !== openedForHash) {
    setOpenedForHash(hash);
    const id = decodeURIComponent(hash.replace(/^#/, ""));
    const target = id.startsWith("setting-")
      ? sections.find((sec) => sec.entries.some((e) => settingAnchor(e.rule.key) === id))
      : undefined;
    if (target) setOpenIds(new Set([...openSet, target.id]));
  }

  const toggleSection = (id: string) =>
    setOpenIds((prev) => {
      const next = new Set(prev ?? openSet);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const setValue = (key: string, value: TParadiseRuleValue) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
    setServerErrors((prev) => {
      if (!(key in prev)) return prev;
      return Object.fromEntries(Object.entries(prev).filter(([k]) => k !== key));
    });
  };

  const discard = () => {
    setDraft({});
    setServerErrors({});
  };

  const save = async (phrase?: string) => {
    setIsBusy(true);
    try {
      await update({ values: pendingValues(changes, draft), ...(phrase ? { confirm: phrase } : {}) });
      setDraft({});
      setServerErrors({});
      setConfirm(null);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: a.saved_title,
        message: fill(a.saved_message, { count: changes.length }),
      });
    } catch (err) {
      const body = (err ?? {}) as TErrorBody;
      if (body.errors) {
        setServerErrors(body.errors);
        setConfirm(null);
        failToast(a.save_failed_title, a.save_failed_message);
      } else if (body.error === "confirm_required") {
        setConfirm({ type: "save" });
        failToast(a.save_failed_title, a.confirm_required);
      } else {
        failToast(a.save_failed_title, body.error ?? a.save_failed_message);
      }
    } finally {
      setIsBusy(false);
    }
  };

  const handleSave = () => {
    if (changes.length === 0) return;
    if (hasClientErrors) {
      failToast(a.save_failed_title, a.validation.fix_first);
      return;
    }
    if (needsConfirm(changes)) {
      setConfirm({ type: "save" });
      return;
    }
    void save();
  };

  const doReset = async (rule: TRegistryRule, phrase?: string) => {
    setIsBusy(true);
    try {
      const fresh = await reset({ keys: [rule.key], ...(phrase ? { confirm: phrase } : {}) });
      setDraft((prev) =>
        pruneDraft(fresh.rules, Object.fromEntries(Object.entries(prev).filter(([k]) => k !== rule.key)))
      );
      setServerErrors((prev) => Object.fromEntries(Object.entries(prev).filter(([k]) => k !== rule.key)));
      setConfirm(null);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: a.reset_done_title,
        message: fill(a.reset_done_message, { name: rule.label }),
      });
    } catch (err) {
      const body = (err ?? {}) as TErrorBody;
      if (body.error === "confirm_required") {
        setConfirm({ type: "reset", rule });
        failToast(a.reset_failed_title, a.confirm_required);
      } else {
        setConfirm(null);
        failToast(a.reset_failed_title, body.errors?.[rule.key] ?? body.error ?? a.reset_failed_message);
      }
    } finally {
      setIsBusy(false);
    }
  };

  const handleReset = (rule: TRegistryRule) => {
    // Saved value already is the default: the only thing to undo is the unsaved edit.
    if (!rule.changed) {
      setDraft((prev) => Object.fromEntries(Object.entries(prev).filter(([k]) => k !== rule.key)));
      setServerErrors((prev) => Object.fromEntries(Object.entries(prev).filter(([k]) => k !== rule.key)));
      return;
    }
    if (rule.risk === "high") {
      setConfirm({ type: "reset", rule });
      return;
    }
    void doReset(rule);
  };

  const apply = async () => {
    if (!applyRule?.apply_section) return;
    setIsApplying(true);
    const promise = memberService.terapkanBawaan([applyRule.apply_section as TMemberDefaultsSection]);
    setPromiseToast(promise, {
      loading: a.applying,
      success: {
        title: a.applied,
        message: (r) => fill(a.applied_message, { count: Object.values(r.updated).reduce((x, y) => x + y, 0) }),
      },
      error: { title: a.apply_failed, message: (e) => (e as TErrorBody)?.error ?? a.apply_failed },
    });
    try {
      await promise;
      setApplyRule(null);
    } catch {
      // The toast already says what failed; the dialog stays open to try again.
    } finally {
      setIsApplying(false);
    }
  };

  useUnsavedChanges({
    label: changes.length === 1 ? a.changes_label_one : fill(a.changes_label, { count: changes.length }),
    isDirty: changes.length > 0,
    isSaving: isBusy,
    canSave: !hasClientErrors,
    onSave: handleSave,
    onDiscard: discard,
  });

  if (error) {
    return (
      <StateBox tone="danger">
        <p>{a.load_failed}</p>
        <Button variant="secondary" size="lg" className="mt-3 min-h-11" onClick={() => void reload()}>
          {a.retry}
        </Button>
      </StateBox>
    );
  }
  if (!data) {
    return (
      <Loader className="space-y-4" aria-busy="true">
        <Loader.Item height="44px" />
        <Loader.Item height="120px" />
        <Loader.Item height="120px" />
        <Loader.Item height="120px" />
      </Loader>
    );
  }

  const confirmChanges: TRuleChange[] =
    confirm?.type === "reset"
      ? [
          {
            key: confirm.rule.key,
            name: confirm.rule.label,
            from: formatRuleValue(confirm.rule, confirm.rule.value, a),
            to: formatRuleValue(confirm.rule, confirm.rule.default, a),
          },
        ]
      : changes
          .filter((r) => r.risk === "high")
          .map((r) => ({
            key: r.key,
            name: r.label,
            from: formatRuleValue(r, r.value, a),
            to: formatRuleValue(r, draft[r.key], a),
          }));

  const firstLegacyId = visible.find((sec) => sec.source === "legacy")?.id;

  const renderSection = (section: TRuleSection) => {
    const isOpen = isDesktop || isFiltering || openSet.has(section.id);
    const bodyId = `${sectionAnchor(section.id)}-body`;
    const title = (
      <>
        <span className="min-w-0 text-left">{section.title}</span>
        <span className="font-normal shrink-0 text-12 text-tertiary">
          {fill(a.rules_in_section, { count: section.entries.length })}
        </span>
      </>
    );
    return (
      <section key={section.id} id={sectionAnchor(section.id)} className="scroll-mt-20 space-y-3">
        {section.id === firstLegacyId && (
          <div className="space-y-0.5 border-t border-subtle pt-6">
            <p className="text-12 font-medium tracking-wide text-secondary uppercase">{a.other_tabs_title}</p>
            <p className="text-11 text-tertiary">{a.other_tabs_hint}</p>
          </div>
        )}
        <div className="space-y-0.5">
          <h2 className="text-16 font-medium text-primary">
            {isDesktop ? (
              <span className="flex items-baseline gap-3">{title}</span>
            ) : (
              <button
                type="button"
                aria-expanded={isOpen}
                aria-controls={bodyId}
                aria-label={fill(isOpen ? a.collapse : a.expand, { title: section.title })}
                onClick={() => toggleSection(section.id)}
                className={cn(
                  "flex min-h-11 w-full items-center justify-between gap-3 rounded-field text-16 font-medium",
                  focusRing
                )}
              >
                <span className="flex min-w-0 items-baseline gap-3">{title}</span>
                {isOpen ? (
                  <ChevronDown aria-hidden className="size-4 shrink-0" />
                ) : (
                  <ChevronRight aria-hidden className="size-4 shrink-0" />
                )}
              </button>
            )}
          </h2>
          {section.description && isOpen && <p className="text-11 leading-5 text-tertiary">{section.description}</p>}
        </div>
        <div id={bodyId} hidden={!isOpen} className="divide-y divide-subtle rounded-card border border-subtle">
          {section.entries.map((entry) => {
            const { rule } = entry;
            const registry = rule.source === "registry" ? rule : null;
            return (
              <RuleRow
                key={rule.key}
                entry={entry}
                value={registry ? effectiveValue(registry, draft) : rule.value}
                isChanged={isChanged(entry)}
                hasDraft={Object.hasOwn(draft, rule.key) && changes.some((c) => c.key === rule.key)}
                error={serverErrors[rule.key] ?? clientErrors[rule.key]}
                disabled={isBusy}
                onChange={(value) => setValue(rule.key, value)}
                onReset={() => registry && handleReset(registry)}
                onApply={() => registry && setApplyRule(registry)}
              />
            );
          })}
        </div>
      </section>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative w-full sm:w-80">
          <Search
            aria-hidden
            className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-tertiary"
          />
          <label htmlFor="rules-search" className="sr-only">
            {a.search_label}
          </label>
          <input
            id="rules-search"
            type="search"
            value={query}
            placeholder={a.search_placeholder}
            autoComplete="off"
            onChange={(e) => setQuery(e.target.value)}
            className={cn(inputClass, "min-h-11 w-full pl-9", focusRing)}
          />
        </div>
        <Button
          variant={changedOnly ? "primary" : "secondary"}
          size="lg"
          className="min-h-11"
          aria-pressed={changedOnly}
          onClick={() => setChangedOnly((v) => !v)}
        >
          {a.changed_filter}
        </Button>
        <p className="text-12 text-tertiary" aria-live="polite">
          {fill(a.count, { shown: countEntries(visible), total })}
          {" · "}
          {fill(a.count_changed, { count: changedTotal })}
        </p>
      </div>

      <div className="lg:grid lg:grid-cols-[14rem_minmax(0,1fr)] lg:items-start lg:gap-8">
        <nav aria-label={a.topics} className="sticky top-4 hidden max-h-[calc(100vh-10rem)] overflow-y-auto lg:block">
          <ul className="space-y-0.5">
            {visible.map((section) => (
              <li key={section.id}>
                <a
                  href={`#${sectionAnchor(section.id)}`}
                  onClick={(e) => {
                    e.preventDefault();
                    scrollToId(sectionAnchor(section.id));
                  }}
                  className={cn(
                    "flex min-h-9 items-center justify-between gap-2 rounded-field px-2 py-1 text-13 text-secondary hover:bg-layer-transparent-hover hover:text-primary",
                    focusRing
                  )}
                >
                  <span className="min-w-0 truncate">{section.title}</span>
                  <span className="shrink-0 text-11 text-tertiary">{section.entries.length}</span>
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="min-w-0 space-y-8">
          {visible.length === 0 ? (
            <StateBox>
              <p>{changedOnly && query.trim() === "" ? a.empty_changed : a.empty_search}</p>
              <Button
                variant="secondary"
                size="lg"
                className="mt-3 min-h-11"
                onClick={() => {
                  setQuery("");
                  setChangedOnly(false);
                }}
              >
                {a.empty_clear}
              </Button>
            </StateBox>
          ) : (
            visible.map(renderSection)
          )}
        </div>
      </div>

      <ConfirmRulesModal
        isOpen={confirm !== null}
        changes={confirmChanges}
        isSaving={isBusy}
        onCancel={() => setConfirm(null)}
        onConfirm={(phrase) => (confirm?.type === "reset" ? void doReset(confirm.rule, phrase) : void save(phrase))}
      />

      <AlertModalCore
        isOpen={applyRule !== null}
        variant="primary"
        title={applyRule ? fill(a.apply_all_name, { name: applyRule.label }) : ""}
        content={a.apply_confirm}
        isSubmitting={isApplying}
        primaryButtonText={{ default: a.apply_yes, loading: a.applying }}
        secondaryButtonText={s.common.cancel}
        handleClose={() => setApplyRule(null)}
        handleSubmit={() => void apply()}
      />
    </div>
  );
}
