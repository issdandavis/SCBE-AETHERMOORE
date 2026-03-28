export interface LanguageInfo {
  name: string;
  extension: string;
  color: string;
  icon: string;
  prismLanguage: string;
  executionCommand?: string;
  template: string;
}

export const LANGUAGE_MAP: { [key: string]: LanguageInfo } = {
  // JavaScript / TypeScript
  '.js': {
    name: 'JavaScript',
    extension: '.js',
    color: '#f7df1e',
    icon: 'JS',
    prismLanguage: 'javascript',
    executionCommand: 'node',
    template: '// JavaScript file\nconsole.log("Hello from JavaScript!");'
  },
  '.jsx': {
    name: 'React JSX',
    extension: '.jsx',
    color: '#61dafb',
    icon: 'JSX',
    prismLanguage: 'jsx',
    template: 'import React from "react";\n\nfunction Component() {\n  return <div>Hello React!</div>;\n}\n\nexport default Component;'
  },
  '.ts': {
    name: 'TypeScript',
    extension: '.ts',
    color: '#3178c6',
    icon: 'TS',
    prismLanguage: 'typescript',
    executionCommand: 'ts-node',
    template: '// TypeScript file\nconst greeting: string = "Hello from TypeScript!";\nconsole.log(greeting);'
  },
  '.tsx': {
    name: 'React TSX',
    extension: '.tsx',
    color: '#3178c6',
    icon: 'TSX',
    prismLanguage: 'tsx',
    template: 'import React from "react";\n\ninterface Props {\n  message: string;\n}\n\nconst Component: React.FC<Props> = ({ message }) => {\n  return <div>{message}</div>;\n};\n\nexport default Component;'
  },
  
  // Python
  '.py': {
    name: 'Python',
    extension: '.py',
    color: '#3776ab',
    icon: 'PY',
    prismLanguage: 'python',
    executionCommand: 'python',
    template: '# Python file\nprint("Hello from Python!")'
  },
  
  // Web
  '.html': {
    name: 'HTML',
    extension: '.html',
    color: '#e34c26',
    icon: 'HTML',
    prismLanguage: 'html',
    template: '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <title>Document</title>\n</head>\n<body>\n  <h1>Hello World!</h1>\n</body>\n</html>'
  },
  '.css': {
    name: 'CSS',
    extension: '.css',
    color: '#264de4',
    icon: 'CSS',
    prismLanguage: 'css',
    template: '/* CSS Stylesheet */\nbody {\n  margin: 0;\n  padding: 0;\n  font-family: sans-serif;\n}'
  },
  '.scss': {
    name: 'SCSS',
    extension: '.scss',
    color: '#c6538c',
    icon: 'SCSS',
    prismLanguage: 'scss',
    template: '// SCSS file\n$primary-color: #3498db;\n\nbody {\n  color: $primary-color;\n}'
  },
  
  // Java
  '.java': {
    name: 'Java',
    extension: '.java',
    color: '#b07219',
    icon: 'JAVA',
    prismLanguage: 'java',
    executionCommand: 'javac',
    template: 'public class Main {\n  public static void main(String[] args) {\n    System.out.println("Hello from Java!");\n  }\n}'
  },
  
  // C/C++
  '.c': {
    name: 'C',
    extension: '.c',
    color: '#555555',
    icon: 'C',
    prismLanguage: 'c',
    executionCommand: 'gcc',
    template: '#include <stdio.h>\n\nint main() {\n  printf("Hello from C!\\n");\n  return 0;\n}'
  },
  '.cpp': {
    name: 'C++',
    extension: '.cpp',
    color: '#f34b7d',
    icon: 'C++',
    prismLanguage: 'cpp',
    executionCommand: 'g++',
    template: '#include <iostream>\n\nint main() {\n  std::cout << "Hello from C++!" << std::endl;\n  return 0;\n}'
  },
  '.h': {
    name: 'C Header',
    extension: '.h',
    color: '#555555',
    icon: 'H',
    prismLanguage: 'c',
    template: '#ifndef HEADER_H\n#define HEADER_H\n\n// Header file\n\n#endif'
  },
  
  // C#
  '.cs': {
    name: 'C#',
    extension: '.cs',
    color: '#178600',
    icon: 'C#',
    prismLanguage: 'csharp',
    executionCommand: 'csc',
    template: 'using System;\n\nclass Program {\n  static void Main() {\n    Console.WriteLine("Hello from C#!");\n  }\n}'
  },
  
  // Ruby
  '.rb': {
    name: 'Ruby',
    extension: '.rb',
    color: '#cc342d',
    icon: 'RB',
    prismLanguage: 'ruby',
    executionCommand: 'ruby',
    template: '# Ruby file\nputs "Hello from Ruby!"'
  },
  
  // PHP
  '.php': {
    name: 'PHP',
    extension: '.php',
    color: '#4F5D95',
    icon: 'PHP',
    prismLanguage: 'php',
    executionCommand: 'php',
    template: '<?php\n// PHP file\necho "Hello from PHP!";\n?>'
  },
  
  // Go
  '.go': {
    name: 'Go',
    extension: '.go',
    color: '#00ADD8',
    icon: 'GO',
    prismLanguage: 'go',
    executionCommand: 'go run',
    template: 'package main\n\nimport "fmt"\n\nfunc main() {\n  fmt.Println("Hello from Go!")\n}'
  },
  
  // Rust
  '.rs': {
    name: 'Rust',
    extension: '.rs',
    color: '#dea584',
    icon: 'RS',
    prismLanguage: 'rust',
    executionCommand: 'rustc',
    template: 'fn main() {\n  println!("Hello from Rust!");\n}'
  },
  
  // Swift
  '.swift': {
    name: 'Swift',
    extension: '.swift',
    color: '#ffac45',
    icon: 'SWIFT',
    prismLanguage: 'swift',
    executionCommand: 'swift',
    template: '// Swift file\nprint("Hello from Swift!")'
  },
  
  // Kotlin
  '.kt': {
    name: 'Kotlin',
    extension: '.kt',
    color: '#A97BFF',
    icon: 'KT',
    prismLanguage: 'kotlin',
    executionCommand: 'kotlinc',
    template: 'fun main() {\n  println("Hello from Kotlin!")\n}'
  },
  
  // R
  '.r': {
    name: 'R',
    extension: '.r',
    color: '#198CE7',
    icon: 'R',
    prismLanguage: 'r',
    executionCommand: 'Rscript',
    template: '# R file\nprint("Hello from R!")'
  },
  
  // SQL
  '.sql': {
    name: 'SQL',
    extension: '.sql',
    color: '#e38c00',
    icon: 'SQL',
    prismLanguage: 'sql',
    template: '-- SQL file\nSELECT * FROM users WHERE active = true;'
  },
  
  // Shell
  '.sh': {
    name: 'Shell',
    extension: '.sh',
    color: '#89e051',
    icon: 'SH',
    prismLanguage: 'bash',
    executionCommand: 'bash',
    template: '#!/bin/bash\n# Shell script\necho "Hello from Bash!"'
  },
  '.bash': {
    name: 'Bash',
    extension: '.bash',
    color: '#89e051',
    icon: 'BASH',
    prismLanguage: 'bash',
    template: '#!/bin/bash\necho "Hello from Bash!"'
  },
  
  // Data formats
  '.json': {
    name: 'JSON',
    extension: '.json',
    color: '#292929',
    icon: 'JSON',
    prismLanguage: 'json',
    template: '{\n  "name": "example",\n  "version": "1.0.0"\n}'
  },
  '.yaml': {
    name: 'YAML',
    extension: '.yaml',
    color: '#cb171e',
    icon: 'YAML',
    prismLanguage: 'yaml',
    template: '# YAML file\nname: example\nversion: 1.0.0'
  },
  '.yml': {
    name: 'YAML',
    extension: '.yml',
    color: '#cb171e',
    icon: 'YML',
    prismLanguage: 'yaml',
    template: '# YAML file\nname: example\nversion: 1.0.0'
  },
  '.xml': {
    name: 'XML',
    extension: '.xml',
    color: '#0060ac',
    icon: 'XML',
    prismLanguage: 'xml',
    template: '<?xml version="1.0" encoding="UTF-8"?>\n<root>\n  <item>Example</item>\n</root>'
  },
  '.toml': {
    name: 'TOML',
    extension: '.toml',
    color: '#9c4221',
    icon: 'TOML',
    prismLanguage: 'toml',
    template: '# TOML file\n[package]\nname = "example"\nversion = "1.0.0"'
  },
  
  // Markdown
  '.md': {
    name: 'Markdown',
    extension: '.md',
    color: '#083fa1',
    icon: 'MD',
    prismLanguage: 'markdown',
    template: '# Markdown Document\n\nHello **World**!'
  },
  
  // Other languages
  '.lua': {
    name: 'Lua',
    extension: '.lua',
    color: '#000080',
    icon: 'LUA',
    prismLanguage: 'lua',
    executionCommand: 'lua',
    template: '-- Lua file\nprint("Hello from Lua!")'
  },
  '.perl': {
    name: 'Perl',
    extension: '.perl',
    color: '#0298c3',
    icon: 'PERL',
    prismLanguage: 'perl',
    executionCommand: 'perl',
    template: '#!/usr/bin/perl\n# Perl file\nprint "Hello from Perl!\\n";'
  },
  '.scala': {
    name: 'Scala',
    extension: '.scala',
    color: '#c22d40',
    icon: 'SCALA',
    prismLanguage: 'scala',
    executionCommand: 'scala',
    template: 'object Main {\n  def main(args: Array[String]): Unit = {\n    println("Hello from Scala!")\n  }\n}'
  },
  '.dart': {
    name: 'Dart',
    extension: '.dart',
    color: '#00B4AB',
    icon: 'DART',
    prismLanguage: 'dart',
    executionCommand: 'dart',
    template: 'void main() {\n  print("Hello from Dart!");\n}'
  },
  '.vim': {
    name: 'Vimscript',
    extension: '.vim',
    color: '#199f4b',
    icon: 'VIM',
    prismLanguage: 'vim',
    template: '" Vim script\necho "Hello from Vim!"'
  },
  '.dockerfile': {
    name: 'Dockerfile',
    extension: '.dockerfile',
    color: '#384d54',
    icon: 'DOCKER',
    prismLanguage: 'docker',
    template: 'FROM node:18-alpine\nWORKDIR /app\nCOPY . .\nRUN npm install\nCMD ["npm", "start"]'
  },
  '.graphql': {
    name: 'GraphQL',
    extension: '.graphql',
    color: '#e10098',
    icon: 'GQL',
    prismLanguage: 'graphql',
    template: 'type Query {\n  hello: String\n}'
  },
  '.prisma': {
    name: 'Prisma',
    extension: '.prisma',
    color: '#2D3748',
    icon: 'PRISMA',
    prismLanguage: 'prisma',
    template: 'model User {\n  id    Int    @id @default(autoincrement())\n  email String @unique\n  name  String?\n}'
  },
};

