from flask import Flask, render_template, Response, redirect, url_for, request, session, abort, send_file
import cv2
from ultralytics import YOLO
import threading
import time
import json
from flask import jsonify
import os
import sqlite3
import tempfile
import shutil
from flask_sqlalchemy import SQLAlchemy
import re
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text, literal_column, func, and_
from sqlalchemy import or_, asc, desc
from functools import wraps
from uuid import uuid4
from werkzeug.utils import secure_filename
try:
    import serial
except Exception:
    serial = None

try:
    from b2sdk.v2 import InMemoryAccountInfo, B2Api
    B2_DEPS_AVAILABLE = True
except ImportError:
    B2_DEPS_AVAILABLE = False

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Database configuration (SQLite file-based)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads', 'reports')
DETECTION_UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads', 'detections')
ALLOWED_REPORT_IMAGE_EXTS = {'jpg', 'jpeg', 'png'}
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

# Initialize SQLAlchemy
db = SQLAlchemy(app)

ALLOWED_ROLES = {'admin', 'user'}
ALLOWED_STATUSES = {'active', 'suspended', 'locked', 'archived'}
BACKUP_ALLOWED_EXTS = {'db', 'sqlite', 'sqlite3', 'sql'}
BACKUP_DIR = os.path.join(app.root_path, 'backups')
BACKUP_LOG_PATH = os.path.join(app.root_path, 'backup_history.log')
BACKUP_LOCK = threading.Lock()
RESTORE_STATE = {"in_progress": False}


def _get_current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    try:
        return User.query.get(int(uid))
    except Exception:
        return None


def _is_admin(user) -> bool:
    if not user:
        return False
    role = getattr(user, 'role', None)
    if role is None:
        return False
    return str(role).strip().lower() == 'admin'


def _require_admin():
    cu = _get_current_user()
    if not _is_admin(cu):
        abort(403)
    return cu


@app.before_request
def _block_writes_during_restore():
    if not RESTORE_STATE.get("in_progress"):
        return None
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return None
    allowed_paths = {"/admin/backups/import", "/admin/backups/export"}
    if request.path in allowed_paths:
        return None
    return ("Restore in progress. Please try again shortly.", 503)


def _login_required():
    cu = _get_current_user()
    if not cu:
        return redirect(url_for('login', next=request.path))
    return cu


def _require_role(*roles):
    cu = _login_required()
    if not isinstance(cu, User):
        return cu
    role = str(getattr(cu, 'role', '') or '').strip().lower()
    allowed = {str(r).strip().lower() for r in roles}
    if role not in allowed:
        abort(403)
    return cu


def login_required_view(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        cu = _login_required()
        if not isinstance(cu, User):
            return cu
        return fn(*args, **kwargs)
    return wrapper


def _get_db_path():
    # Check instance folder first (standard Flask location)
    instance_db = os.path.join(app.instance_path, 'users.db')
    if os.path.exists(instance_db):
        return instance_db

    db_path = os.path.join(app.root_path, 'users.db')
    if os.path.exists(db_path):
        return db_path
    return 'users.db'


def _backup_log_append(entry: dict):
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        line = json.dumps(entry, separators=(",", ":"), ensure_ascii=False)
        with open(BACKUP_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _backup_log_read(limit: int = 50):
    if not os.path.exists(BACKUP_LOG_PATH):
        return []
    try:
        with open(BACKUP_LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        items = []
        for line in lines[-limit:]:
            try:
                items.append(json.loads(line.strip()))
            except Exception:
                continue
        return list(reversed(items))
    except Exception:
        return []


def _validate_backup_db(path: str):
    try:
        conn = sqlite3.connect(path)
        check = conn.execute("PRAGMA integrity_check").fetchone()
        if not check or str(check[0]).lower() != 'ok':
            conn.close()
            return False, 'Database integrity check failed.'
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        existing = {r[0] for r in rows}
        required = {'user', 'report', 'detection'}
        if not required.issubset(existing):
            conn.close()
            return False, 'Backup schema is missing required tables.'
        conn.close()
        return True, ''
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return False, 'Backup validation failed.'


def require_admin_view(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        _require_admin()
        return fn(*args, **kwargs)
    return wrapper


def _get_csrf_token() -> str:
    token = session.get('csrf_token')
    if not token:
        token = os.urandom(16).hex()
        session['csrf_token'] = token
    return token


def _validate_csrf() -> None:
    token = session.get('csrf_token')
    form_token = request.form.get('csrf_token')
    if not token or not form_token or token != form_token:
        abort(400)


def _redirect_back(default_endpoint: str = 'users_page'):
    nxt = request.form.get('next') or request.args.get('next')
    if nxt:
        return redirect(nxt)
    return redirect(url_for(default_endpoint))

# User model for authentication (accounts only)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    status = db.Column(db.String(20), nullable=False, default='active')
    suspended_until = db.Column(db.Integer, nullable=True)
    false_reports_count = db.Column(db.Integer, nullable=False, default=0)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    obstruction_type = db.Column(db.String(50), nullable=True)
    photo_path = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))
    status_updated_at = db.Column(db.Integer, nullable=True, default=lambda: int(time.time()))
    is_fixed = db.Column(db.Boolean, nullable=False, default=False)
    fixed_at = db.Column(db.Integer, nullable=True)
    is_false_report = db.Column(db.Boolean, nullable=False, default=False)
    thumbs_up_count = db.Column(db.Integer, nullable=False, default=0)
    thumbs_down_count = db.Column(db.Integer, nullable=False, default=0)

    @property
    def created_at_iso(self) -> str:
        try:
            return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(self.created_at)))
        except Exception:
            return str(self.created_at)

    @property
    def status_updated_at_iso(self) -> str:
        try:
            val = int(self.status_updated_at) if self.status_updated_at else int(self.created_at)
            return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(val))
        except Exception:
            return ''


class Reaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    reaction_type = db.Column(db.String(10), nullable=False)  # 'up' or 'down'
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))
    updated_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()), onupdate=lambda: int(time.time()))

    __table_args__ = (
        db.UniqueConstraint('report_id', 'user_id', name='unique_user_report_reaction'),
    )


class Detection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))
    status_updated_at = db.Column(db.Integer, nullable=True, default=lambda: int(time.time()))
    is_fixed = db.Column(db.Boolean, nullable=False, default=False)
    fixed_at = db.Column(db.Integer, nullable=True)
    detected_class = db.Column(db.String(50), nullable=True)
    final_class = db.Column(db.String(50), nullable=True)
    confidence_score = db.Column(db.Float, nullable=True)
    snapshot_image_path = db.Column(db.String(512), nullable=True)
    detection_source = db.Column(db.String(50), nullable=True)
    review_status = db.Column(db.String(20), nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reviewed_at = db.Column(db.Integer, nullable=True)
    visibility_scope = db.Column(db.String(20), nullable=True)

    @property
    def created_at_iso(self) -> str:
        try:
            return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(self.created_at)))
        except Exception:
            return str(self.created_at)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))

    @property
    def created_at_iso(self) -> str:
        try:
            return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(self.created_at)))
        except Exception:
            return str(self.created_at)


class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()), onupdate=lambda: int(time.time()))

