import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import "./MessageBody.css";

type Role = "user" | "assistant";

/** Entfernt ein umschließendes ```markdown … ```, das manche Modelle liefern. */
function unwrapAssistantMarkdown(raw: string): string {
  const t = raw.trim();
  const re = /^```(?:markdown|md)?\s*\r?\n([\s\S]*?)\r?\n```\s*$/;
  const m = t.match(re);
  if (m) return m[1].trim();
  return raw;
}

type Props = {
  role: Role;
  content: string;
};

export function MessageBody({ role, content }: Props) {
  if (role === "user") {
    return <div className="message-plain">{content}</div>;
  }

  const text = unwrapAssistantMarkdown(content);

  return (
    <div className="message-md">
      <ReactMarkdown
        remarkPlugins={[remarkBreaks]}
        components={{
          a: ({ node: _n, ...props }) => (
            <a {...props} target="_blank" rel="noreferrer noopener" className="message-md-a" />
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
