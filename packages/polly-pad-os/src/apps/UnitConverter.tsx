import React, { useState, useMemo } from 'react';
import { ArrowRightLeft, Copy, Check } from 'lucide-react';

const CATEGORIES: Record<string, { name: string; units: Record<string, number> }> = {
  Length: {
    name: 'Length',
    units: {
      Meters: 1,
      Kilometers: 1000,
      Centimeters: 0.01,
      Millimeters: 0.001,
      Micrometers: 1e-6,
      Nanometers: 1e-9,
      Miles: 1609.344,
      Yards: 0.9144,
      Feet: 0.3048,
      Inches: 0.0254,
      Nautical_Miles: 1852,
    },
  },
  Weight: {
    name: 'Weight',
    units: {
      Kilograms: 1,
      Grams: 0.001,
      Milligrams: 1e-6,
      Micrograms: 1e-9,
      Pounds: 0.45359237,
      Ounces: 0.0283495,
      Stones: 6.35029,
      Tons: 1000,
    },
  },
  Temperature: {
    name: 'Temperature',
    units: { Celsius: 1, Fahrenheit: 1, Kelvin: 1 },
  },
  Volume: {
    name: 'Volume',
    units: {
      Liters: 1,
      Milliliters: 0.001,
      Gallons_US: 3.78541,
      Gallons_UK: 4.54609,
      Quarts: 0.946353,
      Pints: 0.473176,
      Cups: 0.236588,
      Fluid_Ounces: 0.0295735,
      Cubic_Meters: 1000,
    },
  },
  Speed: {
    name: 'Speed',
    units: {
      'm/s': 1,
      'km/h': 0.277778,
      mph: 0.44704,
      Knots: 0.514444,
      'ft/s': 0.3048,
      Mach: 340.3,
    },
  },
  Data: {
    name: 'Data Size',
    units: {
      Bytes: 1,
      KB: 1024,
      MB: 1048576,
      GB: 1073741824,
      TB: 1099511627776,
      PB: 1125899906842624,
    },
  },
  Area: {
    name: 'Area',
    units: {
      sq_meters: 1,
      sq_kilometers: 1e6,
      sq_feet: 0.092903,
      sq_miles: 2.59e6,
      Acres: 4046.86,
      Hectares: 10000,
    },
  },
  Pressure: {
    name: 'Pressure',
    units: { Pascal: 1, kPa: 1000, bar: 100000, psi: 6894.76, atm: 101325, mmHg: 133.322 },
  },
  Energy: {
    name: 'Energy',
    units: {
      Joule: 1,
      kJ: 1000,
      calorie: 4.184,
      kcal: 4184,
      Wh: 3600,
      kWh: 3600000,
      eV: 1.602e-19,
    },
  },
  Time: {
    name: 'Time',
    units: {
      Seconds: 1,
      Minutes: 60,
      Hours: 3600,
      Days: 86400,
      Weeks: 604800,
      Months: 2.628e6,
      Years: 3.154e7,
    },
  },
};

function convertTemperature(value: number, from: string, to: string): number {
  let c = value;
  if (from === 'Fahrenheit') c = ((value - 32) * 5) / 9;
  if (from === 'Kelvin') c = value - 273.15;
  if (to === 'Celsius') return c;
  if (to === 'Fahrenheit') return (c * 9) / 5 + 32;
  if (to === 'Kelvin') return c + 273.15;
  return c;
}

