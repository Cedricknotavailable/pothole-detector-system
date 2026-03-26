# Design Document: Email OTP Verification

## Overview

This design specifies a secure OTP (One-Time Password) email verification system for the Flask-based road defect reporting application. The system integrates with the existing User authentication flow to add email verification for registration and password reset operations.

The OTP system generates cryptographically secure 6-digit codes, stores them with expiration metadata, sends them via EmailJS client-side integration, and verifies them before allowing sensitive account operations. The design follows Flask/SQLAlchemy patterns established in the existing codebase and maintains consistency with the application's security model.

Key design goals:
- Minimal disruption to existing authentication flows
- Client-side email sending via EmailJS to avoid server-side SMTP configuration
- Secure OTP storage using hashing (similar to password hashing pattern)
- Rate limiting to prevent abuse
- Session-based state management during verification flows

## Architecture

### System Components

```mermaid
graph TB
    subgraph "Client Browser"
        RF[Register Form]
        PF[Password Reset Form]
        OI[OTP Input UI]
        EJS[EmailJS Client]
    end
    
    subgraph "Flask Backend"
        RR[/register Route]
        PR[/recover Route]
        VR[/verify-otp Route]
        RS[/resend-otp Route]
        OG[OTP Generator]
        OV[OTP Verifier]
        RL[Rate Limiter]
        SM[Session Manager]
    end
    
    subgraph "Database"
        UT[User Table]
        OT[OTP Table]
    end
    
    subgraph "External"
        ES[EmailJS Service]
    end
    
    RF -->|POST credentials| RR
    RR -->|generate OTP| OG
    OG -->|store hashed| OT
    RR -->|return OTP code| RF
    RF -->|send email| EJS
    EJS -->|deliver| ES
    
    OI -->|POST OTP| VR
    VR -->|verify| OV
    OV -->|check hash| OT
    VR -->|create user| UT
    
    PF -->|POST identifier| PR
    PR -->|generate OTP| OG
    PR -->|return OTP code| PF
    PF -->|send email| EJS
    
    OI -->|request resend| RS
    RS -->|check limits| RL
    RS -->|generate new| OG
    
    RR -.->|store temp data| SM
    PR -.->|store temp data| SM
    VR -.->|read temp data| SM
```

### Component Responsibilities

**OTP Generator**
- Generate cryptographically secure 6-digit codes using `secrets` module
- Ensure codes are zero-padded to exactly 6 digits
- Create OTP records with email, purpose, expiration, and hashed code

**OTP Verifier**
- Hash submitted OTP codes and compare with stored hashes
- Check expiration timestamps (10-minute window)
- Track verification attempts (max 3 per OTP)
- Invalidate OTP after successful verification or max attempts

**Rate Limiter**
- Track OTP generation requests per email address
- Enforce 3 requests per 15-minute window
- Enforce 30-second cooldown between resend requests
- Store rate limit data in session (stateless approach)

**Session Manager**
- Store registration data (username, email, password_hash) during OTP verification
- Store password reset user_id during OTP verification
- Store OTP metadata (email, purpose, timestamp) for verification context
- Expire session data after 15 minutes of inactivity

**EmailJS Client Integration**
- Client-side JavaScript sends OTP emails using EmailJS SDK
- Uses service ID: `service_cs9uath`
- Uses template ID: `template_ai1brni`
- Uses public key: `dXcaIv5LGMTpybpw2`
- Backend returns OTP code in JSON response for client to send

### Data Flow

**Registration Flow:**
1. User submits registration form (username, email, password)
2. Backend validates input and checks uniqueness
3. Backend generates OTP and stores hashed version in database
4. Backend stores registration data in session
5. Backend returns JSON with OTP code and success flag
6. Client sends OTP email via EmailJS
7. Client displays OTP input form
8. User enters OTP code
9. Client submits OTP to `/verify-otp` endpoint
10. Backend verifies OTP hash and checks expiration
11. Backend creates User record from session data
12. Backend clears session and returns success

**Password Reset Flow:**
1. User submits identifier (username or email)
2. Backend looks up user by identifier
3. Backend generates OTP and stores hashed version
4. Backend stores user_id in session
5. Backend returns JSON with OTP code (always returns success for security)
6. Client sends OTP email via EmailJS
7. Client displays OTP input form
8. User enters OTP code
9. Client submits OTP to `/verify-otp` endpoint
10. Backend verifies OTP hash and checks expiration
11. Backend returns success and allows password reset form
12. User submits new password
13. Backend updates password and clears session

## Components and Interfaces

### Database Models

**OTP Model**

