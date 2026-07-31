"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Feed" },
  { href: "/trades", label: "Trades" },
  { href: "/docs", label: "Docs" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <nav className="border-b border-border px-6 py-3">
      <div className="mx-auto flex max-w-4xl items-center justify-between">
        <Link href="/" className="text-lg font-semibold text-accent">
          Quantica
        </Link>
        <div className="flex gap-6">
          {links.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`text-sm transition-colors ${
                pathname === href
                  ? "text-foreground font-medium"
                  : "text-muted hover:text-foreground"
              }`}
            >
              {label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
