import { useEffect, useMemo, useState } from "react";
import { Loader2, Play, RefreshCw } from "lucide-react";
import { classifierPredictionUrl, classifierProbabilityUrl } from "../lib/api";
import { useClassifier, useMislabels } from "../hooks/useAef";
import type {
  AefTile,
  ClassifierKind,
  LabelSource,
} from "../types/aef";
import { ConfusionMatrix } from "../components/ConfusionMatrix";
import { MetricsCard } from "../components/MetricsCard";
import { MislabelList } from "../components/MislabelList";
import { PcaPreviewImage } from "../components/PcaPreviewImage";

const LABEL_SOURCES: LabelSource[] = ["gladl", "glads2", "radd"];

interface TileYearKey {
  key: string;
  tile: string;
  year: number;
  split: string;
}

function flattenTiles(tiles: AefTile[]): TileYearKey[] {
  const out: TileYearKey[] = [];
  for (const t of tiles) {
    for (const y of t.years) {
      out.push({ key: `${t.tileId}:${y}:${t.split}`, tile: t.tileId, year: y, split: t.split });
    }
  }
  return out;
}

export function ClassifierPage({
  trainTiles,
  testTiles,
}: {
  trainTiles: AefTile[];
  testTiles: AefTile[];
}) {
  const trainKeys = useMemo(() => flattenTiles(trainTiles.filter((t) => t.hasLabels)), [trainTiles]);
  const testKeys = useMemo(
    () => [...trainKeys, ...flattenTiles(testTiles)],
    [trainKeys, testTiles],
  );
  const [model, setModel] = useState<ClassifierKind>("mlp");
  const [labelSource, setLabelSource] = useState<LabelSource>("gladl");
  const [trainSel, setTrainSel] = useState<string[]>([]);
  const [valSel, setValSel] = useState<string | null>(null);
  const [testSel, setTestSel] = useState<string | null>(null);
  const [sample, setSample] = useState(3000);
  const [overlay, setOverlay] = useState<"prediction" | "probability">("prediction");
  const [topMislabels, setTopMislabels] = useState(15);
  const [refreshSeed, setRefreshSeed] = useState(0);

  const classifier = useClassifier();
  const mislabels = useMislabels(classifier.data?.modelId ?? null, topMislabels);

  useEffect(() => {
    if (trainKeys.length && trainSel.length === 0) {
      setTrainSel(trainKeys.slice(0, Math.min(2, trainKeys.length - 1)).map((k) => k.key));
    }
    if (trainKeys.length && !valSel) {
      setValSel(trainKeys[Math.min(2, trainKeys.length - 1)].key);
    }
    if (testKeys.length && !testSel) {
      const candidate =
        testKeys.find(
          (k) => k.split === "test" || (k.split === "train" && !trainSel.includes(k.key) && k.key !== valSel),
        ) ?? testKeys[testKeys.length - 1];
      setTestSel(candidate.key);
    }
  }, [trainKeys, testKeys, trainSel, valSel, testSel]);

  const toggleTrain = (key: string) =>
    setTrainSel((cur) =>
      cur.includes(key) ? cur.filter((k) => k !== key) : [...cur, key],
    );

  const handleRun = async () => {
    if (!testSel || trainSel.length === 0) return;
    await classifier.run({
      model,
      train_tiles: trainSel,
      val_tile: valSel,
      test_tile: testSel,
      label_source: labelSource,
      sample_per_tile: sample,
      refresh: false,
    });
  };

  const overlayUrl = classifier.data
    ? overlay === "prediction"
      ? `${classifierPredictionUrl(classifier.data.modelId)}?v=${refreshSeed}`
      : `${classifierProbabilityUrl(classifier.data.modelId)}?v=${refreshSeed}`
    : null;

  return (
    <div className="space-y-4">
      <section className="panel p-4">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <p className="label-upper">Estimator</p>
            <div className="mt-1 inline-flex rounded-md border border-slate-800 bg-obsidian-950 p-0.5 text-xs">
              {(["svm", "mlp"] as ClassifierKind[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setModel(m)}
                  className={`rounded px-3 py-1 ${
                    model === m ? "bg-sky-600/30 text-sky-200" : "text-slate-400"
                  }`}
                >
                  {m.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
          <div>
            <p className="label-upper">Label source</p>
            <select
              value={labelSource}
              onChange={(e) => setLabelSource(e.target.value as LabelSource)}
              className="input mt-1 w-32 py-1 font-mono text-xs"
            >
              {LABEL_SOURCES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <p className="label-upper">Pixels / tile</p>
            <input
              type="number"
              min={500}
              max={20000}
              step={500}
              value={sample}
              onChange={(e) => setSample(Number(e.target.value))}
              className="input mt-1 w-28 py-1 font-mono text-xs"
            />
          </div>
          <button
            type="button"
            className="btn-primary text-xs"
            onClick={handleRun}
            disabled={
              classifier.loading || trainSel.length === 0 || !testSel
            }
          >
            {classifier.loading ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Training
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5" /> Train &amp; evaluate
              </>
            )}
          </button>
          {classifier.data && (
            <button
              type="button"
              className="btn text-xs"
              onClick={() => {
                setRefreshSeed((s) => s + 1);
                mislabels.reload();
              }}
            >
              <RefreshCw className="h-3.5 w-3.5" /> Refresh overlay
            </button>
          )}
        </div>
        <p className="mt-3 text-[11px] text-slate-500">
          Pick training tiles, an optional validation tile, and a test tile.
          The classifier is trained synchronously (a few seconds) and cached
          on the backend by request hash, so re-runs are instant.
        </p>
        <div className="mt-3 grid gap-3 lg:grid-cols-3">
          <TileSelector
            label="Training (multi-select)"
            options={trainKeys}
            selected={new Set(trainSel)}
            onToggle={toggleTrain}
            multi
          />
          <TileSelector
            label="Validation (optional)"
            options={trainKeys}
            selected={new Set(valSel ? [valSel] : [])}
            onToggle={(key) => setValSel(valSel === key ? null : key)}
          />
          <TileSelector
            label="Test"
            options={testKeys}
            selected={new Set(testSel ? [testSel] : [])}
            onToggle={(key) => setTestSel(key)}
          />
        </div>
      </section>

      {classifier.error && (
        <div className="panel border-rose-900/60 bg-rose-950/20 p-4 text-sm text-rose-200">
          {classifier.error}
        </div>
      )}

      {classifier.data && (
        <>
          <section className="grid gap-4 xl:grid-cols-2">
            <MetricsCard
              title="Validation metrics"
              metrics={classifier.data.valMetrics}
            />
            <MetricsCard title="Test metrics" metrics={classifier.data.testMetrics} />
          </section>

          <section className="grid gap-4 xl:grid-cols-[1fr_360px]">
            <div className="panel">
              <div className="panel-header">
                <p className="label-upper">Test tile overlay</p>
                <div className="inline-flex rounded-md border border-slate-800 bg-obsidian-950 p-0.5 text-[11px]">
                  <button
                    type="button"
                    onClick={() => setOverlay("prediction")}
                    className={`rounded px-2 py-1 ${
                      overlay === "prediction"
                        ? "bg-sky-600/30 text-sky-200"
                        : "text-slate-400"
                    }`}
                  >
                    Prediction
                  </button>
                  <button
                    type="button"
                    onClick={() => setOverlay("probability")}
                    className={`rounded px-2 py-1 ${
                      overlay === "probability"
                        ? "bg-sky-600/30 text-sky-200"
                        : "text-slate-400"
                    }`}
                  >
                    Probability
                  </button>
                </div>
              </div>
              {overlayUrl ? (
                <div className="p-3">
                  <PcaPreviewImage
                    src={overlayUrl}
                    alt="prediction"
                    className="aspect-square max-h-[60vh]"
                  />
                  <p className="mt-2 text-[11px] text-slate-500">
                    Crimson = predicted deforestation, navy = stable. The
                    probability mode shows a confidence ramp.
                  </p>
                </div>
              ) : null}
            </div>
            <ConfusionMatrix metrics={classifier.data.testMetrics} />
          </section>

          <section className="space-y-2">
            <div className="flex items-center gap-2 text-xs">
              <p className="label-upper">Top mislabels</p>
              <input
                type="number"
                min={5}
                max={50}
                value={topMislabels}
                onChange={(e) => setTopMislabels(Number(e.target.value))}
                className="input w-20 py-1 font-mono text-xs"
              />
            </div>
            <MislabelList
              regions={mislabels.data?.regions ?? []}
              loading={mislabels.loading}
              error={mislabels.error}
            />
          </section>
        </>
      )}
    </div>
  );
}

function TileSelector({
  label,
  options,
  selected,
  onToggle,
  multi,
}: {
  label: string;
  options: TileYearKey[];
  selected: Set<string>;
  onToggle: (key: string) => void;
  multi?: boolean;
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-obsidian-950/60 p-3">
      <p className="label-upper">{label}</p>
      <div className="mt-2 flex max-h-40 flex-wrap gap-1.5 overflow-y-auto">
        {options.map((o) => {
          const active = selected.has(o.key);
          return (
            <button
              key={o.key}
              type="button"
              onClick={() => onToggle(o.key)}
              className={`rounded-md border px-2 py-1 font-mono text-[11px] ${
                active
                  ? "border-sky-500 bg-sky-600/20 text-sky-200"
                  : "border-slate-700 bg-obsidian-900 text-slate-400 hover:bg-obsidian-800"
              }`}
              title={o.split}
            >
              {o.tile}:{o.year}
              <span className="ml-1 text-[9px] uppercase text-slate-500">
                {o.split}
              </span>
            </button>
          );
        })}
        {options.length === 0 && (
          <p className="text-xs text-slate-500">No tiles available.</p>
        )}
      </div>
      {!multi && (
        <p className="mt-1 text-[10px] text-slate-500">single select</p>
      )}
    </div>
  );
}
