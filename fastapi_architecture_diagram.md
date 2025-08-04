# FastAPI Architecture Diagram

## Core Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application Layer                    │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐      │
│  │   Route         │ │   Dependency    │ │   Middleware    │      │
│  │   Handlers      │ │   Injection     │ │   System        │      │
│  │                 │ │                 │ │                 │      │
│  │ @app.get("/")   │ │ Depends()       │ │ CORS, Auth,     │      │
│  │ async def...    │ │ Security()      │ │ Compression     │      │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Pydantic Integration Layer                    │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐      │
│  │   Input         │ │   Output        │ │   OpenAPI       │      │
│  │   Validation    │ │   Serialization │ │   Schema        │      │
│  │                 │ │                 │ │   Generation    │      │
│  │ BaseModel       │ │ JSON Response   │ │ Auto Docs       │      │
│  │ Type Checking   │ │ Type Safety     │ │ Swagger UI      │      │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Starlette Framework Layer                    │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐      │
│  │   Routing       │ │   Request/      │ │   WebSocket     │      │
│  │   System        │ │   Response      │ │   Support       │      │
│  │                 │ │   Handling      │ │                 │      │
│  │ URL Routing     │ │ HTTP Methods    │ │ Real-time       │      │
│  │ Path Params     │ │ Status Codes    │ │ Communication   │      │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           ASGI Interface Layer                      │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐      │
│  │   Async         │ │   Protocol      │ │   Server        │      │
│  │   Interface     │ │   Support       │ │   Integration   │      │
│  │                 │ │                 │ │                 │      │
│  │ async/await     │ │ HTTP/1.1        │ │ Uvicorn         │      │
│  │ Coroutines      │ │ HTTP/2          │ │ Hypercorn       │      │
│  │ Event Loop      │ │ WebSockets      │ │ Daphne          │      │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

## Request Flow Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   HTTP Client   │────▶│   ASGI Server   │────▶│   FastAPI App   │
│                 │     │   (Uvicorn)     │     │                 │
│ curl, browser,  │     │                 │     │ Route matching  │
│ requests lib    │     │ HTTP parsing    │     │ Middleware exec │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Response      │◀────│   Pydantic      │◀────│   Dependency    │
│   Serialization │     │   Validation    │     │   Injection     │
│                 │     │                 │     │                 │
│ JSON encoding   │     │ Input/Output    │     │ Security check  │
│ Status codes    │     │ Type checking   │     │ Database conn   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
                                            ┌─────────────────┐
                                            │   Route Handler │
                                            │                 │
                                            │ Business logic  │
                                            │ Data processing │
                                            │ Response return │
                                            └─────────────────┘
```

## Dependency Injection Tree

```
                    ┌─────────────────┐
                    │   Route Handler │
                    │                 │
                    │ @app.get("/")   │
                    └─────────┬───────┘
                              │
                ┌─────────────▼─────────────┐
                │     Dependency Tree       │
                │                           │
                │  ┌─────────────────────┐ │
                │  │  get_current_user   │ │
                │  │                     │ │
                │  │  ┌───────────────┐  │ │
                │  │  │ HTTPBearer    │  │ │
                │  │  └───────────────┘  │ │
                │  │  ┌───────────────┐  │ │
                │  │  │ get_database  │  │ │
                │  │  └───────────────┘  │ │
                │  └─────────────────────┘ │
                │                           │
                │  ┌─────────────────────┐ │
                │  │  require_admin      │ │
                │  │                     │ │
                │  │  ┌───────────────┐  │ │
                │  │  │current_user   │  │ │
                │  │  │(from above)   │  │ │
                │  │  └───────────────┘  │ │
                │  └─────────────────────┘ │
                └───────────────────────────┘
```

## Middleware Execution Order

```
                    ┌─────────────────┐
                    │   HTTP Request  │
                    └─────────┬───────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  CORS Middleware│  ← Added last, executes first
                    └─────────┬───────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Auth Middleware │  ← Added second, executes second
                    └─────────┬───────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Timing Middleware│ ← Added first, executes third
                    └─────────┬───────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Route Handler  │  ← Core application logic
                    └─────────┬───────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ HTTP Response   │  ← Flows back through middleware
                    └─────────────────┘
```

## Type System Integration

```
┌─────────────────────────────────────────────────────────────┐
│                    Python Type Hints                        │
│                                                             │
│  def create_user(user: CreateUserRequest) -> UserResponse: │
│      ...                                                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
      ┌───────────────┼───────────────┐
      │               │               │
      ▼               ▼               ▼
┌────────────┐ ┌────────────┐ ┌────────────┐
│  Pydantic  │ │  OpenAPI   │ │    IDE     │
│ Validation │ │  Schema    │ │  Support   │
│            │ │ Generation │ │            │
│ Runtime    │ │ Auto Docs  │ │ Type Check │
│ Checking   │ │ Examples   │ │ Completion │
└────────────┘ └────────────┘ └────────────┘
```