```python
class OTP(db.Model):
    """
    Stores one-time password verification codes with expiration and attempt tracking.
    OTP codes are hashed before storage (never stored in plaintext).
    """
    __tablename__ = 'otp'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    otp_hash = db.Column(db.String(255), nullable=False)
    purpose = db.Column(db.String(20), nullable=False)  # 'registration' or 'password_reset'
    created_at = db.Column(db.Integer, nullable=False)  # Unix timestamp
    expires_at = db.Column(db.Integer, nullable=False)  # Unix timestamp
    attempts = db.Column(db.Integer, nullable=False, default=0)
    verified = db.Column(db.Boolean, nullable=False, default=False)
    
    def is_expired(self) -> bool:
        """Check if OTP has exceeded 10-minute expiration window."""
        return int(time.time()) > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if OTP can still be used (not expired, not verified, attempts < 3)."""
        return not self.verified and not self.is_expired() and self.attempts < 3
    
    def increment_attempts(self) -> None:
        """Increment verification attempt counter."""
        self.attempts += 1
    
    def mark_verified(self) -> None:
        """Mark OTP as successfully verified."""
        self.verified = True
```

**Database Indexes:**
- `email` column indexed for fast lookup during verification
- Composite index on `(email, purpose, verified)` for active OTP queries
- `expires_at` column indexed for cleanup queries

### Backend API Endpoints

**POST /register**

Modified to support OTP flow:

```python
@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handle user registration with OTP verification.
    
    Request (initial):
        - username: string
        - email: string
        - password: string
    
    Response (initial):
        - success: boolean
        - otp_code: string (6 digits) - only if success=true
        - message: string
        - errors: dict (field-specific errors)
    
    Session data stored:
        - pending_registration: {username, email, password_hash, timestamp}
    """
    if request.method == 'GET':
        return render_template('register.html')
    
    # Validation logic (existing)
    # ...
    
    if errors:
        return jsonify({'success': False, 'errors': field_errors})
    
    # Generate OTP
    otp_code = generate_otp()
    otp_hash = generate_password_hash(otp_code)
    
    # Store OTP in database
    now = int(time.time())
    otp_record = OTP(
        email=email,
        otp_hash=otp_hash,
        purpose='registration',
        created_at=now,
        expires_at=now + 600,  # 10 minutes
        attempts=0,
        verified=False
    )
    db.session.add(otp_record)
    db.session.commit()
    
    # Store registration data in session
    session['pending_registration'] = {
        'username': username,
        'email': email,
        'password_hash': generate_password_hash(password),
        'timestamp': now
    }
    session['otp_email'] = email
    session['otp_purpose'] = 'registration'
    
    return jsonify({
        'success': True,
        'otp_code': otp_code,  # Client will send this via EmailJS
        'message': 'Verification code generated. Please check your email.'
    })
```

**POST /verify-otp**

New endpoint for OTP verification:

```python
@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    """
    Verify OTP code and complete registration or password reset.
    
    Request:
        - otp_code: string (6 digits)
    
    Response:
        - success: boolean
        - message: string
        - next_step: string ('complete' or 'reset_password')
        - attempts_remaining: int (optional)
    
    Side effects:
        - Creates User record if purpose is 'registration'
        - Allows password reset if purpose is 'password_reset'
        - Invalidates OTP after successful verification
        - Clears session data after completion
    """
    otp_code = (request.form.get('otp_code') or '').strip()
    
    if not otp_code or len(otp_code) != 6 or not otp_code.isdigit():
        return jsonify({
            'success': False,
            'message': 'Invalid OTP format. Please enter a 6-digit code.'
        }), 400
    
    # Get OTP context from session
    email = session.get('otp_email')
    purpose = session.get('otp_purpose')
    
    if not email or not purpose:
        return jsonify({
            'success': False,
            'message': 'Verification session expired. Please start over.'
        }), 400
    
    # Find active OTP
    otp_record = OTP.query.filter_by(
        email=email,
        purpose=purpose,
        verified=False
    ).order_by(OTP.created_at.desc()).first()
    
    if not otp_record:
        return jsonify({
            'success': False,
            'message': 'No active verification code found. Please request a new one.'
        }), 404
    
    # Check if OTP is still valid
    if not otp_record.is_valid():
        if otp_record.is_expired():
            message = 'Verification code has expired. Please request a new one.'
        else:
            message = 'Too many failed attempts. Please request a new code.'
        return jsonify({'success': False, 'message': message}), 400
    
    # Verify OTP hash
    if not check_password_hash(otp_record.otp_hash, otp_code):
        otp_record.increment_attempts()
        db.session.commit()
        
        attempts_remaining = 3 - otp_record.attempts
        return jsonify({
            'success': False,
            'message': f'Invalid verification code. {attempts_remaining} attempts remaining.',
            'attempts_remaining': attempts_remaining
        }), 400
    
    # OTP verified successfully
    otp_record.mark_verified()
    db.session.commit()
    
    # Complete the operation based on purpose
    if purpose == 'registration':
        pending = session.get('pending_registration')
        if not pending:
            return jsonify({
                'success': False,
                'message': 'Registration data not found. Please start over.'
            }), 400
        
        # Create user account
        user = User(
            username=pending['username'],
            email=pending['email'],
            password_hash=pending['password_hash'],
            role='user',
            status='active'
        )
        db.session.add(user)
        db.session.commit()
        
        # Clear session
        session.pop('pending_registration', None)
        session.pop('otp_email', None)
        session.pop('otp_purpose', None)
        
        return jsonify({
            'success': True,
            'message': 'Email verified! Your account has been created.',
            'next_step': 'complete',
            'redirect': url_for('login')
        })
    
    elif purpose == 'password_reset':
        # Allow password reset form
        session['otp_verified'] = True
        
        return jsonify({
            'success': True,
            'message': 'Identity verified. You can now reset your password.',
            'next_step': 'reset_password'
        })
    
    return jsonify({'success': False, 'message': 'Unknown purpose'}), 400
```

