# =====================================================================
# IMPORTS SECTION
# =====================================================================
# FastAPI core imports for building REST API
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware

# SQLAlchemy imports for database ORM (Object-Relational Mapping)
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

# Pydantic imports for data validation and serialization
from pydantic import BaseModel, EmailStr, Field

# Standard library imports
from datetime import datetime, timedelta
from typing import Optional, List
import enum

# Security imports for password hashing and JWT tokens
from passlib.context import CryptContext
import jwt

# =====================================================================
# DATABASE CONFIGURATION
# =====================================================================
# SQLite database URL - stores data in a local file
SQLALCHEMY_DATABASE_URL = "sqlite:///./financial_planner.db"

# Create database engine with SQLite-specific configuration
# check_same_thread=False allows multiple threads to use the connection
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# Session factory for creating database sessions
# autocommit=False: Manual transaction control
# autoflush=False: Manual flush control
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all database models
Base = declarative_base()

# =====================================================================
# SECURITY CONFIGURATION
# =====================================================================
# Secret key for JWT token encoding (CHANGE THIS IN PRODUCTION!)
SECRET_KEY = "your-secret-key-change-in-production"

# JWT algorithm for token encoding/decoding
ALGORITHM = "HS256"

# Token expiration time in minutes
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
# tokenUrl="token" specifies the login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# =====================================================================
# ENUMS - Define allowed values for specific fields
# =====================================================================

# Category types for expense categorization
class CategoryType(str, enum.Enum):
    FIXED = "fixed"              # Fixed expenses (rent, insurance)
    RECURRING = "recurring"       # Regular recurring expenses
    VARIABLE = "variable"         # Variable expenses (groceries)
    SAVINGS = "savings"           # Savings allocations
    EMERGENCY = "emergency"       # Emergency fund
    DISCRETIONARY = "discretionary"  # Optional spending

# Priority levels for categories
class Priority(str, enum.Enum):
    HIGH = "high"       # High priority expenses
    MEDIUM = "medium"   # Medium priority expenses
    LOW = "low"         # Low priority expenses

# Status of expense transactions
class ExpenseStatus(str, enum.Enum):
    PENDING = "pending"       # Expense pending confirmation
    CONFIRMED = "confirmed"   # Expense confirmed
    REFUNDED = "refunded"     # Expense was refunded

# Payment methods for expenses
class PaymentMethod(str, enum.Enum):
    CASH = "cash"                   # Cash payment
    CARD = "card"                   # Card payment
    MOBILE_WALLET = "mobile_wallet" # Mobile wallet (JazzCash, Easypaisa, etc.)

# =====================================================================
# DATABASE MODELS (SQLAlchemy ORM Models)
# =====================================================================

# User model - stores user account information
class User(Base):
    __tablename__ = "users"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # User credentials and basic info
    email = Column(String, unique=True, index=True)  # Unique email for login
    hashed_password = Column(String)                 # Encrypted password
    full_name = Column(String)                       # User's full name
    phone = Column(String)                           # Phone number
    date_of_birth = Column(DateTime)                 # Date of birth
    
    # Financial information
    monthly_salary = Column(Float)                   # Monthly income
    currency = Column(String, default="PKR")         # Currency (default: Pakistani Rupee)
    
    # Account metadata
    created_at = Column(DateTime, default=datetime.utcnow)  # Account creation timestamp
    is_active = Column(Boolean, default=True)               # Account status
    
    # Relationships - define connections to other tables
    categories = relationship("Category", back_populates="user")  # User's categories
    expenses = relationship("Expense", back_populates="user")     # User's expenses
    budgets = relationship("Budget", back_populates="user")       # User's budgets
    goals = relationship("Goal", back_populates="user")           # User's financial goals

