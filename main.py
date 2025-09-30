from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta
from typing import Optional, List
from passlib.context import CryptContext
import jwt
import enum

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./financial_planner.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Security
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Enums
class CategoryType(str, enum.Enum):
    FIXED = "fixed"
    RECURRING = "recurring"
    VARIABLE = "variable"
    SAVINGS = "savings"
    EMERGENCY = "emergency"
    DISCRETIONARY = "discretionary"

class Priority(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ExpenseStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REFUNDED = "refunded"

class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    MOBILE_WALLET = "mobile_wallet"

# Database Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    phone = Column(String)
    date_of_birth = Column(DateTime)
    monthly_salary = Column(Float)
    currency = Column(String, default="PKR")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    categories = relationship("Category", back_populates="user")
    expenses = relationship("Expense", back_populates="user")
    budgets = relationship("Budget", back_populates="user")
    goals = relationship("Goal", back_populates="user")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    category_type = Column(SQLEnum(CategoryType))
    priority = Column(SQLEnum(Priority), default=Priority.MEDIUM)
    icon = Column(String)
    color = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="categories")
    expenses = relationship("Expense", back_populates="category")
    budgets = relationship("Budget", back_populates="category")

class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    amount = Column(Float)
    description = Column(String)
    merchant = Column(String)
    payment_method = Column(SQLEnum(PaymentMethod))
    status = Column(SQLEnum(ExpenseStatus), default=ExpenseStatus.CONFIRMED)
    notes = Column(String)
    location = Column(String)
    is_recurring = Column(Boolean, default=False)
    is_business = Column(Boolean, default=False)
    expense_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")

class Budget(Base):
    __tablename__ = "budgets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    amount = Column(Float)
    percentage = Column(Float)
    rollover_enabled = Column(Boolean, default=False)
    month = Column(Integer)
    year = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")

class Goal(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    target_amount = Column(Float)
    current_amount = Column(Float, default=0)
    deadline = Column(DateTime)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="goals")

# Pydantic Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    monthly_salary: Optional[float] = None
    currency: str = "PKR"

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    phone: Optional[str]
    monthly_salary: Optional[float]
    currency: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class CategoryCreate(BaseModel):
    name: str
    category_type: CategoryType
    priority: Priority = Priority.MEDIUM
    icon: Optional[str] = None
    color: Optional[str] = None

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

class BudgetCreate(BaseModel):
    category_id: int
    amount: float
    percentage: Optional[float] = None
    rollover_enabled: bool = False
    month: int
    year: int

class BudgetResponse(BaseModel):
    id: int
    category_id: int
    amount: float
    percentage: Optional[float]
    rollover_enabled: bool
    month: int
    year: int
    spent: float = 0
    remaining: float = 0
    
    class Config:
        from_attributes = True

class GoalCreate(BaseModel):
    name: str
    target_amount: float
    deadline: datetime

class GoalResponse(BaseModel):
    id: int
    name: str
    target_amount: float
    current_amount: float
    deadline: datetime
    is_completed: bool
    progress_percentage: float = 0
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class DashboardStats(BaseModel):
    total_income: float
    total_expenses: float
    total_budget: float
    budget_used_percentage: float
    savings_rate: float
    top_categories: List[dict]
    recent_expenses: List[ExpenseResponse]