**POST /resend-otp**

New endpoint for resending OTP:

```python
@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    """
    Generate and send a new OTP code.
    
    Response:
        - success: boolean
        - otp_code: string (6 digits) - only if success=true
        - message: string
        - cooldown_remaining: int (seconds, optional)
    
    Rate limiting:
        - 30-second cooldown between resends
        - 3 OTP generations per 15-minute window
    """
    email = session.get('otp_email')
    purpose = session.get('otp_purpose')
    
    if not email or not purpose:
        return jsonify({
            'success': False,
            'message': 'No active verification session.'
        }), 400
    
    # Check 30-second cooldown
    last_resend = session.get('last_otp_resend', 0)
    now = int(time.time())
    cooldown = 30 - (now - last_resend)
    
    if cooldown > 0:
        return jsonify({
            'success': False,
            'message': f'Please wait {cooldown} seconds before requesting a new code.',
            'cooldown_remaining': cooldown
        }), 429
    
    # Check rate limit (3 per 15 minutes)
    rate_limit_key = f'otp_rate_{email}'
    rate_data = session.get(rate_limit_key, {'count': 0, 'window_start': now})
    
    if now - rate_data['window_start'] > 900:  # 15 minutes
        rate_data = {'count': 0, 'window_start': now}
    
    if rate_data['count'] >= 3:
        return jsonify({
            'success': False,
            'message': 'Too many requests. Please try again in 15 minutes.'
        }), 429
    
    # Invalidate previous OTP
    OTP.query.filter_by(
        email=email,
        purpose=purpose,
        verified=False
    ).update({'verified': True})
    db.session.commit()
    
    # Generate new OTP
    otp_code = generate_otp()
    otp_hash = generate_password_hash(otp_code)
    
    otp_record = OTP(
        email=email,
        otp_hash=otp_hash,
        purpose=purpose,
        created_at=now,
        expires_at=now + 600,
        attempts=0,
        verified=False
    )
    db.session.add(otp_record)
    db.session.commit()
    
    # Update rate limiting
    rate_data['count'] += 1
    session[rate_limit_key] = rate_data
    session['last_otp_resend'] = now
    
    return jsonify({
        'success': True,
        'otp_code': otp_code,
        'message': 'New verification code generated.'
    })
```

**POST /recover (modified)**

Updated to support OTP flow:

```python
@app.route('/recover', methods=['GET', 'POST'])
def recover():
    """
    Handle password recovery with OTP verification.
    
    Request:
        - identifier: string (username or email)
    
    Response:
        - success: boolean
        - otp_code: string (6 digits) - only if user exists
        - message: string
    
    Session data stored:
        - reset_user_id: int
        - otp_email: string
        - otp_purpose: 'password_reset'
    
    Note: Always returns success message for security (timing attack prevention)
    """
    if request.method == 'GET':
        return render_template('recover.html')
    
    identifier = (request.form.get('identifier') or '').strip()
    
    # Validation (existing)
    # ...
    
    # Look up user
    is_email = '@' in identifier
    if is_email:
        user = User.query.filter(func.lower(User.email) == identifier.lower()).first()
    else:
        user = User.query.filter_by(username=identifier).first()
    
    # Always return success for security
    if not user:
        return jsonify({
            'success': True,
            'message': 'If the account exists, a verification code has been sent.',
            'otp_code': None  # No code generated
        })
    
    # Generate OTP
    otp_code = generate_otp()
    otp_hash = generate_password_hash(otp_code)
    
    now = int(time.time())
    otp_record = OTP(
        email=user.email,
        otp_hash=otp_hash,
        purpose='password_reset',
        created_at=now,
        expires_at=now + 600,
        attempts=0,
        verified=False
    )
    db.session.add(otp_record)
    db.session.commit()
    
    # Store reset context in session
    session['reset_user_id'] = user.id
    session['otp_email'] = user.email
    session['otp_purpose'] = 'password_reset'
    
    return jsonify({
        'success': True,
        'otp_code': otp_code,
        'message': 'If the account exists, a verification code has been sent.'
    })
```

