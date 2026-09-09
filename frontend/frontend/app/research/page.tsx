import { ResearchChat } from "@/components/research/ResearchChat"

export default function ResearchPage() {
  // Height assumes AppShell gives this route the full remaining viewport
  // below the header/sidebar. Adjust the calc() if your shell reserves
  // different space.
  return (
    <div className="h-[calc(100vh-0px)]">
      <ResearchChat />
    </div>
  )
}
