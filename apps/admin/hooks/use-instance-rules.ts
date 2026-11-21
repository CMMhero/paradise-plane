/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: rule registry hook for God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback } from "react";
import useSWR, { useSWRConfig } from "swr";
import { InstanceRulesService } from "@plane/services";
import type { TRulesReset, TRulesResponse, TRulesUpdate } from "@plane/types";

const service = new InstanceRulesService();

export const INSTANCE_RULES_KEY = "INSTANCE_RULES";
/** Cache key of People > New member defaults; a member-default rule is stored there. */
const MEMBER_DEFAULTS_KEY = "INSTANCE_MEMBER_DEFAULTS";

/**
 * Loads the rule list once (SWR dedupes) and keeps it fresh: `update` and `reset`
 * write through the API and replace the cache with the server's answer. Errors
 * are thrown as the response body (see InstanceRulesService).
 */
export function useInstanceRules() {
  const { data, error, mutate, isLoading } = useSWR<TRulesResponse>(INSTANCE_RULES_KEY, () => service.list(), {
    revalidateOnFocus: false,
  });
  const { mutate: mutateGlobal } = useSWRConfig();

  const accept = useCallback(
    async (fresh: TRulesResponse) => {
      await mutate(fresh, { revalidate: false });
      // Member-default rules also show on the New member defaults page.
      void mutateGlobal(MEMBER_DEFAULTS_KEY);
      return fresh;
    },
    [mutate, mutateGlobal]
  );

  const update = useCallback((payload: TRulesUpdate) => service.update(payload).then(accept), [accept]);
  const reset = useCallback((payload: TRulesReset) => service.reset(payload).then(accept), [accept]);

  return { data, error, isLoading, update, reset, reload: () => mutate() };
}
