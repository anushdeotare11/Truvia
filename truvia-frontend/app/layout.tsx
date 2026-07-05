import type { Metadata } from "next";
import "./globals.css";
import QueryProvider from "@/providers/query-provider";
import { AuthProvider } from "@/context/auth-context";

export const metadata: Metadata = {
  title: "Truvia — Public Safety Intelligence Platform",
  description: "AI-powered Digital Public Safety Intelligence Platform for countering fraud and scams.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <QueryProvider>
          <AuthProvider>
            {children}
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
