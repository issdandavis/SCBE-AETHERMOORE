param(
  [Parameter(Mandatory=$true)][string]$Prompt,
  [string]$Provider = 'hf',
  [string]$Model = 'Qwen/Qwen2.5-7B-Instruct',
  [string]$VaultPath = 'C:/Users/issda/OneDrive/Documents/DOCCUMENTS/A follder'
)

python "scripts/system/ai_bridge.py" --provider $Provider --model $Model --prompt $Prompt --vault-path $VaultPath
