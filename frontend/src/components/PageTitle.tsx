"use client";

import { useEffect } from "react";

export function usePageTitle(title: string) {
  useEffect(() => {
    document.title = `${title} | ClearScript`;
    return () => {
      document.title = "ClearScript — PBM Disclosure Audit Engine";
    };
  }, [title]);
}
