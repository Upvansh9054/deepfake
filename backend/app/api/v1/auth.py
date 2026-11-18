from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, decode_token, security
from app.core.rate_limiter import login_rate_limiter
from app.models.entities import User, AuditLog
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token, UserUpdate
from typing import Optional, List

router = APIRouter()

def require_roles(allowed_roles: List[str]):
    """Role-based authorization dependency factory."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: role '{current_user.role}' lacks permission. Required: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker

async def get_current_user(
    credentials: Optional[object] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency that authenticates JWT token and yields the User object."""
    if not credentials or not hasattr(credentials, "credentials"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    return user

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Registers a new user account."""
    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_in.email.lower().strip()))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists"
        )
    
    hashed_pw = get_password_hash(user_in.password)
    user = User(
        email=user_in.email.lower().strip(),
        hashed_password=hashed_pw,
        full_name=user_in.full_name.strip(),
        role=user_in.role or "user",
        is_active=True
    )
    db.add(user)
    await db.flush()

    # Log audit
    audit = AuditLog(
        user_id=user.id,
        action="user_registered",
        resource_type="user",
        resource_id=user.id,
        details={"email": user.email, "role": user.role}
    )
    db.add(audit)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(data={"sub": user.id, "email": user.email, "role": user.role})
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.post("/login", response_model=Token, dependencies=[Depends(login_rate_limiter)])
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticates user with email and password and returns access token."""
    email_clean = credentials.email.lower().strip()
    result = await db.execute(select(User).where(User.email == email_clean))
    user = result.scalars().first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact security administrator."
        )

    # Log audit
    audit = AuditLog(
        user_id=user.id,
        action="user_logged_in",
        resource_type="user",
        resource_id=user.id,
        details={"email": user.email}
    )
    db.add(audit)
    await db.commit()

    access_token = create_access_token(data={"sub": user.id, "email": user.email, "role": user.role})
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Fetches currently authenticated user."""
    return UserResponse.model_validate(current_user)

@router.put("/me", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Updates user profile information."""
    if user_update.full_name:
        current_user.full_name = user_update.full_name.strip()
    if user_update.password:
        current_user.hashed_password = get_password_hash(user_update.password)
    
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)

