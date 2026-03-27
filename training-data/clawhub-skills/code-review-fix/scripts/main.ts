#!/usr/bin/env bun
import { parseArgs } from 'util';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join } from 'path';
import { chargeUser, checkBalance, getPaymentLink } from '../lib/billing';
import { analyzeCode, fixCode } from '../lib/analyzer';

const CONFIG = {
  freeCalls: 3, // 前3次免费
  stateFile: join(process.cwd(), '.code-review-fix-state.json'),
};

interface State {
  [userId: string]: {
    freeCallsUsed: number;
    totalCalls: number;
  };
}

function loadState(): State {
  if (existsSync(CONFIG.stateFile)) {
    return JSON.parse(readFileSync(CONFIG.stateFile, 'utf-8'));
  }
  return {};
}

function saveState(state: State) {
  writeFileSync(CONFIG.stateFile, JSON.stringify(state, null, 2));
}

function getUserId(): string {
  // 使用环境变量或机器标识作为用户ID
  return process.env.SKILLPAY_USER_ID || 'local-user-' + require('os').userInfo().username;
}

async function main() {
  const { values, positionals } = parseArgs({
    args: Bun.argv,
    options: {
      fix: { type: 'boolean' },
      security: { type: 'boolean' },
      style: { type: 'boolean' },
      performance: { type: 'boolean' },
      explain: { type: 'boolean' },
      help: { type: 'boolean' },
    },
    strict: true,
    allowPositionals: true,
  });

  if (values.help) {
    console.log(`
Code Review & Fix - 智能代码审查与修复

Usage:
  /code-review [file]          审查代码
  /code-review --fix            审查并自动修复
  /code-review --security       只检查安全问题
  /code-review --style          只检查风格问题
  /code-review --performance    只检查性能问题
  /code-review --explain        学习模式（附带解释）

Options:
  --fix         自动修复问题
  --security    安全检查模式
  --style       风格检查模式
  --performance 性能检查模式
  --explain     解释模式
  --help        显示帮助
`);
    return;
  }

  // 获取要审查的文件
  let targetFile = positionals[2];
  if (!targetFile) {
    // 如果没有指定文件，尝试找当前目录的主要文件
    const files = ['index.ts', 'index.js', 'main.ts', 'main.js', 'app.ts', 'app.js'];
    for (const f of files) {
      if (existsSync(join(process.cwd(), f))) {
        targetFile = f;
        break;
      }
    }
  }

  if (!targetFile || !existsSync(join(process.cwd(), targetFile))) {
    console.log('❌ 请指定要审查的文件，或在包含代码文件的目录中运行');
    return;
  }

  const filePath = join(process.cwd(), targetFile);
  const code = readFileSync(filePath, 'utf-8');

  // === 计费流程开始 ===
  const userId = getUserId();
  const state = loadState();
  const userState = state[userId] || { freeCallsUsed: 0, totalCalls: 0 };

  const isFree = userState.freeCallsUsed < CONFIG.freeCalls;

  if (!isFree) {
    console.log('⏳ 检查计费状态...');
    const result = await chargeUser(userId);
    if (!result.ok) {
      console.log(`
❌ 余额不足！
当前余额: ${result.balance} USDT

请充值: ${result.paymentUrl}

或获取充值链接:
$ /code-review payment-link 10  # 充值 10 USDT
`);
      return;
    }
    console.log(`✅ 扣费成功！当前余额: ${result.balance} USDT`);
  } else {
    userState.freeCallsUsed++;
    console.log(`🎁 免费试用 (${userState.freeCallsUsed}/${CONFIG.freeCalls})`);
  }

  userState.totalCalls++;
  state[userId] = userState;
  saveState(state);
  // === 计费流程结束 ===

  // 执行代码审查
  console.log(`\n🔍 正在审查: ${targetFile}`);
  console.log('═══════════════════════════════════════');

  const analysis = await analyzeCode(code, {
    security: values.security,
    style: values.style,
    performance: values.performance,
    explain: values.explain,
  });

  console.log(analysis.report);

  // 如果需要修复
  if (values.fix && analysis.fixable) {
    console.log('\n🔧 正在自动修复...');
    const fixedCode = await fixCode(code, analysis);
    writeFileSync(filePath, fixedCode);
    console.log('✅ 修复完成！');
  }

  if (isFree && userState.freeCallsUsed >= CONFIG.freeCalls) {
    console.log(`
═══════════════════════════════════════
🎉 免费试用已结束，下次调用将开始计费

定价:
  单次调用: 0.001 USDT
  更多套餐: https://skillpay.me/skill/${SKILL_ID}
`);
  }
}

// 处理支付链接生成
if (Bun.argv[2] === 'payment-link') {
  const amount = parseFloat(Bun.argv[3] || '10');
  const userId = getUserId();
  const link = await getPaymentLink(userId, amount);
  console.log(`💰 充值链接 (${amount} USDT):\n${link}`);
  process.exit(0);
}

// 处理余额查询
if (Bun.argv[2] === 'balance') {
  const userId = getUserId();
  const balance = await checkBalance(userId);
  console.log(`💰 当前余额: ${balance} USDT`);
  process.exit(0);
}

main().catch(console.error);
