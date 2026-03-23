"""Parse Cash App bank statements and categorize transactions for tax purposes."""
import pdfplumber
import os
import re
from collections import defaultdict

months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'august', 'september', 'October', 'november', 'deccember'
]

base = r'C:\Users\issda\OneDrive\Downloads'

biz_keywords = ['anthropic', 'claude', 'openai', 'chatgpt', 'gpt', 'hetzner', 'github', 'copilot',
                'hugging', 'hf.co', 'digitalocean', 'aws', 'azure', 'google cloud', 'gcp',
                'domain', 'namecheap', 'godaddy', 'cloudflare', 'vercel', 'netlify', 'heroku',
                'adobe', 'figma', 'canva', 'notion', 'airtable', 'zapier', 'slack',
                'cursor', 'replit', 'codespace', 'jetbrains', 'vscode', 'npm', 'pypi',
                'uspto', 'patent', 'colab', 'kaggle', 'perplexity', 'midjourney',
                'stripe', 'shopify', 'gumroad', 'x.ai', 'xai', 'grok']

subscription_keywords = ['netflix', 'disney', 'youtube', 'spotify', 'hulu', 'amazon prime',
                         'play pass', 'bitlife', 'apple', 'att', 'phone', 'wireless',
                         'xbox', 'playstation', 'steam', 'nintendo']

income_keywords = ['burger managemen', 'direct dep', 'direct deposit']
crypto_keywords = ['btc', 'bitcoin', 'stock buy', 'stock sell', 'auto invest', 'googl', 'aal',
                   'round ups']

summaries = {}
biz_expenses = []
crypto_activity = []
income_items = []
subscriptions = []

for m in months:
    path = os.path.join(base, f'{m}2025monthly-statement (1).pdf')
    if not os.path.exists(path):
        print(f'MISSING: {m}')
        continue
    pdf = pdfplumber.open(path)

    p1 = pdf.pages[0].extract_text() or ''
    money_in = re.search(r'Money In.*?\$([\d,]+\.\d+)', p1)
    money_out = re.search(r'Money Out.*?\$([\d,]+\.\d+)', p1)
    fees = re.search(r'Fees.*?\$([\d,]+\.\d+)', p1)

    summaries[m] = {
        'money_in': money_in.group(1) if money_in else '?',
        'money_out': money_out.group(1) if money_out else '?',
        'fees': fees.group(1) if fees else '?'
    }

    for page in pdf.pages:
        text = page.extract_text() or ''
        lines = text.split('\n')
        for line in lines:
            line_lower = line.lower()

            for kw in biz_keywords:
                if kw in line_lower:
                    biz_expenses.append((m, line.strip()))
                    break

            for kw in crypto_keywords:
                if kw in line_lower:
                    crypto_activity.append((m, line.strip()))
                    break

            for kw in income_keywords:
                if kw in line_lower:
                    income_items.append((m, line.strip()))
                    break

            for kw in subscription_keywords:
                if kw in line_lower:
                    subscriptions.append((m, line.strip()))
                    break
    pdf.close()

print('=' * 70)
print('MONTHLY CASH FLOW SUMMARY')
print('=' * 70)
for m in months:
    if m in summaries:
        s = summaries[m]
        print(f'  {m:>12}: In ${s["money_in"]:>10}  Out ${s["money_out"]:>10}  Fees ${s["fees"]:>8}')

print()
print('=' * 70)
print(f'POTENTIAL BUSINESS EXPENSES ({len(biz_expenses)} found)')
print('=' * 70)
for month, line in biz_expenses:
    print(f'  [{month[:3]}] {line}')

print()
print('=' * 70)
print(f'INCOME / DEPOSITS ({len(income_items)} found)')
print('=' * 70)
for month, line in income_items:
    print(f'  [{month[:3]}] {line}')

print()
print('=' * 70)
print(f'CRYPTO / STOCK ACTIVITY (summary)')
print('=' * 70)
btc_buys = [l for _, l in crypto_activity if ('btc' in l.lower() or 'bitcoin' in l.lower()) and 'round up' not in l.lower()]
btc_roundups = [l for _, l in crypto_activity if 'round up' in l.lower()]
stock_txns = [l for _, l in crypto_activity if 'invest' in l.lower() or 'stock' in l.lower()]
print(f'  Bitcoin direct purchases: {len(btc_buys)}')
print(f'  Bitcoin round-ups: {len(btc_roundups)}')
print(f'  Stock auto-invests: {len(stock_txns)}')
print()
print('  Direct BTC purchases:')
for month, line in crypto_activity:
    if ('btc' in line.lower() or 'bitcoin' in line.lower()) and 'round up' not in line.lower() and 'paycheck' not in line.lower():
        print(f'    [{month[:3]}] {line}')
print()
print('  Paycheck BTC purchases:')
for month, line in crypto_activity:
    if 'paycheck' in line.lower():
        print(f'    [{month[:3]}] {line}')

print()
print('=' * 70)
print(f'PERSONAL SUBSCRIPTIONS (monthly)')
print('=' * 70)
seen = set()
for month, line in subscriptions:
    desc = re.sub(r'[\d$.,]+', '', line).strip()[:40]
    key = (month, desc)
    if key not in seen:
        seen.add(key)
        print(f'  [{month[:3]}] {line}')