# Ensure database tables are created safely within app context
with app.app_context():
    db.create_all()
    try:
        cols = db.session.execute(text("PRAGMA table_info(user)")).fetchall()
        existing = {str(c[1]).lower() for c in cols}
        if 'role' not in existing:
            db.session.execute(text("ALTER TABLE user ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'"))
        if 'status' not in existing:
            db.session.execute(text("ALTER TABLE user ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active'"))
        if 'suspended_until' not in existing:
            db.session.execute(text("ALTER TABLE user ADD COLUMN suspended_until INTEGER"))
        if 'false_reports_count' not in existing:
            db.session.execute(text("ALTER TABLE user ADD COLUMN false_reports_count INTEGER NOT NULL DEFAULT 0"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        cols = db.session.execute(text("PRAGMA table_info(report)")).fetchall()
        existing = {str(c[1]).lower() for c in cols}
        if existing:
            if 'created_at' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN created_at INTEGER"))
            if 'status_updated_at' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN status_updated_at INTEGER"))
            if 'latitude' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN latitude REAL"))
            if 'longitude' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN longitude REAL"))
            if 'obstruction_type' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN obstruction_type VARCHAR(50)"))
            if 'photo_path' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN photo_path VARCHAR(512)"))
            if 'is_fixed' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN is_fixed BOOLEAN NOT NULL DEFAULT 0"))
            if 'fixed_at' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN fixed_at INTEGER"))
            if 'is_false_report' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN is_false_report BOOLEAN NOT NULL DEFAULT 0"))
            if 'thumbs_up_count' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN thumbs_up_count INTEGER NOT NULL DEFAULT 0"))
            if 'thumbs_down_count' not in existing:
                db.session.execute(text("ALTER TABLE report ADD COLUMN thumbs_down_count INTEGER NOT NULL DEFAULT 0"))
            try:
                db.session.execute(text("UPDATE report SET status_updated_at = created_at WHERE status_updated_at IS NULL"))
            except Exception:
                pass
            db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        cols = db.session.execute(text("PRAGMA table_info(detection)")).fetchall()
        existing = {str(c[1]).lower() for c in cols}
        if existing:
            if 'created_at' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN created_at INTEGER"))
            if 'status_updated_at' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN status_updated_at INTEGER"))
            if 'label' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN label VARCHAR(50) NOT NULL DEFAULT ''"))
            if 'confidence' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN confidence REAL NOT NULL DEFAULT 0"))
            if 'latitude' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN latitude REAL NOT NULL DEFAULT 0"))
            if 'longitude' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN longitude REAL NOT NULL DEFAULT 0"))
            if 'is_fixed' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN is_fixed BOOLEAN NOT NULL DEFAULT 0"))
            if 'fixed_at' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN fixed_at INTEGER"))
            if 'detected_class' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN detected_class VARCHAR(50)"))
            if 'final_class' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN final_class VARCHAR(50)"))
            if 'confidence_score' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN confidence_score REAL"))
            if 'snapshot_image_path' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN snapshot_image_path VARCHAR(512)"))
            if 'detection_source' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN detection_source VARCHAR(50)"))
            if 'review_status' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN review_status VARCHAR(20)"))
            if 'reviewed_by' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN reviewed_by INTEGER"))
            if 'reviewed_at' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN reviewed_at INTEGER"))
            if 'visibility_scope' not in existing:
                db.session.execute(text("ALTER TABLE detection ADD COLUMN visibility_scope VARCHAR(20)"))
            try:
                db.session.execute(text("UPDATE detection SET status_updated_at = created_at WHERE status_updated_at IS NULL"))
            except Exception:
                pass
            db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        cols = db.session.execute(text("PRAGMA table_info(notification)")).fetchall()
        existing = {str(c[1]).lower() for c in cols}
        if existing:
            if 'created_at' not in existing:
                db.session.execute(text("ALTER TABLE notification ADD COLUMN created_at INTEGER"))
            if 'is_read' not in existing:
                db.session.execute(text("ALTER TABLE notification ADD COLUMN is_read BOOLEAN NOT NULL DEFAULT 0"))
            if 'link' not in existing:
                db.session.execute(text("ALTER TABLE notification ADD COLUMN link VARCHAR(500)"))
            db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        cols = db.session.execute(text("PRAGMA table_info(settings)")).fetchall()
        existing = {str(c[1]).lower() for c in cols}
        if not existing:
            # Table created by db.create_all(), but if we need to migrate or check
            pass
        
        # Seed default settings if not present
        defaults = {
            'fixed_defect_expiration_days': '30',
            'auto_fix_threshold': '3'
        }
        for k, v in defaults.items():
            s = Settings.query.filter_by(key=k).first()
            if not s:
                db.session.add(Settings(key=k, value=v))
        db.session.commit()
    except Exception:
        db.session.rollback()

model = YOLO("best.pt")  # use your model path
camera = None
gps_latest = {"lat": None, "lon": None, "valid": False, "ts": None}
gps_thread = None
gps_stop_event = threading.Event()
gps_lock = threading.Lock()
last_log_time = 0.0
LOG_COOLDOWN_SEC = 2.0
gps_port_cfg = None
gps_baud_cfg = None
_gps_started = False
GPS_VALID_GRACE_SEC = 1.0

def nmea_to_decimal(coord, direction):
    if not coord or not direction:
        return None
    try:
        if "," in coord:
            coord = coord.split(",")[0]
        if "." not in coord:
            return None
        # Use direction to determine degree length: lat (N/S) = 2 deg digits, lon (E/W) = 3 deg digits
        deg_len = 2 if direction in ("N", "S") else 3
        deg = float(coord[:deg_len])
        minutes = float(coord[deg_len:])
        dec = deg + minutes / 60.0
        if direction in ("S", "W"):
            dec = -dec
        return dec
    except Exception:
        return None

def parse_rmc(fields):
    if len(fields) < 7:
        return None, None, False
    status = fields[2] if len(fields) > 2 else "V"
    lat = nmea_to_decimal(fields[3] if len(fields) > 3 else None, fields[4] if len(fields) > 4 else None)
    lon = nmea_to_decimal(fields[5] if len(fields) > 5 else None, fields[6] if len(fields) > 6 else None)
    valid = status == "A" and lat is not None and lon is not None
    return lat, lon, valid

def parse_gga(fields):
    # GGA: $GxGGA, time, lat, N/S, lon, E/W, fix_quality, num_sats, ...
    # fix_quality: 0 = invalid, 1 = GPS fix, 2 = DGPS fix, 4 = RTK, etc.
    if len(fields) < 7:
        return None, None, False
    lat = nmea_to_decimal(fields[2] if len(fields) > 2 else None, fields[3] if len(fields) > 3 else None)
    lon = nmea_to_decimal(fields[4] if len(fields) > 4 else None, fields[5] if len(fields) > 5 else None)
    try:
        fix_q = int(fields[6]) if len(fields) > 6 and fields[6] != '' else 0
    except Exception:
        fix_q = 0
    valid = (fix_q > 0) and (lat is not None) and (lon is not None)
    return lat, lon, valid

def gps_reader_loop(port, baud):
    global gps_latest
    if serial is None:
        return
    try:
        ser = serial.Serial(port=port, baudrate=baud, timeout=1)
        try:
            print(f"[GPS] Opened {port} @ {baud}")
        except Exception:
            pass
    except Exception:
        ser = None
    while not gps_stop_event.is_set():
        try:
            if ser is None or not ser.is_open:
                try:
                    ser = serial.Serial(port=port, baudrate=baud, timeout=1)
                    try:
                        print(f"[GPS] Reopened {port} @ {baud}")
                    except Exception:
                        pass
                except Exception:
                    time.sleep(1.0)
                    continue
            line = ser.readline().decode(errors="ignore").strip()
            if not line:
                continue
            parts = line.split(",")
            if line.startswith("$GPRMC") or line.startswith("$GNRMC"):
                lat, lon, valid = parse_rmc(parts)
            elif line.startswith("$GPGGA") or line.startswith("$GNGGA"):
                lat, lon, valid = parse_gga(parts)
            else:
                continue
            if lat is not None and lon is not None:
                nowt = time.time()
                with gps_lock:
                    prev_valid = bool(gps_latest.get("valid"))
                    prev_ts = gps_latest.get("ts") or 0
                    # If current sentence says invalid but we had a recent valid fix, keep it valid within grace window
                    eff_valid = bool(valid)
                    if not eff_valid and prev_valid and (nowt - prev_ts) <= GPS_VALID_GRACE_SEC:
                        eff_valid = True
                    gps_latest = {"lat": lat, "lon": lon, "valid": eff_valid, "ts": nowt}
                if valid:
                    try:
                        print(f"[GPS] Fix lat={lat:.6f} lon={lon:.6f}")
                    except Exception:
                        pass
        except Exception:
            time.sleep(0.2)
            continue
    try:
        if ser is not None:
            ser.close()
    except Exception:
        pass

def ensure_gps_thread():
    global gps_thread, gps_port_cfg, gps_baud_cfg
    if gps_thread is None or not gps_thread.is_alive():
        gps_stop_event.clear()
        port = os.environ.get("GPS_SERIAL_PORT", "COM3")
        baud = int(os.environ.get("GPS_BAUD", "4800"))
        gps_port_cfg = port
        gps_baud_cfg = baud
        gps_thread = threading.Thread(target=gps_reader_loop, args=(port, baud), daemon=True)
        gps_thread.start()

def open_camera(index=0):
    global camera
    if camera is None or not getattr(camera, 'isOpened', lambda: False)():
        cam = None
        if os.name == 'nt' and hasattr(cv2, 'CAP_DSHOW'):
            cam = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if cam is not None and not cam.isOpened():
                cam.release()
                cam = None
        if cam is None:
            cam = cv2.VideoCapture(index)
        camera = cam
    ensure_gps_thread()

def close_camera():
    global camera
    if camera is not None:
        try:
            camera.release()
        except Exception:
            pass
        camera = None

def _save_detection_snapshot(frame):
    try:
        os.makedirs(DETECTION_UPLOAD_FOLDER, exist_ok=True)
        fname = f"{uuid4().hex}.jpg"
        abs_path = os.path.join(DETECTION_UPLOAD_FOLDER, fname)
        ok = cv2.imwrite(abs_path, frame)
        if ok:
            return f"uploads/detections/{fname}"
    except Exception:
        return None
    return None

def generate_frames():
    global camera
    while True:
        if camera is None:
            break
        success, frame = camera.read()
        if not success:
            break
        results = model(frame, stream=True)
        for r in results:
            frame = r.plot()  # draw bounding boxes
            try:
                if hasattr(r, "boxes") and r.boxes is not None and len(r.boxes) > 0:
                    now = time.time()
                    if now - globals().get("last_log_time", 0.0) >= LOG_COOLDOWN_SEC:
                        with gps_lock:
                            lat = gps_latest.get("lat")
                            lon = gps_latest.get("lon")
                            valid = gps_latest.get("valid")
                            gts = gps_latest.get("ts") or 0
                        is_recent = (now - gts) <= GPS_VALID_GRACE_SEC
                        eff_valid = bool(valid) and is_recent
                        confs = r.boxes.conf.tolist() if getattr(r.boxes, "conf", None) is not None else []
                        clss = r.boxes.cls.tolist() if getattr(r.boxes, "cls", None) is not None else []
                        idxs = list(range(len(confs))) if confs else []
                        idxs = [i for i in idxs if confs[i] is not None and confs[i] >= 0.5]
                        if idxs:
                            best_i = max(idxs, key=lambda i: confs[i])
                            best_conf = float(confs[best_i])
                            best_cls = int(clss[best_i]) if clss else 0
                            names = getattr(model, "names", {}) or {}
                            best_label = str(names.get(best_cls, str(best_cls)))
                            if eff_valid and lat is not None and lon is not None:
                                try:
                                    with app.app_context():
                                        if best_conf > 0.60:
                                            row = Detection(
                                                label=best_label,
                                                confidence=best_conf,
                                                confidence_score=best_conf,
                                                latitude=float(lat),
                                                longitude=float(lon),
                                                created_at=int(now),
                                                status_updated_at=int(now),
                                                detected_class=best_label,
                                                final_class=best_label,
                                                detection_source='ai_survey',
                                                review_status='confirmed',
                                                visibility_scope='public',
                                            )
                                        else:
                                            snapshot_rel = _save_detection_snapshot(frame)
                                            row = Detection(
                                                label=best_label,
                                                confidence=best_conf,
                                                confidence_score=best_conf,
                                                latitude=float(lat),
                                                longitude=float(lon),
                                                created_at=int(now),
                                                status_updated_at=int(now),
                                                detected_class=best_label,
                                                final_class=None,
                                                snapshot_image_path=snapshot_rel,
                                                detection_source='ai_survey',
                                                review_status='pending',
                                                visibility_scope='admin_only',
                                            )
                                        db.session.add(row)
                                        db.session.commit()
                                except Exception:
                                    db.session.rollback()
                            globals()["last_log_time"] = now
                            try:
                                if eff_valid and lat is not None and lon is not None:
                                    ts_iso = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))
                                    if best_conf > 0.60:
                                        print(f"{best_label} detected at ({float(lon)}, {float(lat)}) at {ts_iso}")
                                    else:
                                        print(f"{best_label} queued for review at ({float(lon)}, {float(lat)}) at {ts_iso}")
                                else:
                                    ts_iso = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))
                                    print(f"{best_label} detected but GPS fix invalid/stale at {ts_iso}")
                            except Exception:
                                pass
            except Exception:
                pass

        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.context_processor
def inject_notifications():
    uid = session.get('user_id')
    count = 0
    if uid:
        try:
            count = Notification.query.filter_by(user_id=int(uid), is_read=False).count()
        except Exception:
            pass
    return dict(unread_notifications_count=count)

@app.route('/')
def root_redirect():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        errors = []
        field_errors = {"username": [], "password": []}

        if not identifier:
            errors.append('Username or email is required.')
            field_errors["username"].append('Username or email is required.')
        if not password:
            errors.append('Password is required.')
            field_errors["password"].append('Password is required.')

        user = None
        if not errors:
            try:
                is_email = bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', identifier))
                if is_email:
                    user = User.query.filter(func.lower(User.email) == identifier.lower()).first()
                else:
                    user = User.query.filter_by(username=identifier).first()
            except Exception:
                user = None
                errors.append('Unable to process login right now. Please try again.')

        if not errors:
            if user is None or (not user.check_password(password)):
                errors.append('Invalid username or email, or password.')
                field_errors["password"].append('Invalid username or email, or password.')

        if not errors:
            user_status = str(getattr(user, 'status', '') or '').strip().lower()
            if user_status == 'locked':
                errors.append('Your account is locked. Please contact an administrator.')
                field_errors["username"].append('Your account is locked. Please contact an administrator.')
            elif user_status == 'suspended':
                now_ts = int(time.time())
                until_ts = getattr(user, 'suspended_until', None)
                if until_ts is None:
                    until_ts = now_ts + 5 * 60
                    user.suspended_until = int(until_ts)
                    try:
                        db.session.commit()
                    except Exception:
                        db.session.rollback()

                if int(until_ts) > now_ts:
                    remaining = int(until_ts) - now_ts
                    minutes = remaining // 60
                    seconds = remaining % 60
                    errors.append(f'Your account is suspended. Try again in {minutes}m {seconds}s.')
                    field_errors["username"].append(f'Your account is suspended. Try again in {minutes}m {seconds}s.')
                else:
                    user.status = 'active'
                    user.suspended_until = None
                    try:
                        db.session.commit()
                    except Exception:
                        db.session.rollback()

        if errors:
            return render_template('/login.html', errors=errors, field_errors=field_errors, values={"username": identifier})

        session['user_id'] = int(user.id)
        _get_csrf_token()
        if _is_admin(user):
            return redirect(url_for('index_page'))
        return redirect(url_for('map_page'))

    return render_template('/login.html', errors=[], field_errors={"username": [], "password": []}, values={})


