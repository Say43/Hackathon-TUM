import { ArrowRight, Boxes, Globe2, Layers, Sparkles } from "lucide-react";
import type { AefTile, HealthResponse, NavKey } from "../types/aef";

export function OverviewPage({
  health,
  tiles,
  testTiles,
  onNavigate,
}: {
  health: HealthResponse | null;
  tiles: AefTile[];
  testTiles: AefTile[];
  onNavigate: (k: NavKey) => void;
}) {
  const totalYears = tiles.reduce((sum, t) => sum + t.years.length, 0);
  const totalTestYears = testTiles.reduce((sum, t) => sum + t.years.length, 0);
  const labelledTiles = tiles.filter((t) => t.hasLabels).length;

  return (
    <div className="space-y-6">
      <section className="panel p-6">
        <div className="flex flex-wrap items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-violet-600 to-sky-700 text-white">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">
              AlphaEarth Foundations Explorer
            </h2>
            <p className="text-sm text-slate-400">
              A workshop-style sandbox over Google's AEF embeddings, adapted to
              Makeathon 2026's deforestation labels.
            </p>
          </div>
        </div>
        <p className="mt-4 max-w-3xl text-sm leading-relaxed text-slate-400">
          AEF compresses years of multi-modal Earth observation into a 64-dim
          embedding per pixel. This dashboard lets you visualise those
          embeddings (PCA false-colour, channel composites), project them into
          2D (PCA, UMAP), and train SVM / MLP classifiers on top of the weak{" "}
          <span className="text-slate-200">gladl / glads2 / radd</span>{" "}
          deforestation labels — all without touching a Jupyter cell.
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <Stat icon={Globe2} label="Train tiles" value={tiles.length} />
          <Stat icon={Boxes} label="Tiles with labels" value={labelledTiles} />
          <Stat icon={Layers} label="Train tile-years" value={totalYears} />
          <Stat icon={Sparkles} label="Test tile-years" value={totalTestYears} />
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Card
          title="Embedding Map"
          description="See a tile-year as a PCA-3 false-colour image. The PCA captures most variance in the first 3 components, so anomalies pop visually."
          onOpen={() => onNavigate("embedding-map")}
        />
        <Card
          title="Channel Explorer"
          description="Pick any 3 of 64 AEF bands and view them as an RGB composite, or scroll one band as grayscale. See per-channel min/max/mean."
          onOpen={() => onNavigate("channels")}
        />
        <Card
          title="Low-dim Analysis"
          description="Sample labelled pixels across tiles, project to PCA-2D and UMAP-2D, and see how forested vs. deforested clusters look."
          onOpen={() => onNavigate("scatter")}
        />
        <Card
          title="Classifier Lab"
          description="Train an SVM or MLP on AEF pixels with a tile/year split, evaluate on a held-out tile, and surface high-confidence disagreements with the weak labels."
          onOpen={() => onNavigate("classifier")}
        />
      </section>

      <section className="panel p-4 text-xs text-slate-500">
        <p>
          Backend cache:{" "}
          <span className="font-mono text-slate-300">
            {health?.cacheDir || "unknown"}
          </span>
          {" — "}
          first PCA preview / UMAP scatter / classifier run takes a few seconds
          to compute, then it streams from disk on every refresh. Hit{" "}
          <span className="font-mono text-slate-300">/api/debug/paths</span> on
          the backend to inspect path resolution.
        </p>
      </section>
    </div>
  );
}

function Stat({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Globe2;
  label: string;
  value: number;
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-obsidian-950/60 px-4 py-3">
      <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <p className="mt-1 font-mono text-xl font-semibold text-white">{value}</p>
    </div>
  );
}

function Card({
  title,
  description,
  onOpen,
}: {
  title: string;
  description: string;
  onOpen: () => void;
}) {
  return (
    <article className="panel flex h-full flex-col p-5">
      <h3 className="text-base font-semibold text-white">{title}</h3>
      <p className="mt-2 flex-1 text-sm text-slate-400">{description}</p>
      <button type="button" className="btn-primary mt-4 self-start text-xs" onClick={onOpen}>
        Open <ArrowRight className="h-3.5 w-3.5" />
      </button>
    </article>
  );
}
