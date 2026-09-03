export type RendererKind = "mcq" | "free_form" | "lines" | "complexity_question" | "code_writing" | "graph_construction" | "unknown";

/** Maps only interaction formats to renderers. It does not interpret mode,
 * purpose, progression, or pedagogical intent. */
export function rendererForType(type: string): RendererKind {
  if (type === "mcq") return "mcq";
  if (type === "free_form") return "free_form";
  if (type === "output_prediction" || type === "code_tracing") return "lines";
  if (type === "complexity_question") return "complexity_question";
  if (type === "code_writing") return "code_writing";
  if (type === "graph_construction") return "graph_construction";
  return "unknown";
}
