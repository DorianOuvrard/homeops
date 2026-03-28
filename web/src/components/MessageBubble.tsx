interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
}

function formatTime(): string {
  const now = new Date();
  return `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
}

export default function MessageBubble({ role, content }: MessageBubbleProps) {
  const isUser = role === "user";
  const time = formatTime();

  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} mb-4`}>
      <div
        className={`max-w-[80%] px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap break-words ${
          isUser
            ? "bg-[#1a237e] text-white rounded-2xl rounded-br-sm"
            : "bg-[#1a237e] text-white rounded-2xl rounded-bl-sm"
        }`}
      >
        {content}
      </div>
      <span className="text-[10px] mt-1.5 px-1 text-gray-400 font-medium tracking-wide">
        {isUser ? `VOUS · ${time}` : `HODOOR · ${time}`}
      </span>
    </div>
  );
}
