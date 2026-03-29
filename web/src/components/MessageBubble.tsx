import { useRef, useState } from "react";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  imageUrl?: string;
  audioUrl?: string;
  toolsUsed?: string[];
}

function formatTime(): string {
  const now = new Date();
  return `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
}

const DEFAULT_PHOTO_PROMPTS = ["analyse cette photo.", "identifie cet appareil.", "identifie et enregistre cet appareil."];

function extractImage(content: string): { text: string; url: string | null } {
  const match = content.match(/^\[image:(\/api\/v1\/uploads\/[^\]]+)\]\s*/);
  if (match) {
    const text = content.slice(match[0].length).trim();
    const filtered = DEFAULT_PHOTO_PROMPTS.includes(text.toLowerCase()) ? "" : text;
    return { text: filtered, url: match[1] };
  }
  const photoMatch = content.match(/^\[photo\]\s*/i);
  if (photoMatch) {
    const text = content.slice(photoMatch[0].length).trim();
    const filtered = DEFAULT_PHOTO_PROMPTS.includes(text.toLowerCase()) ? "" : text;
    return { text: filtered, url: null };
  }
  const filtered = DEFAULT_PHOTO_PROMPTS.includes(content.toLowerCase()) ? "" : content;
  return { text: filtered, url: null };
}

function PlayButton({ audioUrl }: { audioUrl: string }) {
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const toggle = () => {
    if (playing && audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setPlaying(false);
      return;
    }
    const audio = new Audio(audioUrl);
    audioRef.current = audio;
    audio.onended = () => setPlaying(false);
    audio.onerror = () => setPlaying(false);
    audio.play();
    setPlaying(true);
  };

  return (
    <button
      onClick={toggle}
      className="mt-1 p-1.5 rounded-full hover:bg-[#d4915e]/20 transition-colors"
      title={playing ? "Arrêter" : "Écouter"}
    >
      {playing ? (
        <svg viewBox="0 0 24 24" fill="#d4915e" className="w-4 h-4">
          <path d="M6 6h4v12H6zm8 0h4v12h-4z" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="#d4915e" className="w-4 h-4">
          <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" />
        </svg>
      )}
    </button>
  );
}

const TOOL_LABELS: Record<string, string> = {
  search_records: "Recherche Odoo",
  create_record: "Création Odoo",
  update_record: "Mise à jour Odoo",
  get_record: "Lecture Odoo",
  delete_record: "Suppression Odoo",
  search_product_docs: "Recherche docs",
  search_common_issues: "Pannes connues",
  set_mode: "Changement mode",
  list_models: "Modèles Odoo",
  get_fields: "Champs Odoo",
};

function dedupeTools(tools: string[]): string[] {
  const seen = new Map<string, number>();
  for (const t of tools) {
    seen.set(t, (seen.get(t) ?? 0) + 1);
  }
  return [...seen.entries()].map(([name, count]) =>
    count > 1 ? `${name}×${count}` : name
  );
}

export default function MessageBubble({ role, content, imageUrl, audioUrl, toolsUsed }: MessageBubbleProps) {
  const isUser = role === "user";
  const time = formatTime();

  const { text: displayText, url: historyImageUrl } = extractImage(content);
  const resolvedImage = imageUrl || historyImageUrl;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div className="max-w-[80%]">
        {/* Image */}
        {resolvedImage && (
          <div className="mb-1">
            <img
              src={resolvedImage}
              alt="Photo"
              className="rounded-2xl max-h-60 object-cover shadow-sm"
            />
          </div>
        )}

        {/* Text bubble */}
        {displayText && (
          <div
            className={`px-4 py-2.5 text-[15px] leading-relaxed whitespace-pre-wrap ${
              isUser
                ? "bg-[#c45d3e] text-white rounded-2xl rounded-br-sm"
                : "bg-[#f5efe8] text-[#3d3833] rounded-2xl rounded-bl-sm border-l-3 border-[#d4915e]"
            }`}
          >
            {displayText}
          </div>
        )}

        {/* Tool badges */}
        {!isUser && toolsUsed && toolsUsed.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1.5 px-1">
            {dedupeTools(toolsUsed).map((tool, i) => {
              const baseName = tool.replace(/×\d+$/, "");
              const label = TOOL_LABELS[baseName] ?? baseName;
              const suffix = tool.includes("×") ? ` ${tool.slice(tool.indexOf("×"))}` : "";
              return (
                <span
                  key={i}
                  className="text-[9px] font-medium px-1.5 py-0.5 rounded-full bg-[#f0ece7] text-[#8a837b]"
                >
                  {label}{suffix}
                </span>
              );
            })}
          </div>
        )}

        {/* Audio button */}
        {!isUser && audioUrl && <PlayButton audioUrl={audioUrl} />}

        {/* Timestamp */}
        <div className={`text-[10px] mt-1.5 px-1 font-medium tracking-wide ${
          isUser ? "text-gray-400 text-right" : "text-[#d4915e]"
        }`}>
          {isUser ? `VOUS · ${time}` : `HODOOR · ${time}`}
        </div>
      </div>
    </div>
  );
}