export default function UnitConverter() {
  const [category, setCategory] = useState('Length');
  const [fromUnit, setFromUnit] = useState('Meters');
  const [toUnit, setToUnit] = useState('Kilometers');
  const [value, setValue] = useState(1);
  const [copied, setCopied] = useState(false);

  const units = CATEGORIES[category].units;
  const unitNames = Object.keys(units);

  const result = useMemo(() => {
    if (category === 'Temperature') return convertTemperature(value, fromUnit, toUnit);
    const fromFactor = units[fromUnit];
    const toFactor = units[toUnit];
    return (value * fromFactor) / toFactor;
  }, [value, fromUnit, toUnit, category, units]);

  const swap = () => {
    const tmp = fromUnit;
    setFromUnit(toUnit);
    setToUnit(tmp);
  };

  const copy = () => {
    navigator.clipboard.writeText(
      `${value} ${fromUnit} = ${result.toLocaleString(undefined, { maximumFractionDigits: 10 })} ${toUnit}`
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const formatNumber = (n: number): string => {
    if (Math.abs(n) < 0.000001 || Math.abs(n) > 1e12) return n.toExponential(6);
    return n.toLocaleString(undefined, { maximumFractionDigits: 10 });
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4 overflow-y-auto">
      <h2 className="text-lg text-blue-200 font-semibold mb-4">Unit Converter</h2>

      <select
        value={category}
        onChange={(e) => {
          setCategory(e.target.value);
          const u = Object.keys(CATEGORIES[e.target.value].units);
          setFromUnit(u[0]);
          setToUnit(u[1] || u[0]);
        }}
        className="w-full bg-[#162032] border border-blue-500/15 rounded-xl px-3 py-2 text-sm outline-none mb-4 focus:border-blue-500/30"
      >
        {Object.entries(CATEGORIES).map(([key, val]) => (
          <option key={key} value={key}>
            {val.name}
          </option>
        ))}
      </select>

      <div className="space-y-3">
        {/* From */}
        <div>
          <label className="text-xs text-blue-300/30 mb-1 block">From</label>
          <div className="flex gap-2">
            <input
              type="number"
              value={value}
              onChange={(e) => setValue(Number(e.target.value))}
              className="flex-1 bg-[#162032] border border-blue-500/15 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/30 font-mono"
            />
            <select
              value={fromUnit}
              onChange={(e) => setFromUnit(e.target.value)}
              className="bg-[#162032] border border-blue-500/15 rounded-lg px-2 py-2 text-xs outline-none focus:border-blue-500/30 w-28"
            >
              {unitNames.map((u) => (
                <option key={u} value={u}>
                  {u.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Swap */}
        <div className="flex items-center justify-center">
          <button
            onClick={swap}
            className="p-1.5 rounded-lg hover:bg-blue-500/15 text-blue-400 transition-colors"
          >
            <ArrowRightLeft size={14} />
          </button>
        </div>

        {/* To */}
        <div>
          <label className="text-xs text-blue-300/30 mb-1 block">To</label>
          <div className="flex gap-2">
            <div className="flex-1 bg-[#162032] border border-blue-500/15 rounded-lg px-3 py-2 text-sm text-blue-200 font-mono flex items-center">
              {formatNumber(result)}
            </div>
            <select
              value={toUnit}
              onChange={(e) => setToUnit(e.target.value)}
              className="bg-[#162032] border border-blue-500/15 rounded-lg px-2 py-2 text-xs outline-none focus:border-blue-500/30 w-28"
            >
              {unitNames.map((u) => (
                <option key={u} value={u}>
                  {u.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <button
        onClick={copy}
        className="mt-4 w-full py-2 rounded-xl bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 text-xs transition-colors flex items-center justify-center gap-1.5"
      >
        {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
        {copied ? 'Copied!' : 'Copy Result'}
      </button>

      {/* Quick reference */}
      <div className="mt-4">
        <div className="text-[10px] uppercase tracking-wider text-blue-400/30 mb-2">
          Quick Reference (1 {fromUnit})
        </div>
        <div className="space-y-0.5 max-h-40 overflow-y-auto">
          {unitNames
            .filter((u) => u !== fromUnit)
            .slice(0, 8)
            .map((u) => (
              <div
                key={u}
                className="flex justify-between text-[10px] px-2 py-1 rounded bg-[#162032]"
              >
                <span className="text-blue-300/30">{u.replace(/_/g, ' ')}</span>
                <span className="text-blue-200/50 font-mono">
                  {category === 'Temperature'
                    ? formatNumber(convertTemperature(1, fromUnit, u))
                    : formatNumber((1 * units[fromUnit]) / units[u])}
                </span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
