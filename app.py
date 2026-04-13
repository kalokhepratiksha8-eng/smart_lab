from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import qrcode
import os
import socket
from functools import wraps

app = Flask(__name__)
app.secret_key = 'qrlab_secret_2024'

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="P@K!2816#P",
        database="smartlabmanagement"
    )

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# Lab ID -> actual table names in DB
LAB_TABLE = {1: 'sl',  2: 'osl',  3: 'spl',  4: 'es',  5: 'pl',  6: 'ccl'}
PC_TABLE  = {1: 'sl_pcs',  2: 'osl_pcs',  3: 'spl_pcs',  4: 'es_pcs',  5: 'pl_pcs',  6: 'ccl_pcs'}
EQ_TABLE  = {1: 'sl_equipment',  2: 'osl_equipment',  3: 'spl_equipment',  4: 'es_equipment',  5: 'pl_equipment',  6: 'ccl_equipment'}
SW_TABLE  = {1: 'sl_software',  2: 'osl_software',  3: 'spl_software',  4: 'es_software',  5: 'pl_software',  6: 'ccl_software'}

# ───────────────────────────── LOGIN / LOGOUT ─────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Support both 'username' and 'email' field names
        username = request.form.get('username', request.form.get('email', '')).strip()
        password = request.form.get('password', '').strip()
        try:
            db = get_db()
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
            user = cursor.fetchone()
            db.close()
            if user:
                session['username'] = user['username']
                session['role'] = user.get('role', 'Admin')
                return redirect(url_for('home'))
            else:
                flash('Invalid username or password.', 'error')
        except Exception as e:
            flash(f'DB Error: {e}', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ───────────────────────────── HOME DASHBOARD ─────────────────────────────

@app.route('/')
@login_required
def home():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) as cnt FROM lab")
        labs_count = cursor.fetchone()['cnt']

        # Total PCs = sum of no_pc column from each lab table
        pc_total = 0
        for tbl in LAB_TABLE.values():
            try:
                cursor.execute(f"SELECT COALESCE(SUM(no_pc), 0) as cnt FROM {tbl}")
                pc_total += int(cursor.fetchone()['cnt'])
            except:
                try:
                    cursor.execute(f"SELECT COALESCE(SUM(total_pcs), 0) as cnt FROM {tbl}")
                    pc_total += int(cursor.fetchone()['cnt'])
                except:
                    pass
        pcs_count = pc_total

        # Count DISTINCT software names across all 6 labs (no duplicates)
        try:
            cursor.execute("""
                SELECT COUNT(DISTINCT software_name) as cnt FROM (
                    SELECT software_name FROM sl_software
                    UNION SELECT software_name FROM osl_software
                    UNION SELECT software_name FROM spl_software
                    UNION SELECT software_name FROM es_software
                    UNION SELECT software_name FROM pl_software
                    UNION SELECT software_name FROM ccl_software
                ) all_sw
            """)
            software_count = cursor.fetchone()['cnt']
        except:
            software_count = 0

        maintenance_count = 0  # can be updated if you have a maintenance table

        db.close()
        return render_template('dashboard.html',
            labs_count=labs_count,
            pcs_count=pcs_count,
            software_count=software_count,
            maintenance_count=maintenance_count
        )
    except Exception as e:
        flash(f'Dashboard error: {e}', 'error')
        return render_template('dashboard.html',
            labs_count=0, pcs_count=0, software_count=0, maintenance_count=0
        )

# ───────────────────────────── LABS LIST ─────────────────────────────

