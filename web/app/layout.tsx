import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Sidebar } from "@/components/Sidebar";
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
  title: "Garg Dental Operations Toolkit",
  description: "Excel Comparator, Collection Priority Analyzer, and Inventory Movement Analyzer.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex bg-slate-50 dark:bg-slate-950">
        <Sidebar />
        {/* pt-16 clears the fixed hamburger trigger Sidebar renders below
            md: - most pages only have p-6, not enough room on their own. */}
        <main className="flex-1 overflow-y-auto pt-16 md:pt-0 print:overflow-visible print:pt-0">{children}</main>
      </body>
    </html>
  );
}
