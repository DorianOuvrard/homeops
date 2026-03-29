function speakHodor() {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) {
    return;
  }

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance("Hodor");
  utterance.lang = "en-US";
  utterance.rate = 0.9;
  utterance.pitch = 0.8;
  window.speechSynthesis.speak(utterance);
}

export default function Header() {
  return (
    <div className="bg-white border-b border-[#f0ece7] px-4 py-3 flex items-center justify-center shrink-0">
      <button
        type="button"
        onClick={speakHodor}
        className="flex items-center gap-2 text-[#c45d3e] font-bold text-lg tracking-wide"
        title="Ecouter Hodor"
      >
        <img src="/hodoor-logo.png" alt="Hodoor" className="h-8 object-contain" />
      </button>
    </div>
  );
}
