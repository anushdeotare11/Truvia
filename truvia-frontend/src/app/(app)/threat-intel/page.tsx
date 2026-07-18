"use client";

import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PageLoader } from "@/components/AppShell";

/**
 * Legacy route. The Threat Intelligence Engine now lives under /intelligence/*.
 * Preserve any inbound ?entity= link by mapping it to the new ?focus= param.
 */
function Redirector() {
  const router = useRouter();
  const params = useSearchParams();
  useEffect(() => {
    const entity = params.get("entity") || params.get("focus");
    router.replace(entity ? `/intelligence/graph?focus=${entity}` : "/intelligence/graph");
  }, [router, params]);
  return <PageLoader />;
}

export default function LegacyThreatIntelPage() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Redirector />
    </Suspense>
  );
}