# Category model - stores expense categories
class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))  # Links to User table
    
    # Category details
    name = Column(String)                              # Category name (e.g., "Food", "Transport")
    category_type = Column(SQLEnum(CategoryType))      # Type of category
    priority = Column(SQLEnum(Priority), default=Priority.MEDIUM)  # Priority level
    icon = Column(String)                              # Icon identifier for UI
    color = Column(String)                             # Color code for UI
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="categories")
    expenses = relationship("Expense", back_populates="category")
    budgets = relationship("Budget", back_populates="category")

# Expense model - stores individual expense transactions
class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))      # Links to User
    category_id = Column(Integer, ForeignKey("categories.id"))  # Links to Category
    
    # Expense details
    amount = Column(Float)                                 # Expense amount
    description = Column(String)                           # Description of expense
    merchant = Column(String)                              # Store/vendor name
    payment_method = Column(SQLEnum(PaymentMethod))        # How payment was made
    status = Column(SQLEnum(ExpenseStatus), default=ExpenseStatus.CONFIRMED)
    notes = Column(String)                                 # Additional notes
    location = Column(String)                              # Location of expense
    
    # Flags
    is_recurring = Column(Boolean, default=False)          # Is this a recurring expense?
    is_business = Column(Boolean, default=False)           # Business expense flag
    
    # Timestamps
    expense_date = Column(DateTime, default=datetime.utcnow)  # When expense occurred
    created_at = Column(DateTime, default=datetime.utcnow)    # When record was created
    
    # Relationships
    user = relationship("User", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")

# Budget model - stores monthly budget allocations per category
class Budget(Base):
    __tablename__ = "budgets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    
    # Budget details
    amount = Column(Float)                        # Budget amount for category
    percentage = Column(Float)                    # Percentage of total budget
    rollover_enabled = Column(Boolean, default=False)  # Allow unused budget to rollover?
    
    # Time period
    month = Column(Integer)                       # Month (1-12)
    year = Column(Integer)                        # Year
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")

# Goal model - stores financial goals (savings targets)
class Goal(Base):
    __tablename__ = "goals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Goal details
    name = Column(String)                         # Goal name (e.g., "New Car")
    target_amount = Column(Float)                 # Target amount to save
    current_amount = Column(Float, default=0)     # Amount saved so far
    deadline = Column(DateTime)                   # Target completion date
    is_completed = Column(Boolean, default=False) # Goal completion status
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="goals")

# =====================================================================
# PYDANTIC MODELS (Request/Response Schemas)
# Purpose: Validate incoming data and serialize outgoing data
# =====================================================================

# User registration schema
class UserCreate(BaseModel):
    email: EmailStr                      # Validated email format
    password: str                        # Plain text password (will be hashed)
    full_name: str
    phone: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    monthly_salary: Optional[float] = None
    currency: str = "PKR"

# User response schema (returned to client)
class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    phone: Optional[str]
    monthly_salary: Optional[float]
    currency: str
    created_at: datetime
    
    class Config:
        from_attributes = True  # Allow creation from ORM models

# Category creation schema
class CategoryCreate(BaseModel):
    name: str
    category_type: CategoryType
    priority: Priority = Priority.MEDIUM
    icon: Optional[str] = None
    color: Optional[str] = None

# Category response schema
class CategoryResponse(BaseModel):
    id: int
    name: str
    category_type: CategoryType
    priority: Priority
    icon: Optional[str]
    color: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Expense creation schema
class ExpenseCreate(BaseModel):
    category_id: int
    amount: float
    description: str
    merchant: Optional[str] = None
    payment_method: PaymentMethod
    notes: Optional[str] = None
    location: Optional[str] = None
    is_recurring: bool = False
    is_business: bool = False
    expense_date: Optional[datetime] = None

# Expense response schema
class ExpenseResponse(BaseModel):
    id: int
    category_id: int
    amount: float
    description: str
    merchant: Optional[str]
    payment_method: PaymentMethod
    status: ExpenseStatus
    notes: Optional[str]
    expense_date: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

