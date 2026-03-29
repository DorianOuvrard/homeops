import { useRef, useState } from "react";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  imageUrl?: string;
  audioUrl?: string;
}

function formatTime(): string {
  const now = new Date();
  return `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
}

function extractImage(content: string): { text: string; url: string | null } {
  const match = content.match(/^\[image:(\/api\/v1\/uploads\/[^\]]+)\]\s*/);
  if (match) {
    return { text: content.slice(match[0].length).trim(), url: match[1] };
  }
  const photoMatch = content.match(/^\[photo\]\s*/i);
  if (photoMatch) {
    return { text: content.slice(photoMatch[0].length).trim(), url: null };
  }
  return { text: content, url: null };
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
      className="mt-1 p-1.5 rounded-full hover:bg-[#f57c00]/20 transition-colors"
      title={playing ? "Arrêter" : "Écouter"}
    >
      {playing ? (
        <svg viewBox="0 0 24 24" fill="#f57c00" className="w-4 h-4">
          <path d="M6 6h4v12H6zm8 0h4v12h-4z" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="#f57c00" className="w-4 h-4">
          <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" />
        </svg>
      )}
    </button>
  );
}

export default function MessageBubble({ role, content, imageUrl, audioUrl }: MessageBubbleProps) {
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
                ? "bg-[#1a237e] text-white rounded-2xl rounded-br-sm"
                : "bg-[#fef0e4] text-gray-800 rounded-2xl rounded-bl-sm border-l-3 border-[#f57c00]"
            }`}
          >
            {displayText}
          </div>
        )}

        {/* Audio button */}
        {!isUser && audioUrl && <PlayButton audioUrl={audioUrl} />}

        {/* Timestamp */}
        <div className={`text-[10px] mt-1.5 px-1 font-medium tracking-wide ${
          isUser ? "text-gray-400 text-right" : "text-[#f57c00]"
        }`}>
          {isUser ? `VOUS · ${time}` : `HODOOR · ${time}`}
        </div>
      </div>
    </div>
  );
}
