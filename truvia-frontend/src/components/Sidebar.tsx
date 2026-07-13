"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "./Icon";
import { useAuth } from "@/lib/auth";
import { navForRole } from "@/lib/nav";

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname();
  const { user } = useAuth();
  const items = user ? navForRole(user.role) : [];

  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div
          className="fixed inset-0 bg-black/60 z-[55] lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={`fixed left-0 top-0 h-screen w-sidebar-width bg-surface-container-lowest border-r border-outline-variant flex flex-col z-[60] transition-transform duration-300 ${
          open ? "translate-x-0" : "-translate-x-full"
        } lg:translate-x-0`}
      >
        <div className="px-card-padding py-stack-lg flex items-center gap-stack-sm">
          <div className="w-10 h-10 bg-primary-container rounded-lg flex items-center justify-center">
            <Icon name="security" className="text-white text-[24px]" fill />
          </div>
          <div className="flex flex-col">
            <span className="text-headline-sm font-bold text-primary tracking-tight leading-tight">
              TRUVIA
            </span>
            <span className="font-label-md text-[10px] text-on-surface-variant -mt-0.5 uppercase tracking-widest">
              Intelligence
            </span>
          </div>
        </div>

        <nav className="flex-1 mt-stack-sm px-stack-sm space-y-1 overflow-y-auto custom-scrollbar">
          {items.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={`${item.name}-${item.href}`}
                href={item.href}
                onClick={onClose}
                className={`flex items-center gap-stack-md px-stack-md py-stack-sm rounded-lg transition-colors ${
                  active
                    ? "bg-primary-container/20 text-primary font-bold"
                    : "text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
                }`}
              >
                <Icon name={item.icon} fill={active} />
                <span className="font-body-md">{item.name}</span>
              </Link>
            );
          })}
        </nav>

        <div className="p-stack-md border-t border-outline-variant">
          <div className="flex items-center gap-stack-md p-stack-sm rounded-lg bg-surface-container">
            <div className="w-9 h-9 rounded-full bg-primary flex items-center justify-center text-on-primary shrink-0">
              <Icon name="account_circle" className="text-[22px]" />
            </div>
            <div className="flex flex-col min-w-0">
              <span className="font-label-md text-[11px] text-on-surface font-bold truncate">
                {user?.name ?? "—"}
              </span>
              <span className="text-[10px] text-primary uppercase tracking-widest truncate">
                {user?.role ?? ""}
              </span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
