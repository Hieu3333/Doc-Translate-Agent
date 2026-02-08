from fastapi import APIRouter, HTTPException, status
from core.schemas.user import UserSignUp, UserLogin, UserResponse, LoginResponse
from core.database import get_supabase_client
from core.auth import hash_password, verify_password, create_access_token
import uuid

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignUp):
    """Register a new user"""
    supabase = get_supabase_client()
    
    # Check if user already exists
    try:
        response = supabase.table("users").select("id").eq("email", user_data.email).execute()
        if response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    except Exception as e:
        if "does not exist" not in str(e):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error during signup"
            )
    
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Create new user
    user_id = str(uuid.uuid4())
    try:
        response = supabase.table("users").insert({
            "id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "password": hashed_password,
            "created_at": "now()"
        }).execute()
        
        if response.data:
            user = response.data[0]
            return UserResponse(
                id=user["id"],
                username=user["username"],
                email=user["email"],
                created_at=user["created_at"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )

@router.post("/login", response_model=LoginResponse)
async def login(credentials: UserLogin):
    """Login user and return access token"""
    supabase = get_supabase_client()
    
    # Find user by email
    try:
        response = supabase.table("users").select("*").eq("email", credentials.email).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user = response.data[0]
        
        # Verify password
        if not verify_password(credentials.password, user["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": user["id"], "email": user["email"]})
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user["id"],
                username=user["username"],
                email=user["email"],
                created_at=user["created_at"]
            )
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during login: {str(e)}"
        )
