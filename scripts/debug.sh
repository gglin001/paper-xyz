# scripts for debug usage

curl http://127.0.0.1:11235/models

curl http://127.0.0.1:11235/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
     "messages": [{"role": "user", "content": "hi"}]
   }'
