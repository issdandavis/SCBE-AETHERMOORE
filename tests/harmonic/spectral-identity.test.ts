/**
 * Spectral Identity System Tests
 * 
 * Tests for the Rainbow Chromatic Fingerprinting system that maps
 * multi-dimensional trust vectors to unique color signatures.
 * 
 * @module tests/harmonic/spectral-identity
 */

import { beforeEach, describe, expect, it } from 'vitest';
import {
    SPECTRAL_BANDS,
    SpectralIdentityGenerator,
    TONGUE_COLORS,
    spectralGenerator
} from '../../src/harmonic/spectral-identity.js';

describe('SpectralIdentityGenerator', () => {
  let generator: SpectralIdentityGenerator;

  beforeEach(() => {
    generator = new SpectralIdentityGenerator();
  });

  describe('generateIdentity', () => {
    it('should generate valid spectral identity from 6D trust vector', () => {
      const trustVector = [0.8, 0.6, 0.7, 0.5, 0.9, 0.4];
      const identity = generator.generateIdentity('test-entity-1', trustVector);

      expect(identity).toBeDefined();
      expect(identity.entityId).toBe('test-entity-1');
      expect(identity.spectrum).toHaveLength(7);
      expect(identity.tongueSignature).toHaveLength(6);
      expect(identity.hexCode).toMatch(/^#[0-9A-F]{6}$/);
      expect(identity.spectralHash).toMatch(/^SP-[0-9A-F]{4}-[0-9A-F]{4}$/);
      expect(['HIGH', 'MEDIUM', 'LOW']).toContain(identity.confidence);
    });

    it('should throw error for invalid trust vector length', () => {
      expect(() => generator.generateIdentity('test', [0.5, 0.5])).toThrow(
        'Trust vector must have 6 dimensions'
      );
    });

    it('should clamp trust vector values to [0, 1]', () => {
      const trustVector = [1.5, -0.2, 0.5, 0.5, 0.5, 0.5];
      const identity = generator.generateIdentity('test', trustVector);

      // Should not throw, values should be clamped
      expect(identity.spectrum.every(v => v >= 0 && v <= 1)).toBe(true);
    });

    it('should generate unique identities for different trust vectors', () => {
      const identity1 = generator.generateIdentity('entity-1', [0.9, 0.1, 0.5, 0.5, 0.5, 0.5]);
      const identity2 = generator.generateIdentity('entity-2', [0.1, 0.9, 0.5, 0.5, 0.5, 0.5]);

      expect(identity1.spectralHash).not.toBe(identity2.spectralHash);
      expect(identity1.hexCode).not.toBe(identity2.hexCode);
    });

    it('should generate consistent identity for same inputs', () => {
      const trustVector = [0.7, 0.3, 0.8, 0.2, 0.6, 0.4];
      const identity1 = generator.generateIdentity('same-entity', trustVector);
      const identity2 = generator.generateIdentity('same-entity', trustVector);

      expect(identity1.spectralHash).toBe(identity2.spectralHash);
      expect(identity1.hexCode).toBe(identity2.hexCode);
    });

    it('should incorporate layer scores when provided', () => {
      const trustVector = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5];
      const layerScores = Array(14).fill(0.8);

      const withLayers = generator.generateIdentity('test', trustVector, layerScores);
      const withoutLayers = generator.generateIdentity('test', trustVector);

      // Spectrums should differ when layer scores are provided
      expect(withLayers.spectrum).not.toEqual(withoutLayers.spectrum);
    });
  });

  describe('spectrum generation', () => {
    it('should map Sacred Tongues to spectral bands', () => {
      // High KO (Koraelin) should boost Red band
      const highKO = generator.generateIdentity('ko-test', [1.0, 0.1, 0.1, 0.1, 0.1, 0.1]);
      expect(highKO.spectrum[0]).toBeGreaterThan(highKO.spectrum[1]);

      // High AV (Avali) should boost Orange band
      const highAV = generator.generateIdentity('av-test', [0.1, 1.0, 0.1, 0.1, 0.1, 0.1]);
      expect(highAV.spectrum[1]).toBeGreaterThan(highAV.spectrum[0]);
    });

    it('should have 7 bands (ROYGBIV)', () => {
      expect(SPECTRAL_BANDS).toHaveLength(7);
      expect(SPECTRAL_BANDS.map(b => b.name)).toEqual([
        'Red', 'Orange', 'Yellow', 'Green', 'Blue', 'Indigo', 'Violet'
      ]);
    });
  });

  describe('tongue signature', () => {
    it('should generate 6 tongue colors', () => {
      const identity = generator.generateIdentity('test', [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]);
      expect(identity.tongueSignature).toHaveLength(6);
    });

    it('should modulate base colors by trust intensity', () => {
      const lowTrust = generator.generateIdentity('low', [0.1, 0.1, 0.1, 0.1, 0.1, 0.1]);
      const highTrust = generator.generateIdentity('high', [0.9, 0.9, 0.9, 0.9, 0.9, 0.9]);

      // High trust should have brighter colors
      const lowBrightness = lowTrust.tongueSignature.reduce(
        (sum, c) => sum + c.r + c.g + c.b, 0
      );
      const highBrightness = highTrust.tongueSignature.reduce(
        (sum, c) => sum + c.r + c.g + c.b, 0
      );

      expect(highBrightness).toBeGreaterThan(lowBrightness);
    });
  });

  describe('confidence levels', () => {
    it('should return HIGH confidence for high variance vectors', () => {
      // High variance = very different values
      const identity = generator.generateIdentity('test', [1.0, 0.0, 1.0, 0.0, 1.0, 0.0]);
      expect(identity.confidence).toBe('HIGH');
    });

    it('should return LOW confidence for uniform vectors', () => {
      // Low variance = all same values
      const identity = generator.generateIdentity('test', [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]);
      expect(identity.confidence).toBe('LOW');
    });
  });

  describe('compareIdentities', () => {
    it('should return 1.0 for identical identities', () => {
      const trustVector = [0.7, 0.3, 0.8, 0.2, 0.6, 0.4];
      const identity1 = generator.generateIdentity('entity-1', trustVector);
      const identity2 = generator.generateIdentity('entity-2', trustVector);

      const similarity = generator.compareIdentities(identity1, identity2);
      expect(similarity).toBeCloseTo(1.0, 2);
    });

    it('should return low similarity for very different identities', () => {
      const identity1 = generator.generateIdentity('entity-1', [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]);
      const identity2 = generator.generateIdentity('entity-2', [0.0, 0.0, 0.0, 0.0, 0.0, 1.0]);

      const similarity = generator.compareIdentities(identity1, identity2);
      expect(similarity).toBeLessThan(0.9); // Different identities should have < 90% similarity
    });

    it('should return moderate similarity for partially similar identities', () => {
      const identity1 = generator.generateIdentity('entity-1', [0.8, 0.6, 0.4, 0.2, 0.3, 0.5]);
      const identity2 = generator.generateIdentity('entity-2', [0.7, 0.5, 0.5, 0.3, 0.4, 0.4]);

      const similarity = generator.compareIdentities(identity1, identity2);
      expect(similarity).toBeGreaterThan(0.7);
      expect(similarity).toBeLessThan(1.0);
    });
  });

  describe('generateVisual', () => {
    it('should generate ASCII visual representation', () => {
      const identity = generator.generateIdentity('visual-test', [0.8, 0.6, 0.7, 0.5, 0.9, 0.4]);
      const visual = generator.generateVisual(identity);

      expect(visual).toContain('SPECTRAL IDENTITY');
      expect(visual).toContain('visual-test');
      expect(visual).toContain('Red');
      expect(visual).toContain('Violet');
      expect(visual).toContain('%');
    });

    it('should show spectrum bars', () => {
      const identity = generator.generateIdentity('test', [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]);
      const visual = generator.generateVisual(identity);

      // Should contain bar characters
      expect(visual).toContain('█');
      expect(visual).toContain('░');
    });
  });

  describe('TONGUE_COLORS', () => {
    it('should have all 6 Sacred Tongue colors defined', () => {
      expect(Object.keys(TONGUE_COLORS)).toHaveLength(6);
      expect(TONGUE_COLORS).toHaveProperty('KO');
      expect(TONGUE_COLORS).toHaveProperty('AV');
      expect(TONGUE_COLORS).toHaveProperty('RU');
      expect(TONGUE_COLORS).toHaveProperty('CA');
      expect(TONGUE_COLORS).toHaveProperty('UM');
      expect(TONGUE_COLORS).toHaveProperty('DR');
    });

    it('should have valid RGB values', () => {
      for (const [tongue, color] of Object.entries(TONGUE_COLORS)) {
        expect(color.r).toBeGreaterThanOrEqual(0);
        expect(color.r).toBeLessThanOrEqual(255);
        expect(color.g).toBeGreaterThanOrEqual(0);
        expect(color.g).toBeLessThanOrEqual(255);
        expect(color.b).toBeGreaterThanOrEqual(0);
        expect(color.b).toBeLessThanOrEqual(255);
      }
    });
  });

  describe('singleton instance', () => {
    it('should export a singleton spectralGenerator', () => {
      expect(spectralGenerator).toBeInstanceOf(SpectralIdentityGenerator);
    });

    it('should work the same as new instance', () => {
      const trustVector = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5];
      const fromSingleton = spectralGenerator.generateIdentity('test', trustVector);
      const fromNew = generator.generateIdentity('test', trustVector);

      expect(fromSingleton.spectralHash).toBe(fromNew.spectralHash);
    });
  });

  describe('color name generation', () => {
    it('should generate descriptive color names', () => {
      const identity = generator.generateIdentity('test', [0.9, 0.1, 0.1, 0.1, 0.1, 0.1]);
      expect(identity.colorName).toBeTruthy();
      expect(typeof identity.colorName).toBe('string');
    });

    it('should include band name in color name', () => {
      // High red should have "Red" in name
      const redIdentity = generator.generateIdentity('red', [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]);
      expect(redIdentity.colorName.toLowerCase()).toContain('red');
    });
  });
});

describe('SPECTRAL_BANDS', () => {
  it('should map to SCBE 14 layers', () => {
    const allLayers = SPECTRAL_BANDS.flatMap(b => b.layers);
    const uniqueLayers = [...new Set(allLayers)].sort((a, b) => a - b);

    // Should cover layers 1-14
    expect(uniqueLayers).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]);
  });

  it('should have wavelength ranges in visible spectrum', () => {
    for (const band of SPECTRAL_BANDS) {
      expect(band.wavelengthMin).toBeGreaterThanOrEqual(380);
      expect(band.wavelengthMax).toBeLessThanOrEqual(750);
      expect(band.wavelengthMin).toBeLessThan(band.wavelengthMax);
    }
  });

  it('should have hue ranges for color mapping', () => {
    for (const band of SPECTRAL_BANDS) {
      expect(band.hueMin).toBeGreaterThanOrEqual(0);
      expect(band.hueMax).toBeLessThanOrEqual(360);
    }
  });
});
