import { useRef } from "react";

interface PhotoUploadProps {
  onPhoto: (file: File) => void;
  disabled?: boolean;
}

function CameraIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
      <path d="M12 15.2A3.2 3.2 0 1 0 12 8.8a3.2 3.2 0 0 0 0 6.4z" />
      <path d="M9 3L7.17 5H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2h-3.17L15 3H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z" />
    </svg>
  );
}

function GalleryIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
      <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z" />
    </svg>
  );
}

export default function PhotoUpload({ onPhoto, disabled }: PhotoUploadProps) {
  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onPhoto(file);
      e.target.value = "";
    }
  };

  return (
    <>
      {/* Camera input (opens rear camera on mobile) */}
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleChange}
        disabled={disabled}
      />
      {/* Gallery input (no capture, opens file picker) */}
      <input
        ref={galleryRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleChange}
        disabled={disabled}
      />
      <button
        type="button"
        onClick={() => cameraRef.current?.click()}
        disabled={disabled}
        className="p-2 text-gray-400 hover:text-[#d4915e] disabled:opacity-40 transition-colors"
        title="Prendre une photo"
      >
        <CameraIcon />
      </button>
      <button
        type="button"
        onClick={() => galleryRef.current?.click()}
        disabled={disabled}
        className="p-2 text-gray-400 hover:text-[#d4915e] disabled:opacity-40 transition-colors"
        title="Choisir depuis la galerie"
      >
        <GalleryIcon />
      </button>
    </>
  );
}
