Get-ChildItem -Path 'D:/Codes/Final-Year-Project/AI-Powered-Government-Scheme-Fulfillment-Engine/frontend/govt_scheme_app/lib/core/presentation' -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ('==== '+$_.Name+' ===='); Get-Content -LiteralPath $_.FullName }
Write-Output '==== END PRESENTATION ===='
Get-ChildItem -Path 'D:/Codes/Final-Year-Project/AI-Powered-Government-Scheme-Fulfillment-Engine/frontend/govt_scheme_app/lib/screens/recommendations/widgets' -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ('==== '+$_.Name+' ===='); Get-Content -LiteralPath $_.FullName }
Write-Output '==== END WIDGETS ===='
Get-ChildItem -Path 'D:/Codes/Final-Year-Project/AI-Powered-Government-Scheme-Fulfillment-Engine/frontend/govt_scheme_app/test' -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ('==== '+$_.Name+' ===='); Get-Content -LiteralPath $_.FullName }
Write-Output '==== END TESTS ===='
