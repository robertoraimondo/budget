# Author: Roberto Raimondo - IS Senior Systems Engineer II
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import os
from bank_lookup import lookup_bank_by_routing, get_bank_suggestions, validate_routing_number

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///budget.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

db = SQLAlchemy(app)

# Make datetime and current_user available in all templates
@app.context_processor
def inject_datetime():
    return {'datetime': datetime, 'date': date, 'current_user': current_user}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    accounts = db.relationship('Account', backref='user', lazy=True)
    categories = db.relationship('Category', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # income, expense, investment
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Add unique constraint per user
    __table_args__ = (db.UniqueConstraint('name', 'user_id', name='unique_category_per_user'),)
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(50), nullable=False)  # checking, savings, investment, credit
    balance = db.Column(db.Float, default=0.0)
    bank_name = db.Column(db.String(100), nullable=True)  # Bank name from routing lookup
    routing_number = db.Column(db.String(9), nullable=True)  # Bank routing number
    account_number = db.Column(db.String(255), nullable=True)  # Full account number (encrypted)
    account_number_last4 = db.Column(db.String(4), nullable=True)  # Last 4 digits for security
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def set_account_number(self, account_number):
        """Set account number and automatically extract last 4 digits"""
        if account_number:
            # Store the full account number (in production, this should be encrypted)
            self.account_number = account_number
            # Extract last 4 digits
            clean_number = ''.join(filter(str.isdigit, account_number))
            if len(clean_number) >= 4:
                self.account_number_last4 = clean_number[-4:]
            else:
                self.account_number_last4 = clean_number
    
    def get_masked_account_number(self):
        """Return masked account number for display purposes"""
        if not self.account_number:
            return None
        clean_number = ''.join(filter(str.isdigit, self.account_number))
        if len(clean_number) <= 4:
            return '*' * len(clean_number)
        else:
            mask_length = len(clean_number) - 4
            return '*' * mask_length + clean_number[-4:]
    
    def __repr__(self):
        return f'<Account {self.name}>'

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # income, expense, transfer
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    
    category = db.relationship('Category', backref=db.backref('transactions', lazy=True))
    account = db.relationship('Account', backref=db.backref('transactions', lazy=True))
    
    def __repr__(self):
        return f'<Transaction {self.description}: ${self.amount}>'

class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    shares = db.Column(db.Float, nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=True)
    purchase_date = db.Column(db.Date, nullable=False, default=date.today)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    
    account = db.relationship('Account', backref=db.backref('investments', lazy=True))
    
    @property
    def total_value(self):
        return self.shares * (self.current_price or self.purchase_price)
    
    @property
    def gain_loss(self):
        return (self.current_price or self.purchase_price - self.purchase_price) * self.shares
    
    def __repr__(self):
        return f'<Investment {self.symbol}: {self.shares} shares>'

class MonthlyBudget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    
    # Budget amounts
    budgeted_income = db.Column(db.Float, nullable=False, default=0.0)
    budgeted_expenses = db.Column(db.Float, nullable=False, default=0.0)
    
    # Calculated field for net budget (income - expenses)
    @property
    def budgeted_net(self):
        return self.budgeted_income - self.budgeted_expenses
    
    user = db.relationship('User', backref=db.backref('monthly_budgets', lazy=True))
    
    def __repr__(self):
        return f'<MonthlyBudget {self.month}/{self.year}: Income ${self.budgeted_income} - Expenses ${self.budgeted_expenses} = Net ${self.budgeted_net}>'

# Authentication Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'error')
            return render_template('register.html')
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Create default categories for new user
        default_categories = [
            Category(name='Salary', type='income', user_id=user.id),
            Category(name='Freelance', type='income', user_id=user.id),
            Category(name='Groceries', type='expense', user_id=user.id),
            Category(name='Rent', type='expense', user_id=user.id),
            Category(name='Utilities', type='expense', user_id=user.id),
            Category(name='Transportation', type='expense', user_id=user.id),
            Category(name='Entertainment', type='expense', user_id=user.id),
            Category(name='Healthcare', type='expense', user_id=user.id),
            Category(name='Stocks', type='investment', user_id=user.id),
            Category(name='Bonds', type='investment', user_id=user.id),
        ]
        
        for category in default_categories:
            db.session.add(category)
        
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'error')
    
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    print(f"Logout called by user: {current_user.username}")  # Debug line
    logout_user()
    session.clear()  # Clear all session data
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

