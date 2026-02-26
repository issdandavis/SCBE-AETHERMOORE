param(
    [Parameter(Mandatory=$true)]
    [string]$Title,
    [Parameter(Mandatory=$true)]
    [string]$Summary,
    [string]$VaultPath = "C:/Users/issda/OneDrive/Documents/DOCCUMENTS/A follder",
    [string]$Files = "",
    [string]$Next = ""
)

python "scripts/system/obsidian_byproduct_note.py" `
  --vault-path "$VaultPath" `
  --title "$Title" `
  --summary "$Summary" `
  --files "$Files" `
  --next "$Next"
