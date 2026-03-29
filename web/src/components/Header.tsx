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
    <div className="bg-[#1a237e] px-4 py-3 flex items-center justify-center shrink-0">
      <button
        type="button"
        onClick={speakHodor}
        className="text-white font-bold text-lg tracking-wide"
        title="Ecouter Hodor"
      >
        HODOOR
      </button>
    </div>
  );
}
