import { describe, it, expect, vi } from 'vitest';
import {
  MODEL_NAME,
  getAiClient,
  HOME_TOOLS,
  MAIL_TOOLS,
  AUTOMATOR_TOOLS,
  SYSTEM_INSTRUCTION
} from '../lib/gemini';

// ========== MODEL CONFIGURATION TESTS ==========

describe('MODEL_NAME', () => {
  it('is set to riftrunner', () => {
    expect(MODEL_NAME).toBe('riftrunner');
  });

  it('is a non-empty string', () => {
    expect(typeof MODEL_NAME).toBe('string');
    expect(MODEL_NAME.length).toBeGreaterThan(0);
  });
});

// ========== AI CLIENT TESTS ==========

describe('getAiClient', () => {
  it('returns a function', () => {
    expect(typeof getAiClient).toBe('function');
  });

  it('creates a new client instance', () => {
    // Skip if no API key is set (CI/test environment)
    if (!process.env.API_KEY) {
      console.log('Skipping: API_KEY not set');
      return;
    }
    const client = getAiClient();
    expect(client).toBeDefined();
  });
});

// ========== HOME TOOLS TESTS ==========

describe('HOME_TOOLS', () => {
  it('is an array of tools', () => {
    expect(Array.isArray(HOME_TOOLS)).toBe(true);
    expect(HOME_TOOLS.length).toBeGreaterThan(0);
  });

  it('contains function declarations', () => {
    expect(HOME_TOOLS[0].functionDeclarations).toBeDefined();
    expect(Array.isArray(HOME_TOOLS[0].functionDeclarations)).toBe(true);
  });

  describe('delete_item function', () => {
    const deleteItem = HOME_TOOLS[0].functionDeclarations?.find(
      f => f.name === 'delete_item'
    );

    it('exists', () => {
      expect(deleteItem).toBeDefined();
    });

    it('has required itemName parameter', () => {
      expect(deleteItem?.parameters?.required).toContain('itemName');
    });

    it('has description', () => {
      expect(deleteItem?.description).toBeDefined();
      expect(deleteItem?.description?.length).toBeGreaterThan(0);
    });

    it('itemName is a string type', () => {
      expect(deleteItem?.parameters?.properties?.itemName?.type).toBe('STRING');
    });
  });

  describe('explode_folder function', () => {
    const explodeFolder = HOME_TOOLS[0].functionDeclarations?.find(
      f => f.name === 'explode_folder'
    );

    it('exists', () => {
      expect(explodeFolder).toBeDefined();
    });

    it('has required folderName parameter', () => {
      expect(explodeFolder?.parameters?.required).toContain('folderName');
    });

    it('has description about outward arrows', () => {
      expect(explodeFolder?.description).toContain('arrows');
    });
  });

  describe('explain_item function', () => {
    const explainItem = HOME_TOOLS[0].functionDeclarations?.find(
      f => f.name === 'explain_item'
    );

    it('exists', () => {
      expect(explainItem).toBeDefined();
    });

    it('has required itemName parameter', () => {
      expect(explainItem?.parameters?.required).toContain('itemName');
    });

    it('mentions question mark in description', () => {
      expect(explainItem?.description).toContain('?');
    });
  });

  describe('change_background function', () => {
    const changeBg = HOME_TOOLS[0].functionDeclarations?.find(
      f => f.name === 'change_background'
    );

    it('exists', () => {
      expect(changeBg).toBeDefined();
    });

    it('has sketch_description parameter', () => {
      expect(changeBg?.parameters?.properties?.sketch_description).toBeDefined();
    });

    it('describes wallpaper generation', () => {
      expect(changeBg?.description).toContain('wallpaper');
    });
  });
});

// ========== MAIL TOOLS TESTS ==========

describe('MAIL_TOOLS', () => {
  it('is an array of tools', () => {
    expect(Array.isArray(MAIL_TOOLS)).toBe(true);
    expect(MAIL_TOOLS.length).toBeGreaterThan(0);
  });

  it('contains function declarations', () => {
    expect(MAIL_TOOLS[0].functionDeclarations).toBeDefined();
  });

  describe('delete_email function', () => {
    const deleteEmail = MAIL_TOOLS[0].functionDeclarations?.find(
      f => f.name === 'delete_email'
    );

    it('exists', () => {
      expect(deleteEmail).toBeDefined();
    });

    it('has required subject_text parameter', () => {
      expect(deleteEmail?.parameters?.required).toContain('subject_text');
    });

    it('has optional sender_text parameter', () => {
      expect(deleteEmail?.parameters?.properties?.sender_text).toBeDefined();
    });

    it('describes strike-out gesture', () => {
      expect(deleteEmail?.description).toMatch(/line|strike|X/i);
    });
  });

  describe('summarize_email function', () => {
    const summarizeEmail = MAIL_TOOLS[0].functionDeclarations?.find(
      f => f.name === 'summarize_email'
    );

    it('exists', () => {
      expect(summarizeEmail).toBeDefined();
    });

    it('has required subject_text parameter', () => {
      expect(summarizeEmail?.parameters?.required).toContain('subject_text');
    });

    it('mentions multiple calls for multiple emails', () => {
      expect(summarizeEmail?.description).toContain('MULTIPLE');
    });
  });
});

