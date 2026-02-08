# Doc Translate Agent - Authentication API

A FastAPI-based authentication system with Supabase PostgreSQL backend.

## Features

- **User Signup**: Register new users with email and password
- **User Login**: Authenticate users and receive JWT tokens
- **Password Hashing**: Secure password storage with bcrypt
- **JWT Authentication**: Token-based authentication for protected routes
- **Supabase Integration**: PostgreSQL database on Supabase

## Setup Instructions

### 1. Prerequisites

- Python 3.8+
- Supabase account (free tier available at https://supabase.com)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up Supabase

1. Create a new project on [Supabase](https://supabase.com)
2. Get your API credentials:
   - SUPABASE_URL: Available in Settings > API
   - SUPABASE_KEY (anon key): Available in Settings > API
3. Run the SQL migration in your Supabase SQL editor:
   - Copy contents of `migrations/001_create_users_table.sql`
   - Paste and execute in Supabase SQL editor

### 4. Configure Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```

2. Fill in your values:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_anon_key
   SECRET_KEY=your-secret-key-for-jwt-tokens
   PORT=8000
   ```

### 5. Run the Server

```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Authentication Endpoints

#### 1. Signup
**POST** `/auth/signup`

Request:
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "securepassword123"
}
```

Response:
```json
{
  "id": "uuid-here",
  "username": "john_doe",
  "email": "john@example.com",
  "created_at": "2024-02-08T10:00:00Z"
}
```

#### 2. Login
**POST** `/auth/login`

Request:
```json
{
  "email": "john@example.com",
  "password": "securepassword123"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid-here",
    "username": "john_doe",
    "email": "john@example.com",
    "created_at": "2024-02-08T10:00:00Z"
  }
}
```

### Translation Session Endpoints

All session endpoints require `Authorization: Bearer <token>` header.

#### 3. Create Session
**POST** `/sessions`

Request:
```json
{
  "main_file": "document content or file path",
  "context": "Optional context for translation"
}
```

Response:
```json
{
  "id": "session-uuid",
  "user_id": "user-uuid",
  "main_file": "document content",
  "context": "context text",
  "created_at": "2024-02-08T10:00:00Z",
  "updated_at": "2024-02-08T10:00:00Z"
}
```

#### 4. Get Session with Messages
**GET** `/sessions/{session_id}`

Response:
```json
{
  "id": "session-uuid",
  "user_id": "user-uuid",
  "main_file": "document content",
  "context": "context text",
  "created_at": "2024-02-08T10:00:00Z",
  "updated_at": "2024-02-08T10:00:00Z",
  "messages": [
    {
      "id": "message-uuid",
      "session_id": "session-uuid",
      "role": "user",
      "content": "Translate this document",
      "file_path": null,
      "created_at": "2024-02-08T10:05:00Z"
    }
  ]
}
```

#### 5. List Sessions
**GET** `/sessions`

Response:
```json
[
  {
    "id": "session-uuid",
    "user_id": "user-uuid",
    "main_file": "document content",
    "context": "context text",
    "created_at": "2024-02-08T10:00:00Z",
    "updated_at": "2024-02-08T10:00:00Z"
  }
]
```

#### 6. Update Session
**PUT** `/sessions/{session_id}`

Request (all fields optional):
```json
{
  "main_file": "updated document content",
  "context": "updated context"
}
```

#### 7. Delete Session
**DELETE** `/sessions/{session_id}`

Status: 204 No Content

### Message Endpoints

#### 8. Add Message to Session
**POST** `/sessions/{session_id}/messages`

Request:
```json
{
  "role": "user",
  "content": "Please translate this",
  "file_path": "/path/to/optional/file"
}
```

Response:
```json
{
  "id": "message-uuid",
  "session_id": "session-uuid",
  "role": "user",
  "content": "Please translate this",
  "file_path": "/path/to/optional/file",
  "created_at": "2024-02-08T10:05:00Z"
}
```

#### 9. Get Messages in Session
**GET** `/sessions/{session_id}/messages`

Response:
```json
[
  {
    "id": "message-uuid-1",
    "session_id": "session-uuid",
    "role": "user",
    "content": "First message",
    "file_path": null,
    "created_at": "2024-02-08T10:05:00Z"
  },
  {
    "id": "message-uuid-2",
    "session_id": "session-uuid",
    "role": "assistant",
    "content": "Response message",
    "file_path": null,
    "created_at": "2024-02-08T10:06:00Z"
  }
]
```

#### 10. Chat with Agent
**POST** `/sessions/{session_id}/chat`

Send a message to the agent and receive a response. Both user and agent messages are automatically saved.

Request:
```json
{
  "message": "Please translate this to French",
  "file_path": null
}
```

Response:
```json
{
  "user_message": {
    "id": "message-uuid-1",
    "session_id": "session-uuid",
    "role": "user",
    "content": "Please translate this to French",
    "file_path": null,
    "created_at": "2024-02-08T10:05:00Z"
  },
  "agent_response": {
    "id": "message-uuid-2",
    "session_id": "session-uuid",
    "role": "assistant",
    "content": "Agent response with translation...",
    "file_path": null,
    "created_at": "2024-02-08T10:05:01Z"
  }
}
```

### Health Check
**GET** `/health`

Response:
```json
{
  "status": "ok"
}
```

## Using the Access Token

Include the token in the Authorization header for protected routes:

```
Authorization: Bearer <your_access_token>
```

## Project Structure

```
.
├── main.py                          # FastAPI application
├── requirements.txt                 # Python dependencies
├── .env.example                    # Environment variables template
├── migrations/
│   └── 001_create_users_table.sql  # Database schema
├── core/
│   ├── auth.py                     # Authentication utilities
│   ├── database.py                 # Supabase client setup
│   └── schemas/
│       ├── user.py                 # User models
│       └── session.py              # Session and message models
└── api/
    ├── auth.py                     # Authentication routes
    └── sessions.py                 # Session and message routes