# Main Routes
@app.route('/')
@login_required
def dashboard():
    try:
        # Get summary statistics for current user
        total_accounts = Account.query.filter_by(user_id=current_user.id).count()
        total_balance = db.session.query(db.func.sum(Account.balance)).filter(Account.user_id == current_user.id).scalar() or 0
        
        recent_transactions = Transaction.query.join(Account).filter(Account.user_id == current_user.id).order_by(Transaction.date.desc()).limit(5).all()
        
        # Monthly spending by category for current user
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        monthly_expenses = db.session.query(
            Category.name, 
            db.func.sum(Transaction.amount)
        ).join(Transaction).join(Account).filter(
            Transaction.type == 'expense',
            db.extract('month', Transaction.date) == current_month,
            db.extract('year', Transaction.date) == current_year,
            Account.user_id == current_user.id
        ).group_by(Category.name).all()
        
        return render_template('dashboard.html',
                             total_accounts=total_accounts,
                             total_balance=total_balance,
                             recent_transactions=recent_transactions,
                             monthly_expenses=monthly_expenses)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Database error in dashboard: {e}")
        print(f"Full traceback: {error_details}")
        flash(f'Database error detected: {str(e)}. Please reset the database if this persists.', 'error')
        # Return a basic dashboard with error message
        return render_template('dashboard.html', 
                             total_accounts=0, 
                             total_balance=0, 
                             recent_transactions=[], 
                             monthly_expenses=[])

@app.route('/accounts')
@login_required
def accounts():
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    return render_template('accounts.html', accounts=accounts)

@app.route('/accounts/add', methods=['GET', 'POST'])
@login_required
def add_account():
    if request.method == 'POST':
        name = request.form['name']
        account_type = request.form['account_type']
        balance = float(request.form['balance'] or 0)
        
        # Get bank information
        routing_number = request.form.get('routing_number', '').strip()
        bank_name = request.form.get('bank_name', '').strip()
        account_number = request.form.get('account_number', '').strip()
        
        # Validate routing number if provided
        if routing_number and not validate_routing_number(routing_number):
            flash('Invalid routing number. Please check and try again.', 'error')
            return render_template('add_account.html')
        
        # If routing number is provided but no bank name, try to look it up
        if routing_number and not bank_name:
            bank_info = lookup_bank_by_routing(routing_number)
            if bank_info.get('valid') and bank_info.get('bank_name'):
                bank_name = bank_info['bank_name']
        
        account = Account(
            name=name, 
            account_type=account_type, 
            balance=balance, 
            bank_name=bank_name or None,
            routing_number=routing_number or None,
            user_id=current_user.id
        )
        
        # Set account number using the secure method (automatically extracts last 4)
        if account_number:
            account.set_account_number(account_number)
        db.session.add(account)
        db.session.commit()
        
        if bank_name:
            flash(f'Account added successfully with {bank_name}!', 'success')
        else:
            flash('Account added successfully!', 'success')
        return redirect(url_for('accounts'))
    
    return render_template('add_account.html')