**POST /reset-password**

New endpoint for completing password reset:

```python
@app.route('/reset-password', methods=['POST'])
def reset_password():
    """
    Complete password reset after OTP verification.
    
    Request:
        - new_password: string
    
    Response:
        - success: boolean
        - message: string
        - redirect: string (URL)
    
    Requires:
        - session['otp_verified'] = True
        - session['reset_user_id'] = int
    """
    if not session.get('otp_verified'):
        return jsonify({
            'success': False,
            'message': 'Please verify your identity first.'
        }), 403
    
    user_id = session.get('reset_user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'message': 'Reset session expired. Please start over.'
        }), 400
    
    new_password = request.form.get('new_password', '')
    
    # Validate password (same rules as registration)
    errors = []
    if len(new_password) < 8:
        errors.append('Password must be at least 8 characters long.')
    if not re.search(r'[A-Z]', new_password):
        errors.append('Password must contain at least one uppercase letter.')
    if not re.search(r'[a-z]', new_password):
        errors.append('Password must contain at least one lowercase letter.')
    if not re.search(r'\d', new_password):
        errors.append('Password must contain at least one number.')
    if not re.search(r'[^A-Za-z0-9]', new_password):
        errors.append('Password must contain at least one special character.')
    
    if errors:
        return jsonify({'success': False, 'message': ' '.join(errors)}), 400
    
    # Update password
    user = User.query.get(user_id)
    if not user:
        return jsonify({
            'success': False,
            'message': 'User not found.'
        }), 404
    
    user.set_password(new_password)
    db.session.commit()
    
    # Clear session
    session.pop('otp_verified', None)
    session.pop('reset_user_id', None)
    session.pop('otp_email', None)
    session.pop('otp_purpose', None)
    
    return jsonify({
        'success': True,
        'message': 'Password reset successfully. You can now log in.',
        'redirect': url_for('login')
    })
```

### Helper Functions

**generate_otp()**

```python
import secrets

def generate_otp() -> str:
    """
    Generate a cryptographically secure 6-digit OTP code.
    
    Returns:
        String of exactly 6 digits with leading zeros preserved.
    
    Example:
        "042857", "000123", "999999"
    """
    code = secrets.randbelow(1000000)
    return f"{code:06d}"
```

**cleanup_expired_otps()**

```python
def cleanup_expired_otps() -> int:
    """
    Remove OTP records older than 1 hour.
    
    Returns:
        Number of records deleted.
    
    Should be called periodically (e.g., via background task or before_request hook).
    """
    cutoff = int(time.time()) - 3600  # 1 hour ago
    deleted = OTP.query.filter(OTP.created_at < cutoff).delete()
    db.session.commit()
    return deleted
```

### Frontend Integration

**EmailJS Client Setup**

Add to base template or registration/recovery pages:

```html
<!-- EmailJS SDK -->
<script type="text/javascript" src="https://cdn.jsdelivr.net/npm/@emailjs/browser@3/dist/email.min.js"></script>
<script type="text/javascript">
  (function(){
    emailjs.init("dXcaIv5LGMTpybpw2");
  })();
</script>
```

**Registration Form JavaScript**