// ========== AUTOMATOR TOOLS TESTS ==========

describe('AUTOMATOR_TOOLS', () => {
  it('is an array of tools', () => {
    expect(Array.isArray(AUTOMATOR_TOOLS)).toBe(true);
    expect(AUTOMATOR_TOOLS.length).toBeGreaterThan(0);
  });

  describe('analyze_automation_context function', () => {
    const analyzeContext = AUTOMATOR_TOOLS[0].functionDeclarations?.find(
      f => f.name === 'analyze_automation_context'
    );

    it('exists', () => {
      expect(analyzeContext).toBeDefined();
    });

    it('has required focus_area parameter', () => {
      expect(analyzeContext?.parameters?.required).toContain('focus_area');
    });

    it('mentions Jira/Zapier/Kindle', () => {
      expect(analyzeContext?.description).toContain('Jira');
      expect(analyzeContext?.description).toContain('Zapier');
      expect(analyzeContext?.description).toContain('Kindle');
    });
  });

  describe('link_integrations function', () => {
    const linkIntegrations = AUTOMATOR_TOOLS[0].functionDeclarations?.find(
      f => f.name === 'link_integrations'
    );

    it('exists', () => {
      expect(linkIntegrations).toBeDefined();
    });

    it('has required source_node and target_node parameters', () => {
      expect(linkIntegrations?.parameters?.required).toContain('source_node');
      expect(linkIntegrations?.parameters?.required).toContain('target_node');
    });

    it('describes connecting nodes', () => {
      expect(linkIntegrations?.description).toContain('connect');
    });
  });
});

// ========== SYSTEM INSTRUCTION TESTS ==========

describe('SYSTEM_INSTRUCTION', () => {
  it('is a non-empty string', () => {
    expect(typeof SYSTEM_INSTRUCTION).toBe('string');
    expect(SYSTEM_INSTRUCTION.length).toBeGreaterThan(0);
  });

  it('mentions Gemini Ink assistant name', () => {
    expect(SYSTEM_INSTRUCTION).toContain('Gemini Ink');
  });

  it('mentions ink strokes interaction', () => {
    expect(SYSTEM_INSTRUCTION).toContain('ink');
    expect(SYSTEM_INSTRUCTION).toContain('strokes');
  });

  it('describes AUTOMATOR app context', () => {
    expect(SYSTEM_INSTRUCTION).toContain('AUTOMATOR');
  });

  it('mentions Aethermore Games project', () => {
    expect(SYSTEM_INSTRUCTION).toContain('Aethermore Games');
  });

  it('describes professional behavior', () => {
    expect(SYSTEM_INSTRUCTION).toContain('professional');
  });
});

// ========== TOOL SCHEMA VALIDATION TESTS ==========

describe('Tool Schema Validation', () => {
  const allTools = [...HOME_TOOLS, ...MAIL_TOOLS, ...AUTOMATOR_TOOLS];

  it('all tools have valid structure', () => {
    allTools.forEach(tool => {
      expect(tool.functionDeclarations).toBeDefined();
      expect(Array.isArray(tool.functionDeclarations)).toBe(true);
    });
  });

  it('all function declarations have name and description', () => {
    allTools.forEach(tool => {
      tool.functionDeclarations?.forEach(fn => {
        expect(fn.name).toBeDefined();
        expect(typeof fn.name).toBe('string');
        expect(fn.description).toBeDefined();
        expect(typeof fn.description).toBe('string');
      });
    });
  });

  it('all function declarations have valid parameter schemas', () => {
    allTools.forEach(tool => {
      tool.functionDeclarations?.forEach(fn => {
        if (fn.parameters) {
          expect(fn.parameters.type).toBe('OBJECT');
          expect(fn.parameters.properties).toBeDefined();
        }
      });
    });
  });

  it('required parameters exist in properties', () => {
    allTools.forEach(tool => {
      tool.functionDeclarations?.forEach(fn => {
        if (fn.parameters?.required) {
          fn.parameters.required.forEach((reqParam: string) => {
            expect(fn.parameters?.properties?.[reqParam]).toBeDefined();
          });
        }
      });
    });
  });
});

// ========== FUNCTION COUNT TESTS ==========

describe('Function Counts', () => {
  it('HOME_TOOLS has 4 functions', () => {
    expect(HOME_TOOLS[0].functionDeclarations?.length).toBe(4);
  });

  it('MAIL_TOOLS has 2 functions', () => {
    expect(MAIL_TOOLS[0].functionDeclarations?.length).toBe(2);
  });

  it('AUTOMATOR_TOOLS has 2 functions', () => {
    expect(AUTOMATOR_TOOLS[0].functionDeclarations?.length).toBe(2);
  });
});
