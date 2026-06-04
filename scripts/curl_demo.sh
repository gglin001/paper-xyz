# scripts for debug usage

API_BASE=http://127.0.0.1:11235

curl $API_BASE/v1/models

curl $API_BASE/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
     "messages": [{"role": "user", "content": "hi"}]
   }'