export function detectLanguage(filename: string): LanguageInfo {
  const ext = '.' + filename.split('.').pop()?.toLowerCase();
  
  // Special cases
  if (filename.toLowerCase() === 'dockerfile') {
    return LANGUAGE_MAP['.dockerfile'];
  }
  
  return LANGUAGE_MAP[ext] || {
    name: 'Plain Text',
    extension: '.txt',
    color: '#666666',
    icon: 'TXT',
    prismLanguage: 'plaintext',
    template: '// New file'
  };
}

export function getAllLanguages(): LanguageInfo[] {
  return Object.values(LANGUAGE_MAP);
}

export function getLanguagesByCategory() {
  return {
    'Web Development': ['.html', '.css', '.scss', '.js', '.jsx', '.ts', '.tsx'],
    'Backend': ['.py', '.java', '.php', '.rb', '.go', '.rs', '.cs'],
    'Systems': ['.c', '.cpp', '.h', '.rs', '.go'],
    'Mobile': ['.swift', '.kt', '.dart', '.java'],
    'Data & Config': ['.json', '.yaml', '.yml', '.xml', '.toml', '.sql'],
    'Scripting': ['.sh', '.bash', '.lua', '.perl', '.r', '.py'],
    'Other': ['.md', '.vim', '.dockerfile', '.graphql', '.prisma', '.scala']
  };
}