@app.route('/recover', methods=['GET', 'POST'])
def recover():
    errors = []
    field_errors = {"identifier": []}
    values = {}
    show_otp = False
    info_msg = None

    if request.method == 'POST':
        identifier = (request.form.get('identifier') or '').strip()
        values = {"identifier": identifier}

        if not identifier:
            errors.append('Username or email is required.')
            field_errors["identifier"].append('Username or email is required.')
        else:
            if '@' in identifier and not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', identifier):
                errors.append('Enter a valid email address.')
                field_errors["identifier"].append('Enter a valid email address.')

        if not errors:
            now_ts = int(time.time())
            last_ts = int(session.get('recover_last_ts') or 0)
            count = int(session.get('recover_count') or 0)
            if now_ts - last_ts <= 60:
                count += 1
            else:
                count = 1
            session['recover_last_ts'] = now_ts
            session['recover_count'] = count
            if count > 5:
                errors.append('Please wait before trying again.')
                field_errors["identifier"].append('Please wait before trying again.')

        if not errors:
            try:
                is_email = bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', identifier))
                if is_email:
                    _ = User.query.filter(func.lower(User.email) == identifier.lower()).first()
                else:
                    _ = User.query.filter_by(username=identifier).first()
            except Exception:
                pass
            show_otp = True
            info_msg = 'If the account exists, a verification code has been sent.'

    return render_template(
        '/recover.html',
        errors=errors,
        field_errors=field_errors,
        values=values,
        show_otp=show_otp,
        info_msg=info_msg,
    )


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip()
        password = request.form.get('password') or ''

        errors = []
        field_errors = {"username": [], "email": [], "password": []}

        if not username:
            errors.append('Username is required.')
            field_errors["username"].append('Username is required.')
        if not email:
            errors.append('Email is required.')
            field_errors["email"].append('Email is required.')
        else:
            if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
                errors.append('Email address is not valid.')
                field_errors["email"].append('Email address is not valid.')
        if not password:
            errors.append('Password is required.')
            field_errors["password"].append('Password is required.')

        if password:
            pwd_errors = []
            if len(password) < 8:
                pwd_errors.append('be at least 8 characters long')
            if not re.search(r'[A-Z]', password):
                pwd_errors.append('contain at least one uppercase letter')
            if not re.search(r'[a-z]', password):
                pwd_errors.append('contain at least one lowercase letter')
            if not re.search(r'\d', password):
                pwd_errors.append('contain at least one number')
            if not re.search(r'[^A-Za-z0-9]', password):
                pwd_errors.append('contain at least one special character')
            if pwd_errors:
                msg = 'Password must ' + ', '.join(pwd_errors) + '.'
                errors.append(msg)
                field_errors["password"].append(msg)

        # Uniqueness checks should run regardless of other errors if values are provided
        try:
            if username and User.query.filter_by(username=username).first() is not None:
                errors.append('Username is already taken.')
                field_errors["username"].append('Username is already taken.')
            if email and User.query.filter_by(email=email).first() is not None:
                errors.append('Email is already registered.')
                field_errors["email"].append('Email is already registered.')
        except Exception:
            errors.append('Unable to validate uniqueness at the moment. Please try again.')

        if errors:
            return render_template('/register.html', errors=errors, field_errors=field_errors, values={'username': username, 'email': email})

        try:
            user = User(username=username, email=email, role='user', status='active')
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            field_errors["username"].append('Username may be taken.')
            field_errors["email"].append('Email may be registered.')
            return render_template('/register.html', errors=['Username or email already exists.'], field_errors=field_errors, values={'username': username, 'email': email})
        except Exception:
            db.session.rollback()
            return render_template('/register.html', errors=['An unexpected error occurred. Please try again.'], field_errors=field_errors, values={'username': username, 'email': email})

        return redirect(url_for('login'))

    return render_template('/register.html', errors=[], field_errors={"username": [], "email": [], "password": []}, values={})


@app.route('/index')
def index_page():
    current_user = _require_admin()
    return render_template('/index.html', current_user=current_user, is_admin=True)

@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    current_user = _require_admin()
    
    errors = []
    success = False
    success_msg = request.args.get('success_msg')
    error_msg = request.args.get('error_msg')
    if error_msg:
        errors.append(error_msg)
    
    if request.method == 'POST':
        _validate_csrf()
        action = request.form.get('action')
        
        if action == 'general_settings':
            # 1. Fixed Defect Marker Expiration
            expiration_days = request.form.get('fixed_defect_expiration_days', '').strip()
            try:
                val = int(expiration_days)
                if val < 1:
                    errors.append('Expiration days must be at least 1.')
                else:
                    s = Settings.query.filter_by(key='fixed_defect_expiration_days').first()
                    if not s:
                        s = Settings(key='fixed_defect_expiration_days')
                        db.session.add(s)
                    s.value = str(val)
            except ValueError:
                errors.append('Expiration days must be a number.')
                
            # 2. Automatic Fix Threshold
            auto_fix_threshold = request.form.get('auto_fix_threshold', '').strip()
            try:
                val = int(auto_fix_threshold)
                if val < 1:
                    errors.append('Auto-fix threshold must be at least 1.')
                else:
                    s = Settings.query.filter_by(key='auto_fix_threshold').first()
                    if not s:
                        s = Settings(key='auto_fix_threshold')
                        db.session.add(s)
                    s.value = str(val)
            except ValueError:
                errors.append('Auto-fix threshold must be a number.')
            
            # 3. False Report Threshold
            false_report_threshold = request.form.get('false_report_threshold', '').strip()
            try:
                val = int(false_report_threshold)
                if val < 1:
                    errors.append('False report threshold must be at least 1.')
                else:
                    s = Settings.query.filter_by(key='false_report_threshold').first()
                    if not s:
                        s = Settings(key='false_report_threshold')
                        db.session.add(s)
                    s.value = str(val)
            except ValueError:
                errors.append('False report threshold must be a number.')

            if not errors:
                try:
                    db.session.commit()
                    success = True
                except Exception as e:
                    db.session.rollback()
                    errors.append('Failed to save settings: ' + str(e))
    
    # Load current settings
    settings_map = {}
    try:
        all_settings = Settings.query.all()
        for s in all_settings:
            settings_map[s.key] = s.value
    except Exception:
        pass
        
    # Defaults if missing
    if 'fixed_defect_expiration_days' not in settings_map:
        settings_map['fixed_defect_expiration_days'] = '30'
    if 'auto_fix_threshold' not in settings_map:
        settings_map['auto_fix_threshold'] = '3'
    if 'false_report_threshold' not in settings_map:
        settings_map['false_report_threshold'] = '5'
        
    b2_connected = False
    backups = []
    
    if B2_DEPS_AVAILABLE:
        key_id = settings_map.get('b2_key_id')
        app_key = settings_map.get('b2_app_key')
        bucket_name = settings_map.get('b2_bucket_name')
        
        if key_id and app_key and bucket_name:
            try:
                info = InMemoryAccountInfo()
                b2_api = B2Api(info)
                b2_api.authorize_account("production", key_id, app_key)
                bucket = b2_api.get_bucket_by_name(bucket_name)
                b2_connected = True
                
                # List backups
                for file_version, _ in bucket.ls(folder_to_list='', show_versions=False):
                    if 'backup_users_' in file_version.file_name and file_version.file_name.endswith('.db'):
                        # Convert timestamp from filename if possible, or use upload timestamp
                        ts = file_version.upload_timestamp / 1000.0
                        date_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
                        backups.append({
                            'id': file_version.id_,
                            'name': file_version.file_name,
                            'createdTime': date_str
                        })
                # Sort backups desc
                backups.sort(key=lambda x: x['name'], reverse=True)
            except Exception:
                b2_connected = False
                # If auth fails, we might want to clear stored creds or just show disconnected
                pass

    return render_template(
        'settings.html',
        current_user=current_user,
        is_admin=True,
        settings=settings_map,
        errors=errors,
        success=success,
        success_msg=success_msg,
        csrf_token=_get_csrf_token(),
        b2_connected=b2_connected,
        backups=backups
    )

@app.route('/settings/b2/connect', methods=['POST'])
def b2_connect():
    current_user = _require_admin()
    _validate_csrf()
    if not B2_DEPS_AVAILABLE:
        return redirect(url_for('settings_page', error_msg='Backblaze B2 library is not available.'))
    
    key_id = request.form.get('key_id', '').strip()
    app_key = request.form.get('app_key', '').strip()
    bucket_name = request.form.get('bucket_name', '').strip()
    
    if not key_id or not app_key or not bucket_name:
        return redirect(url_for('settings_page', error_msg='Please provide Key ID, Application Key, and Bucket Name.')) 

    # Save to DB
    try:
        for k, v in [('b2_key_id', key_id), ('b2_app_key', app_key), ('b2_bucket_name', bucket_name)]:
            s = Settings.query.filter_by(key=k).first()
            if not s: s = Settings(key=k); db.session.add(s)
            s.value = v
        db.session.commit()
    except Exception:
        db.session.rollback()
        return redirect(url_for('settings_page', error_msg='Unable to save Backblaze B2 settings.'))

    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", key_id, app_key)
        b2_api.get_bucket_by_name(bucket_name)
        return redirect(url_for('settings_page', success_msg='Connected to Backblaze B2 successfully.'))
    except Exception:
        return redirect(url_for('settings_page', error_msg='Backblaze B2 connection failed. Verify Key ID, Application Key, and bucket access.'))

@app.route('/settings/b2/disconnect', methods=['POST'])
def b2_disconnect():
    _require_admin()
    _validate_csrf()
    try:
        Settings.query.filter(Settings.key.in_(['b2_key_id', 'b2_app_key', 'b2_bucket_name'])).delete(synchronize_session=False)
        db.session.commit()
    except Exception:
        db.session.rollback()
    return redirect(url_for('settings_page', success_msg='Disconnected from Backblaze B2.'))

@app.route('/settings/b2/backup', methods=['POST'])
def b2_backup():
    current_user = _require_admin()
    _validate_csrf()
    
    if not B2_DEPS_AVAILABLE:
        return redirect(url_for('settings_page'))
        
    # Get creds
    s_key_id = Settings.query.filter_by(key='b2_key_id').first()
    s_app_key = Settings.query.filter_by(key='b2_app_key').first()
    s_bucket = Settings.query.filter_by(key='b2_bucket_name').first()
    
    if not s_key_id or not s_app_key or not s_bucket:
        return redirect(url_for('settings_page'))
        
    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", s_key_id.value, s_app_key.value)
        bucket = b2_api.get_bucket_by_name(s_bucket.value)
        
        # Backup file
        db_path = os.path.join(app.root_path, 'users.db')
        if not os.path.exists(db_path):
             db_path = 'users.db' 
             
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_users_{timestamp}.db"
        
        bucket.upload_local_file(
            local_file=db_path,
            file_name=backup_name,
            file_infos={'author': current_user.username}
        )
        
        return redirect(url_for('settings_page', success_msg=f'Backup created successfully: {backup_name}'))
    except Exception as e:
        return redirect(url_for('settings_page')) 

@app.route('/settings/b2/restore', methods=['POST'])
def b2_restore():
    current_user = _require_admin()
    _validate_csrf()
    
    file_id = request.form.get('file_id')
    if not file_id:
        return redirect(url_for('settings_page'))
        
    s_key_id = Settings.query.filter_by(key='b2_key_id').first()
    s_app_key = Settings.query.filter_by(key='b2_app_key').first()
    s_bucket = Settings.query.filter_by(key='b2_bucket_name').first()
    
    if not s_key_id or not s_app_key or not s_bucket:
        return redirect(url_for('settings_page'))
        
    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", s_key_id.value, s_app_key.value)
        bucket = b2_api.get_bucket_by_name(s_bucket.value)
        
        # Download to temp file
        temp_path = os.path.join(app.root_path, 'restore_temp.db')
        
        file_version = b2_api.get_file_info(file_id)
        download_dest = bucket.download_file_by_id(file_id)
        download_dest.save_to(temp_path)

        # Check integrity
        with open(temp_path, 'rb') as f:
            header = f.read(16)
            if b'SQLite format 3' not in header:
                 return redirect(url_for('settings_page')) 
        
        # Restore
        db_path = os.path.join(app.root_path, 'users.db')
        
        # Close DB connection
        db.session.remove()
        db.engine.dispose()
        
        # Replace
        import shutil
        shutil.move(temp_path, db_path)
            
        return redirect(url_for('settings_page', success_msg='Database restored successfully.'))
    except Exception as e:
        return redirect(url_for('settings_page'))


