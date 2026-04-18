import { useEffect, useState } from "react";
import { ImageOff, Loader2 } from "lucide-react";

export function PcaPreviewImage({
  src,
  alt,
  className,
}: {
  src: string;
  alt: string;
  className?: string;
}) {
  const [state, setState] = useState<"loading" | "ok" | "error">("loading");
  useEffect(() => {
    setState("loading");
  }, [src]);
  return (
    <div
      className={`relative overflow-hidden rounded-xl border border-slate-800 bg-obsidian-950 ${
        className ?? ""
      }`}
    >
      <img
        src={src}
        alt={alt}
        className="block h-full w-full object-contain"
        onLoad={() => setState("ok")}
        onError={() => setState("error")}
      />
      {state === "loading" && (
        <div className="absolute inset-0 grid place-items-center bg-obsidian-950/80 text-slate-500">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      )}
      {state === "error" && (
        <div className="absolute inset-0 grid place-items-center bg-obsidian-950/90 text-rose-300">
          <div className="flex flex-col items-center gap-1 text-xs">
            <ImageOff className="h-5 w-5" />
            failed to load image
          </div>
        </div>
      )}
    </div>
  );
}
