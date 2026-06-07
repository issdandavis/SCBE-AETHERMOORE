export interface AbacusRow {
  id: string;
  label: string;
  value: number;
  count: number;
  maxCount: number;
}

export interface AbacusLayer {
  id: string;
  name: string;
  rows: AbacusRow[];
}

export interface LayeredAbacusState {
  activeLayerId: string;
  layers: AbacusLayer[];
}

export interface AbacusRowTotal extends AbacusRow {
  total: number;
}

export interface AbacusLayerTotal {
  id: string;
  name: string;
  rows: AbacusRowTotal[];
  total: number;
}

export interface AbacusTotals {
  layers: AbacusLayerTotal[];
  total: number;
}

export interface SetAbacusRowInput {
  count?: number;
  label?: string;
  layerId?: string;
  rowId: string;
  value?: number;
}

export interface AddAbacusLayerInput {
  layerId?: string;
  name?: string;
  rows?: Partial<AbacusRow>[];
}

export function createDefaultAbacusState(): LayeredAbacusState {
  return {
    activeLayerId: 'decimal',
    layers: [
      {
        id: 'decimal',
        name: 'Decimal Place Chunks',
        rows: [
          createRow('ones', 'ones', 1, 0),
          createRow('tens', 'tens', 10, 0),
          createRow('hundreds', 'hundreds', 100, 0),
          createRow('thousands', 'thousands', 1000, 0),
        ],
      },
      {
        id: 'fractional',
        name: 'Fractional Chunks',
        rows: [
          createRow('tenths', 'tenths', 0.1, 0),
          createRow('hundredths', 'hundredths', 0.01, 0),
          createRow('thousandths', 'thousandths', 0.001, 0),
        ],
      },
      {
        id: 'prime',
        name: 'Prime Basis Chunks',
        rows: [
          createRow('p2', 'prime 2', 2, 0),
          createRow('p3', 'prime 3', 3, 0),
          createRow('p5', 'prime 5', 5, 0),
          createRow('p7', 'prime 7', 7, 0),
          createRow('p11', 'prime 11', 11, 0),
          createRow('p13', 'prime 13', 13, 0),
        ],
      },
      {
        id: 'agent',
        name: 'Agent Work Tokens',
        rows: [
          createRow('observe', 'observe', 1, 0),
          createRow('plan', 'plan', 5, 0),
          createRow('act', 'act', 25, 0),
          createRow('verify', 'verify', 125, 0),
        ],
      },
    ],
  };
}

export function normalizeAbacusState(value?: Partial<LayeredAbacusState>): LayeredAbacusState {
  const fallback = createDefaultAbacusState();
  if (!value?.layers?.length) {
    return fallback;
  }

  const layers = value.layers.map((layer, layerIndex) => ({
    id: safeId(layer.id, `layer-${layerIndex + 1}`),
    name: layer.name?.trim() || `Layer ${layerIndex + 1}`,
    rows: (layer.rows?.length ? layer.rows : fallback.layers[0].rows).map((row, rowIndex) =>
      createRow(
        safeId(row.id, `row-${rowIndex + 1}`),
        row.label?.trim() || `row ${rowIndex + 1}`,
        finiteOr(row.value, 1),
        finiteOr(row.count, 0),
        finiteOr(row.maxCount, 12)
      )
    ),
  }));

  const activeLayerId = layers.some((layer) => layer.id === value.activeLayerId)
    ? (value.activeLayerId ?? layers[0].id)
    : layers[0].id;

  return { activeLayerId, layers };
}

export function calculateAbacusTotals(state: LayeredAbacusState): AbacusTotals {
  const layers = state.layers.map((layer) => {
    const rows = layer.rows.map((row) => ({
      ...row,
      total: round(row.value * row.count),
    }));
    return {
      id: layer.id,
      name: layer.name,
      rows,
      total: round(rows.reduce((sum, row) => sum + row.total, 0)),
    };
  });

  return {
    layers,
    total: round(layers.reduce((sum, layer) => sum + layer.total, 0)),
  };
}

export function setAbacusRow(
  state: LayeredAbacusState,
  input: SetAbacusRowInput
): LayeredAbacusState {
  const layerId = input.layerId ?? state.activeLayerId;
  let found = false;
  const layers = state.layers.map((layer) => {
    if (layer.id !== layerId) return layer;
    return {
      ...layer,
      rows: layer.rows.map((row) => {
        if (row.id !== input.rowId) return row;
        found = true;
        return {
          ...row,
          label: input.label?.trim() || row.label,
          value: input.value === undefined ? row.value : finiteOr(input.value, row.value),
          count: input.count === undefined ? row.count : clampCount(input.count, row.maxCount),
        };
      }),
    };
  });

  if (!found) {
    throw new Error(`Unknown abacus row: ${input.rowId}`);
  }

  return { ...state, activeLayerId: layerId, layers };
}

export function addAbacusLayer(
  state: LayeredAbacusState,
  input: AddAbacusLayerInput = {}
): LayeredAbacusState {
  const id = safeId(input.layerId, `layer-${state.layers.length + 1}`);
  if (state.layers.some((layer) => layer.id === id)) {
    throw new Error(`Duplicate abacus layer: ${id}`);
  }

  const rows = input.rows?.map((row, index) =>
    createRow(
      safeId(row.id, `row-${index + 1}`),
      row.label?.trim() || `row ${index + 1}`,
      finiteOr(row.value, 1),
      finiteOr(row.count, 0),
      finiteOr(row.maxCount, 12)
    )
  ) ?? [createRow('unit', 'unit', 1, 0), createRow('bundle', 'bundle', 10, 0)];

  const layer = {
    id,
    name: input.name?.trim() || `Layer ${state.layers.length + 1}`,
    rows,
  };

  return {
    activeLayerId: id,
    layers: [...state.layers, layer],
  };
}

export function resetAbacus(): LayeredAbacusState {
  return createDefaultAbacusState();
}

function createRow(
  id: string,
  label: string,
  value: number,
  count: number,
  maxCount = 12
): AbacusRow {
  const safeMax = Math.max(1, Math.floor(finiteOr(maxCount, 12)));
  return {
    id,
    label,
    value: finiteOr(value, 1),
    count: clampCount(count, safeMax),
    maxCount: safeMax,
  };
}

function clampCount(value: number, maxCount: number): number {
  return Math.max(0, Math.min(maxCount, Math.floor(finiteOr(value, 0))));
}

function finiteOr(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function round(value: number): number {
  return Number(value.toFixed(6));
}

function safeId(value: unknown, fallback: string): string {
  if (typeof value !== 'string') return fallback;
  return (
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9_-]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 48) || fallback
  );
}