```javascript
// Handle registration form submission
document.getElementById('registerForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const formData = new FormData(this);
  
  try {
    // Submit to backend
    const response = await fetch('/register', {
      method: 'POST',
      body: formData
    });
    
    const data = await response.json();
    
    if (!data.success) {
      // Show validation errors
      displayErrors(data.errors);
      return;
    }
    
    // Send OTP email via EmailJS
    if (data.otp_code) {
      await emailjs.send('service_cs9uath', 'template_ai1brni', {
        to_email: formData.get('email'),
        otp_code: data.otp_code,
        expiration_minutes: 10
      });
      
      // Show OTP input form
      showOTPForm(data.message);
    }
  } catch (error) {
    showError('Failed to send verification email. Please try again.');
  }
});

// Handle OTP verification
document.getElementById('verifyBtn').addEventListener('click', async function() {
  const otpCode = document.getElementById('otp').value;
  
  const formData = new FormData();
  formData.append('otp_code', otpCode);
  
  try {
    const response = await fetch('/verify-otp', {
      method: 'POST',
      body: formData
    });
    
    const data = await response.json();
    
    if (data.success) {
      showSuccess(data.message);
      setTimeout(() => {
        window.location.href = data.redirect;
      }, 1500);
    } else {
      showError(data.message);
      if (data.attempts_remaining !== undefined) {
        updateAttemptsDisplay(data.attempts_remaining);
      }
    }
  } catch (error) {
    showError('Verification failed. Please try again.');
  }
});

// Handle OTP resend
document.getElementById('resendBtn').addEventListener('click', async function() {
  try {
    const response = await fetch('/resend-otp', {
      method: 'POST'
    });
    
    const data = await response.json();
    
    if (data.success && data.otp_code) {
      // Send new OTP via EmailJS
      const email = document.getElementById('email').value;
      await emailjs.send('service_cs9uath', 'template_ai1brni', {
        to_email: email,
        otp_code: data.otp_code,
        expiration_minutes: 10
      });
      
      showSuccess('New verification code sent!');
      startResendCooldown(30);
    } else {
      showError(data.message);
      if (data.cooldown_remaining) {
        startResendCooldown(data.cooldown_remaining);
      }
    }
  } catch (error) {
    showError('Failed to resend code. Please try again.');
  }
});

function startResendCooldown(seconds) {
  const btn = document.getElementById('resendBtn');
  btn.disabled = true;
  
  let remaining = seconds;
  const interval = setInterval(() => {
    remaining--;
    btn.textContent = `Resend (${remaining}s)`;
    
    if (remaining <= 0) {
      clearInterval(interval);
      btn.disabled = false;
      btn.textContent = 'Resend code';
    }
  }, 1000);
}
```

## Data Models

### OTP Table Schema

```sql
CREATE TABLE otp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) NOT NULL,
    otp_hash VARCHAR(255) NOT NULL,
    purpose VARCHAR(20) NOT NULL,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    verified BOOLEAN NOT NULL DEFAULT 0
);

CREATE INDEX idx_otp_email ON otp(email);
CREATE INDEX idx_otp_lookup ON otp(email, purpose, verified);
CREATE INDEX idx_otp_cleanup ON otp(expires_at);
```

### Session Data Structure

**Registration Session:**
```python
{
    'pending_registration': {
        'username': 'john_doe',
        'email': 'john@example.com',
        'password_hash': 'pbkdf2:sha256:...',
        'timestamp': 1710123456
    },
    'otp_email': 'john@example.com',
    'otp_purpose': 'registration',
    'last_otp_resend': 1710123456,
    'otp_rate_john@example.com': {
        'count': 1,
        'window_start': 1710123456
    }
}
```

