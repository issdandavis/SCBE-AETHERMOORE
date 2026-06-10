import { useMemo, useState } from 'react';
import { Layers, Plus, RotateCcw, Sigma } from 'lucide-react';
import {
  addAbacusLayer,
  calculateAbacusTotals,
  normalizeAbacusState,
  resetAbacus,
  setAbacusRow,
  type AbacusLayer,
  type LayeredAbacusState,
} from '@/lib/layeredAbacus';

interface LayeredAbacusProps {
  data?: {
    abacus?: Partial<LayeredAbacusState>;
  };
}

const layerAccent = [
  'from-cyan-400 to-sky-500',
  'from-amber-300 to-orange-500',
  'from-emerald-300 to-teal-500',
  'from-fuchsia-300 to-rose-500',
  'from-lime-300 to-green-500',
];

export default function LayeredAbacus({ data }: LayeredAbacusProps) {
  const [state, setState] = useState(() => normalizeAbacusState(data?.abacus));
  const totals = useMemo(() => calculateAbacusTotals(state), [state]);
  const activeLayer =
    state.layers.find((layer) => layer.id === state.activeLayerId) ?? state.layers[0];
  const activeTotal = totals.layers.find((layer) => layer.id === activeLayer.id);

  const updateRow = (rowId: string, patch: { count?: number; label?: string; value?: number }) => {
    setState((current) => setAbacusRow(current, { layerId: activeLayer.id, rowId, ...patch }));
  };

  const addLayer = () => {
    setState((current) =>
      addAbacusLayer(current, {
        name: `Layer ${current.layers.length + 1}`,
        rows: [
          { id: 'unit', label: 'unit', value: 1, count: 0 },
          { id: 'bundle', label: 'bundle', value: 10, count: 0 },
          { id: 'gross', label: 'gross', value: 100, count: 0 },
        ],
      })
    );
  };

  return (
    <div className="h-full min-h-0 bg-[#07111d] text-slate-100 overflow-hidden">
      <div className="h-full grid grid-cols-[220px_minmax(0,1fr)_240px]">
        <aside className="border-r border-white/10 bg-[#0a1724] p-3 flex flex-col gap-3 min-h-0">
          <div className="rounded-lg border border-cyan-300/20 bg-cyan-300/5 px-3 py-2">
            <div className="flex items-center gap-2 text-cyan-100 text-sm font-semibold">
              <Layers size={15} />
              Layered Abacus
            </div>
            <div className="mt-2 text-3xl font-semibold tabular-nums tracking-tight">
              {formatNumber(totals.total)}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={addLayer}
              className="flex-1 h-8 rounded-md bg-cyan-400/15 text-cyan-100 text-xs font-medium hover:bg-cyan-400/25 transition-colors inline-flex items-center justify-center gap-1.5"
            >
              <Plus size={13} />
              Layer
            </button>
            <button
              onClick={() => setState(resetAbacus())}
              className="h-8 w-8 rounded-md bg-white/5 text-slate-300 hover:bg-white/10 transition-colors inline-flex items-center justify-center"
              title="Reset"
            >
              <RotateCcw size={13} />
            </button>
          </div>

          <div className="flex-1 min-h-0 overflow-auto pr-1 space-y-2">
            {state.layers.map((layer, index) => {
              const layerTotal = totals.layers.find((entry) => entry.id === layer.id)?.total ?? 0;
              const active = layer.id === activeLayer.id;
              return (
                <button
                  key={layer.id}
                  onClick={() => setState((current) => ({ ...current, activeLayerId: layer.id }))}
                  className={`w-full text-left rounded-lg border px-3 py-2 transition-all ${
                    active
                      ? 'border-cyan-300/40 bg-cyan-300/10 shadow-[0_0_24px_rgba(34,211,238,0.08)]'
                      : 'border-white/8 bg-white/[0.03] hover:bg-white/[0.06]'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <div
                      className={`h-2.5 w-2.5 rounded-full bg-gradient-to-br ${layerAccent[index % layerAccent.length]}`}
                    />
                    <div className="min-w-0 flex-1 truncate text-xs font-semibold text-slate-100">
                      {layer.name}
                    </div>
                  </div>
                  <div className="mt-1 text-lg tabular-nums text-slate-200">
                    {formatNumber(layerTotal)}
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        <main className="min-h-0 overflow-auto p-4 bg-[radial-gradient(circle_at_20%_20%,rgba(34,211,238,0.08),transparent_30%),linear-gradient(180deg,#091522,#07111d)]">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <div className="text-[11px] uppercase tracking-[0.22em] text-cyan-200/55">
                active layer
              </div>
              <h2 className="text-2xl font-semibold tracking-tight">{activeLayer.name}</h2>
            </div>
            <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-right">
              <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">
                layer total
              </div>
              <div className="text-xl tabular-nums text-cyan-100">
                {formatNumber(activeTotal?.total ?? 0)}
              </div>
            </div>
          </div>

          <div className="space-y-3">
            {activeLayer.rows.map((row, rowIndex) => (
              <AbacusRowView
                key={row.id}
                layer={activeLayer}
                rowIndex={rowIndex}
                row={row}
                total={activeTotal?.rows.find((entry) => entry.id === row.id)?.total ?? 0}
                updateRow={updateRow}
              />
            ))}
          </div>
        </main>

        <aside className="border-l border-white/10 bg-[#08131f] p-3 min-h-0 flex flex-col">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-100">
            <Sigma size={15} />
            Chunk Ledger
          </div>
          <div className="mt-3 flex-1 min-h-0 overflow-auto space-y-3 pr-1">
            {totals.layers.map((layer) => (
              <div key={layer.id} className="rounded-lg border border-white/8 bg-white/[0.03] p-2">
                <div className="flex justify-between gap-2 text-xs font-semibold">
                  <span className="truncate text-slate-200">{layer.name}</span>
                  <span className="tabular-nums text-cyan-100">{formatNumber(layer.total)}</span>
                </div>
                <div className="mt-2 space-y-1">
                  {layer.rows
                    .filter((row) => row.count > 0 || row.total !== 0)
                    .map((row) => (
                      <div
                        key={row.id}
                        className="grid grid-cols-[1fr_auto] gap-2 text-[11px] text-slate-400"
                      >
                        <span className="truncate">
                          {row.count} x {row.label}
                        </span>
                        <span className="tabular-nums text-slate-200">
                          {formatNumber(row.total)}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}

interface AbacusRowViewProps {
  layer: AbacusLayer;
  row: AbacusLayer['rows'][number];
  rowIndex: number;
  total: number;
  updateRow: (rowId: string, patch: { count?: number; label?: string; value?: number }) => void;
}

function AbacusRowView({ row, rowIndex, total, updateRow }: AbacusRowViewProps) {
  const accent = layerAccent[rowIndex % layerAccent.length];
  return (
    <section className="rounded-xl border border-white/10 bg-[#0b1a29]/85 p-3 shadow-[0_18px_40px_rgba(0,0,0,0.18)]">
      <div className="grid grid-cols-[minmax(120px,1fr)_96px_96px_96px] gap-3 items-center">
        <input
          value={row.label}
          onChange={(event) => updateRow(row.id, { label: event.target.value })}
          className="h-9 rounded-md bg-black/20 border border-white/10 px-3 text-sm text-slate-100 outline-none focus:border-cyan-300/50"
          aria-label={`${row.id} label`}
        />
        <label className="grid gap-1">
          <span className="text-[10px] uppercase tracking-[0.16em] text-slate-500">value</span>
          <input
            type="number"
            step="any"
            value={row.value}
            onChange={(event) => updateRow(row.id, { value: Number(event.target.value) })}
            className="h-8 rounded-md bg-black/20 border border-white/10 px-2 text-xs tabular-nums text-slate-100 outline-none focus:border-cyan-300/50"
          />
        </label>
        <label className="grid gap-1">
          <span className="text-[10px] uppercase tracking-[0.16em] text-slate-500">count</span>
          <input
            type="number"
            min={0}
            max={row.maxCount}
            value={row.count}
            onChange={(event) => updateRow(row.id, { count: Number(event.target.value) })}
            className="h-8 rounded-md bg-black/20 border border-white/10 px-2 text-xs tabular-nums text-slate-100 outline-none focus:border-cyan-300/50"
          />
        </label>
        <div className="text-right">
          <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">total</div>
          <div className="text-lg tabular-nums text-cyan-100">{formatNumber(total)}</div>
        </div>
      </div>

      <div className="mt-3 rounded-lg bg-black/20 border border-white/8 px-3 py-2">
        <div className="flex items-center gap-1.5 overflow-hidden">
          {Array.from({ length: row.maxCount }).map((_, index) => {
            const active = index < row.count;
            return (
              <button
                key={index}
                onClick={() =>
                  updateRow(row.id, {
                    count: active && index === row.count - 1 ? index : index + 1,
                  })
                }
                className={`h-7 flex-1 min-w-4 rounded-full border transition-all ${
                  active
                    ? `border-white/20 bg-gradient-to-br ${accent} shadow-[0_0_14px_rgba(34,211,238,0.18)]`
                    : 'border-white/10 bg-white/[0.04] hover:bg-white/[0.08]'
                }`}
                title={`${row.label} count ${index + 1}`}
              />
            );
          })}
        </div>
      </div>
    </section>
  );
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 6,
  }).format(value);
}
