import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-8 px-6 py-16">
      <header>
        <p className="text-sm uppercase tracking-widest text-primary">Scaffold</p>
        <h1 className="mt-2 text-4xl font-semibold">Face Search & OSINT Platform</h1>
        <p className="mt-4 max-w-2xl text-muted-foreground">
          Dashboard UI will connect to FastAPI for upload, local face embeddings, FAISS search,
          and optional OSINT verification.
        </p>
      </header>
      <nav className="flex gap-4 text-sm">
        <Link className="underline underline-offset-4" href="/dashboard">
          Dashboard (placeholder)
        </Link>
        <a className="underline underline-offset-4" href="http://localhost:8000/docs" target="_blank" rel="noreferrer">
          API Docs
        </a>
      </nav>
    </main>
  );
}