@app.route('/accounts/<int:account_id>')
@login_required
def account_detail(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    return render_template('account_detail.html', account=account)

@app.route('/accounts/<int:account_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_account(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        account.name = request.form['name']
        account.account_type = request.form['account_type']
        account.balance = float(request.form['balance'] or 0)
        
        # Update bank information
        routing_number = request.form.get('routing_number', '').strip()
        bank_name = request.form.get('bank_name', '').strip()
        account_number = request.form.get('account_number', '').strip()
        
        # Validate routing number if provided
        if routing_number and not validate_routing_number(routing_number):
            flash('Invalid routing number. Please check and try again.', 'error')
            return render_template('edit_account.html', account=account)
        
        # Update bank info
        account.routing_number = routing_number or None
        account.bank_name = bank_name or None
        
        # Update account number
        if account_number:
            account.set_account_number(account_number)
        
        db.session.commit()
        flash('Account updated successfully!', 'success')
        return redirect(url_for('account_detail', account_id=account.id))
    
    return render_template('edit_account.html', account=account)

@app.route('/accounts/<int:account_id>/delete', methods=['POST'])
@login_required
def delete_account(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    
    account_name = account.name
    transaction_count = len(account.transactions)
    investment_count = len(account.investments)
    
    # Delete all associated transactions
    for transaction in account.transactions[:]:
        # No need to adjust balance since the account is being deleted anyway
        db.session.delete(transaction)
    
    # Delete all associated investments
    for investment in account.investments[:]:
        db.session.delete(investment)
    
    # Delete the account
    db.session.delete(account)
    db.session.commit()
    
    # Create detailed success message
    details = []
    if transaction_count > 0:
        details.append(f'{transaction_count} transaction{"s" if transaction_count != 1 else ""}')
    if investment_count > 0:
        details.append(f'{investment_count} investment{"s" if investment_count != 1 else ""}')
    
    if details:
        detail_text = f' and {" and ".join(details)}'
    else:
        detail_text = ''
    
    flash(f'Account "{account_name}"{detail_text} deleted successfully.', 'success')
    return redirect(url_for('accounts'))

@app.route('/reset-assets', methods=['POST'])
@login_required
def reset_assets():
    """Reset ALL data including all users - complete database reset"""
    
    # Get ALL data from database for counting
    all_users = User.query.all()
    all_accounts = Account.query.all()
    all_transactions = Transaction.query.all()
    all_investments = Investment.query.all()
    all_categories = Category.query.order_by(Category.name).all()
    all_budgets = MonthlyBudget.query.all()
    
    # Count totals
    total_users = len(all_users)
    total_accounts = len(all_accounts)
    total_transactions = len(all_transactions)
    total_investments = len(all_investments)
    total_categories = len(all_categories)
    total_budgets = len(all_budgets)
    
    # Delete ALL data in proper order to avoid foreign key constraints
    
    # 1. Delete transactions (they reference accounts and categories)
    for transaction in all_transactions:
        db.session.delete(transaction)
    
    # 2. Delete investments (they reference accounts)
    for investment in all_investments:
        db.session.delete(investment)
    
    # 3. Delete monthly budgets (they reference categories)
    for budget in all_budgets:
        db.session.delete(budget)
    
    # 4. Delete accounts (they reference users)
    for account in all_accounts:
        db.session.delete(account)
    
    # 5. Delete categories (they reference users)
    for category in all_categories:
        db.session.delete(category)
    
    # 6. Delete ALL users (complete database reset)
    for user in all_users:
        db.session.delete(user)
    
    # Commit all deletions
    db.session.commit()
    
    # Logout current user since they no longer exist
    logout_user()
    
    # Create summary message
    summary_parts = []
    if total_users > 0:
        summary_parts.append(f"{total_users} user{'s' if total_users != 1 else ''}")
    if total_accounts > 0:
        summary_parts.append(f"{total_accounts} account{'s' if total_accounts != 1 else ''}")
    if total_transactions > 0:
        summary_parts.append(f"{total_transactions} transaction{'s' if total_transactions != 1 else ''}")
    if total_investments > 0:
        summary_parts.append(f"{total_investments} investment{'s' if total_investments != 1 else ''}")
    if total_categories > 0:
        summary_parts.append(f"{total_categories} categor{'ies' if total_categories != 1 else 'y'}")
    if total_budgets > 0:
        summary_parts.append(f"{total_budgets} budget{'s' if total_budgets != 1 else ''}")
    
    if summary_parts:
        summary = ", ".join(summary_parts)
        flash(f'Complete database reset successful: {summary} deleted.', 'success')
    else:
        flash('Database was already empty.', 'info')
    
    # Redirect to login page since user is logged out
    return redirect(url_for('login'))



@app.route('/transactions')
@login_required
def transactions():
    page = request.args.get('page', 1, type=int)
    account_id = request.args.get('account_id', type=int)
    
    # Base query for user's transactions
    query = Transaction.query.join(Account).filter(Account.user_id == current_user.id)
    
    # Filter by account if specified
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
        # Verify the account belongs to the user
        account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
        account_name = account.name
    else:
        account_name = None
    
    transactions = query.order_by(Transaction.date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('transactions.html', transactions=transactions, account_name=account_name, account_id=account_id)

@app.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        date_str = request.form['date']
        description = request.form['description']
        amount = float(request.form['amount'])
        transaction_type = request.form['type']
        category_id = request.form['category_id'] if request.form['category_id'] else None
        account_id = int(request.form['account_id'])
        
        # Convert string date to date object
        transaction_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        transaction = Transaction(
            date=transaction_date,
            description=description,
            amount=amount,
            type=transaction_type,
            category_id=category_id,
            account_id=account_id
        )
        
        # Update account balance
        account = Account.query.get(account_id)
        if transaction_type == 'income':
            account.balance += amount
        elif transaction_type == 'expense':
            account.balance -= amount
        
        db.session.add(transaction)
        db.session.commit()
        
        flash('Transaction added successfully!', 'success')
        return redirect(url_for('transactions'))
    
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    return render_template('add_transaction.html', categories=categories, accounts=accounts)

@app.route('/transactions/<int:transaction_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    # Get transaction and verify ownership through account
    transaction = Transaction.query.join(Account).filter(
        Transaction.id == transaction_id,
        Account.user_id == current_user.id
    ).first_or_404()
    
    if request.method == 'POST':
        # Store old values for balance adjustment
        old_amount = transaction.amount
        old_type = transaction.type
        old_account_id = transaction.account_id
        
        # Update transaction fields
        date_str = request.form['date']
        transaction.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        transaction.description = request.form['description']
        new_amount = float(request.form['amount'])
        new_type = request.form['type']
        new_category_id = request.form['category_id'] if request.form['category_id'] else None
        new_account_id = int(request.form['account_id'])
        
        # Revert old transaction effect on old account
        old_account = Account.query.get(old_account_id)
        if old_type == 'income':
            old_account.balance -= old_amount
        elif old_type == 'expense':
            old_account.balance += old_amount
        
        # Apply new transaction effect on new account
        new_account = Account.query.get(new_account_id)
        if new_type == 'income':
            new_account.balance += new_amount
        elif new_type == 'expense':
            new_account.balance -= new_amount
        
        # Update transaction
        transaction.amount = new_amount
        transaction.type = new_type
        transaction.category_id = new_category_id
        transaction.account_id = new_account_id
        
        db.session.commit()
        flash('Transaction updated successfully!', 'success')
        return redirect(url_for('transactions'))
    
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    return render_template('edit_transaction.html', transaction=transaction, categories=categories, accounts=accounts)

@app.route('/transactions/<int:transaction_id>/delete', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    # Get transaction and verify ownership through account
    transaction = Transaction.query.join(Account).filter(
        Transaction.id == transaction_id,
        Account.user_id == current_user.id
    ).first_or_404()
    
    # Revert transaction effect on account balance
    account = transaction.account
    if transaction.type == 'income':
        account.balance -= transaction.amount
    elif transaction.type == 'expense':
        account.balance += transaction.amount
    
    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted successfully!', 'success')
    return redirect(url_for('transactions'))

@app.route('/investments')
@login_required
def investments():
    investments = Investment.query.join(Account).filter(Account.user_id == current_user.id).all()
    return render_template('investments.html', investments=investments)

@app.route('/investments/add', methods=['GET', 'POST'])
@login_required
def add_investment():
    if request.method == 'POST':
        symbol = request.form['symbol'].upper()
        name = request.form['name']
        shares = float(request.form['shares'])
        purchase_price = float(request.form['purchase_price'])
        current_price = float(request.form['current_price']) if request.form['current_price'] else None
        purchase_date = datetime.strptime(request.form['purchase_date'], '%Y-%m-%d').date()
        account_id = int(request.form['account_id'])
        
        investment = Investment(
            symbol=symbol,
            name=name,
            shares=shares,
            purchase_price=purchase_price,
            current_price=current_price,
            purchase_date=purchase_date,
            account_id=account_id
        )
        
        db.session.add(investment)
        db.session.commit()
        
        flash('Investment added successfully!', 'success')
        return redirect(url_for('investments'))
    
    accounts = Account.query.filter_by(account_type='investment', user_id=current_user.id).all()
    return render_template('add_investment.html', accounts=accounts)

@app.route('/categories')
@login_required
def categories():
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    return render_template('categories.html', categories=categories)

@app.route('/categories/add', methods=['GET', 'POST'])
@login_required
def add_category():
    if request.method == 'POST':
        name = request.form['name']
        category_type = request.form['type']
        
        category = Category(name=name, type=category_type, user_id=current_user.id)
        db.session.add(category)
        db.session.commit()
        
        flash('Category added successfully!', 'success')
        return redirect(url_for('categories'))
    
    return render_template('add_category.html')

@app.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    category = Category.query.filter_by(id=category_id, user_id=current_user.id).first()
    
    if not category:
        flash('Category not found!', 'error')
        return redirect(url_for('categories'))
    
    # Check if category has associated transactions
    transaction_count = Transaction.query.filter_by(category_id=category_id).count()
    
    if transaction_count > 0:
        flash(f'Cannot delete category "{category.name}" - it has {transaction_count} associated transactions. Please reassign or delete those transactions first.', 'error')
        return redirect(url_for('categories'))
    
    # Note: MonthlyBudget no longer references categories, so no budget check needed
    
    try:
        db.session.delete(category)
        db.session.commit()
        flash(f'Category "{category.name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting category: {str(e)}', 'error')
    
    return redirect(url_for('categories'))

@app.route('/budget')
@login_required
def budget():
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # Get or create available budget for current user
    monthly_budget = MonthlyBudget.query.filter_by(
        user_id=current_user.id,
        month=current_month,
        year=current_year
    ).first()
    
    # Calculate actual income and expenses for current month
    actual_income = db.session.query(db.func.sum(Transaction.amount)).join(Account).filter(
        Transaction.type == 'income',
        db.extract('month', Transaction.date) == current_month,
        db.extract('year', Transaction.date) == current_year,
        Account.user_id == current_user.id
    ).scalar() or 0
    
    actual_expenses = db.session.query(db.func.sum(Transaction.amount)).join(Account).filter(
        Transaction.type == 'expense',
        db.extract('month', Transaction.date) == current_month,
        db.extract('year', Transaction.date) == current_year,
        Account.user_id == current_user.id
    ).scalar() or 0
    
    actual_net = actual_income - actual_expenses
    
    budget_data = {
        'monthly_budget': monthly_budget,
        'actual_income': actual_income,
        'actual_expenses': actual_expenses,
        'actual_net': actual_net,
        'current_month': current_month,
        'current_year': current_year
    }
    
    if monthly_budget:
        budget_data.update({
            'income_variance': actual_income - monthly_budget.budgeted_income,
            'expense_variance': actual_expenses - monthly_budget.budgeted_expenses,
            'net_variance': actual_net - monthly_budget.budgeted_net
        })
    
    return render_template('budget.html', budget_data=budget_data)

@app.route('/budget/add', methods=['GET', 'POST'])
@login_required
def add_budget():
    if request.method == 'POST':
        budgeted_income = float(request.form.get('budgeted_income', 0))
        budgeted_expenses = float(request.form.get('budgeted_expenses', 0))
        month = int(request.form['month'])
        year = int(request.form['year'])
        
        # Check if budget already exists for this user and month
        existing_budget = MonthlyBudget.query.filter_by(
            user_id=current_user.id, month=month, year=year
        ).first()
        
        if existing_budget:
            existing_budget.budgeted_income = budgeted_income
            existing_budget.budgeted_expenses = budgeted_expenses
        else:
            budget = MonthlyBudget(
                user_id=current_user.id,
                budgeted_income=budgeted_income,
                budgeted_expenses=budgeted_expenses,
                month=month,
                year=year
            )
            db.session.add(budget)
        
        db.session.commit()
        
        flash('Available budget updated successfully!', 'success')
        return redirect(url_for('budget'))
    
    # Get current month/year for default values
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    return render_template('add_budget.html', 
                         current_month=current_month, 
                         current_year=current_year)

@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

@app.route('/reports/print')
@login_required
def print_reports():
    from sqlalchemy import func, extract
    
    # Get current year and month
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Get all accounts for the user
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    # Get all categories
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    
    # Get transactions for current month
    current_month_transactions = Transaction.query.join(Account).filter(
        Account.user_id == current_user.id,
        extract('year', Transaction.date) == current_year,
        extract('month', Transaction.date) == current_month
    ).order_by(Transaction.date.desc()).all()
    
    # Get monthly summary for current year
    monthly_summary = db.session.query(
        extract('month', Transaction.date).label('month'),
        func.sum(Transaction.amount).filter(Transaction.type == 'income').label('income'),
        func.sum(Transaction.amount).filter(Transaction.type == 'expense').label('expenses')
    ).join(Account).filter(
        Account.user_id == current_user.id,
        extract('year', Transaction.date) == current_year
    ).group_by(extract('month', Transaction.date)).all()
    
    # Get category spending for current month
    category_spending = db.session.query(
        Category.name,
        func.sum(Transaction.amount).label('total')
    ).join(Transaction).join(Account).filter(
        Account.user_id == current_user.id,
        Transaction.type == 'expense',
        extract('year', Transaction.date) == current_year,
        extract('month', Transaction.date) == current_month
    ).group_by(Category.id).all()
    
    # Get investments
    investments = Investment.query.join(Account).filter(Account.user_id == current_user.id).all()
    
    # Calculate totals
    total_assets = sum(account.balance for account in accounts if account.balance > 0)
    total_liabilities = abs(sum(account.balance for account in accounts if account.balance < 0))
    net_worth = total_assets - total_liabilities
    
    # Monthly totals
    month_income = sum(t.amount for t in current_month_transactions if t.type == 'income')
    month_expenses = sum(t.amount for t in current_month_transactions if t.type == 'expense')
    month_net = month_income - month_expenses
    
    return render_template('print_reports.html', 
                         accounts=accounts,
                         categories=categories,
                         current_month_transactions=current_month_transactions,
                         monthly_summary=monthly_summary,
                         category_spending=category_spending,
                         investments=investments,
                         total_assets=total_assets,
                         total_liabilities=total_liabilities,
                         net_worth=net_worth,
                         month_income=month_income,
                         month_expenses=month_expenses,
                         month_net=month_net,
                         current_year=current_year,
                         current_month=current_month,
                         report_date=datetime.now())

@app.route('/api/monthly-spending')
@login_required
def api_monthly_spending():
    current_year = datetime.now().year
    
    monthly_data = []
    for month in range(1, 13):
        total_spending = db.session.query(db.func.sum(Transaction.amount)).join(Account).filter(
            Transaction.type == 'expense',
            db.extract('month', Transaction.date) == month,
            db.extract('year', Transaction.date) == current_year,
            Account.user_id == current_user.id
        ).scalar() or 0
        
        monthly_data.append({
            'month': month,
            'spending': float(total_spending)
        })
    
    return jsonify(monthly_data)

@app.route('/api/net-worth')
@login_required
def api_net_worth():
    """Get net worth summary data for current user"""
    
    # Get all user accounts
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    # Calculate assets (positive balances) and liabilities (negative balances)
    cash_assets = sum(account.balance for account in accounts if account.balance > 0)
    liabilities = abs(sum(account.balance for account in accounts if account.balance < 0))
    
    # Get investment values
    investment_assets = 0
    for account in accounts:
        for investment in account.investments:
            # Use current_value if available, otherwise use purchase value
            if hasattr(investment, 'current_value') and investment.current_value:
                investment_assets += investment.current_value
            else:
                investment_assets += investment.shares * investment.purchase_price
    
    # Total calculations
    total_assets = cash_assets + investment_assets
    net_worth = total_assets - liabilities
    
    return jsonify({
        'assets': total_assets,
        'liabilities': liabilities,
        'net_worth': net_worth,
        'cash_assets': cash_assets,
        'investment_assets': investment_assets,
        'account_count': len(accounts)
    })

# Bank Lookup API Routes
@app.route('/api/lookup-bank/<routing_number>')
@login_required
def api_lookup_bank(routing_number):
    """API endpoint to lookup bank by routing number"""
    try:
        result = lookup_bank_by_routing(routing_number)
        return jsonify(result)
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 400

@app.route('/api/bank-suggestions/<partial_routing>')
@login_required
def api_bank_suggestions(partial_routing):
    """API endpoint to get bank suggestions based on partial routing number"""
    try:
        suggestions = get_bank_suggestions(partial_routing)
        return jsonify({"suggestions": suggestions})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/validate-routing/<routing_number>')
@login_required
def api_validate_routing(routing_number):
    """API endpoint to validate routing number"""
    try:
        is_valid = validate_routing_number(routing_number)
        return jsonify({"valid": is_valid})
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 400

def init_db():
    """Initialize the database tables"""
    try:
        print("Initializing database...")
        # Only create tables if they don't exist (don't drop existing data)
        db.create_all()
        print("Database tables ready")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        print("This might be due to an existing database with incompatible schema.")
        print("Please run: python reset_db.py to reset the database if needed.")
        raise e

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', debug=True)