import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "agenteval — the reproducible benchmark for Claude Code skills",
  description:
    "A reproducible benchmark for Claude Code skill bundles.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-neutral-950 text-neutral-100 font-mono">
        <div className="max-w-6xl mx-auto px-6 py-8">
          <header className="mb-8 border-b border-neutral-800 pb-4">
            <a href="/" className="text-xl font-semibold">
              agenteval
            </a>{" "}
            <span className="text-neutral-500">
              · reproducible benchmark for Claude Code skills
            </span>
          </header>
          <main>{children}</main>
          <footer className="mt-16 pt-4 border-t border-neutral-800 text-xs text-neutral-500">
            Apache-2.0 · methodology:{" "}
            <a className="underline" href="https://github.com/agenteval/agenteval/blob/main/docs/methodology.md">
              docs/methodology.md
            </a>
          </footer>
        </div>
      </body>
    </html>
  );
}
