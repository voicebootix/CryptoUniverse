# Simple WebSocket Test using PowerShell
# Tests the WebSocket chat endpoint

$ErrorActionPreference = "Stop"

# Configuration
$wsUrl = "wss://cryptouniverse.onrender.com/api/v1/chat/ws/test-session-123"
$token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3YTFlZThjZC1iZmM5LTRlNGUtODViMi02OWM4ZTkxMDU0YWYiLCJlbWFpbCI6ImFkbWluQGNyeXB0b3VuaXZlcnNlLmNvbSIsInJvbGUiOiJhZG1pbiIsInRlbmFudF9pZCI6IiIsImV4cCI6MTc1NzQ0NTEwMywiaWF0IjoxNzU3NDE3MTAzLCJqdGkiOiJhMTYyNzAxZjdkODRlMTAyMzJmYzc2ZGU1MGE4NzcyMzUiLCJ0eXBlIjoiYWNjZXNzIn0.B2CErhzWDlW5px-m24MZeTaPHIsgRPBZ8EO99pL2ZfU"

Write-Host "🚀 Testing WebSocket Chat Endpoint" -ForegroundColor Cyan
Write-Host "URL: $wsUrl" -ForegroundColor Yellow

try {
    # Create WebSocket client
    $ws = New-Object System.Net.WebSockets.ClientWebSocket
    
    # Add authentication header
    $ws.Options.SetRequestHeader("Authorization", "Bearer $token")
    
    # Connect
    Write-Host "🔗 Connecting to WebSocket..." -ForegroundColor Yellow
    $uri = [System.Uri]::new($wsUrl)
    $cts = New-Object System.Threading.CancellationTokenSource
    
    $connectTask = $ws.ConnectAsync($uri, $cts.Token)
    $connectTask.Wait(10000) # 10 second timeout
    
    if ($ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
        Write-Host "✅ WebSocket connected successfully!" -ForegroundColor Green
        Write-Host "State: $($ws.State)" -ForegroundColor Green
        
        # Send a test message
        $message = @{
            type = "chat_message"
            message = "Hello from PowerShell WebSocket test!"
            timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        } | ConvertTo-Json
        
        Write-Host "📤 Sending message: $message" -ForegroundColor Cyan
        
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($message)
        $buffer = New-Object System.ArraySegment[byte] -ArgumentList @(,$bytes)
        
        $sendTask = $ws.SendAsync($buffer, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $cts.Token)
        $sendTask.Wait(5000)
        
        Write-Host "✅ Message sent successfully!" -ForegroundColor Green
        
        # Try to receive response
        Write-Host "⏳ Waiting for response..." -ForegroundColor Yellow
        
        $receiveBuffer = New-Object byte[] 4096
        $receiveSegment = New-Object System.ArraySegment[byte] -ArgumentList @(,$receiveBuffer)
        
        $receiveTask = $ws.ReceiveAsync($receiveSegment, $cts.Token)
        
        if ($receiveTask.Wait(15000)) {
            $result = $receiveTask.Result
            $responseText = [System.Text.Encoding]::UTF8.GetString($receiveBuffer, 0, $result.Count)
            Write-Host "📨 Response received: $responseText" -ForegroundColor Green
        } else {
            Write-Host "⚠️ No response received within 15 seconds" -ForegroundColor Yellow
        }
        
    } else {
        Write-Host "❌ Failed to connect. State: $($ws.State)" -ForegroundColor Red
    }
    
} catch {
    Write-Host "❌ WebSocket test failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Full error: $($_.Exception)" -ForegroundColor Red
} finally {
    if ($ws) {
        try {
            $ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "Test completed", $cts.Token).Wait(2000)
            $ws.Dispose()
            Write-Host "🔒 WebSocket connection closed" -ForegroundColor Gray
        } catch {
            Write-Host "⚠️ Error closing WebSocket: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}

Write-Host "🎉 WebSocket test completed!" -ForegroundColor Cyan