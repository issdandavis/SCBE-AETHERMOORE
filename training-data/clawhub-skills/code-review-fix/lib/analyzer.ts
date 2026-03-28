interface AnalysisOptions {
  security?: boolean;
  style?: boolean;
  performance?: boolean;
  explain?: boolean;
}

interface CodeIssue {
  severity: 'Critical' | 'High' | 'Medium' | 'Low';
  line: number;
  type: 'bug' | 'security' | 'performance' | 'style';
  description: string;
  fixSuggestion?: string;
  explanation?: string;
}

interface AnalysisResult {
  report: string;
  issues: CodeIssue[];
  fixable: boolean;
}

// 简单的启发式代码分析（实际项目可以接入 LLM）
export async function analyzeCode(code: string, options: AnalysisOptions): Promise<AnalysisResult> {
  const issues: CodeIssue[] = [];
  const lines = code.split('\n');

  // 检查常见问题
  lines.forEach((line, index) => {
    const lineNum = index + 1;

    // 安全问题检测
    if (options.security || (!options.security && !options.style && !options.performance)) {
      if (line.includes('eval(')) {
        issues.push({
          severity: 'Critical',
          line: lineNum,
          type: 'security',
          description: '使用了 eval()，可能导致代码注入攻击',
          fixSuggestion: '使用 safer 的替代方案，如 JSON.parse() 或 Function 构造函数',
          explanation: options.explain ? 'eval() 会执行任意字符串作为代码，攻击者可以通过注入恶意代码来控制你的程序。' : undefined,
        });
      }
      if (line.includes('innerHTML') && !line.includes('textContent')) {
        issues.push({
          severity: 'High',
          line: lineNum,
          type: 'security',
          description: '使用 innerHTML 可能导致 XSS 攻击',
          fixSuggestion: '使用 textContent 替代，或对内容进行 sanitize',
          explanation: options.explain ? 'XSS (Cross-Site Scripting) 攻击允许攻击者在用户浏览器中执行恶意脚本。' : undefined,
        });
      }
      if (line.includes('console.log') && line.includes('password')) {
        issues.push({
          severity: 'High',
          line: lineNum,
          type: 'security',
          description: '敏感信息（密码）可能被记录到日志',
          fixSuggestion: '删除或注释掉包含敏感信息的日志',
          explanation: options.explain ? '日志可能被存储在不安全的地方，导致敏感信息泄露。' : undefined,
        });
      }
    }

    // 性能问题检测
    if (options.performance || (!options.security && !options.style && !options.performance)) {
      if (line.includes('document.querySelectorAll') && line.includes('forEach')) {
        issues.push({
          severity: 'Medium',
          line: lineNum,
          type: 'performance',
          description: '循环中进行 DOM 查询可能影响性能',
          fixSuggestion: '将 DOM 查询结果缓存到循环外部',
          explanation: options.explain ? 'DOM 查询是昂贵的操作，在循环中重复执行会显著降低性能。' : undefined,
        });
      }
    }

    // 风格问题检测
    if (options.style || (!options.security && !options.style && !options.performance)) {
      if (line.includes('var ')) {
        issues.push({
          severity: 'Low',
          line: lineNum,
          type: 'style',
          description: '使用 var 而不是 let/const',
          fixSuggestion: '使用 let 或 const 替代 var',
          explanation: options.explain ? 'var 有函数作用域提升问题，let/const 提供块级作用域，更安全。' : undefined,
        });
      }
      if (line.trim().endsWith(';') === false && line.trim().length > 0 && !line.trim().startsWith('//') && !line.trim().startsWith('/*') && !line.trim().startsWith('*') && !line.includes('{') && !line.includes('}') && !line.includes('`')) {
        // 简单的分号检查（避免误报）
      }
    }
  });

  // 生成报告
  const report = generateReport(issues, options);

  return {
    report,
    issues,
    fixable: issues.some(i => i.fixSuggestion),
  };
}

function generateReport(issues: CodeIssue[], options: AnalysisOptions): string {
  if (issues.length === 0) {
    return '✅ 代码检查通过，未发现问题！';
  }

  let report = '';

  // 按严重程度分组
  const critical = issues.filter(i => i.severity === 'Critical');
  const high = issues.filter(i => i.severity === 'High');
  const medium = issues.filter(i => i.severity === 'Medium');
  const low = issues.filter(i => i.severity === 'Low');

  report += `📊 发现 ${issues.length} 个问题\n`;
  report += '═══════════════════════════════════════\n\n';

  if (critical.length > 0) {
    report += `🔴 Critical (${critical.length})\n`;
    critical.forEach(issue => {
      report += `   Line ${issue.line}: ${issue.description}\n`;
      if (issue.explanation) report += `      ℹ️ ${issue.explanation}\n`;
      if (issue.fixSuggestion) report += `      💡 ${issue.fixSuggestion}\n`;
    });
    report += '\n';
  }

  if (high.length > 0) {
    report += `🟠 High (${high.length})\n`;
    high.forEach(issue => {
      report += `   Line ${issue.line}: ${issue.description}\n`;
      if (issue.explanation) report += `      ℹ️ ${issue.explanation}\n`;
      if (issue.fixSuggestion) report += `      💡 ${issue.fixSuggestion}\n`;
    });
    report += '\n';
  }

  if (medium.length > 0) {
    report += `🟡 Medium (${medium.length})\n`;
    medium.forEach(issue => {
      report += `   Line ${issue.line}: ${issue.description}\n`;
      if (issue.explanation) report += `      ℹ️ ${issue.explanation}\n`;
      if (issue.fixSuggestion) report += `      💡 ${issue.fixSuggestion}\n`;
    });
    report += '\n';
  }

  if (low.length > 0) {
    report += `🟢 Low (${low.length})\n`;
    low.forEach(issue => {
      report += `   Line ${issue.line}: ${issue.description}\n`;
      if (issue.explanation) report += `      ℹ️ ${issue.explanation}\n`;
      if (issue.fixSuggestion) report += `      💡 ${issue.fixSuggestion}\n`;
    });
    report += '\n';
  }

  const fixableCount = issues.filter(i => i.fixSuggestion).length;
  if (fixableCount > 0) {
    report += `\n═══════════════════════════════════════\n`;
    report += `💪 ${fixableCount} 个问题可自动修复\n`;
    report += `运行: /code-review --fix 来自动修复\n`;
  }

  return report;
}

// 简单的自动修复
export async function fixCode(code: string, analysis: AnalysisResult): Promise<string> {
  let fixedCode = code;

  // 简单的替换修复
  analysis.issues.forEach(issue => {
    if (issue.type === 'style' && issue.description.includes('var ')) {
      // 将 var 替换为 let/const（简单实现）
      const lines = fixedCode.split('\n');
      const lineIndex = issue.line - 1;
      if (lines[lineIndex]) {
        lines[lineIndex] = lines[lineIndex].replace(/\bvar\s+/g, 'let ');
        fixedCode = lines.join('\n');
      }
    }
    // 更多修复规则可以在这里添加
  });

  return fixedCode;
}