**Password Reset Session:**
```python
{
    'reset_user_id': 42,
    'otp_email': 'john@example.com',
    'otp_purpose': 'password_reset',
    'otp_verified': True,
    'last_otp_resend': 1710123456,
    'otp_rate_john@example.com': {
        'count': 2,
        'window_start': 1710123456
    }
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, I identified the following redundancies:

- Properties 1.1 and 1.2 both test 6-digit format - combined into Property 1
- Properties 2.1 and 2.5 both test data storage - combined into Property 2
- Properties 3.1, 3.2, 3.3, 3.4 all test EmailJS configuration - combined into Property 4
- Properties 4.3 and 5.4 both test OTP verification logic - combined into Property 8
- Properties 4.5 and 5.7 both test error handling - combined into Property 9
- Properties 6.1, 6.2, 6.3 all test attempt limiting - combined into Property 11
- Properties 7.1 and 7.2 both test rate limiting - combined into Property 13
- Properties 3.6 and 10.3 both test no OTP on email failure - combined into Property 5
- Properties 11.2 and 4.6 both test registration session storage - combined into Property 19

### Property 1: OTP Format and Randomness

*For any* generated OTP code, the code SHALL be exactly 6 digits with leading zeros preserved and SHALL use a cryptographically secure random number generator.

**Validates: Requirements 1.1, 1.2**

### Property 2: OTP Storage Completeness

*For any* OTP generation request, the stored OTP record SHALL contain the email address, creation timestamp, expiration timestamp, purpose (registration or password_reset), and hashed code.

**Validates: Requirements 2.1, 2.5**

### Property 3: OTP Expiration Calculation

*For any* OTP record, the expiration timestamp SHALL equal the creation timestamp plus 600 seconds (10 minutes).

**Validates: Requirements 2.2**

### Property 4: EmailJS Configuration

*For any* OTP email sent, the client SHALL use service ID "service_cs9uath", template ID "template_ai1brni", and public key "dXcaIv5LGMTpybpw2".

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

### Property 5: No OTP on Email Failure

*For any* OTP generation request where email sending fails, no OTP record SHALL exist in the database.

**Validates: Requirements 3.6, 10.3**

### Property 6: Email Payload Completeness

*For any* OTP email payload, it SHALL include the 6-digit OTP code and expiration time in minutes.

**Validates: Requirements 3.5**

### Property 7: Registration Before User Creation

*For any* registration submission, an OTP record SHALL exist for the email address before any User record is created for that email.

**Validates: Requirements 4.1**

### Property 8: OTP Verification Logic

*For any* OTP verification attempt, the system SHALL hash the submitted code and compare it to the stored hash, accepting the code if and only if the hashes match, the OTP is not expired, the OTP has not been verified, and attempts < 3.

**Validates: Requirements 4.3, 5.4, 9.2**

### Property 9: OTP Verification Error Handling

*For any* invalid or expired OTP verification attempt, the system SHALL return an error response with a specific reason (invalid code, expired, or too many attempts) and SHALL NOT create or modify user accounts.

**Validates: Requirements 4.5, 5.7**

### Property 10: User Creation After Valid OTP

*For any* valid OTP verification for registration purpose, a User record SHALL be created with the username, email, and password_hash from the session data.

**Validates: Requirements 4.4**

### Property 11: Attempt Limiting

*For any* OTP code, after 3 failed verification attempts, the OTP SHALL be considered invalid and all subsequent verification attempts SHALL be rejected.

**Validates: Requirements 6.1, 6.2, 6.3**

### Property 12: Attempt Counter Increment

*For any* failed OTP verification, the attempts field SHALL be incremented by exactly 1.

**Validates: Requirements 6.4**

### Property 13: Rate Limiting Window

*For any* email address, the system SHALL allow a maximum of 3 OTP generation requests within any 15-minute window, rejecting the 4th request with an error.

**Validates: Requirements 7.1, 7.2**

### Property 14: Rate Limit Tracking

*For any* OTP generation request, the system SHALL store or update the request count and window start timestamp in the session.

**Validates: Requirements 7.3**

### Property 15: Rate Limit Window Reset

*For any* email address where 15 minutes have elapsed since the window start, the next OTP generation request SHALL reset the counter to 1 and start a new window.

**Validates: Requirements 7.4**

### Property 16: Resend Invalidates Previous OTP

*For any* OTP resend request, all previous OTP records for the same email and purpose SHALL be marked as verified=True (invalidated).

**Validates: Requirements 8.2**

### Property 17: Resend Cooldown

*For any* email address, OTP resend requests within 30 seconds of the last resend SHALL be rejected with a cooldown error.

**Validates: Requirements 8.4**

### Property 18: OTP Hashing

*For any* OTP code stored in the database, the otp_hash field SHALL contain a hashed value (not the plaintext code), and the plaintext code SHALL NOT appear in any database field or log.

**Validates: Requirements 9.1, 9.3**

### Property 19: OTP Hash Round Trip

*For any* generated OTP code, hashing the code and then verifying it against the stored hash SHALL succeed.

**Validates: Requirements 9.2**

### Property 20: Registration Session Storage

*For any* registration submission that generates an OTP, the session SHALL contain pending_registration data with username, email, and password_hash fields.

**Validates: Requirements 4.6, 11.2**

### Property 21: Password Reset Session Storage

*For any* password reset request that generates an OTP, the session SHALL contain reset_user_id with the user's ID.

**Validates: Requirements 11.3**

### Property 22: Session Cleanup After Completion

*For any* successful OTP verification and account operation completion, all OTP-related session data (pending_registration, reset_user_id, otp_email, otp_purpose, otp_verified) SHALL be cleared.

**Validates: Requirements 11.4**

### Property 23: Password Update After Valid Reset

*For any* password reset with valid OTP verification, the user's password_hash SHALL be updated to the new password hash.

**Validates: Requirements 5.6**

### Property 24: User Lookup by Username or Email

*For any* password recovery request, the system SHALL successfully look up users by either username (exact match) or email (case-insensitive match).

**Validates: Requirements 5.1**

### Property 25: OTP Invalidation After Success

*For any* successfully verified OTP, the verified field SHALL be set to True, preventing reuse of the same code.

**Validates: Requirements 2.4**

### Property 26: Expired OTP Rejection

*For any* OTP verification attempt where current_time > expires_at, the verification SHALL be rejected with an "expired" error.

**Validates: Requirements 2.3**

### Property 27: OTP Cleanup

*For any* OTP record where created_at is more than 1 hour old, the cleanup function SHALL delete the record.

**Validates: Requirements 9.4**

### Property 28: Attempts Remaining Feedback

*For any* failed OTP verification where attempts < 3, the response SHALL include attempts_remaining = (3 - attempts).

**Validates: Requirements 12.4**

### Property 29: Error Message Specificity

*For any* OTP verification failure, the error message SHALL indicate the specific reason: "Invalid verification code" for wrong code, "Verification code has expired" for expired OTP, or "Too many failed attempts" for attempts >= 3.

**Validates: Requirements 12.2**

### Property 30: No Sequential Patterns

*For any* sequence of 100 generated OTP codes, no more than 2 consecutive codes SHALL differ by exactly 1 (preventing obvious sequential patterns).

**Validates: Requirements 1.3**

## Error Handling

### OTP Generation Errors

**Invalid Email Format**
- Validation occurs before OTP generation
- Returns 400 Bad Request with field-specific error
- No OTP record created

**Rate Limit Exceeded**
- Returns 429 Too Many Requests
- Error message: "Too many requests. Please try again in X minutes."
- Includes retry-after information

**Database Errors**
- Catches SQLAlchemy exceptions during OTP creation
- Rolls back transaction
- Returns 500 Internal Server Error
- Logs error details for admin review

**Email Service Errors**
- Client-side EmailJS errors caught in JavaScript
- Displays user-friendly message: "Failed to send verification email. Please try again."
- No OTP record created (backend doesn't know about client failure)
- User can retry within rate limits

### OTP Verification Errors

**Invalid OTP Format**
- Returns 400 Bad Request
- Error message: "Invalid OTP format. Please enter a 6-digit code."
- Does not increment attempt counter

**OTP Not Found**
- Returns 404 Not Found
- Error message: "No active verification code found. Please request a new one."
- Occurs when no OTP exists or all OTPs are verified/expired

**OTP Expired**
- Returns 400 Bad Request
- Error message: "Verification code has expired. Please request a new one."
- Does not increment attempt counter (already invalid)

**Invalid OTP Code**
- Returns 400 Bad Request
- Error message: "Invalid verification code. X attempts remaining."
- Increments attempt counter
- After 3 attempts, OTP becomes invalid

**Session Expired**
- Returns 400 Bad Request
- Error message: "Verification session expired. Please start over."
- Occurs when session data is missing or older than 15 minutes

**Database Errors**
- Catches SQLAlchemy exceptions
- Rolls back transaction
- Returns 500 Internal Server Error
- Logs error details

### Password Reset Errors

**User Not Found**
- Returns success message for security (timing attack prevention)
- Message: "If the account exists, a verification code has been sent."
- No OTP generated
- No indication that user doesn't exist

**Invalid Password Format**
- Returns 400 Bad Request
- Lists all password requirements not met
- Does not update password

**OTP Not Verified**
- Returns 403 Forbidden
- Error message: "Please verify your identity first."
- Prevents password reset without OTP verification

### Edge Cases

**Multiple Concurrent OTP Requests**
- Rate limiting prevents rapid requests
- Each request creates a new OTP record
- Previous OTPs remain valid until expired or verified
- Resend endpoint explicitly invalidates previous OTPs

**Session Timeout During Verification**
- 15-minute inactivity timeout
- User must restart registration/reset flow
- OTP records remain in database until cleanup

**Browser Refresh During OTP Flow**
- Session data persists across page refreshes
- OTP input form can be re-displayed
- User can continue verification

**Expired OTP with Valid Session**
- User can request resend
- New OTP generated with new expiration
- Session data preserved

**Database Cleanup During Active Verification**
- Cleanup only removes records older than 1 hour
- Active OTPs (< 10 minutes old) are never cleaned up
- No impact on ongoing verifications

## Testing Strategy

### Unit Testing Approach

Unit tests will focus on specific examples, edge cases, and error conditions:

**OTP Generation Tests**
- Test that `generate_otp()` returns exactly 6 digits
- Test leading zero preservation (e.g., "000123")
- Test boundary values (000000, 999999)

**OTP Hashing Tests**
- Test that stored OTP is hashed, not plaintext
- Test that `check_password_hash()` correctly verifies OTP
- Test that wrong OTP fails verification

**Expiration Tests**
- Test OTP created with correct expiration (created_at + 600)
- Test `is_expired()` returns True after 10 minutes
- Test `is_expired()` returns False before 10 minutes

**Attempt Tracking Tests**
- Test `increment_attempts()` increases counter by 1
- Test `is_valid()` returns False after 3 attempts
- Test attempt counter persists across requests

**Rate Limiting Tests**
- Test 4th request within 15 minutes is rejected
- Test request after 15 minutes resets counter
- Test 30-second cooldown between resends

**Session Management Tests**
- Test registration data stored in session
- Test session cleared after successful verification
- Test session timeout after 15 minutes

**Error Handling Tests**
- Test invalid OTP format returns 400
- Test expired OTP returns appropriate error
- Test missing session data returns 400

### Property-Based Testing Approach

Property tests will verify universal properties across all inputs using a PBT library (e.g., Hypothesis for Python). Each test will run a minimum of 100 iterations.

**PBT Library Selection: Hypothesis**
- Mature Python property-based testing library
- Integrates with pytest
- Provides strategies for generating test data
- Supports stateful testing for complex flows

**Property Test Configuration**
```python
from hypothesis import given, settings, strategies as st

