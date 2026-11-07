import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, '/home/meghapant/Projects/PDF/backend')

from app import app, db
from auth_service import AuthService

def run_auth_tests():
    print("=== STARTING PHASE 1 AUTHENTICATION TEST SUITE ===")
    client = app.test_client()

    # 1. System Info branding
    res = client.get('/api/system/info')
    assert res.status_code == 200
    info = res.get_json()
    assert "StudyGeneratorExam" in info['name']
    print(f"[PASS] 1. System Info verified: {info['name']} ({info['version']})")

    # 2. Signup validation - short password
    res = client.post('/api/auth/signup', json={
        "email": "invalid@test.com",
        "password": "short",
        "name": "Invalid User"
    })
    assert res.status_code == 400
    print("[PASS] 2. Signup validation: rejected short password")

    # 3. Signup validation - password without numbers
    res = client.post('/api/auth/signup', json={
        "email": "invalid@test.com",
        "password": "passwordonly",
        "name": "Invalid User"
    })
    assert res.status_code == 400
    print("[PASS] 3. Signup validation: rejected password without numbers")

    # 4. Successful Signup
    test_email = "testteacher@studygeneratorexam.com"
    # Clean previous if exists
    existing = db.get_user_by_email(test_email)
    if existing:
        db.delete_user(existing.id)

    res = client.post('/api/auth/signup', json={
        "email": test_email,
        "password": "TeacherPass2026!",
        "name": "Dr. Emily Watson",
        "institution": "Cambridge Academy"
    })
    assert res.status_code == 201
    signup_data = res.get_json()
    assert signup_data['success'] is True
    assert signup_data['user']['email'] == test_email
    assert signup_data['user']['is_verified'] is False
    token = signup_data['token']
    verif_token = signup_data['verification_token']
    print(f"[PASS] 4. User registered: {signup_data['user']['name']} ({signup_data['user']['email']})")

    # 5. Duplicate Email Rejection
    res = client.post('/api/auth/signup', json={
        "email": test_email,
        "password": "TeacherPass2026!",
        "name": "Duplicate"
    })
    assert res.status_code == 409
    print("[PASS] 5. Duplicate email rejection verified")

    # 6. Verify Email using token
    res = client.get(f'/api/auth/verify-email?token={verif_token}')
    assert res.status_code == 200
    verif_data = res.get_json()
    assert verif_data['user']['is_verified'] is True
    print("[PASS] 6. Email verification successful")

    # 7. Login with Wrong Password
    res = client.post('/api/auth/login', json={
        "email": test_email,
        "password": "WrongPassword123!"
    })
    assert res.status_code == 401
    print("[PASS] 7. Rejected invalid password")

    # 8. Login with Correct Password
    res = client.post('/api/auth/login', json={
        "email": test_email,
        "password": "TeacherPass2026!",
        "remember_me": True
    })
    assert res.status_code == 200
    login_data = res.get_json()
    token = login_data['token']
    print(f"[PASS] 8. Login successful with JWT token issued")

    # 9. Protected Profile Check via /api/auth/me
    res = client.get('/api/auth/me', headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    me = res.get_json()
    assert me['authenticated'] is True
    assert me['user']['name'] == "Dr. Emily Watson"
    print("[PASS] 9. Protected /api/auth/me verified with Bearer token")

    # 10. Profile Update
    res = client.put('/api/auth/profile', 
                     headers={"Authorization": f"Bearer {token}"},
                     json={"name": "Prof. Emily Watson, Ph.D.", "institution": "Oxford & Cambridge"})
    assert res.status_code == 200
    updated_user = res.get_json()['user']
    assert updated_user['name'] == "Prof. Emily Watson, Ph.D."
    assert updated_user['institution'] == "Oxford & Cambridge"
    print("[PASS] 10. Profile update verified")

    # 11. Change Password
    res = client.put('/api/auth/change-password',
                     headers={"Authorization": f"Bearer {token}"},
                     json={"current_password": "TeacherPass2026!", "new_password": "NewTeacherPass2026#"})
    assert res.status_code == 200
    print("[PASS] 11. Password changed successfully")

    # 12. Login with New Password
    res = client.post('/api/auth/login', json={
        "email": test_email,
        "password": "NewTeacherPass2026#"
    })
    assert res.status_code == 200
    token = res.get_json()['token']
    print("[PASS] 12. Verified login with newly changed password")

    # 13. Forgot Password & Reset Token
    res = client.post('/api/auth/forgot-password', json={"email": test_email})
    assert res.status_code == 200
    reset_token = res.get_json()['reset_token']
    assert reset_token is not None
    print(f"[PASS] 13. Generated reset token: {reset_token[:12]}...")

    # 14. Reset Password with Token
    res = client.post('/api/auth/reset-password', json={
        "token": reset_token,
        "new_password": "ResetPassword2026$"
    })
    assert res.status_code == 200
    print("[PASS] 14. Password reset via token succeeded")

    # 15. Google Sign-In Flow
    google_email = "googleteacher@studygeneratorexam.com"
    res = client.post('/api/auth/google', json={
        "email": google_email,
        "name": "Dr. Sarah Chen",
        "institution": "MIT"
    })
    assert res.status_code == 200
    g_user = res.get_json()['user']
    assert g_user['auth_provider'] == 'google'
    assert g_user['is_verified'] is True
    print(f"[PASS] 15. Google auth flow provisioned & logged in: {g_user['name']}")

    # 16. Role Authorization: Admin Only Route
    # Test user (non-admin) should get 403 Forbidden
    res = client.get('/api/admin/users', headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    print("[PASS] 16a. Non-admin user blocked from /api/admin/users (403 Forbidden)")

    # Admin user login
    res = client.post('/api/auth/login', json={
        "email": "admin@studygeneratorexam.com",
        "password": "AdminPass123!"
    })
    assert res.status_code == 200
    admin_token = res.get_json()['token']
    res = client.get('/api/admin/users', headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    admin_data = res.get_json()
    assert admin_data['total'] >= 2
    print(f"[PASS] 16b. Admin verified: access granted to {admin_data['total']} users")

    # 17. Mobile Number Signup and Login Flow
    mobile_user_email = "mobileuser@studygeneratorexam.com"
    mobile_phone = "+91 9876543210"
    existing_mob = db.get_user_by_email(mobile_user_email)
    if existing_mob:
        db.delete_user(existing_mob.id)

    res = client.post('/api/auth/signup', json={
        "email": mobile_user_email,
        "phone": mobile_phone,
        "password": "MobileUserPass2026!",
        "name": "Prof. Rajesh Kumar",
        "institution": "IIT Delhi"
    })
    assert res.status_code == 201
    mob_signup_data = res.get_json()
    assert mob_signup_data['success'] is True
    assert mob_signup_data['user']['phone'] == mobile_phone
    print(f"[PASS] 17a. User registered with mobile number: {mob_signup_data['user']['name']} ({mob_signup_data['user']['phone']})")

    # Login using mobile number formatted
    res = client.post('/api/auth/login', json={
        "email": "+91 98765 43210",
        "password": "MobileUserPass2026!"
    })
    assert res.status_code == 200
    mob_token = res.get_json()['token']
    assert res.get_json()['user']['email'] == mobile_user_email
    print("[PASS] 17b. Login successful using mobile number with spaces/country code")

    # Login using plain mobile digits
    res = client.post('/api/auth/login', json={
        "identifier": "9876543210",
        "password": "MobileUserPass2026!"
    })
    assert res.status_code == 200
    assert res.get_json()['user']['name'] == "Prof. Rajesh Kumar"
    print("[PASS] 17c. Login successful using plain 10-digit mobile number")

    # Update profile phone number
    res = client.put('/api/auth/profile',
                     headers={"Authorization": f"Bearer {mob_token}"},
                     json={"name": "Prof. Rajesh Kumar", "institution": "IIT Bombay", "phone": "+91 9123456789"})
    assert res.status_code == 200
    assert res.get_json()['user']['phone'] == "+91 9123456789"
    print("[PASS] 17d. Profile phone number updated successfully")

    # Clean up mobile test user
    db.delete_user(mob_signup_data['user']['id'])

    # 18. Account Deletion
    # Emily deletes her account
    res = client.delete('/api/auth/account', 
                        headers={"Authorization": f"Bearer {token}"},
                        json={"password": "ResetPassword2026$"})
    assert res.status_code == 200
    # Confirm account is gone
    res = client.get('/api/auth/me', headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.get_json()['authenticated'] is False

    # Calling protected route now returns 401
    res_prof = client.put('/api/auth/profile', 
                          headers={"Authorization": f"Bearer {token}"},
                          json={"name": "Ghost"})
    assert res_prof.status_code == 401
    print("[PASS] 18. User account deletion verified (session invalidated & 401 on protected route)")

    print("\n=== ALL 18 PHASE 1 AUTHENTICATION TESTS PASSED WITH 100% SUCCESS ===")

if __name__ == '__main__':
    run_auth_tests()
