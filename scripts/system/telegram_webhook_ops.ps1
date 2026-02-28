param(
    [ValidateSet("set", "get", "delete", "test")]
    [string]$Action = "get",
    [string]$Token = "",
    [string]$WebhookUrl = "",
    [string]$SecretToken = "",
    [string]$ChatId = "",
    [string]$Message = "SCBE Telegram test",
    [switch]$DropPendingUpdates
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Token)) {
    $Token = $env:TELEGRAM_BOT_TOKEN
}
if ([string]::IsNullOrWhiteSpace($Token)) {
    $Token = $env:SCBE_TELEGRAM_BOT_TOKEN
}
if ([string]::IsNullOrWhiteSpace($Token)) {
    throw "Missing Telegram bot token. Set TELEGRAM_BOT_TOKEN or pass -Token."
}

$base = "https://api.telegram.org/bot$Token"

function Invoke-TelegramApi {
    param(
        [string]$MethodName,
        [hashtable]$Payload = @{}
    )
    $uri = "$base/$MethodName"
    return Invoke-RestMethod -Method Post -Uri $uri -ContentType "application/json" -Body ($Payload | ConvertTo-Json -Compress)
}

switch ($Action) {
    "set" {
        if ([string]::IsNullOrWhiteSpace($WebhookUrl)) {
            throw "Webhook URL is required for action 'set'."
        }
        if (-not $WebhookUrl.StartsWith("https://")) {
            throw "Webhook URL must start with https://"
        }

        $payload = @{
            url = $WebhookUrl
            drop_pending_updates = [bool]$DropPendingUpdates
        }
        if (-not [string]::IsNullOrWhiteSpace($SecretToken)) {
            $payload["secret_token"] = $SecretToken
        }

        $resp = Invoke-TelegramApi -MethodName "setWebhook" -Payload $payload
        $resp | ConvertTo-Json -Depth 6
    }
    "get" {
        $resp = Invoke-TelegramApi -MethodName "getWebhookInfo"
        $resp | ConvertTo-Json -Depth 6
    }
    "delete" {
        $payload = @{
            drop_pending_updates = [bool]$DropPendingUpdates
        }
        $resp = Invoke-TelegramApi -MethodName "deleteWebhook" -Payload $payload
        $resp | ConvertTo-Json -Depth 6
    }
    "test" {
        if ([string]::IsNullOrWhiteSpace($ChatId)) {
            if (-not [string]::IsNullOrWhiteSpace($env:TELEGRAM_CHAT_ID)) {
                $ChatId = $env:TELEGRAM_CHAT_ID
            } elseif (-not [string]::IsNullOrWhiteSpace($env:SCBE_TELEGRAM_CHAT_ID)) {
                $ChatId = $env:SCBE_TELEGRAM_CHAT_ID
            }
        }
        if ([string]::IsNullOrWhiteSpace($ChatId)) {
            throw "ChatId is required for action 'test'. Pass -ChatId or set TELEGRAM_CHAT_ID."
        }
        if ($ChatId -notmatch "^-?\d+$") {
            throw "ChatId must be numeric."
        }

        $payload = @{
            chat_id = $ChatId
            text = $Message
            disable_notification = $false
        }
        $resp = Invoke-TelegramApi -MethodName "sendMessage" -Payload $payload
        $resp | ConvertTo-Json -Depth 6
    }
}
