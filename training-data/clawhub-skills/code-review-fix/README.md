# Code Review & Fix Skill

智能代码审查与修复技能，支持 SkillPay 计费接入。

## 功能特性

- ✅ 代码问题检测（bug、安全、性能）
- ✅ 代码风格检查
- ✅ 自动修复
- ✅ 解释教育模式
- ✅ SkillPay 计费集成
- ✅ 前3次免费试用

## 快速开始

```bash
# 安装依赖
cd code-review-fix
bun install

# 运行帮助
bun run scripts/main.ts --help

# 审查代码
bun run scripts/main.ts your-file.ts

# 审查并自动修复
bun run scripts/main.ts your-file.ts --fix

# 学习模式（带解释）
bun run scripts/main.ts your-file.ts --explain
```

## SkillPay 计费配置

编辑 `lib/billing.ts` 中的配置：

```typescript
const BILLING_API_KEY = 'your-api-key';  // 从 skillpay.me 获取
export const SKILL_ID = 'your-skill-id';
```

## 计费命令

```bash
# 查看余额
bun run scripts/main.ts balance

# 获取充值链接
bun run scripts/main.ts payment-link 10  # 充值 10 USDT
```

## 目录结构

```
code-review-fix/
├── SKILL.md              # Skill 定义
├── README.md             # 本文件
├── package.json          # 项目配置
├── scripts/
│   └── main.ts          # 主入口
├── lib/
│   ├── billing.ts       # SkillPay 计费集成
│   └── analyzer.ts      # 代码分析核心
└── config/
    └── rules.json       # 审查规则（可选）
```

## 定价

- 前3次：免费
- 单次调用：0.001 USDT
- 更多套餐：见 skillpay.me

## 扩展开发

### 添加新的检查规则

编辑 `lib/analyzer.ts` 中的 `analyzeCode` 函数。

### 接入 LLM 进行智能分析

可以在 `analyzeCode` 函数中接入 Claude API 或其他 LLM：

```typescript
const response = await fetch('https://api.anthropic.com/v1/messages', {
  method: 'POST',
  headers: {
    'x-api-key': process.env.ANTHROPIC_API_KEY,
    'content-type': 'application/json',
  },
  body: JSON.stringify({
    model: 'claude-sonnet-4-6',
    messages: [{ role: 'user', content: `审查代码: ${code}` }],
  }),
});
```

## License

MIT
