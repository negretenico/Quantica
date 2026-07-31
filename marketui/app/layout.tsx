import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Nav from "./components/Nav";
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
  title: "Quantica",
  description:
    "Real-time market intelligence: feed, trade recommendations, and pipeline performance",
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
      <body className="min-h-full flex flex-col">
        <Nav />
        <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-8">
          {children}
        </main>
        <footer className="border-t border-border px-6 py-4 text-center text-xs text-muted">
          Quantica pipeline: Binance WSS &rarr; Kafka &rarr; ML analysis &rarr;
          LLM narrative
        </footer>
      </body>
    </html>
  );
}
