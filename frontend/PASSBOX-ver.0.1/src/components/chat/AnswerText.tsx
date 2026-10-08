// Renders an AI answer as plain text, turning only **bold** markers into <strong>.
// Everything else (including any HTML or markdown links) stays literal text, so a
// verified answer can never inject markup or auto-load remote content into the page.
export function AnswerText({ text }: { text: string }) {
  const parts = text.split(/\*\*([^*\n]+)\*\*/g)
  return (
    <p className="answer-text">
      {parts.map((part, index) => (index % 2 === 1 ? <strong key={index}>{part}</strong> : part))}
    </p>
  )
}