@app.route('/admin/backups')
def admin_backups_page():
    current_user = _require_admin()
    success_msg = request.args.get('success_msg')
    error_msg = request.args.get('error_msg')
    ts = time.strftime("%Y%m%d_%H%M%S")
    default_format = 'db'
    default_filename = f"backup_{ts}.{default_format}"
    history = _backup_log_read(50)
    for item in history:
        name = str(item.get('filename') or '')
        item['can_download'] = bool(name and os.path.exists(os.path.join(BACKUP_DIR, name)))
        ts_val = int(item.get('timestamp') or 0)
        item['timestamp_iso'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts_val)) if ts_val else ''
    return render_template(
        '/backup_management.html',
        current_user=current_user,
        is_admin=True,
        csrf_token=_get_csrf_token(),
        success_msg=success_msg,
        error_msg=error_msg,
        default_filename=default_filename,
        default_format=default_format,
        history=history
    )


@app.route('/admin/backups/export', methods=['POST'])
def admin_backups_export():
    current_user = _require_admin()
    _validate_csrf()
    if not BACKUP_LOCK.acquire(blocking=False):
        return jsonify({'success': False, 'message': 'A backup operation is already in progress.'}), 409
    started_at = int(time.time())
    try:
        fmt = str(request.form.get('backup_format') or 'db').strip().lower().lstrip('.')
        if fmt not in {'db', 'sql'}:
            return jsonify({'success': False, 'message': 'Unsupported backup format.'}), 400
        raw_name = (request.form.get('backup_filename') or '').strip()
        safe_name = secure_filename(raw_name) if raw_name else ''
        if not safe_name:
            safe_name = f"backup_{time.strftime('%Y%m%d_%H%M%S')}"
        if '.' not in safe_name:
            safe_name = f"{safe_name}.{fmt}"
        else:
            base, _ext = safe_name.rsplit('.', 1)
            safe_name = f"{base}.{fmt}"

        os.makedirs(BACKUP_DIR, exist_ok=True)
        output_path = os.path.join(BACKUP_DIR, safe_name)
        db_path = _get_db_path()
        ok, msg = _validate_backup_db(db_path)
        if not ok:
            return jsonify({'success': False, 'message': msg}), 400

        if fmt == 'db':
            src = sqlite3.connect(db_path)
            dest = sqlite3.connect(output_path)
            src.backup(dest)
            dest.close()
            src.close()
        else:
            conn = sqlite3.connect(db_path)
            with open(output_path, 'w', encoding='utf-8') as f:
                for line in conn.iterdump():
                    f.write(line + '\n')
            conn.close()

        _backup_log_append({
            "user": current_user.username,
            "operation": "export",
            "filename": safe_name,
            "timestamp": started_at,
            "status": "success"
        })
        return send_file(output_path, as_attachment=True, download_name=safe_name)
    except Exception:
        _backup_log_append({
            "user": current_user.username,
            "operation": "export",
            "filename": None,
            "timestamp": started_at,
            "status": "failure"
        })
        return jsonify({'success': False, 'message': 'Failed to export backup.'}), 500
    finally:
        BACKUP_LOCK.release()


@app.route('/admin/backups/import', methods=['POST'])
def admin_backups_import():
    current_user = _require_admin()
    _validate_csrf()
    if not BACKUP_LOCK.acquire(blocking=False):
        return jsonify({'success': False, 'message': 'A backup operation is already in progress.'}), 409
    started_at = int(time.time())
    temp_path = None
    temp_db_path = None
    try:
        uploaded = request.files.get('backup_file')
        if not uploaded or not uploaded.filename:
            return jsonify({'success': False, 'message': 'Please select a backup file.'}), 400
        filename = secure_filename(uploaded.filename)
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in BACKUP_ALLOWED_EXTS:
            return jsonify({'success': False, 'message': 'Invalid file format.'}), 400
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.' + ext)
        temp_path = tmp.name
        tmp.close()
        uploaded.save(temp_path)

        if ext == 'sql':
            temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
            temp_db_path = temp_db.name
            temp_db.close()
            conn = sqlite3.connect(temp_db_path)
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                conn.executescript(f.read())
            conn.close()
            candidate_path = temp_db_path
        else:
            with open(temp_path, 'rb') as f:
                header = f.read(16)
                if b'SQLite format 3' not in header:
                    return jsonify({'success': False, 'message': 'Backup file is corrupted or not a valid SQLite database.'}), 400
            candidate_path = temp_path
        ok, msg = _validate_backup_db(candidate_path)
        if not ok:
            return jsonify({'success': False, 'message': msg}), 400

        RESTORE_STATE["in_progress"] = True
        db.session.remove()
        db.engine.dispose()
        db_path = _get_db_path()
        shutil.move(candidate_path, db_path)

        _backup_log_append({
            "user": current_user.username,
            "operation": "import",
            "filename": filename,
            "timestamp": started_at,
            "status": "success"
        })
        return jsonify({'success': True, 'message': 'Database restored successfully.'})
    except Exception:
        _backup_log_append({
            "user": current_user.username,
            "operation": "import",
            "filename": None,
            "timestamp": started_at,
            "status": "failure"
        })
        return jsonify({'success': False, 'message': 'Restore failed. Please verify the backup file.'}), 500
    finally:
        RESTORE_STATE["in_progress"] = False
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        if temp_db_path and os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except Exception:
                pass
        BACKUP_LOCK.release()


@app.route('/admin/backups/download/<path:filename>')
def admin_backups_download(filename):
    _require_admin()
    safe_name = secure_filename(filename)
    if not safe_name:
        abort(404)
    file_path = os.path.join(BACKUP_DIR, safe_name)
    if not os.path.exists(file_path):
        abort(404)
    return send_file(file_path, as_attachment=True, download_name=safe_name)


@app.errorhandler(413)
def handle_large_upload(error):
    if request.path.startswith('/admin/backups'):
        if request.method == 'POST':
            return jsonify({'success': False, 'message': 'File too large.'}), 413
        return redirect(url_for('admin_backups_page', error_msg='File too large.'))
    return ("File too large.", 413)

@app.route('/start', methods=['POST'])
def start_stream():
    _require_admin()
    data = request.get_json() or {}
    camera_index = data.get('camera_index', 0)
    try:
        camera_index = int(camera_index)
    except (ValueError, TypeError):
        camera_index = 0
    open_camera(camera_index)
    return ('OK', 200)

@app.route('/stop', methods=['POST'])
def stop_stream():
    _require_admin()
    close_camera()
    return ('OK', 200)

@app.route('/map')
def map_page():
    current_user = _login_required()
    if not isinstance(current_user, User):
        return current_user
    is_admin = _is_admin(current_user)
    return render_template('/map.html', current_user=current_user, is_admin=is_admin)


@app.route('/reports', methods=['GET', 'POST'])
def reports_page():
    current_user = _login_required()
    if not isinstance(current_user, User):
        return current_user
    is_admin = _is_admin(current_user)
    csrf_token = _get_csrf_token()

    success = (request.args.get('success') or '').strip()

    def _parse_float(s):
        try:
            return float(str(s).strip())
        except Exception:
            return None

    def _validate_lat_lng(lat, lng, errors):
        if lat is None:
            errors.append('Latitude is required and must be a number.')
        if lng is None:
            errors.append('Longitude is required and must be a number.')
        if lat is not None and (lat < -90.0 or lat > 90.0):
            errors.append('Latitude must be between -90 and 90.')
        if lng is not None and (lng < -180.0 or lng > 180.0):
            errors.append('Longitude must be between -180 and 180.')

    def _allowed_image(filename: str) -> bool:
        if not filename:
            return False
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        return ext in ALLOWED_REPORT_IMAGE_EXTS

    if request.method == 'POST':
        _validate_csrf()
        lat = _parse_float(request.form.get('latitude'))
        lng = _parse_float(request.form.get('longitude'))
        obstruction_type = (request.form.get('obstruction_type') or '').strip()
        photo = request.files.get('photo')

        errors = []

        _validate_lat_lng(lat, lng, errors)

        allowed_types = {'Pothole', 'Road Crack', 'Other'}
        if not obstruction_type:
            errors.append('Obstruction type is required.')
        elif obstruction_type not in allowed_types:
            errors.append('Invalid obstruction type.')

        photo_rel = None
        if photo and getattr(photo, 'filename', None):
            fname = (photo.filename or '').strip()
            if not _allowed_image(fname):
                errors.append('Photo must be a .jpg, .jpeg, or .png image.')
            else:
                safe = secure_filename(fname)
                ext = safe.rsplit('.', 1)[-1].lower()
                unique = f"{uuid4().hex}.{ext}"
                try:
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                    abs_path = os.path.join(UPLOAD_FOLDER, unique)
                    photo.save(abs_path)
                    photo_rel = f"uploads/reports/{unique}"
                except Exception:
                    errors.append('Unable to save uploaded photo. Please try again.')

        if not errors:
            title = f"{obstruction_type} report"
            body = ''
            now_ts = int(time.time())
            r = Report(
                user_id=int(current_user.id),
                title=title,
                body=body,
                latitude=float(lat),
                longitude=float(lng),
                obstruction_type=obstruction_type,
                photo_path=photo_rel,
                created_at=now_ts,
                status_updated_at=now_ts,
            )
            db.session.add(r)
            
            # Notify Admins about new report
            try:
                admins = User.query.filter_by(role='admin').all()
                for admin in admins:
                    if admin.id == current_user.id:
                        continue # Don't notify self if admin submitted
                    msg = f"New report submitted by {current_user.username}: {title}"
                    notif = Notification(
                        user_id=admin.id,
                        title="New User Report",
                        message=msg,
                        link=url_for('defects_page', q=current_user.username)
                    )
                    db.session.add(notif)
            except Exception:
                pass

            db.session.commit()
            return redirect(url_for('reports_page', success='1'))

        # fall through to render with errors
    else:
        errors = []

    pre_lat = request.args.get('lat')
    pre_lng = request.args.get('lng')
    if request.method == 'GET':
        lat = _parse_float(pre_lat)
        lng = _parse_float(pre_lng)
        obstruction_type = ''
    else:
        lat = lat
        lng = lng
        obstruction_type = obstruction_type

    return render_template(
        '/reports.html',
        current_user=current_user,
        is_admin=is_admin,
        csrf_token=csrf_token,
        errors=errors,
        success=success,
        values={'latitude': '' if lat is None else lat, 'longitude': '' if lng is None else lng, 'obstruction_type': obstruction_type},
    )


