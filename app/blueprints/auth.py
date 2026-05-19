import sys
import traceback
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.database import get_db
from app.utils.logger import log_action, log_with_context, log_exception, get_logger
from app.translations import t

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
auth_bp.strict_slashes = False


def _error_info(e):
    tb = sys.exc_info()[-1]
    return {
        'error': True,
        'message': str(e),
        'function': sys._getframe(1).f_code.co_name,
        'line': tb.tb_lineno if tb else 0,
        'trace': traceback.format_exc()
    }


@auth_bp.route('/login', methods=['GET', 'POST'])
@log_with_context('LOGIN', 'AUTHENTICATION')
@log_exception
def login():
    try:
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            db = get_db()
            if isinstance(db, dict) and db.get('error'):
                flash(f'Database error: {db["message"]}', 'danger')
                return render_template('auth/login.html')
            user = db.users.find_one({'username': username})
            
            if user and user['password'] == password:
                session['user_id'] = str(user['_id'])
                session['username'] = user['username']
                session['role'] = user['role']
                log_action('LOGIN_SUCCESS', 'AUTHENTICATION', f"User {username} logged in successfully")
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard.index'))
            log_action('LOGIN_FAILED', 'AUTHENTICATION', f"Invalid credentials for user {username}")
            flash('Invalid credentials', 'danger')
        return render_template('auth/login.html')
    except Exception as e:
        err = _error_info(e)
        get_logger().error(f"login() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f'Login error: {err["message"]}', 'danger')
        return render_template('auth/login.html')


@auth_bp.route('/logout')
@log_with_context('LOGOUT', 'AUTHENTICATION')
@log_exception
def logout():
    try:
        username = session.get('username', 'unknown')
        session.clear()
        log_action('LOGOUT_SUCCESS', 'AUTHENTICATION', f"User {username} logged out")
        flash('Logged out successfully', 'info')
        return redirect(url_for('auth.login'))
    except Exception as e:
        err = _error_info(e)
        get_logger().error(f"logout() line {err['line']}: {err['message']}\n{err['trace']}")
        return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
@log_with_context('REGISTER', 'AUTHENTICATION')
@log_exception
def register():
    try:
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            if password != confirm_password:
                flash(t('passwords_do_not_match', session.get('lang', 'en')), 'warning')
                return render_template('auth/login.html', active_tab='register')

            db = get_db()
            if isinstance(db, dict) and db.get('error'):
                flash(f"Database error: {db['message']}", 'danger')
                return render_template('auth/login.html', active_tab='register')

            existing = db.users.find_one({'username': username})
            if existing:
                flash(t('username_taken', session.get('lang', 'en')), 'warning')
                return render_template('auth/login.html', active_tab='register')

            user_data = {
                'username': username,
                'full_name': full_name,
                'email': email,
                'password': password,
                'role': 'worker',
                'created_at': datetime.utcnow()
            }
            db.users.insert_one(user_data)
            log_action('REGISTRATION_SUCCESS', 'AUTHENTICATION', f"New user {username} registered")

            flash(t('registration_success', session.get('lang', 'en')), 'success')
            return redirect(url_for('auth.login'))

        return render_template('auth/login.html', active_tab='register')
    except Exception as e:
        err = _error_info(e)
        get_logger().error(f"register() line {err['line']}: {err['message']}\n{err['trace']}")
        flash(f"{t('registration_failed', session.get('lang', 'en'))}: {err['message']}", 'danger')
        return render_template('auth/login.html', active_tab='register')
