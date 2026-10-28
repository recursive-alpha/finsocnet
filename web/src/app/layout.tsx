import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Header } from "@/components/Header";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "FinSocNet — Financial Social Intelligence Network",
  description:
    "Explore trading creators across 31 platforms, mined Knowledge Cards, trader strategy rulebooks, and agent skills.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full flex flex-col bg-[#09090b] text-zinc-100 selection:bg-emerald-500/20 selection:text-emerald-400">
        <Header />
        <main className="flex-1 pb-16">{children}</main>
        <footer className="border-t border-zinc-900 bg-zinc-950 py-6 px-4 text-center text-xs font-mono text-zinc-600">
          FinSocNet v2 • SQLite FTS5 + Knowledge Cards • Agent Skills Specification
        </footer>
      </body>
    </html>
  );
}