# Initialize database
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(title="Financial Planner API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Auth utilities
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# API Endpoints

@app.get("/")
def read_root():
    return {"message": "Financial Planner API 🚀", "version": "1.0.0"}

# Authentication
@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        phone=user.phone,
        date_of_birth=user.date_of_birth,
        monthly_salary=user.monthly_salary,
        currency=user.currency
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.put("/users/me", response_model=UserResponse)
def update_user(
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
    monthly_salary: Optional[float] = None,
    currency: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if full_name:
        current_user.full_name = full_name
    if phone:
        current_user.phone = phone
    if monthly_salary:
        current_user.monthly_salary = monthly_salary
    if currency:
        current_user.currency = currency
    
    db.commit()
    db.refresh(current_user)
    return current_user

# Categories
@app.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_category = Category(**category.dict(), user_id=current_user.id)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@app.get("/categories", response_model=List[CategoryResponse])
def get_categories(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Category).filter(Category.user_id == current_user.id).all()

@app.get("/categories/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@app.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_update: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    for key, value in category_update.dict().items():
        setattr(category, key, value)
    
    db.commit()
    db.refresh(category)
    return category

@app.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db.delete(category)
    db.commit()
    return {"message": "Category deleted successfully"}

# Expenses
@app.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    expense: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(
        Category.id == expense.category_id,
        Category.user_id == current_user.id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    expense_data = expense.dict()
    if not expense_data.get('expense_date'):
        expense_data['expense_date'] = datetime.utcnow()
    
    db_expense = Expense(**expense_data, user_id=current_user.id)
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

@app.get("/expenses", response_model=List[ExpenseResponse])
def get_expenses(
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Expense).filter(Expense.user_id == current_user.id)
    
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    
    return query.order_by(Expense.expense_date.desc()).offset(skip).limit(limit).all()

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

@app.put("/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: int,
    expense_update: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user.id
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    for key, value in expense_update.dict(exclude_unset=True).items():
        setattr(expense, key, value)
    
    db.commit()
    db.refresh(expense)
    return expense

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

# Budgets
@app.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(
        Category.id == budget.category_id,
        Category.user_id == current_user.id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db_budget = Budget(**budget.dict(), user_id=current_user.id)
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget

@app.get("/budgets", response_model=List[BudgetResponse])
def get_budgets(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Budget).filter(Budget.user_id == current_user.id)
    
    if month:
        query = query.filter(Budget.month == month)
    if year:
        query = query.filter(Budget.year == year)
    
    budgets = query.all()
    
    for budget in budgets:
        expenses = db.query(Expense).filter(
            Expense.user_id == current_user.id,
            Expense.category_id == budget.category_id
        ).all()
        
        if month and year:
            expenses = [e for e in expenses if e.expense_date.month == month and e.expense_date.year == year]
        
        budget.spent = sum(e.amount for e in expenses)
        budget.remaining = budget.amount - budget.spent
    
    return budgets

# Goals
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

@app.get("/goals", response_model=List[GoalResponse])
def get_goals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goals = db.query(Goal).filter(Goal.user_id == current_user.id).all()
    
    for goal in goals:
        if goal.target_amount > 0:
            goal.progress_percentage = (goal.current_amount / goal.target_amount) * 100
        else:
            goal.progress_percentage = 0
    
    return goals

@app.put("/goals/{goal_id}/add-amount")
def add_goal_amount(
    goal_id: int,
    amount: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id
    ).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    goal.current_amount += amount
    if goal.current_amount >= goal.target_amount:
        goal.is_completed = True
    
    db.commit()
    db.refresh(goal)
    return goal

# Dashboard
@app.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    now = datetime.utcnow()
    month = now.month
    year = now.year
    
    expenses = db.query(Expense).filter(
        Expense.user_id == current_user.id,
        Expense.expense_date >= datetime(year, month, 1)
    ).all()
    
    total_expenses = sum(e.amount for e in expenses)
    total_income = current_user.monthly_salary or 0
    
    budgets = db.query(Budget).filter(
        Budget.user_id == current_user.id,
        Budget.month == month,
        Budget.year == year
    ).all()
    total_budget = sum(b.amount for b in budgets)
    
    budget_used = (total_expenses / total_budget * 100) if total_budget > 0 else 0
    savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0
    
    category_spending = {}
    for expense in expenses:
        category_id = expense.category_id
        if category_id not in category_spending:
            category = db.query(Category).filter(Category.id == category_id).first()
            category_spending[category_id] = {
                "category_name": category.name if category else "Unknown",
                "amount": 0
            }
        category_spending[category_id]["amount"] += expense.amount
    
    top_categories = sorted(
        category_spending.values(),
        key=lambda x: x["amount"],
        reverse=True
    )[:5]
    
    recent_expenses = sorted(expenses, key=lambda x: x.expense_date, reverse=True)[:10]
    
    return DashboardStats(
        total_income=total_income,
        total_expenses=total_expenses,
        total_budget=total_budget,
        budget_used_percentage=budget_used,
        savings_rate=savings_rate,
        top_categories=top_categories,
        recent_expenses=recent_expenses
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