@app.route('/my-reports')
def my_reports_page():
    current_user = _require_role('user')
    if not isinstance(current_user, User):
        return current_user

    q = (request.args.get('q') or '').strip()
    type_filter = (request.args.get('type') or '').strip().lower()
    status_filter = (request.args.get('status') or '').strip().lower()
    start_date = (request.args.get('start_date') or '').strip()
    end_date = (request.args.get('end_date') or '').strip()
    sort = (request.args.get('sort') or 'date_desc').strip().lower()
    try:
        page = max(1, int(request.args.get('page', '1')))
    except Exception:
        page = 1
    try:
        per_page = int(request.args.get('per_page', '10'))
    except Exception:
        per_page = 10
    if per_page not in (10, 20, 50):
        per_page = 10

    query = Report.query.filter(Report.user_id == int(current_user.id))
    
    # Date Range Filter
    if start_date:
        try:
            # Parse YYYY-MM-DD to timestamp
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            query = query.filter(Report.created_at >= start_ts)
        except ValueError:
            pass
            
    if end_date:
        try:
            # Parse YYYY-MM-DD to timestamp (end of day)
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            query = query.filter(Report.created_at <= end_ts)
        except ValueError:
            pass

    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Report.title.ilike(like),
            Report.body.ilike(like),
            Report.obstruction_type.ilike(like),
        ))
    if type_filter:
        if type_filter == 'pothole':
            query = query.filter(Report.obstruction_type.ilike('%pothole%'))
        elif type_filter == 'crack':
            query = query.filter(Report.obstruction_type.ilike('%crack%'))
        elif type_filter == 'other':
            query = query.filter(or_(
                Report.obstruction_type == None,
                and_(
                    ~Report.obstruction_type.ilike('%pothole%'),
                    ~Report.obstruction_type.ilike('%crack%'),
                ),
            ))
        else:
            query = query.filter(text('1=0'))
    if status_filter:
        if status_filter == 'fixed':
            query = query.filter(Report.is_fixed == True)
        elif status_filter == 'open':
            query = query.filter(or_(Report.is_fixed == False, Report.is_fixed == None))
        else:
            query = query.filter(text('1=0'))
    
    # Hide false reports from user view
    query = query.filter(Report.is_false_report == False)
    if sort == 'date_asc':
        query = query.order_by(asc(Report.created_at), asc(Report.id))
    elif sort == 'type':
        query = query.order_by(asc(Report.obstruction_type), desc(Report.created_at), desc(Report.id))
    else:
        sort = 'date_desc'
        query = query.order_by(desc(Report.created_at), desc(Report.id))

    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    if page > pages:
        page = pages
    offset = (page - 1) * per_page
    reports = query.limit(per_page).offset(offset).all()
    start = 0 if total == 0 else offset + 1
    end = 0 if total == 0 else min(total, offset + len(reports))

    return render_template(
        '/my_reports.html',
        current_user=current_user,
        is_admin=False,
        reports=reports,
        q=q,
        type_filter=type_filter,
        status_filter=status_filter,
        start_date=start_date,
        end_date=end_date,
        sort=sort,
        per_page=per_page,
        page=page,
        pages=pages,
        total=total,
        start=start,
        end=end,
    )

@app.route('/notifications')
def notifications_page():
    current_user = _login_required()
    if not isinstance(current_user, User):
        return current_user
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    notifications = pagination.items
    
    # Simple unread count
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    return render_template(
        'notifications.html',
        current_user=current_user,
        notifications=notifications,
        pagination=pagination,
        unread_count=unread_count,
        is_admin=_is_admin(current_user),
        csrf_token=_get_csrf_token()
    )

@app.route('/notifications/unread')
def unread_notifications():
    current_user = _login_required()
    if not isinstance(current_user, User):
        return jsonify({'error': 'Unauthorized'}), 401
    
    notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(10).all()
    
    data = []
    for n in notifs:
        data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'link': n.link,
            'created_at_iso': n.created_at_iso
        })
    
    return jsonify({'items': data, 'count': len(data)})

@app.route('/notifications/mark-read/<int:id>', methods=['POST'])
def mark_notification_read(id):
    current_user = _login_required()
    if not isinstance(current_user, User):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # AJAX requests might need CSRF header or token
    # For simplicity in this demo, we might skip strict CSRF for AJAX or assume header is sent
    # But let's at least check if we want to be strict.
    # Given the codebase uses _validate_csrf() manually in forms, we should probably do it if possible.
    # But standard fetch won't send it unless we put it in headers.
    # We'll skip strict CSRF for this specific AJAX action for now to avoid breaking the UI flow 
    # if the token isn't easily available in JS.
        
    notif = Notification.query.get_or_404(id)
    if notif.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    notif.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/notifications/mark-all-read', methods=['POST'])
def mark_all_notifications_read():
    current_user = _login_required()
    if not isinstance(current_user, User):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # AJAX-friendly
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})

@app.route('/users')
def users_page():
    current_user = _require_admin()
    is_admin = _is_admin(current_user)
    csrf_token = _get_csrf_token() if current_user else None
    next_url = request.full_path

    q = (request.args.get('q') or '').strip()
    role = (request.args.get('role') or '').strip().lower()
    status = (request.args.get('status') or '').strip().lower()
    sort = (request.args.get('sort') or 'az').strip().lower()
    try:
        page = max(1, int(request.args.get('page', '1')))
    except Exception:
        page = 1
    try:
        per_page = int(request.args.get('per_page', '20'))
    except Exception:
        per_page = 20
    if per_page not in (10, 20, 50, 100):
        per_page = 20

    query = User.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(User.username.ilike(like), User.email.ilike(like)))
    if role in ALLOWED_ROLES:
        query = query.filter(User.role == role)
    elif role:
        # invalid filter value, return empty
        query = query.filter(text('1=0'))

    if status in ALLOWED_STATUSES:
        query = query.filter(User.status == status)
    elif status:
        query = query.filter(text('1=0'))
        
    # Add subquery for report count
    report_count_stmt = db.session.query(
        func.count(Report.id)
    ).filter(Report.user_id == User.id).label('report_count')
    
    # Add subquery for reaction count
    reaction_count_stmt = db.session.query(
        func.count(Reaction.id)
    ).filter(Reaction.user_id == User.id).label('reaction_count')
    
    query = query.add_columns(report_count_stmt, reaction_count_stmt)

    if sort == 'za':
        query = query.order_by(desc(User.username), asc(User.id))
    elif sort == 'reports_desc':
        query = query.order_by(desc('report_count'), asc(User.username))
    elif sort == 'reports_asc':
        query = query.order_by(asc('report_count'), asc(User.username))
    else:
        sort = 'az'
        query = query.order_by(asc(User.username), asc(User.id))

    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    if page > pages:
        page = pages

    results = query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Process results into user objects with count attribute
    users = []
    for row in results:
        # row is (User, report_count, reaction_count)
        user = row[0]
        user.report_count = row[1] or 0
        user.reaction_count = row[2] or 0
        user.has_activity = (user.report_count > 0 or user.reaction_count > 0)
        users.append(user)
        
    start = 0 if total == 0 else ((page - 1) * per_page + 1)
    end = 0 if total == 0 else (min(total, (page - 1) * per_page + len(users)))

    return render_template(
        '/users.html',
        users=users,
        total=total,
        page=page,
        pages=pages,
        per_page=per_page,
        start=start,
        end=end,
        q=q,
        role_filter=role,
        status_filter=status,
        sort=sort,
        csrf_token=csrf_token,
        is_admin=is_admin,
        current_user=current_user,
        next_url=next_url,
    )


@app.route('/users/<int:user_id>/status', methods=['POST'])
def user_set_status(user_id: int):
    current_user = _require_admin()
    _validate_csrf()

    new_status = str((request.form.get('status') or '')).strip().lower()
    if new_status not in ALLOWED_STATUSES:
        abort(400)

    user = User.query.get_or_404(user_id)
    if _is_admin(user):
        abort(403)
    if user.id == current_user.id and new_status != user.status:
        # allow self status changes? generally no; avoid admin locking themselves accidentally
        abort(400)

    user.status = new_status
    if new_status == 'suspended':
        user.suspended_until = int(time.time()) + 5 * 60
    else:
        user.suspended_until = None
    db.session.commit()
    return _redirect_back('users_page')


@app.route('/users/<int:user_id>/role', methods=['POST'])
def user_set_role(user_id: int):
    current_user = _require_admin()
    _validate_csrf()

    new_role = str((request.form.get('role') or '')).strip().lower()
    if new_role not in ALLOWED_ROLES:
        abort(400)

    user = User.query.get_or_404(user_id)
    if _is_admin(user):
        abort(403)
    if user.id == current_user.id and _is_admin(user) and new_role != 'admin':
        # prevent self-demotion
        abort(400)

    user.role = new_role
    db.session.commit()
    return _redirect_back('users_page')


@app.route('/users/<int:user_id>/delete', methods=['POST'])
def user_delete(user_id: int):
    current_user = _require_admin()
    _validate_csrf()

    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        abort(400)

    if _is_admin(user):
        abort(403)
        
    # Check activity before deletion
    has_reports = Report.query.filter_by(user_id=user.id).count() > 0
    has_reactions = Reaction.query.filter_by(user_id=user.id).count() > 0
    
    if has_reports or has_reactions:
        # Cannot delete, only archive
        user.status = 'archived'
        user.suspended_until = None
        db.session.commit()
        return _redirect_back('users_page')

    db.session.delete(user)
    db.session.commit()
    return _redirect_back('users_page')