```

## Database Schema

### Users Table
```sql
users:
  - id (UUID, PRIMARY KEY)
  - username (VARCHAR, UNIQUE)
  - email (VARCHAR, UNIQUE)
  - password (TEXT, hashed)
  - created_at (TIMESTAMP)
  - updated_at (TIMESTAMP)
```

### Translation Sessions Table
```sql
translation_sessions:
  - id (UUID, PRIMARY KEY)
  - user_id (UUID, FOREIGN KEY -> users.id)
  - main_file (TEXT) - File content or path
  - context (TEXT) - Optional context for translation
  - created_at (TIMESTAMP)
  - updated_at (TIMESTAMP)
```

### Messages Table
```sql
messages:
  - id (UUID, PRIMARY KEY)
  - session_id (UUID, FOREIGN KEY -> translation_sessions.id)
  - role (VARCHAR) - e.g., "user", "assistant"
  - content (TEXT) - Message content
  - file_path (VARCHAR, OPTIONAL) - Optional file path
  - created_at (TIMESTAMP)
```

## Next Steps

The authentication, session management, and chat system is now ready. Here's what you can do:

1. **Implement Agent Logic**: Replace the placeholder `process_message_with_agent()` function in [api/sessions.py](api/sessions.py) with your actual translation agent. You can use:
   - OpenAI GPT API
   - Google Translate API
   - LangChain with various LLMs
   - Local open-source models (Llama, Mistral)
   - Custom translation service

2. **Use Chat Endpoint**: The `POST /sessions/{session_id}/chat` endpoint automatically:
   - Saves user message
   - Processes with agent
   - Saves agent response
   - Returns both messages in one request

3. **Create Translation Sessions**: Use `/sessions` endpoints to create and manage translation sessions

4. **Store Messages**: Messages are automatically saved, or manually add with `/sessions/{session_id}/messages`

5. **Add File Upload**: Implement file upload functionality for the `main_file` field

6. **Add Rate Limiting**: Implement rate limiting on auth and chat endpoints to prevent abuse

7. **Add Email Verification**: Enhance security with email verification for signup

8. **WebSocket Support** (Optional): Convert chat endpoint to WebSocket for real-time streaming responses

### Example Flow

```python
# 1. User signs up
POST /auth/signup
{
  "username": "user123",
  "email": "user@example.com",
  "password": "securepass"
}