@settings(max_examples=100)
@given(...)
def test_property_name(...):
    # Test implementation
```

**Property Test Tags**
Each property test will include a comment referencing the design document:
```python
# Feature: email-otp-verification, Property 1: OTP Format and Randomness
```

**Property Tests to Implement**

1. **OTP Format Property** (Property 1)
   - Generate 100 OTPs
   - Assert all are exactly 6 digits
   - Assert all are numeric strings

2. **Expiration Calculation Property** (Property 3)
   - Generate OTPs with random creation timestamps
   - Assert expires_at = created_at + 600 for all

3. **Hash Round Trip Property** (Property 19)
   - Generate random 6-digit codes
   - Hash each code
   - Verify each code against its hash
   - Assert all verifications succeed

4. **Attempt Limiting Property** (Property 11)
   - Generate OTP with random valid code
   - Submit 3 wrong codes
   - Submit correct code
   - Assert 4th attempt is rejected

5. **Rate Limit Window Property** (Property 13)
   - Generate random email address
   - Make 3 OTP requests within 15 minutes
   - Make 4th request
   - Assert 4th request is rejected

6. **Expiration Rejection Property** (Property 26)
   - Generate OTP with created_at > 10 minutes ago
   - Attempt verification with correct code
   - Assert verification is rejected with "expired" error

7. **Invalidation After Success Property** (Property 25)
   - Generate OTP with random code
   - Verify with correct code (succeeds)
   - Verify again with same code
   - Assert second verification fails

8. **Session Cleanup Property** (Property 22)
   - Generate random registration data
   - Store in session
   - Complete verification
   - Assert all OTP session keys are removed

9. **No Sequential Patterns Property** (Property 30)
   - Generate 100 consecutive OTPs
   - Count pairs that differ by exactly 1
   - Assert count <= 2

10. **User Lookup Property** (Property 24)
    - Generate random username and email
    - Create user
    - Lookup by username (exact)
    - Lookup by email (case-insensitive)
    - Assert both lookups return same user

11. **Password Update Property** (Property 23)
    - Generate random user and new password
    - Complete OTP verification
    - Submit password reset
    - Assert password_hash changed

12. **Resend Invalidation Property** (Property 16)
    - Generate first OTP
    - Request resend
    - Assert first OTP has verified=True

13. **Error Message Specificity Property** (Property 29)
    - Test wrong code → "Invalid verification code"
    - Test expired OTP → "Verification code has expired"
    - Test 3 failed attempts → "Too many failed attempts"
    - Assert each error has correct message

### Integration Testing

Integration tests will verify end-to-end flows:

**Registration Flow Integration Test**
1. Submit registration form
2. Verify OTP generated and session created
3. Submit valid OTP
4. Verify User created and session cleared
5. Verify login works with new credentials

**Password Reset Flow Integration Test**
1. Submit recovery request
2. Verify OTP generated
3. Submit valid OTP
4. Submit new password
5. Verify password updated
6. Verify login works with new password

**EmailJS Integration Test** (Manual/E2E)
- Verify EmailJS configuration in client code
- Test actual email delivery in staging environment
- Verify email contains OTP code and expiration

### Test Coverage Goals

- Unit test coverage: >90% for OTP-related functions
- Property test coverage: All 30 correctness properties
- Integration test coverage: Both registration and password reset flows
- Error path coverage: All error conditions in Error Handling section

