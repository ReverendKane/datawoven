import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "@/styles/globals.css";
import Header from "@/components/ui/header";
import { configureAmplify } from "@/lib/amplify-config";
import { AuthProvider } from "@/contexts/AuthContext";

const inter = Inter({ subsets: ["latin"] });

configureAmplify();

export const metadata: Metadata = {
  title: "DataWoven",
  description:
    "Discover automation opportunities and implement custom RAG systems for your business. AI-powered intelligence woven into your workflow.",
  applicationName: "DataWoven",
  keywords: [
    "RAG systems",
    "business automation",
    "AI discovery",
    "knowledge base",
    "document intelligence",
    "business intelligence",
    "small business AI",
    "agentic AI",
    "workflow automation",
  ],
  authors: [{ name: "Benjamin Black" }],
  creator: "Benjamin Black",
  publisher: "DataWoven",
  metadataBase: new URL("https://datawoven.ai"),

  openGraph: {
    title: "DataWoven — Discover. Automate. Transform.",
    description:
      "Uncover automation opportunities with our Discovery service, then implement custom RAG systems tailored to your business needs.",
    url: "https://datawoven.ai",
    siteName: "DataWoven",
    images: [
      {
        url: "/og-image.jpg",
        width: 1200,
        height: 630,
        alt: "DataWoven - Discover. Automate. Transform.",
      },
    ],
    locale: "en_US",
    type: "website",
  },

  twitter: {
    card: "summary_large_image",
    title: "DataWoven — Discover. Automate. Transform.",
    description:
      "AI-powered discovery and implementation services for small businesses. Custom RAG systems that work for you.",
    images: ["/og-image.jpg"],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        className={`${inter.className} antialiased min-h-screen`}
      >
        <AuthProvider>
          <Header />
          <main className="pt-[75px] sm:pt-[35px]">
            <div className="container">{children}</div>
          </main>
        </AuthProvider>
      </body>
    </html>
  );
}