@app.route('/labs')
@login_required
def labs():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT l.lab_id, l.lab_no, l.lab_name, l.location,
                   l.incharge, l.lab_assistant, l.total_pcs,
                   d.dep_name
            FROM lab l
            LEFT JOIN department d ON l.dep_id = d.dep_id
            ORDER BY l.lab_id
        """)
        all_labs = cursor.fetchall()
        db.close()
        return render_template('labs.html', labs=all_labs)
    except Exception as e:
        flash(f'Labs error: {e}', 'error')
        return render_template('labs.html', labs=[])

# ───────────────────────────── LAB DETAIL (6 labs) ─────────────────────────────

@app.route('/lab/<int:lab_id>')
@login_required
def lab_detail(lab_id):
    if lab_id not in LAB_TABLE:
        flash('Lab not found.', 'error')
        return redirect(url_for('labs'))

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Lab info from specific lab table
        cursor.execute(f"SELECT * FROM {LAB_TABLE[lab_id]} LIMIT 1")
        lab_raw = cursor.fetchone()

        if not lab_raw:
            flash('Lab data not found.', 'error')
            db.close()
            return redirect(url_for('labs'))

        # Normalize column names
        lab = {
            'lab_id':        lab_id,
            'lab_name':      lab_raw.get('lab_name', ''),
            'lab_no':        lab_raw.get('lab_no', ''),
            'location':      lab_raw.get('lab_location', lab_raw.get('location', '')),
            'incharge':      lab_raw.get('lab_incharge', lab_raw.get('incharge', '')),
            'lab_assistant': lab_raw.get('lab_assistant', ''),
            'total_pcs':     lab_raw.get('no_pc', lab_raw.get('total_pcs', 0)),
            'lab_time_slot': lab_raw.get('lab_time_slot', ''),
            'dep_name':      'Computer Engineering'
        }

        # PCs for this lab
        cursor.execute(f"SELECT * FROM {PC_TABLE[lab_id]} ORDER BY pc_no")
        pcs = cursor.fetchall()

        # Equipment for this lab
        cursor.execute(f"SELECT * FROM {EQ_TABLE[lab_id]} ORDER BY equipment_name")
        equipment = cursor.fetchall()

        # Software for this lab
        cursor.execute(f"SELECT * FROM {SW_TABLE[lab_id]} ORDER BY software_name")
        softwares = cursor.fetchall()

        db.close()

        return render_template('lab_detail.html',
            lab=lab,
            pcs=pcs,
            equipment=equipment,
            softwares=softwares
        )

    except Exception as e:
        flash(f'Lab detail error: {e}', 'error')
        return redirect(url_for('labs'))

# ───────────────────────────── SOFTWARE ─────────────────────────────

@app.route('/software')
@login_required
def software():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        query = """
            SELECT software_name, version, license_type,
                   GROUP_CONCAT(DISTINCT lab_name ORDER BY lab_name SEPARATOR ', ') as labs
            FROM (
                SELECT software_name, version, license_type, 'SL'  as lab_name FROM sl_software
                UNION ALL
                SELECT software_name, version, license_type, 'OSL' as lab_name FROM osl_software
                UNION ALL
                SELECT software_name, version, license_type, 'SPL' as lab_name FROM spl_software
                UNION ALL
                SELECT software_name, version, license_type, 'ES'  as lab_name FROM es_software
                UNION ALL
                SELECT software_name, version, license_type, 'PL'  as lab_name FROM pl_software
                UNION ALL
                SELECT software_name, version, license_type, 'CCL' as lab_name FROM ccl_software
            ) all_sw
            GROUP BY software_name, version, license_type
            ORDER BY software_name
        """
        cursor.execute(query)
        softwares = cursor.fetchall()
        db.close()

        return render_template('software.html', softwares=softwares)
    except Exception as e:
        flash(f'Software error: {e}', 'error')
        return render_template('software.html', softwares=[])

# ───────────────────────────── QR CODE ─────────────────────────────

@app.route('/generate_qr/<int:lab_id>')
@login_required
def generate_qr(lab_id):
    if lab_id not in LAB_TABLE:
        flash('Lab not found.', 'error')
        return redirect(url_for('labs'))

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM {LAB_TABLE[lab_id]} LIMIT 1")
        lab_raw = cursor.fetchone()
        db.close()

        if not lab_raw:
            flash('Lab data not found.', 'error')
            return redirect(url_for('labs'))

        lab = {
            'lab_id':   lab_id,
            'lab_name': lab_raw.get('lab_name', ''),
            'lab_no':   lab_raw.get('lab_no', ''),
            'location': lab_raw.get('lab_location', lab_raw.get('location', '')),
            'incharge': lab_raw.get('lab_incharge', lab_raw.get('incharge', '')),
            'dep_name': 'Computer Engineering'
        }

        # Always get fresh IP so QR works on current network
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"

        qr_data = f"http://{local_ip}:5000/lab-info?lab_id={lab_id}"

        # Generate QR with better quality
        import qrcode as qr_module
        qr_obj = qr_module.QRCode(
            version=1,
            error_correction=qr_module.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr_obj.add_data(qr_data)
        qr_obj.make(fit=True)
        qr_img = qr_obj.make_image(fill_color="black", back_color="white")
        qr_dir = os.path.join('static', 'qrcodes')
        os.makedirs(qr_dir, exist_ok=True)
        qr_img.save(os.path.join(qr_dir, f"lab_{lab_id}.png"))

        return render_template('qr_code.html',
            lab=lab,
            qr_image=f"qrcodes/lab_{lab_id}.png",
            qr_url=qr_data
        )
    except Exception as e:
        flash(f'QR error: {e}', 'error')
        return redirect(url_for('labs'))

# ───────────────────────────── PCS ─────────────────────────────

@app.route('/pcs')
@login_required
def pcs():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        all_pcs = []
        lab_names = {1: 'SL', 2: 'OSL', 3: 'SPL', 4: 'ES', 5: 'PL', 6: 'CCL'}
        for lab_id, tbl in PC_TABLE.items():
            try:
                cursor.execute(f"SELECT *, {lab_id} as lab_id FROM {tbl} ORDER BY pc_no")
                rows = cursor.fetchall()
                for row in rows:
                    row['lab_name'] = lab_names.get(lab_id, '')
                all_pcs.extend(rows)
            except:
                pass
        db.close()
        return render_template('pcs.html', pcs=all_pcs)
    except Exception as e:
        flash(f'PCs error: {e}', 'error')
        return render_template('pcs.html', pcs=[])

# ───────────────────────────── MAINTENANCE ─────────────────────────────

@app.route('/maintenance')
@login_required
def maintenance():
    return render_template('maintenance.html', maintenance=[])

# ───────────────────────────── USERS ─────────────────────────────

@app.route('/users')
@login_required
def users():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT user_id, username, role FROM users")
        all_users = cursor.fetchall()
        db.close()
        return render_template('users.html', users=all_users)
    except Exception as e:
        flash(f'Users error: {e}', 'error')
        return render_template('users.html', users=[])


# ─────────────── PUBLIC LAB INFO (QR scan lands here) ───────────────

# Fallback static lab data (used if DB is unreachable)
STATIC_LAB_DATA = {
    1: {'lab_name': 'Software Lab (SL)',         'lab_no': 'SL-101',  'location': 'Building A, Floor 1', 'incharge': 'Prof. In-charge',  'lab_assistant': 'Lab Assistant', 'total_pcs': 30, 'lab_time_slot': '9:00 AM - 5:00 PM', 'dep_name': 'Computer Engineering'},
    2: {'lab_name': 'OS Lab (OSL)',               'lab_no': 'OSL-102', 'location': 'Building A, Floor 1', 'incharge': 'Prof. In-charge',  'lab_assistant': 'Lab Assistant', 'total_pcs': 30, 'lab_time_slot': '9:00 AM - 5:00 PM', 'dep_name': 'Computer Engineering'},
    3: {'lab_name': 'Special Purpose Lab (SPL)',  'lab_no': 'SPL-201', 'location': 'Building B, Floor 2', 'incharge': 'Prof. In-charge',  'lab_assistant': 'Lab Assistant', 'total_pcs': 25, 'lab_time_slot': '9:00 AM - 5:00 PM', 'dep_name': 'Computer Engineering'},
    4: {'lab_name': 'Embedded Systems Lab (ES)',  'lab_no': 'ES-202',  'location': 'Building B, Floor 2', 'incharge': 'Prof. In-charge',  'lab_assistant': 'Lab Assistant', 'total_pcs': 20, 'lab_time_slot': '9:00 AM - 5:00 PM', 'dep_name': 'Computer Engineering'},
    5: {'lab_name': 'Programming Lab (PL)',       'lab_no': 'PL-301',  'location': 'Building C, Floor 3', 'incharge': 'Prof. In-charge',  'lab_assistant': 'Lab Assistant', 'total_pcs': 35, 'lab_time_slot': '9:00 AM - 5:00 PM', 'dep_name': 'Computer Engineering'},
    6: {'lab_name': 'Cloud Computing Lab (CCL)',  'lab_no': 'CCL-302', 'location': 'Building C, Floor 3', 'incharge': 'Prof. In-charge',  'lab_assistant': 'Lab Assistant', 'total_pcs': 30, 'lab_time_slot': '9:00 AM - 5:00 PM', 'dep_name': 'Computer Engineering'},
}

@app.route('/lab-info')
def lab_info():
    lab_id = request.args.get('lab_id', type=int)
    if not lab_id or lab_id not in LAB_TABLE:
        # Show a friendly page instead of raw 404
        return render_template('lab_info_error.html', message="Invalid Lab ID. Please scan a valid QR code."), 404

    db_error = None
    lab = None

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM {LAB_TABLE[lab_id]} LIMIT 1")
        lab_raw = cursor.fetchone()
        db.close()

        if lab_raw:
            lab = {
                'lab_id':        lab_id,
                'lab_name':      lab_raw.get('lab_name', ''),
                'lab_no':        lab_raw.get('lab_no', ''),
                'location':      lab_raw.get('lab_location', lab_raw.get('location', '')),
                'incharge':      lab_raw.get('lab_incharge', lab_raw.get('incharge', '')),
                'lab_assistant': lab_raw.get('lab_assistant', ''),
                'total_pcs':     lab_raw.get('no_pc', lab_raw.get('total_pcs', 0)),
                'lab_time_slot': lab_raw.get('lab_time_slot', ''),
                'dep_name':      'Computer Engineering'
            }
    except Exception as e:
        db_error = str(e)

    # Fallback to static data if DB failed or returned empty
    if not lab:
        static = STATIC_LAB_DATA.get(lab_id, {})
        lab = {
            'lab_id':        lab_id,
            'lab_name':      static.get('lab_name', f'Lab {lab_id}'),
            'lab_no':        static.get('lab_no', f'L-{lab_id}'),
            'location':      static.get('location', '-'),
            'incharge':      static.get('incharge', '-'),
            'lab_assistant': static.get('lab_assistant', '-'),
            'total_pcs':     static.get('total_pcs', 0),
            'lab_time_slot': static.get('lab_time_slot', '-'),
            'dep_name':      static.get('dep_name', 'Computer Engineering')
        }

    return render_template('lab_info.html', lab=lab, db_error=db_error)

# ─────────────── CONFIDENTIAL LOGIN (POST from lab_info) ───────────────

@app.route('/lab-confidential', methods=['POST'])
def lab_confidential():
    lab_id   = request.form.get('lab_id', type=int)
    username = request.form.get('user_id', '').strip()
    password = request.form.get('password', '').strip()
    if not lab_id or lab_id not in LAB_TABLE:
        return "Lab not found.", 404
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        def get_lab_dict(lab_raw):
            return {
                'lab_id':        lab_id,
                'lab_name':      lab_raw.get('lab_name', ''),
                'lab_no':        lab_raw.get('lab_no', ''),
                'location':      lab_raw.get('lab_location', lab_raw.get('location', '')),
                'incharge':      lab_raw.get('lab_incharge', lab_raw.get('incharge', '')),
                'lab_assistant': lab_raw.get('lab_assistant', ''),
                'total_pcs':     lab_raw.get('no_pc', lab_raw.get('total_pcs', 0)),
                'lab_time_slot': lab_raw.get('lab_time_slot', ''),
                'dep_name':      'Computer Engineering'
            }

        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()

        cursor.execute(f"SELECT * FROM {LAB_TABLE[lab_id]} LIMIT 1")
        lab_raw = cursor.fetchone()
        lab = get_lab_dict(lab_raw)

        if not user:
            db.close()
            return render_template('lab_info.html', lab=lab,
                                   error="Invalid User ID or Password. Access Denied.")

        cursor.execute(f"SELECT * FROM {PC_TABLE[lab_id]} ORDER BY pc_no")
        pcs = cursor.fetchall()
        cursor.execute(f"SELECT * FROM {EQ_TABLE[lab_id]} ORDER BY equipment_name")
        equipment = cursor.fetchall()
        cursor.execute(f"SELECT * FROM {SW_TABLE[lab_id]} ORDER BY software_name")
        softwares = cursor.fetchall()
        db.close()

        return render_template('lab_confidential.html',
            lab=lab, pcs=pcs, equipment=equipment, softwares=softwares,
            logged_user=user['username'], role=user.get('role', 'Admin')
        )
    except Exception as e:
        # DB failed - show friendly error on lab_info page with static data
        static = STATIC_LAB_DATA.get(lab_id, {})
        lab = {
            'lab_id':        lab_id,
            'lab_name':      static.get('lab_name', f'Lab {lab_id}'),
            'lab_no':        static.get('lab_no', f'L-{lab_id}'),
            'location':      static.get('location', '-'),
            'incharge':      static.get('incharge', '-'),
            'lab_assistant': static.get('lab_assistant', '-'),
            'total_pcs':     static.get('total_pcs', 0),
            'lab_time_slot': static.get('lab_time_slot', '-'),
            'dep_name':      'Computer Engineering'
        }
        return render_template('lab_info.html', lab=lab,
                               error="Server error. Please try again later.")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