# Budget creation schema
class BudgetCreate(BaseModel):
    category_id: int
    amount: float
    percentage: Optional[float] = None
    rollover_enabled: bool = False
    month: int                    # 1-12
    year: int                     # e.g., 2024

# Budget response schema with calculated fields
class BudgetResponse(BaseModel):
    id: int
    category_id: int
    amount: float
    percentage: Optional[float]
    rollover_enabled: bool
    month: int
    year: int
    spent: float = 0              # Calculated: total spent in category
    remaining: float = 0          # Calculated: budget - spent
    
    class Config:
        from_attributes = True

# Goal creation schema
class GoalCreate(BaseModel):
    name: str
    target_amount: float
    deadline: datetime

# Goal response schema with calculated fields
class GoalResponse(BaseModel):
    id: int
    name: str
    target_amount: float
    current_amount: float
    deadline: datetime
    is_completed: bool
    progress_percentage: float = 0  # Calculated: (current/target) * 100
    
    class Config:
        from_attributes = True

# JWT token response schema
class Token(BaseModel):
    access_token: str
    token_type: str

# Dashboard statistics schema
class DashboardStats(BaseModel):
    total_income: float                      # User's monthly income
    total_expenses: float                    # Sum of all expenses this month
    total_budget: float                      # Sum of all budgets
    budget_used_percentage: float            # (expenses/budget) * 100
    savings_rate: float                      # ((income-expenses)/income) * 100
    top_categories: List[dict]               # Top 5 spending categories
    recent_expenses: List[ExpenseResponse]   # Last 10 expenses

# =====================================================================
# DATABASE INITIALIZATION
# Purpose: Create all tables in the database
# =====================================================================
Base.metadata.create_all(bind=engine)

# =====================================================================
# FASTAPI APPLICATION SETUP
# =====================================================================
app = FastAPI(
    title="Financial Planner API",
    version="1.0.0",
    description="Personal finance management API"
)

# CORS middleware - allows frontend from different origins to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allow all origins (restrict in production!)
    allow_credentials=True,       # Allow cookies
    allow_methods=["*"],          # Allow all HTTP methods
    allow_headers=["*"],          # Allow all headers
)

# =====================================================================
# DEPENDENCY FUNCTIONS
# Purpose: Reusable functions injected into route handlers
# =====================================================================

# Database session dependency
# Purpose: Provide database session to each request, ensure cleanup
def get_db():
    db = SessionLocal()
    try:
        yield db  # Provide session to route handler
    finally:
        db.close()  # Always close session after request

# =====================================================================
# AUTHENTICATION UTILITY FUNCTIONS
# =====================================================================

# Verify password against hashed password
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Hash a plain text password
def get_password_hash(password):
    return pwd_context.hash(password)

# Create JWT access token
# Purpose: Generate token for authenticated sessions
def create_access_token(data: dict):
    to_encode = data.copy()
    # Set expiration time
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # Encode and return token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Get current authenticated user from token
# Purpose: Validate token and return user object
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # Exception for invalid credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    # Find user in database
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user

# =====================================================================
# API ENDPOINTS
# =====================================================================

# Root endpoint - API health check
@app.get("/")
def read_root():
    return {"message": "Financial Planner API 🚀", "version": "1.0.0"}

# =====================================================================
# AUTHENTICATION ENDPOINTS
# =====================================================================

# User registration endpoint
# Purpose: Create new user account
@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = get_password_hash(user.password)
    
    # Create new user
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        phone=user.phone,
        date_of_birth=user.date_of_birth,
        monthly_salary=user.monthly_salary,
        currency=user.currency
    )
    
    # Save to database
    db.add(db_user)
    db.commit()
    db.refresh(db_user)  # Refresh to get generated ID
    
    return db_user