@app.route('/defects')
def defects_page():
    current_user = _require_admin()
    is_admin = _is_admin(current_user)
    
    q_filter = (request.args.get('q') or '').strip()
    type_filter = (request.args.get('type') or '').strip().lower()
    source_filter = (request.args.get('source') or '').strip().lower()
    status_filter = (request.args.get('status') or '').strip().lower()
    unsure_filter = (request.args.get('unsure') or '').strip().lower()
    start_date = (request.args.get('start_date') or '').strip()
    end_date = (request.args.get('end_date') or '').strip()
    sort = (request.args.get('sort') or 'date_desc').strip().lower()
    
    try:
        page = max(1, int(request.args.get('page', '1')))
    except Exception:
        page = 1
    try:
        per_page = int(request.args.get('per_page', '20'))
    except Exception:
        per_page = 20
    if per_page not in (10, 20, 50, 100):
        per_page = 20

    # 1. Fetch User Reports
    reports_query = db.session.query(
        Report.id.label('id'),
        Report.obstruction_type.label('type'),
        Report.latitude.label('latitude'),
        Report.longitude.label('longitude'),
        Report.created_at.label('created_at'),
        Report.status_updated_at.label('status_updated_at'),
        User.username.label('submitted_by'),
        literal_column("'user'").label('source'),
        Report.is_fixed.label('is_fixed'),
        literal_column("'confirmed'").label('review_status'),
        literal_column("''").label('detected_class')
    ).join(User, Report.user_id == User.id).filter(Report.is_false_report == False)

    # 2. Fetch System Detections
    detections_query = db.session.query(
        Detection.id.label('id'),
        Detection.label.label('type'),
        Detection.latitude.label('latitude'),
        Detection.longitude.label('longitude'),
        Detection.created_at.label('created_at'),
        Detection.status_updated_at.label('status_updated_at'),
        literal_column("''").label('submitted_by'),
        literal_column("'system'").label('source'),
        Detection.is_fixed.label('is_fixed'),
        Detection.review_status.label('review_status'),
        Detection.detected_class.label('detected_class')
    )

    # 3. Apply Filters
    if q_filter:
        like = f"%{q_filter}%"
        reports_query = reports_query.filter(or_(
            Report.obstruction_type.ilike(like),
            User.username.ilike(like)
        ))
        detections_query = detections_query.filter(or_(
            Detection.label.ilike(like),
            Detection.detected_class.ilike(like)
        ))

    # Date Range Filter
    if start_date:
        try:
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            reports_query = reports_query.filter(Report.created_at >= start_ts)
            detections_query = detections_query.filter(Detection.created_at >= start_ts)
        except ValueError:
            pass
            
    if end_date:
        try:
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            reports_query = reports_query.filter(Report.created_at <= end_ts)
            detections_query = detections_query.filter(Detection.created_at <= end_ts)
        except ValueError:
            pass

    # Type and Unsure Sub-filtering
    if type_filter:
        if type_filter == 'unsure':
            # Reports don't have 'unsure' (they are human submitted)
            reports_query = reports_query.filter(text("1=0"))
            
            # System detections with low confidence or pending review
            # Logic: If unsure_filter is set, filter detections by review_status
            if unsure_filter == 'validated':
                detections_query = detections_query.filter(Detection.review_status == 'confirmed')
            elif unsure_filter == 'unvalidated':
                detections_query = detections_query.filter(Detection.review_status == 'pending')
            elif unsure_filter == 'rejected':
                detections_query = detections_query.filter(Detection.review_status == 'rejected')
            else:
                # Show all detections that were ever unsure (pending or validated/rejected from pending)
                # In this system, low confidence detections start as 'pending'
                # We'll show anything that isn't auto-confirmed (>0.60) if possible, 
                # but review_status is our best indicator.
                detections_query = detections_query.filter(Detection.review_status.in_(['pending', 'confirmed', 'rejected']))
                # If we want ONLY those that were originally unsure, we'd need a flag, 
                # but 'pending' is the indicator for unsure detections in the current system.
        elif type_filter == 'pothole':
            reports_query = reports_query.filter(Report.obstruction_type.ilike('%pothole%'))
            detections_query = detections_query.filter(Detection.label.ilike('%pothole%'))
        elif type_filter == 'crack':
            reports_query = reports_query.filter(Report.obstruction_type.ilike('%crack%'))
            detections_query = detections_query.filter(Detection.label.ilike('%crack%'))
    
    if source_filter:
        if source_filter == 'user':
            detections_query = detections_query.filter(text("1=0"))
        elif source_filter == 'system':
            reports_query = reports_query.filter(text("1=0"))

    if status_filter:
        if status_filter == 'fixed':
            reports_query = reports_query.filter(Report.is_fixed == True)
            detections_query = detections_query.filter(Detection.is_fixed == True)
        elif status_filter == 'open':
            reports_query = reports_query.filter(or_(Report.is_fixed == False, Report.is_fixed == None))
            detections_query = detections_query.filter(or_(Detection.is_fixed == False, Detection.is_fixed == None))

    # Date Range Filter
    if start_date:
        try:
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            reports_query = reports_query.filter(Report.created_at >= start_ts)
            detections_query = detections_query.filter(Detection.created_at >= start_ts)
        except ValueError:
            pass
            
    if end_date:
        try:
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            reports_query = reports_query.filter(Report.created_at <= end_ts)
            detections_query = detections_query.filter(Detection.created_at <= end_ts)
        except ValueError:
            pass

    # Combine queries
    combined_query = reports_query.union_all(detections_query)

    # Apply Sorting
    if sort == 'date_asc':
        combined_query = combined_query.order_by(text('created_at ASC'))
    elif sort == 'reported_asc':
        combined_query = combined_query.order_by(text('created_at ASC'))
    elif sort == 'reported_desc':
        combined_query = combined_query.order_by(text('created_at DESC'))
    elif sort == 'status_updated_asc':
        combined_query = combined_query.order_by(text('status_updated_at ASC'), text('created_at ASC'))
    elif sort == 'status_updated_desc':
        combined_query = combined_query.order_by(text('status_updated_at DESC'), text('created_at DESC'))
    elif sort == 'type':
        combined_query = combined_query.order_by(text('type ASC'), text('created_at DESC'))
    elif sort == 'source':
        combined_query = combined_query.order_by(text('source ASC'), text('created_at DESC'))
    elif sort == 'status':
        combined_query = combined_query.order_by(text('is_fixed ASC'), text('created_at DESC'))
    else: # date_desc default
        combined_query = combined_query.order_by(text('created_at DESC'))

    # Pagination
    total = combined_query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    if page > pages:
        page = pages
    
    offset = (page - 1) * per_page
    results = combined_query.limit(per_page).offset(offset).all()
    
    items = []
    for r in results:
        created_at_val = int(r.created_at) if r.created_at else 0
        status_updated_val = int(r.status_updated_at) if getattr(r, 'status_updated_at', None) else created_at_val
        items.append({
            'id': r.id,
            'type': r.type,
            'lat': r.latitude,
            'lon': r.longitude,
            'created_at': created_at_val,
            'created_at_iso': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(created_at_val)) if created_at_val else '',
            'status_updated_at': status_updated_val,
            'status_updated_at_iso': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(status_updated_val)) if status_updated_val else '',
            'submitted_by': r.submitted_by,
            'source': r.source,
            'is_fixed': r.is_fixed,
            'review_status': r.review_status,
            'detected_class': r.detected_class
        })

    start = 0 if total == 0 else offset + 1
    end = 0 if total == 0 else min(total, offset + len(items))

    return render_template(
        '/defects.html',
        items=items,
        total=total,
        page=page,
        pages=pages,
        per_page=per_page,
        start=start,
        end=end,
        q=q_filter,
        type_filter=type_filter,
        source_filter=source_filter,
        status_filter=status_filter,
        unsure_filter=unsure_filter,
        start_date=start_date,
        end_date=end_date,
        sort=sort,
        is_admin=is_admin,
        current_user=current_user,
        next_url=request.full_path
    )


@app.route('/detections') #for logs
def detections_api():
    current_user = _login_required()
    if not isinstance(current_user, User):
        return current_user
    try:
        is_admin = _is_admin(current_user)
        include_pending = str(request.args.get('include_pending') or '').strip().lower() in {'1', 'true', 'yes'}
        allow_pending = bool(is_admin and include_pending)
        
        expiration_days = 30
        try:
            s_val = Settings.query.filter_by(key='fixed_defect_expiration_days').first()
            if s_val and s_val.value:
                expiration_days = int(s_val.value)
        except Exception:
            pass
            
        cutoff = int(time.time()) - (expiration_days * 24 * 3600)
        query = Detection.query.filter(
            or_(
                Detection.is_fixed == False,
                Detection.fixed_at > cutoff
            )
        )
        query = query.filter(or_(Detection.review_status == None, Detection.review_status != 'rejected'))
        if allow_pending:
            query = query.filter(or_(Detection.review_status == None, Detection.review_status.in_(['confirmed', 'pending'])))
        else:
            query = query.filter(or_(Detection.review_status == None, Detection.review_status == 'confirmed'))
            query = query.filter(or_(Detection.visibility_scope == None, Detection.visibility_scope == 'public'))
        limit = request.args.get('limit', type=int) or 50
        before_id = request.args.get('before_id', type=int)
        after_id = request.args.get('after_id', type=int)
        
        if before_id:
            query = query.filter(Detection.id < before_id)
        if after_id:
            query = query.filter(Detection.id > after_id)

        rows = query.order_by(desc(Detection.id)).limit(limit + 1).all()
        
        has_more = len(rows) > limit
        rows = rows[:limit]
        
        items = []
        for d in rows:
            label_value = d.final_class or d.detected_class or d.label
            review_status = (d.review_status or 'confirmed').strip().lower()
            visibility_scope = (d.visibility_scope or 'public').strip().lower()
            created_at_val = int(d.created_at) if d.created_at else 0
            status_updated_val = int(d.status_updated_at) if getattr(d, 'status_updated_at', None) else created_at_val
            items.append({
                "id": int(d.id),
                "lat": float(d.latitude),
                "lon": float(d.longitude),
                "labels": [str(label_value)],
                "label": str(label_value),
                "detected_class": d.detected_class,
                "final_class": d.final_class,
                "detection_source": d.detection_source or 'ai_survey',
                "review_status": review_status,
                "reviewed_by": int(d.reviewed_by) if d.reviewed_by else None,
                "reviewed_at": int(d.reviewed_at) if d.reviewed_at else None,
                "visibility_scope": visibility_scope,
                "snapshot_image_path": d.snapshot_image_path,
                "conf": float(d.confidence),
                "confidence_score": float(d.confidence_score) if d.confidence_score is not None else float(d.confidence),
                "ts": created_at_val,
                "ts_iso": time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(created_at_val)) if created_at_val else '',
                "status_updated_at": status_updated_val,
                "status_updated_at_iso": time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(status_updated_val)) if status_updated_val else '',
                "gps_valid": True,
                "is_fixed": bool(d.is_fixed),
                "fixed_at": int(d.fixed_at) if d.fixed_at else None
            })
        return jsonify({
            "items": items,
            "has_more": has_more
        })
    except Exception:
        return jsonify({"items": []})


@app.route('/detections/<int:detection_id>/review', methods=['POST'])
def review_detection(detection_id: int):
    current_user = _require_admin()
    try:
        data = request.get_json() or {}
        action = str(data.get('action') or '').strip().lower()
        if action not in {'confirm_pothole', 'confirm_roadcrack', 'reject'}:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400
        det = Detection.query.get_or_404(detection_id)
        now = int(time.time())
        if action == 'reject':
            det.review_status = 'rejected'
            det.visibility_scope = 'admin_only'
            det.reviewed_by = int(current_user.id)
            det.reviewed_at = now
        else:
            final_class = 'pothole' if action == 'confirm_pothole' else 'roadcrack'
            det.final_class = final_class
            det.label = final_class
            if not det.detected_class:
                det.detected_class = det.label
            det.review_status = 'confirmed'
            det.visibility_scope = 'public'
            det.reviewed_by = int(current_user.id)
            det.reviewed_at = now
        det.status_updated_at = now
        if not det.detection_source:
            det.detection_source = 'ai_survey'
        if det.confidence_score is None:
            det.confidence_score = det.confidence
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/reports-data')
def reports_data():
    current_user = _get_current_user()
    current_user_id = current_user.id if current_user else None

    expiration_days = 30
    try:
        s_val = Settings.query.filter_by(key='fixed_defect_expiration_days').first()
        if s_val and s_val.value:
            expiration_days = int(s_val.value)
    except Exception:
        pass

    reports = Report.query.filter(
        Report.created_at >= (time.time() - expiration_days * 24 * 3600),
        Report.is_false_report == False
    ).all()
    
    # Pre-fetch user reactions for these reports if user is logged in
    user_reactions = {}
    if current_user_id:
        # Get all reactions by this user for the fetched reports
        r_ids = [r.id for r in reports]
        if r_ids:
            reactions = Reaction.query.filter(
                Reaction.user_id == current_user_id,
                Reaction.report_id.in_(r_ids)
            ).all()
            for rx in reactions:
                user_reactions[rx.report_id] = rx.reaction_type

    items = []
    for r in reports:
        # if fixed, check if older than expiration_days since fixed
        if r.is_fixed and r.fixed_at:
            if (time.time() - r.fixed_at) > (expiration_days * 24 * 3600):
                continue

        created_at_val = int(r.created_at) if r.created_at else 0
        status_updated_val = int(r.status_updated_at) if getattr(r, 'status_updated_at', None) else created_at_val
        items.append({
            'id': r.id,
            'lat': r.latitude,
            'lon': r.longitude,
            'type': r.obstruction_type,
            'photo': r.photo_path,
            'created_at': created_at_val,
            'created_at_iso': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(created_at_val)) if created_at_val else '',
            'status_updated_at': status_updated_val,
            'status_updated_at_iso': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(status_updated_val)) if status_updated_val else '',
            'is_fixed': r.is_fixed,
            'thumbs_up': r.thumbs_up_count,
            'thumbs_down': r.thumbs_down_count,
            'user_reaction': user_reactions.get(r.id)  # 'up', 'down', or None
        })
    return jsonify({'items': items})


