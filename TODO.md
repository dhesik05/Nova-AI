# API Endpoint Test + Fix Plan

## Step 1: Add/Update TODO tracking
- [x] Document required endpoints and implementation approach
- [ ] Implement missing root-level compatibility endpoints
- [ ] Test each endpoint until success

## Step 2: Implement root-level compatibility endpoints (required)
- [x] GET `/history` (list conversations from DB)
- [x] POST `/new-chat` (create and persist a conversation; return `conversation_id`)
- [x] POST `/speech-to-text` (multipart upload -> `transcribe_audio`)
- [x] POST `/text-to-speech` (generate valid WAV using Python stdlib; return JSON with base64 audio)
- [x] POST `/upload/image` (multipart image upload -> save to `backend/uploads/`; return metadata)

## Step 3: Verify endpoints
- [x] Run server
- [x] Test:
  - GET `/health`
  - POST `/chat`
  - POST `/api/chat/stream`
  - GET `/history`
  - POST `/new-chat`
  - POST `/upload/pdf`
  - POST `/upload/image`
  - POST `/speech-to-text`
  - POST `/text-to-speech`
- [x] Fix any failing endpoints
- [x] Re-test until all required endpoints return a valid response
