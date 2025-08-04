"""
FastAPI Architecture Analysis - Code Examples
Demonstrating core architectural components and design patterns
"""

import asyncio
import time
from typing import Dict, List, Optional, Union
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, Depends, HTTPException, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator, ValidationError
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


# ============================================================================
# 1. PYDANTIC MODELS - TYPE SAFETY AND VALIDATION
# ============================================================================

class UserRole(str, Enum):
    """Enum for user roles - demonstrates type safety"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class User(BaseModel):
    """Pydantic model demonstrating advanced validation features"""
    id: int = Field(..., gt=0, description="User ID must be positive")
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    role: UserRole = UserRole.USER
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Union[str, int]]] = None
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty or only whitespace')
        return v.strip()
    
    class Config:
        # Enable automatic schema generation with examples
        schema_extra = {
            "example": {
                "id": 1,
                "name": "John Doe",
                "email": "john@example.com",
                "role": "user",
                "metadata": {"department": "engineering", "level": 3}
            }
        }


class CreateUserRequest(BaseModel):
    """Request model for user creation"""
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    role: UserRole = UserRole.USER
    metadata: Optional[Dict[str, Union[str, int]]] = None


class UserResponse(BaseModel):
    """Response model with computed fields"""
    id: int
    name: str
    email: str
    role: UserRole
    created_at: datetime
    display_name: str
    
    @classmethod
    def from_user(cls, user: User):
        """Factory method demonstrating response transformation"""
        return cls(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
            display_name=f"{user.name} ({user.role.value})"
        )


# ============================================================================
# 2. DEPENDENCY INJECTION SYSTEM
# ============================================================================

# Database simulation
fake_db: Dict[int, User] = {}
current_id = 1


def get_db():
    """Database dependency - could be real DB connection"""
    return fake_db


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Dict[int, User] = Depends(get_db)
) -> User:
    """Authentication dependency - demonstrates nested dependencies"""
    # Simulate token validation
    if not credentials.credentials == "valid-token":
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Return mock user (in real app, decode token and fetch from DB)
    user_id = 1
    if user_id not in db:
        # Create a default user if none exists
        db[user_id] = User(
            id=user_id,
            name="Admin User",
            email="admin@example.com",
            role=UserRole.ADMIN
        )
    
    return db[user_id]


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Authorization dependency - demonstrates dependency chaining"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


class PaginationParams:
    """Dependency class for pagination"""
    def __init__(self, skip: int = 0, limit: int = 100):
        self.skip = max(0, skip)
        self.limit = min(limit, 1000)  # Cap at 1000


# ============================================================================
# 3. MIDDLEWARE SYSTEM
# ============================================================================

class TimingMiddleware(BaseHTTPMiddleware):
    """Custom middleware to measure request processing time"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request logging"""
    
    async def dispatch(self, request: Request, call_next):
        print(f"Request: {request.method} {request.url}")
        response = await call_next(request)
        print(f"Response: {response.status_code}")
        return response


# ============================================================================
# 4. FASTAPI APPLICATION WITH ADVANCED FEATURES
# ============================================================================

app = FastAPI(
    title="FastAPI Architecture Demo",
    description="Comprehensive demonstration of FastAPI's architectural features",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add middleware (order matters - last added is executed first)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TimingMiddleware)
app.add_middleware(RequestLoggingMiddleware)


# ============================================================================
# 5. ROUTE HANDLERS WITH DEPENDENCY INJECTION
# ============================================================================

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint demonstrating basic response"""
    return {"message": "FastAPI Architecture Demo", "version": "1.0.0"}


@app.post("/users/", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: CreateUserRequest,
    db: Dict[int, User] = Depends(get_db),
    current_user: User = Depends(require_admin),  # Only admins can create users
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> UserResponse:
    """Create user endpoint demonstrating dependency injection and background tasks"""
    global current_id
    
    # Create new user
    new_user = User(
        id=current_id,
        name=user_data.name,
        email=user_data.email,
        role=user_data.role,
        metadata=user_data.metadata
    )
    
    db[current_id] = new_user
    current_id += 1
    
    # Add background task (e.g., send welcome email)
    background_tasks.add_task(send_welcome_email, new_user.email)
    
    return UserResponse.from_user(new_user)


@app.get("/users/", response_model=List[UserResponse])
async def list_users(
    pagination: PaginationParams = Depends(PaginationParams),
    db: Dict[int, User] = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[UserResponse]:
    """List users with pagination"""
    users = list(db.values())
    paginated_users = users[pagination.skip:pagination.skip + pagination.limit]
    return [UserResponse.from_user(user) for user in paginated_users]


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Dict[int, User] = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Get specific user by ID"""
    if user_id not in db:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse.from_user(db[user_id])


@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: CreateUserRequest,
    db: Dict[int, User] = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> UserResponse:
    """Update user (admin only)"""
    if user_id not in db:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user fields
    user = db[user_id]
    user.name = user_data.name
    user.email = user_data.email
    user.role = user_data.role
    if user_data.metadata:
        user.metadata = user_data.metadata
    
    return UserResponse.from_user(user)


@app.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: Dict[int, User] = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete user (admin only)"""
    if user_id not in db:
        raise HTTPException(status_code=404, detail="User not found")
    
    del db[user_id]
    return Response(status_code=204)


# ============================================================================
# 6. ADVANCED FEATURES
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime": "available"
    }


@app.get("/metrics")
async def get_metrics(current_user: User = Depends(require_admin)):
    """Metrics endpoint (admin only)"""
    db = get_db()
    return {
        "total_users": len(db),
        "user_roles": {
            role.value: sum(1 for user in db.values() if user.role == role)
            for role in UserRole
        },
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# 7. ERROR HANDLING
# ============================================================================

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Custom exception handler for Pydantic validation errors"""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation Error",
            "errors": exc.errors()
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": str(hash(str(request.url))),
            "timestamp": datetime.now().isoformat()
        }
    )


# ============================================================================
# 8. BACKGROUND TASKS
# ============================================================================

async def send_welcome_email(email: str):
    """Simulate sending welcome email"""
    print(f"Sending welcome email to {email}")
    await asyncio.sleep(1)  # Simulate async operation
    print(f"Welcome email sent to {email}")


# ============================================================================
# 9. WEBSOCKET SUPPORT (ASGI Feature)
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket):
    """WebSocket endpoint demonstrating real-time communication"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


# ============================================================================
# 10. STARTUP AND SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    print("FastAPI application starting up...")
    # Initialize database, load configuration, etc.
    global fake_db, current_id
    if not fake_db:
        # Create initial admin user
        admin_user = User(
            id=1,
            name="Admin",
            email="admin@example.com", 
            role=UserRole.ADMIN
        )
        fake_db[1] = admin_user
        current_id = 2
    print("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    print("FastAPI application shutting down...")
    # Close database connections, cleanup resources, etc.
    print("Application shutdown complete")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)