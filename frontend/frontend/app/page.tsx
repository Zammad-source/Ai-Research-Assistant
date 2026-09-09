import Link from "next/link";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100dvh-4rem)] px-4 text-center gap-8">
      <div className="max-w-xl">
        <h1 className="text-3xl md:text-4xl font-heading font-semibold mb-3">
          Ask and research — in your own language.
        </h1>
        <p className="text-muted-foreground text-base">
          Urdu, Roman Urdu, Sindhi, Punjabi, Pashto, and English —
          detected automatically.
        </p>
      </div>

      <div className="w-full max-w-sm">
        <Link href="/research">
          <Button
            variant="outline"
            className="w-full h-auto flex-col items-start gap-2 p-5 text-start"
          >
            <Search className="h-5 w-5 text-primary" />
            <span className="font-semibold text-base">Research Assistant</span>
            <span className="text-sm font-normal text-muted-foreground whitespace-normal">
              Ask a question, get a grounded answer with sources.
            </span>
          </Button>
        </Link>
      </div>
    </div>
  );
}