# Login endpoint
# Purpose: Authenticate user and return JWT token
@app.post("/token", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Find user by email (username field in OAuth2 form)
    user = db.query(User).filter(User.email == form_data.username).first()
    
    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# Get current user profile
# Purpose: Return authenticated user's information
@app.get("/users/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# Update user profile
# Purpose: Allow user to update their profile information
@app.put("/users/me", response_model=UserResponse)
def update_user(
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
    monthly_salary: Optional[float] = None,
    currency: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Update only provided fields
    if full_name:
        current_user.full_name = full_name
    if phone:
        current_user.phone = phone
    if monthly_salary is not None:  # Allow 0 as valid value
        current_user.monthly_salary = monthly_salary
    if currency:
        current_user.currency = currency
    
    # Save changes
    db.commit()
    db.refresh(current_user)
    return current_user

# =====================================================================
# CATEGORY ENDPOINTS
# Purpose: Manage expense categories
# =====================================================================

# Create new category
@app.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Create category linked to current user
    db_category = Category(**category.dict(), user_id=current_user.id)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

# Get all categories for current user
@app.get("/categories", response_model=List[CategoryResponse])
def get_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Category).filter(Category.user_id == current_user.id).all()

# Get specific category
@app.get("/categories/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find category belonging to current user
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return category

# Update category
@app.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_update: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find category
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Update all fields
    for key, value in category_update.dict().items():
        setattr(category, key, value)
    
    db.commit()
    db.refresh(category)
    return category

# Delete category
@app.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find category
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Delete category
    db.delete(category)
    db.commit()
    return {"message": "Category deleted successfully"}

# =====================================================================
# EXPENSE ENDPOINTS
# Purpose: Manage expense transactions
# =====================================================================

# Create new expense
@app.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    expense: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify category exists and belongs to user
    category = db.query(Category).filter(
        Category.id == expense.category_id,
        Category.user_id == current_user.id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Prepare expense data
    expense_data = expense.dict()
    
    # Set expense_date to now if not provided
    if not expense_data.get('expense_date'):
        expense_data['expense_date'] = datetime.utcnow()
    
    # Create expense
    db_expense = Expense(**expense_data, user_id=current_user.id)
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    
    return db_expense

# Get expenses with filtering
@app.get("/expenses", response_model=List[ExpenseResponse])
def get_expenses(
    skip: int = 0,                          # Pagination offset
    limit: int = 100,                       # Pagination limit
    category_id: Optional[int] = None,      # Filter by category
    start_date: Optional[datetime] = None,  # Filter by date range
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Base query
    query = db.query(Expense).filter(Expense.user_id == current_user.id)
    
    # Apply filters
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    
    # Order by date (newest first) and paginate
    return query.order_by(Expense.expense_date.desc()).offset(skip).limit(limit).all()

# Get specific expense
@app.get("/expenses/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user.id
    ).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    return expense

# Update expense
@app.put("/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: int,
    expense_update: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find expense
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user.id
    ).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Update only provided fields (exclude_unset=True)
    for key, value in expense_update.dict(exclude_unset=True).items():
        setattr(expense, key, value)
    
    db.commit()
    db.refresh(expense)
    return expense

# Delete expense
@app.delete("/expenses/{expense_id}")
def delete_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user.id
    ).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    db.delete(expense)
    db.commit()
    return {"message": "Expense deleted successfully"}

# =====================================================================
# BUDGET ENDPOINTS
# Purpose: Manage monthly budgets
# =====================================================================

# Create new budget
@app.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify category exists
    category = db.query(Category).filter(
        Category.id == budget.category_id,
        Category.user_id == current_user.id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Create budget
    db_budget = Budget(**budget.dict(), user_id=current_user.id)
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    
    return db_budget

# Get budgets with spending calculations
@app.get("/budgets", response_model=List[BudgetResponse])
def get_budgets(
    month: Optional[int] = None,  # Filter by month
    year: Optional[int] = None,   # Filter by year
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Base query
    query = db.query(Budget).filter(Budget.user_id == current_user.id)
    
    # Apply filters
    if month:
        query = query.filter(Budget.month == month)
    if year:
        query = query.filter(Budget.year == year)
    
    budgets = query.all()
    
    # Calculate spending for each budget
    for budget in budgets:
        # Get all expenses for this category
        expenses = db.query(Expense).filter(
            Expense.user_id == current_user.id,
            Expense.category_id == budget.category_id
        ).all()
        
        # Filter by month/year if specified
        if month and year:
            expenses = [
                e for e in expenses 
                if e.expense_date.month == month and e.expense_date.year == year
            ]
        
        # Calculate totals
        budget.spent = sum(e.amount for e in expenses)
        budget.remaining = budget.amount - budget.spent
    
    return budgets

# =====================================================================
# GOAL ENDPOINTS
# Purpose: Manage financial goals
# =====================================================================

# Create new goal
@app.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(
    goal: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_goal = Goal(**goal.dict(), user_id=current_user.id)
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return db_goal

# Get all goals with progress calculation
@app.get("/goals", response_model=List[GoalResponse])
def get_goals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    goals = db.query(Goal).filter(Goal.user_id == current_user.id).all()
    
    # Calculate progress percentage for each goal
    for goal in goals:
        if goal.target_amount > 0:
            goal.progress_percentage = (goal.current_amount / goal.target_amount) * 100
        else:
            goal.progress_percentage = 0
    
    return goals

# Add amount to goal
# Purpose: Track progress towards goal
@app.put("/goals/{goal_id}/add-amount")
def add_goal_amount(
    goal_id: int,
    amount: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find goal
    goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Add amount to current total
    goal.current_amount += amount
    
    # Check if goal is completed
    if goal.current_amount >= goal.target_amount:
        goal.is_completed = True
    
    db.commit()
    db.refresh(goal)
    return goal

# =====================================================================
# DASHBOARD ENDPOINT
# Purpose: Provide overview statistics and insights
# =====================================================================
@app.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get current month and year
    now = datetime.utcnow()
    month = now.month
    year = now.year
    
    # Get all expenses for current month
    expenses = db.query(Expense).filter(
        Expense.user_id == current_user.id,
        Expense.expense_date >= datetime(year, month, 1)
    ).all()
    
    # Calculate total expenses
    total_expenses = sum(e.amount for e in expenses)
    
    # Get user's monthly income
    total_income = current_user.monthly_salary or 0
    
    # Get all budgets for current month
    budgets = db.query(Budget).filter(
        Budget.user_id == current_user.id,
        Budget.month == month,
        Budget.year == year
    ).all()
    
    # Calculate total budget
    total_budget = sum(b.amount for b in budgets)
    
    # Calculate budget usage percentage
    budget_used = (total_expenses / total_budget * 100) if total_budget > 0 else 0
    
    # Calculate savings rate
    savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0
    
    # Calculate spending by category
    category_spending = {}
    for expense in expenses:
        category_id = expense.category_id
        if category_id not in category_spending:
            # Get category name
            category = db.query(Category).filter(Category.id == category_id).first()
            category_spending[category_id] = {
                "category_name": category.name if category else "Unknown",
                "amount": 0
            }
        # Add expense amount to category total
        category_spending[category_id]["amount"] += expense.amount
    
    # Get top 5 spending categories
    top_categories = sorted(
        category_spending.values(),
        key=lambda x: x["amount"],
        reverse=True
    )[:5]
    
    # Get 10 most recent expenses
    recent_expenses = sorted(expenses, key=lambda x: x.expense_date, reverse=True)[:10]
    
    # Return dashboard statistics
    return DashboardStats(
        total_income=total_income,
        total_expenses=total_expenses,
        total_budget=total_budget,
        budget_used_percentage=budget_used,
        savings_rate=savings_rate,
        top_categories=top_categories,
        recent_expenses=recent_expenses
    )

# =====================================================================
# APPLICATION ENTRY POINT
# Purpose: Run the API server when script is executed directly
# =====================================================================
if __name__ == "__main__":
    import uvicorn
    # Run server on all network interfaces, port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