@app.route('/reports/<int:report_id>/react', methods=['POST'])
def react_to_report(report_id):
    current_user = _login_required()
    if not isinstance(current_user, User):
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json()
    reaction_type = data.get('reaction')
    if reaction_type not in ('up', 'down'):
        return jsonify({'error': 'Invalid reaction type'}), 400

    report = Report.query.get_or_404(report_id)

    # Check ownership
    if report.user_id == current_user.id:
        return jsonify({'error': 'Cannot react to your own report'}), 403

    try:
        existing = Reaction.query.filter_by(report_id=report.id, user_id=current_user.id).first()
        
        if existing:
            if existing.reaction_type == reaction_type:
                # Toggle off (remove reaction)
                db.session.delete(existing)
                if reaction_type == 'up':
                    report.thumbs_up_count = max(0, report.thumbs_up_count - 1)
                else:
                    report.thumbs_down_count = max(0, report.thumbs_down_count - 1)
                action = 'removed'
            else:
                # Change reaction
                old_type = existing.reaction_type
                existing.reaction_type = reaction_type
                if old_type == 'up':
                    report.thumbs_up_count = max(0, report.thumbs_up_count - 1)
                if old_type == 'down':
                    report.thumbs_down_count = max(0, report.thumbs_down_count - 1)
                
                if reaction_type == 'up':
                    report.thumbs_up_count += 1
                else:
                    report.thumbs_down_count += 1
                action = 'changed'
        else:
            # New reaction
            new_rx = Reaction(report_id=report.id, user_id=current_user.id, reaction_type=reaction_type)
            db.session.add(new_rx)
            if reaction_type == 'up':
                    report.thumbs_up_count += 1
            else:
                report.thumbs_down_count += 1
            action = 'added'

        # Auto-fix logic
        auto_fix_threshold = 3
        try:
            s_val = Settings.query.filter_by(key='auto_fix_threshold').first()
            if s_val and s_val.value:
                auto_fix_threshold = int(s_val.value)
        except Exception:
            pass

        if report.thumbs_up_count >= auto_fix_threshold and not report.is_fixed:
            now_ts = int(time.time())
            report.is_fixed = True
            report.fixed_at = now_ts
            report.status_updated_at = now_ts
            
            # Notify user
            try:
                msg = f"Your report '{report.title}' has been automatically marked as fixed due to community confirmation!"
                notif = Notification(
                    user_id=report.user_id,
                    title="Report Verified & Fixed",
                    message=msg,
                    link=url_for('my_reports_page')
                )
                db.session.add(notif)
            except Exception:
                pass

        db.session.commit()
        
        return jsonify({
            'success': True,
            'action': action,
            'thumbs_up': report.thumbs_up_count,
            'thumbs_down': report.thumbs_down_count,
            'is_fixed': report.is_fixed
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/reports/<int:report_id>/fix', methods=['POST'])
def manual_fix_report(report_id):
    current_user = _login_required()
    if not isinstance(current_user, User):
        return jsonify({'error': 'Authentication required'}), 401
        
    report = Report.query.get_or_404(report_id)
    
    # Only owner can manually fix via this endpoint
    if report.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
        
    if not report.is_fixed:
        now_ts = int(time.time())
        report.is_fixed = True
        report.fixed_at = now_ts
        report.status_updated_at = now_ts
        
        # Notify Admins about self-fixed report
        try:
            admins = User.query.filter_by(role='admin').all()
            for admin in admins:
                if admin.id == current_user.id:
                    continue # Don't notify self if admin is fixing their own report (though this endpoint is for users)
                msg = f"User {current_user.username} marked their own report '{report.title}' as fixed."
                notif = Notification(
                    user_id=admin.id,
                    title="Report Marked Fixed by User",
                    message=msg,
                    link=url_for('defects_page', q=current_user.username)
                )
                db.session.add(notif)
        except Exception:
            pass

        db.session.commit()
        
    return jsonify({'success': True, 'is_fixed': True})


@app.route('/reports/<int:report_id>/flag-false', methods=['POST'])
def flag_report_false(report_id):
    current_user = _require_admin()
    
    report = Report.query.get_or_404(report_id)
    if report.is_false_report:
        return jsonify({'success': True, 'message': 'Already flagged as false.'})
        
    try:
        # 1. Mark report as false (soft delete)
        report.is_false_report = True
        report.status_updated_at = int(time.time())
        
        # 2. Increment user's false report count
        user = User.query.get(report.user_id)
        if user:
            user.false_reports_count += 1
            
            # 3. Check threshold and block if exceeded
            threshold = 5
            try:
                s_val = Settings.query.filter_by(key='false_report_threshold').first()
                if s_val and s_val.value:
                    threshold = int(s_val.value)
            except Exception:
                pass
                
            if user.false_reports_count >= threshold:
                user.status = 'locked'
                # Notify Admins about auto-lock
                try:
                    admins = User.query.filter_by(role='admin').all()
                    for admin in admins:
                        msg = f"User {user.username} has been automatically locked after submitting {user.false_reports_count} false reports."
                        notif = Notification(
                            user_id=admin.id,
                            title="User Auto-Locked",
                            message=msg,
                            link=url_for('users_page', q=user.username)
                        )
                        db.session.add(notif)
                except Exception:
                    pass
            
            # 4. Notify the user
            msg = f"Your report '{report.title}' has been flagged as a false report and removed. Please ensure your reports are accurate. Repeated false reports may lead to account suspension."
            if user.status == 'locked':
                msg += " Your account has been locked due to excessive false reports."
                
            notif = Notification(
                user_id=user.id,
                title="Report Flagged as False",
                message=msg,
                link="#"
            )
            db.session.add(notif)
            
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/defects/mark-fixed', methods=['POST'])
def mark_fixed():
    current_user = _require_admin()
    try:
        data = request.json or {}
        ids = data.get('ids', []) # List of objects: {type: 'report'|'detection', id: 123}
        if not ids:
            return jsonify({'success': False, 'message': 'No defects selected'})
        
        now = int(time.time())
        updated_count = 0
        
        for item in ids:
            dtype = str(item.get('type') or '').lower()
            did = item.get('id')
            if not did:
                continue
                
            if dtype == 'report':
                rec = Report.query.get(did)
                if rec and not rec.is_fixed:
                    rec.is_fixed = True
                    rec.fixed_at = now
                    rec.status_updated_at = now
                    updated_count += 1
            elif dtype == 'detection':
                rec = Detection.query.get(did)
                if rec and not rec.is_fixed:
                    status_val = str(rec.review_status or 'confirmed').strip().lower()
                    if status_val != 'confirmed':
                        continue
                    rec.is_fixed = True
                    rec.fixed_at = now
                    rec.status_updated_at = now
                    updated_count += 1
        
        if updated_count > 0:
            db.session.commit()
            
        return jsonify({'success': True, 'updated': updated_count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@app.route('/video')
def video():
    _require_admin()
    if camera is None:
        return "Camera not running", 503
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/gps')
def gps_status():
    _require_admin()
    with gps_lock:
        data = dict(gps_latest)
    if data.get("ts"):
        data["ts_iso"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data["ts"]))
    # include config for debugging
    data["port"] = gps_port_cfg or os.environ.get("GPS_SERIAL_PORT", "COM8")
    data["baud"] = gps_baud_cfg or int(os.environ.get("GPS_BAUD", "4800"))
    return jsonify(data)

@app.before_request
def _ensure_gps_started():
    # Ensure GPS thread is running even when using `flask run` (Flask 3.x has no before_first_request)
    global _gps_started
    if not _gps_started:
        ensure_gps_thread()
        _gps_started = True

# --- Analytics Routes ---

@app.route('/analytics')
@require_admin_view
def analytics_page():
    return render_template('analytics.html', current_user=_get_current_user(), is_admin=True)

@app.route('/api/analytics/overview')
@require_admin_view
def get_analytics_overview():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    admin_area = request.args.get('admin_area')
    admin_level = request.args.get('admin_level', 'province')
    
    detections_query = Detection.query
    reports_query = Report.query

    if start_date:
        try:
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            detections_query = detections_query.filter(Detection.created_at >= start_ts)
            reports_query = reports_query.filter(Report.created_at >= start_ts)
        except ValueError:
            pass
            
    if end_date:
        try:
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            detections_query = detections_query.filter(Detection.created_at <= end_ts)
            reports_query = reports_query.filter(Report.created_at <= end_ts)
        except ValueError:
            pass

    # Apply spatial filtering if admin_area is provided
    if admin_area and admin_area != 'all':
        # Convert queries to lists of objects
        d_list = filter_by_area(detections_query, Detection, admin_area, admin_level)
        r_list = filter_by_area(reports_query, Report, admin_area, admin_level)
        
        # Total Potholes
        total_potholes = sum(1 for d in d_list if ('pothole' in (d.label or '').lower() or 'pothole' in (d.detected_class or '').lower()))
        
        # Total Reports
        # Pre-filter false reports in query before spatial check? 
        # filter_by_area takes a query, so let's add the false report filter to query first
        # But wait, reports_query above doesn't have false report filter yet.
        # Let's apply standard filters to the base query first.
        
        r_list = [r for r in r_list if not r.is_false_report]
        total_reports = len(r_list)
        
        # Active Defects
        active_detections = sum(1 for d in d_list if not d.is_fixed)
        active_reports = sum(1 for r in r_list if not r.is_fixed)
        active_defects = active_detections + active_reports
        
        # Resolved Defects
        resolved_detections = sum(1 for d in d_list if d.is_fixed)
        resolved_reports = sum(1 for r in r_list if r.is_fixed)
        resolved_defects = resolved_detections + resolved_reports
        
        # Avg Repair Time
        total_repair_time = 0
        count_fixed = 0
        for d in d_list:
            if d.is_fixed and d.fixed_at and d.created_at and d.fixed_at > d.created_at:
                total_repair_time += (d.fixed_at - d.created_at)
                count_fixed += 1
        for r in r_list:
            if r.is_fixed and r.fixed_at and r.created_at and r.fixed_at > r.created_at:
                total_repair_time += (r.fixed_at - r.created_at)
                count_fixed += 1
        
        avg_repair_time_hours = 0
        if count_fixed > 0:
            avg_repair_time_hours = (total_repair_time / count_fixed) / 3600
            
        # Detection Accuracy
        # Filter d_list for reviewed items
        reviewed = [d for d in d_list if d.review_status in ('confirmed', 'rejected')]
        total_reviewed = len(reviewed)
        confirmed_count = sum(1 for d in reviewed if d.review_status == 'confirmed')
        
        accuracy = 0
        if total_reviewed > 0:
            accuracy = (confirmed_count / total_reviewed) * 100
            
    else:
        # Standard SQL Query Logic (Faster for global view)
        
        # Total Potholes (from detections)
        total_potholes = detections_query.filter(or_(Detection.label.ilike('%pothole%'), Detection.detected_class.ilike('%pothole%'))).count()
        
        # Total Reports
        total_reports = reports_query.filter(Report.is_false_report == False).count()
        
        # Active Defects (Not Fixed)
        active_detections = detections_query.filter(or_(Detection.is_fixed == False, Detection.is_fixed == None)).count()
        active_reports = reports_query.filter(Report.is_false_report == False).filter(or_(Report.is_fixed == False, Report.is_fixed == None)).count()
        active_defects = active_detections + active_reports

        # Resolved Defects (Fixed)
        resolved_detections = detections_query.filter(Detection.is_fixed == True).count()
        resolved_reports = reports_query.filter(Report.is_false_report == False).filter(Report.is_fixed == True).count()
        resolved_defects = resolved_detections + resolved_reports

        # Avg Repair Time
        fixed_detections_data = detections_query.filter(Detection.is_fixed == True).with_entities(Detection.created_at, Detection.fixed_at).all()
        fixed_reports_data = reports_query.filter(Report.is_false_report == False).filter(Report.is_fixed == True).with_entities(Report.created_at, Report.fixed_at).all()
        
        total_repair_time = 0
        count_fixed = 0
        for created, fixed in fixed_detections_data:
            if fixed and created and fixed > created:
                total_repair_time += (fixed - created)
                count_fixed += 1
        for created, fixed in fixed_reports_data:
            if fixed and created and fixed > created:
                total_repair_time += (fixed - created)
                count_fixed += 1
                
        avg_repair_time_hours = 0
        if count_fixed > 0:
            avg_repair_time_hours = (total_repair_time / count_fixed) / 3600

        # Detection Accuracy (based on review_status)
        reviewed_query = detections_query.filter(Detection.review_status.in_(['confirmed', 'rejected']))
        total_reviewed = reviewed_query.count()
        confirmed_count = reviewed_query.filter(Detection.review_status == 'confirmed').count()
        
        accuracy = 0
        if total_reviewed > 0:
            accuracy = (confirmed_count / total_reviewed) * 100

    return jsonify({
        'total_potholes': total_potholes,
        'total_reports': total_reports,
        'active_defects': active_defects,
        'resolved_defects': resolved_defects,
        'avg_repair_time': round(avg_repair_time_hours, 1),
        'detection_accuracy': round(accuracy, 1)
    })

@app.route('/api/analytics/trends')
@require_admin_view
def get_analytics_trends():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    interval = request.args.get('interval', 'daily') # daily, weekly, monthly
    admin_area = request.args.get('admin_area')
    admin_level = request.args.get('admin_level', 'province')
    
    query = Detection.query
    if start_date:
        try:
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            query = query.filter(Detection.created_at >= start_ts)
        except ValueError:
            pass
    if end_date:
        try:
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            query = query.filter(Detection.created_at <= end_ts)
        except ValueError:
            pass

    if admin_area and admin_area != 'all':
        d_list = filter_by_area(query, Detection, admin_area, admin_level)
        timestamps = [d.created_at for d in d_list]
    else:

        timestamps = [r[0] for r in query.with_entities(Detection.created_at).all()]
        
    timestamps.sort()
    
    data_map = {}
    for ts in timestamps:
        dt = time.localtime(ts)
        if interval == 'monthly':
            key = time.strftime('%Y-%m', dt)
        elif interval == 'weekly':
            key = time.strftime('%Y-W%U', dt)
        else: # daily
            key = time.strftime('%Y-%m-%d', dt)
            
        data_map[key] = data_map.get(key, 0) + 1
        
    sorted_keys = sorted(data_map.keys())
    return jsonify({
        'labels': sorted_keys,
        'values': [data_map[k] for k in sorted_keys]
    })

@app.route('/api/analytics/heatmap')
@require_admin_view
def get_analytics_heatmap():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    admin_area = request.args.get('admin_area')
    admin_level = request.args.get('admin_level', 'province')
    
    d_query = Detection.query
    r_query = Report.query.filter(Report.is_false_report == False)
    
    if start_date:
        try:
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            d_query = d_query.filter(Detection.created_at >= start_ts)
            r_query = r_query.filter(Report.created_at >= start_ts)
        except ValueError:
            pass
    if end_date:
        try:
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            d_query = d_query.filter(Detection.created_at <= end_ts)
            r_query = r_query.filter(Report.created_at <= end_ts)
        except ValueError:
            pass
            
    points = []
    
    if admin_area and admin_area != 'all':
        d_list = filter_by_area(d_query, Detection, admin_area, admin_level)
        r_list = filter_by_area(r_query, Report, admin_area, admin_level)
        
        for d in d_list:

            if d.latitude and d.longitude:
                points.append([d.latitude, d.longitude, 0.5])
        for r in r_list:
            if r.latitude and r.longitude:
                points.append([r.latitude, r.longitude, 0.8])
    else:
        for lat, lng in d_query.with_entities(Detection.latitude, Detection.longitude).all():
            if lat and lng:
                points.append([lat, lng, 0.5])
                
        for lat, lng in r_query.with_entities(Report.latitude, Report.longitude).all():
            if lat and lng:
                points.append([lat, lng, 0.8])
            
    return jsonify(points)

@app.route('/api/analytics/status-distribution')
@require_admin_view
def get_analytics_status_distribution():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    admin_area = request.args.get('admin_area')
    admin_level = request.args.get('admin_level', 'province')
    
    d_query = Detection.query
    r_query = Report.query.filter(Report.is_false_report == False)
    
    if start_date:
        try:
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            d_query = d_query.filter(Detection.created_at >= start_ts)
            r_query = r_query.filter(Report.created_at >= start_ts)
        except ValueError:
            pass
    if end_date:
        try:
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            d_query = d_query.filter(Detection.created_at <= end_ts)
            r_query = r_query.filter(Report.created_at <= end_ts)
        except ValueError:
            pass

    if admin_area and admin_area != 'all':
        d_list = filter_by_area(d_query, Detection, admin_area, admin_level)
        r_list = filter_by_area(r_query, Report, admin_area, admin_level)
        
        detected_open = sum(1 for d in d_list if not d.is_fixed)

        reported_open = sum(1 for r in r_list if not r.is_fixed)
        
        detected_fixed = sum(1 for d in d_list if d.is_fixed)
        reported_fixed = sum(1 for r in r_list if r.is_fixed)
    else:
        detected_open = d_query.filter(or_(Detection.is_fixed == False, Detection.is_fixed == None)).count()
        reported_open = r_query.filter(or_(Report.is_fixed == False, Report.is_fixed == None)).count()
        
        detected_fixed = d_query.filter(Detection.is_fixed == True).count()
        reported_fixed = r_query.filter(Report.is_fixed == True).count()
    
    return jsonify({
        'labels': ['Detected (Open)', 'Reported (Open)', 'Fixed'],
        'values': [detected_open, reported_open, detected_fixed + reported_fixed]
    })

@app.route('/api/analytics/ai-confidence')
@require_admin_view
def get_analytics_confidence():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    admin_area = request.args.get('admin_area')
    admin_level = request.args.get('admin_level', 'province')
    
    query = Detection.query.filter(Detection.confidence > 0)
    
    if start_date:
        try:
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            query = query.filter(Detection.created_at >= start_ts)
        except ValueError:
            pass
    if end_date:
        try:
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            query = query.filter(Detection.created_at <= end_ts)
        except ValueError:
            pass
            
    if admin_area and admin_area != 'all':
        d_list = filter_by_area(query, Detection, admin_area, admin_level)
        confidences = [d.confidence for d in d_list]
    else:

        confidences = [r[0] for r in query.with_entities(Detection.confidence).all()]
    
    bins = [0, 0, 0, 0, 0]
    labels = ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%']
    
    total_conf = 0
    count = 0
    for c in confidences:
        total_conf += c
        count += 1
        if c < 0.2: bins[0] += 1
        elif c < 0.4: bins[1] += 1
        elif c < 0.6: bins[2] += 1
        elif c < 0.8: bins[3] += 1
        else: bins[4] += 1
        
    avg_conf = (total_conf / count) if count > 0 else 0
    
    return jsonify({
        'labels': labels,
        'values': bins,
        'average': round(avg_conf * 100, 1)
    })

@app.route('/api/analytics/repair-performance')
@require_admin_view
def get_analytics_repair_performance():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    admin_area = request.args.get('admin_area')
    admin_level = request.args.get('admin_level', 'province')
    
    d_query = Detection.query.filter(Detection.is_fixed == True)
    r_query = Report.query.filter(Report.is_false_report == False).filter(Report.is_fixed == True)
    
    if start_date:
        try:
            start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
            d_query = d_query.filter(Detection.fixed_at >= start_ts)
            r_query = r_query.filter(Report.fixed_at >= start_ts)
        except ValueError:
            pass
    if end_date:
        try:
            end_ts = int(time.mktime(time.strptime(end_date, "%Y-%m-%d"))) + 86399
            d_query = d_query.filter(Detection.fixed_at <= end_ts)
            r_query = r_query.filter(Report.fixed_at <= end_ts)
        except ValueError:
            pass
            
    timestamps = []
    
    if admin_area and admin_area != 'all':
        d_list = filter_by_area(d_query, Detection, admin_area, admin_level)
        r_list = filter_by_area(r_query, Report, admin_area, admin_level)
        timestamps.extend([d.fixed_at for d in d_list if d.fixed_at])
        timestamps.extend([r.fixed_at for r in r_list if r.fixed_at])
    else:

        timestamps.extend([r[0] for r in d_query.with_entities(Detection.fixed_at).all() if r[0]])
        timestamps.extend([r[0] for r in r_query.with_entities(Report.fixed_at).all() if r[0]])
        
    timestamps.sort()
    
    data_map = {}
    for ts in timestamps:
        dt = time.localtime(ts)
        key = time.strftime('%Y-W%U', dt)
        data_map[key] = data_map.get(key, 0) + 1
        
    sorted_keys = sorted(data_map.keys())
    
    return jsonify({
        'labels': sorted_keys,
        'values': [data_map[k] for k in sorted_keys]
    })


import json
import os
from flask import current_app

_geojson_cache = {}

def load_geojson_polygons(area_type='province'):
    """
    Loads GeoJSON data and returns a dictionary of polygons keyed by area name.
    Supported types: 'province', 'municipality', 'region'
    """
    global _geojson_cache
    if area_type in _geojson_cache:
        return _geojson_cache[area_type]

    filename = f'{area_type}s.json'
    if area_type == 'municipality':
        filename = 'municipalities.json'
    
    filepath = os.path.join(current_app.static_folder, 'data', filename)
    if not os.path.exists(filepath):
        return {}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        polygons = {}
        for feature in data.get('features', []):
            props = feature.get('properties', {})
            # Determine name based on type
            name = ''
            if area_type == 'province':
                name = props.get('NAME_1')
            elif area_type == 'municipality':
                name = props.get('NAME_2')
            elif area_type == 'region':
                name = props.get('name') or props.get('REGION')
            
            if not name:
                continue
                
            geometry = feature.get('geometry')
            if geometry:
                polygons[name] = geometry
        
        _geojson_cache[area_type] = polygons
        return polygons
    except Exception as e:
        print(f"Error loading GeoJSON: {e}")
        return {}

def point_in_polygon(point, polygon_coords):
    """
    Ray-casting algorithm to check if a point is inside a polygon.
    point: (lat, lng)
    polygon_coords: List of [lng, lat] (GeoJSON format)
    """
    lat, lng = point
    inside = False
    j = len(polygon_coords) - 1
    for i in range(len(polygon_coords)):
        xi, yi = polygon_coords[i]
        xj, yj = polygon_coords[j]
        
        intersect = ((yi > lat) != (yj > lat)) and             (lng < (xj - xi) * (lat - yi) / (yj - yi + 1e-9) + xi)
        if intersect:
            inside = not inside
        j = i
    return inside

def is_point_in_geometry(lat, lng, geometry):
    """
    Checks if a point (lat, lng) is inside a GeoJSON geometry (Polygon or MultiPolygon).
    """
    if not lat or not lng:
        return False
        
    geom_type = geometry.get('type')
    coords = geometry.get('coordinates')
    
    if geom_type == 'Polygon':
        if not coords: return False
        return point_in_polygon((lat, lng), coords[0])
        
    elif geom_type == 'MultiPolygon':
        if not coords: return False
        for poly in coords:
            if point_in_polygon((lat, lng), poly[0]):
                return True
        return False
        
    return False

def filter_by_area(query, model, area_name, area_type='province'):
    """
    Filters a SQLAlchemy query by checking if the model's lat/lng are inside the area.
    """
    if not area_name:
        return query.all() # Return list to be consistent
        
    polygons = load_geojson_polygons(area_type)
    geometry = polygons.get(area_name)
    
    if not geometry:
        return query.all()
        
    all_records = query.all()
    filtered = []
    for record in all_records:
        if is_point_in_geometry(record.latitude, record.longitude, geometry):
            filtered.append(record)
            
    return filtered



if __name__ == "__main__":
    ensure_gps_thread()
    app.run(debug=True, host="0.0.0.0", port=8000, use_reloader=False)
