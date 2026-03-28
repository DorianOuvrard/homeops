export default function LoadingDots() {
  return (
    <div className="flex justify-start mb-2">
      <div className="bg-white shadow-sm px-4 py-3 rounded-2xl rounded-bl-sm">
        <div className="flex gap-1 items-center">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
