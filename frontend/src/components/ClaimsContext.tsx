"use client";

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";

interface ClaimsStatus {
  custom_data_loaded: boolean;
  claims_count: number;
  filename?: string;
}

interface ClaimsContextValue {
  status: ClaimsStatus | null;
  refresh: () => void;
}

const ClaimsCtx = createContext<ClaimsContextValue>({ status: null, refresh: () => {} });

export function ClaimsProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<ClaimsStatus | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/claims/status");
      if (res.ok) setStatus(await res.json());
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return <ClaimsCtx.Provider value={{ status, refresh }}>{children}</ClaimsCtx.Provider>;
}

export function useClaimsStatus() {
  return useContext(ClaimsCtx);
}
