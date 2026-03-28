// ═══════════════════════════════════════════════════
// SkillPay Billing Integration / 计费接入
// スキルペイ課金統合 / 결제 연동 / Интеграция биллинга
// ═══════════════════════════════════════════════════

const BILLING_API_URL = 'https://skillpay.me';
const BILLING_API_KEY = 'sk_97337971993cff4076fb179c0e1f42d592a89406507c603db864d6784c849bd8';  // Dashboard → 接入配置 / Integration Config
export const SKILL_ID = '3da52f24-9e3d-43bd-931d-0925e237ed93';

// ① Check balance / 查余额 / 残高確認 / 잔액 확인 / Проверка баланса
export async function checkBalance(userId: string): Promise<number> {
  const resp = await fetch(
    `${BILLING_API_URL}/api/v1/billing/balance?user_id=${encodeURIComponent(userId)}`,
    { headers: { 'X-API-Key': BILLING_API_KEY } }
  );
  const data = await resp.json();
  return data.balance;  // USDT amount / USDT 金额
}

// ② Charge per call / 每次调用扣费 / 呼び出しごとの課金 / 호출당 과금 / Списание за вызов
export async function chargeUser(userId: string): Promise<{
  ok: boolean;
  balance?: number;
  paymentUrl?: string;
}> {
  const resp = await fetch(`${BILLING_API_URL}/api/v1/billing/charge`, {
    method: 'POST',
    headers: {
      'X-API-Key': BILLING_API_KEY,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: userId,
      skill_id: SKILL_ID,
      amount: 0.001,  // USDT per call / 每次调用单价
    }),
  });
  const data = await resp.json();

  if (data.success) {
    return { ok: true, balance: data.balance };
  }

  // Insufficient balance → get payment link
  // 余额不足 → 生成充值链接
  // 残高不足 → 決済リンク生成
  // 잔액 부족 → 결제 링크 생성
  // Недостаточно средств → ссылка на оплату
  return { ok: false, balance: data.balance, paymentUrl: data.payment_url };
}

// ③ Generate payment link / 生成充值链接 / 決済リンク生成 / 결제 링크 생성 / Ссылка на оплату
export async function getPaymentLink(userId: string, amount: number): Promise<string> {
  const resp = await fetch(`${BILLING_API_URL}/api/v1/billing/payment-link`, {
    method: 'POST',
    headers: {
      'X-API-Key': BILLING_API_KEY,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ user_id: userId, amount }),
  });
  const data = await resp.json();
  return data.payment_url;  // BNB Chain USDT payment link / BNB链 USDT 付款链接
}

// ═══════ Usage example / 使用示例 ═══════
//
// async function handleRequest(userId) {
//   const result = await chargeUser(userId);
//   if (result.ok) {
//     // ✅ Execute your skill logic here
//     // ✅ 在这里执行你的 Skill 逻辑
//     return { success: true };
//   } else {
//     // ❌ Insufficient balance, return payment link to user
//     // ❌ 余额不足，返回充值链接给用户
//     return { success: false, paymentUrl: result.paymentUrl };
//   }
// }
