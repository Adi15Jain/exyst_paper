import "@/styles/globals.css";
import type { AppProps } from "next/app";
import Head from "next/head";
import { useRouter } from "next/router";
import { AuthProvider } from "@/lib/auth-context";
import RouteProgress from "@/components/ui/RouteProgress";

export default function App({ Component, pageProps, router }: AppProps) {
    const { asPath } = useRouter();

    return (
        <>
            <Head>
                <meta
                    name="viewport"
                    content="width=device-width, initial-scale=1"
                />
            </Head>
            <AuthProvider>
                {/* Acknowledges every navigation immediately. */}
                <RouteProgress />
                {/* Keying on the path re-runs the enter animation per route, so
                    pages fade in rather than snapping into place. */}
                <div key={asPath || router.asPath} className="page-enter">
                    <Component {...pageProps} />
                </div>
            </AuthProvider>
        </>
    );
}
