# Money Tracker Application

A comprehensive personal finance management web application built with Python Flask that helps you track investments, bank transactions, income, and monthly expenses through an intuitive web interface.

## Features

### 🔐 User Authentication
- Secure user registration and login system
- Password hashing for security
- Session management with Flask-Login
- User-specific data isolation
- Automatic default categories for new users

### 📊 Dashboard
- Overview of total account balances
- Recent transactions summary
- Monthly expense breakdown by category
- Interactive charts and visualizations

### 🏦 Account Management
- Track multiple accounts (checking, savings, investment, credit cards)
- Real-time balance tracking
- Account type categorization

### 💳 Transaction Tracking
- Record income, expenses, and transfers
- Categorize transactions for better organization
- Pagination for easy browsing of transaction history
- Automatic account balance updates

### 📈 Investment Portfolio
- Track stock and investment holdings
- Monitor purchase vs. current prices
- Calculate gain/loss on investments
- Portfolio value summaries

### 📝 Budget Planning
- Set monthly budgets by category
- Track actual vs. budgeted spending
- Visual progress indicators
- Budget variance analysis

### 🏷️ Category Management
- Organize transactions with custom categories
- Separate categories for income, expenses, and investments
- Transaction count per category

### 📊 Financial Reports
- Income vs. expense trends
- Category-wise spending analysis
- Account balance visualizations
- Net worth calculations
- Cash flow analysis

## Technology Stack

- **Backend:** Python Flask with Flask-Login for authentication
- **Database:** SQLite with SQLAlchemy ORM
- **Frontend:** Bootstrap 5, Chart.js
- **Security:** Werkzeug password hashing
- **Icons:** Font Awesome

## Installation

1. **Clone or download the project:**
   ```
   cd d:\MyProject\budget
   ```

2. **Create a virtual environment (recommended):**
   ```powershell
   python -m venv budget_env
   budget_env\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```powershell
   python app.py
   ```

5. **Access the application:**
   Open your browser and go to your production server URL. See `run_production.bat` for details.

## Database

The application uses SQLite database that will be automatically created when you first run the app. Sample data including default categories and accounts will be populated on the first run.
- **Transaction:** Individual financial transactions
- **Investment:** Stock and investment holdings
- **MonthlyBudget:** Monthly budget allocations by category

## Usage

### Getting Started

1. **Create Account:** Register a new user account or log in with existing credentials
2. **Add Accounts:** Start by adding your bank accounts, credit cards, and investment accounts
3. **Create Categories:** Set up categories for different types of income and expenses (default categories are provided)
4. **Record Transactions:** Add your daily transactions with appropriate categories
5. **Track Investments:** Add your investment holdings to monitor portfolio performance
6. **Set Budgets:** Create monthly budgets to track spending goals
7. **Review Reports:** Use the reports section to analyze your financial trends

## File Structure

```
budget/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── budget.db              # SQLite database (created automatically)
├── static/                # Static files (CSS, images)
│   ├── css/
│   │   └── style.css      # Custom styles
│   └── images/
│       ├── dollar.png     # Dashboard background
│       └── dollar1.png    # Login background
├── templates/             # HTML templates
│   ├── base.html          # Base template with navigation
│   ├── login.html         # User login form
│   ├── register.html      # User registration form
│   ├── dashboard.html     # Dashboard with summary and charts
│   ├── accounts.html      # Account listing
│   ├── add_account.html   # Add new account form
│   ├── transactions.html  # Transaction history
│   ├── add_transaction.html # Add transaction form
│   ├── investments.html   # Investment portfolio
│   ├── add_investment.html # Add investment form
│   ├── categories.html    # Category management
│   ├── add_category.html  # Add category form
│   ├── budget.html        # Monthly budget tracking
│   ├── add_budget.html    # Add/edit budget form
│   └── reports.html       # Financial reports and charts
└── README.md              # This file
```

## Development

To modify or extend the application:

1. **Adding new features:** Create new routes in `app.py` and corresponding templates
2. **Database changes:** Modify the models in `app.py` and handle migrations
3. **Styling:** Update Bootstrap classes in templates or add custom CSS
4. **Charts:** Modify Chart.js configurations in template script blocks
5. **Configuration:** Use environment variables for sensitive configuration
6. **Authentication:** Implement user authentication for multi-user scenarios
7. **Migrations:** Use proper database migration tools for schema changes in production
8. **Analytics:** Advanced reporting and analytics
9. **Integrations:** Integration with bank APIs
10. **Backup:** Backup and restore functionality

## License

This project is open source and available under the MIT License.

**Author: Roberto Raimondo - IS Senior Systems Engineer II**