# 2. User logs in and gets token
POST /auth/login
{
  "email": "user@example.com",
  "password": "securepass"
}
# Returns: access_token

# 3. User creates a translation session
POST /sessions
Headers: Authorization: Bearer <access_token>
{
  "main_file": "document to translate...",
  "context": "technical documentation"
}
# Returns: session with id

# 4. User sends a message to the agent (chat endpoint)
POST /sessions/{session_id}/chat
Headers: Authorization: Bearer <access_token>
{
  "message": "Translate this to French",
  "file_path": null
}
# Returns: both user message and agent response

# 5. Alternative: Add message manually
POST /sessions/{session_id}/messages
Headers: Authorization: Bearer <access_token>
{
  "role": "user",
  "content": "Translate to French",
  "file_path": null
}

# 6. Get all messages in session
GET /sessions/{session_id}/messages
Headers: Authorization: Bearer <access_token>
```

## Protecting Routes with Authentication

To create additional protected routes, use this pattern:

```python
from fastapi import APIRouter, Header
from typing import Optional
from core.auth import decode_token

@router.get("/protected")
async def protected_route(authorization: Optional[str] = Header(None)):
    # Verify token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    token = authorization[7:]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    # Use user_id in your logic
    return {"message": f"Hello {user_id}"}
```

## Implementing Agent Logic

The chat endpoint uses a placeholder `process_message_with_agent()` function in [api/sessions.py](api/sessions.py). Replace it with your actual translation agent:

### Example 1: Using OpenAI API

```python
import openai

async def process_message_with_agent(
    user_message: str,
    session_context: Optional[str],
    session_main_file: str,
) -> str:
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": f"You are a translation agent. Context: {session_context}"},
            {"role": "system", "content": f"Document to translate:\n{session_main_file}"},
            {"role": "user", "content": user_message}
        ]
    )
    
    return response.choices[0].message.content
```

### Example 2: Using LangChain

```python
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage

async def process_message_with_agent(
    user_message: str,
    session_context: Optional[str],
    session_main_file: str,
) -> str:
    llm = ChatOpenAI(model="gpt-4")
    
    messages = [
        SystemMessage(content=f"You are a translation agent. Context: {session_context}"),
        SystemMessage(content=f"Document:\n{session_main_file}"),
        HumanMessage(content=user_message)
    ]
    
    response = llm(messages)
    return response.content
```

### Example 3: Using Google Translate API

```python
from google.cloud import translate_v2

async def process_message_with_agent(
    user_message: str,
    session_context: Optional[str],
    session_main_file: str,
) -> str:
    translate_client = translate_v2.Client()
    
    # Extract target language from user message
    result = translate_client.translate_text(
        source_language_code="en",
        target_language_code="fr",  # Extract from message
        contents=[session_main_file]
    )
    
    return result["translations"][0]["translatedText"]
```

Remember to:
- Install the required package: `pip install openai` or `pip install langchain` etc.
- Add API keys to `.env`: `OPENAI_API_KEY=...`
- Update `requirements.txt` with new dependencies

## Security Notes

- Change `SECRET_KEY` in production
- Use HTTPS in production
- Set specific CORS origins instead of "*"
- Never commit `.env` file to version control
- Implement rate limiting for auth endpoints
- Add email verification for signup

## Troubleshooting

**"SUPABASE_URL and SUPABASE_KEY must be set"**: Make sure `.env` file exists and contains valid values.

**"Email already registered"**: User with that email already exists.

**"Invalid email or password"**: Check credentials and ensure user exists.

**Connection errors**: Verify Supabase URL and key are correct.
