#!/usr/bin/env python3
"""
Database initialization script with proper schema creation
This script ensures all tables are created with the latest schema including bank fields
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, User, Account, Category, Transaction, Investment, MonthlyBudget

def initialize_database():
    """Initialize database with complete schema"""
    with app.app_context():
        print("🔧 Initializing Money Tracker Database")
        print("=" * 50)
        
        try:
            print("1. Dropping all existing tables...")
            db.drop_all()
            print("   ✅ All tables dropped")
            
            print("2. Creating all tables with latest schema...")
            db.create_all()
            print("   ✅ All tables created")
            
            print("3. Verifying table structure...")
            
            # Check Account table for new columns
            with db.engine.connect() as conn:
                account_columns = conn.execute(db.text("PRAGMA table_info(account)")).fetchall()
                print(f"   Account table: {len(account_columns)} columns")
                
                bank_fields = ['bank_name', 'routing_number', 'account_number', 'account_number_last4']
                found_fields = []
                
                for col in account_columns:
                    if col[1] in bank_fields:
                        found_fields.append(col[1])
                        print(f"      ✅ {col[1]} column present")
                
                if len(found_fields) == len(bank_fields):
                    print("      ✅ All bank fields present")
                else:
                    missing = set(bank_fields) - set(found_fields)
                    print(f"      ⚠️  Missing bank fields: {missing}")
                
                # Check other tables exist
                tables = conn.execute(db.text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
                table_names = [table[0] for table in tables]
                
                required_tables = ['user', 'account', 'category', 'transaction', 'investment', 'monthly_budget']
                for table in required_tables:
                    if table in table_names:
                        print(f"   ✅ {table} table exists")
                    else:
                        print(f"   ❌ {table} table missing")
            
            print("\n4. Creating default admin user...")
            
            # Check if admin user exists
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@moneytracker.local'
                )
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                db.session.commit()
                print("   ✅ Admin user created (username: admin, password: admin123)")
            else:
                print("   ℹ️  Admin user already exists")
            
            print("\n5. Creating sample data...")
            
            # Create sample account with bank info
            sample_account = Account.query.filter_by(name='Sample Checking Account').first()
            if not sample_account:
                sample_account = Account(
                    name='Sample Checking Account',
                    account_type='checking',
                    balance=1000.00,
                    bank_name='Chase Bank',
                    routing_number='021000021',
                    user_id=admin_user.id
                )
                sample_account.set_account_number('1234567890123456')
                db.session.add(sample_account)
                
                # Create sample categories
                categories = [
                    Category(name='Salary', type='income', user_id=admin_user.id),
                    Category(name='Groceries', type='expense', user_id=admin_user.id),
                    Category(name='Stocks', type='investment', user_id=admin_user.id)
                ]
                
                for category in categories:
                    db.session.add(category)
                
                db.session.commit()
                print("   ✅ Sample data created")
            else:
                print("   ℹ️  Sample data already exists")
            
            print("\n🎉 Database initialization completed successfully!")
            print(f"   📁 Database location: {os.path.abspath('instance/budget.db')}")
            print("   🔑 Admin login: admin / admin123")
            print("   🚀 Ready to start the application: python app.py")
            
        except Exception as e:
            print(f"\n❌ Database initialization failed: {e}")
            print("\nTroubleshooting:")
            print("1. Ensure no Flask app is running")
            print("2. Check file permissions")
            print("3. Verify SQLite installation")
            raise e

if __name__ == '__main__':
    initialize_database()