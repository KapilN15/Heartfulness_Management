import os
import io
import json
import uuid
import pandas as pd
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, session as flask_session
from flask_login import login_required, current_user
from datetime import datetime, date
from app.models import Member, Category, ImportHistory
from app import db
from app.utils.audit import log_action

csv_import_bp = Blueprint('csv_import', __name__)

REQUIRED_COLUMNS = ['full_name', 'gender', 'age', 'religion', 'mobile_number', 'area']


def get_preview_dir():
    """Return path to temporary preview storage directory."""
    import os
    from flask import current_app
    d = os.path.join(current_app.instance_path, 'uploads', 'preview_tmp')
    os.makedirs(d, exist_ok=True)
    return d


def save_preview(data, filename):
    """Save preview data to a temp JSON file. Returns a token."""
    token = str(uuid.uuid4())
    path = os.path.join(get_preview_dir(), f'{token}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'filename': filename, 'rows': data}, f, ensure_ascii=False, default=str)
    return token


def load_preview(token):
    """Load preview data from temp file. Returns (rows, filename) or (None, None)."""
    if not token:
        return None, None
    path = os.path.join(get_preview_dir(), f'{token}.json')
    if not os.path.exists(path):
        return None, None
    with open(path, 'r', encoding='utf-8') as f:
        d = json.load(f)
    return d.get('rows'), d.get('filename', 'unknown.csv')


def delete_preview(token):
    """Delete temp preview file after import or cancel."""
    if not token:
        return
    path = os.path.join(get_preview_dir(), f'{token}.json')
    try:
        os.remove(path)
    except Exception:
        pass
    # Also clean up any stale files older than 24 hours
    try:
        import time
        d = get_preview_dir()
        now = time.time()
        for f in os.listdir(d):
            fp = os.path.join(d, f)
            if os.path.isfile(fp) and (now - os.path.getmtime(fp)) > 86400:
                os.remove(fp)
    except Exception:
        pass


def parse_date(val):
    """Try multiple date formats."""
    if not val or str(val).strip() in ('', 'nan', 'None', 'NaT'):
        return date.today()
    val = str(val).strip()
    for fmt in ('%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d %b %Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(val[:10], fmt).date()
        except Exception:
            pass
    return date.today()


def read_csv_flexible(file_storage):
    """Read CSV or TSV, auto-detecting the separator."""
    raw = file_storage.read()
    first_line = raw.split(b'\n')[0].decode('utf-8', errors='ignore')
    sep = '\t' if first_line.count('\t') >= first_line.count(',') else ','
    try:
        df = pd.read_csv(io.BytesIO(raw), sep=sep, dtype=str, keep_default_na=False)
    except Exception:
        df = pd.read_csv(io.BytesIO(raw), sep=',', dtype=str, keep_default_na=False)
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    return df


@csv_import_bp.route('/csv-import')
@login_required
def index():
    history = ImportHistory.query.order_by(ImportHistory.imported_at.desc()).limit(20).all()
    return render_template('csv_import/index.html', history=history)


@csv_import_bp.route('/csv-import/sample')
@login_required
def sample():
    rows = [
        ['full_name', 'gender', 'age', 'religion', 'mobile_number', 'area', 'join_date', 'status', 'category'],
        ['Arjun Sharma',   'Male',   '30', 'Hindu',     '9876543210', 'HOSUR',      '01-01-2024', 'Active',   'Meditation'],
        ['Priya Patel',    'Female', '25', 'Muslim',    '9123456789', 'TRICHY',     '15-02-2024', 'Active',   'Meditation, Youth Program'],
        ['Ravi Kumar',     'Male',   '40', 'Christian', '9988776655', 'CHENNAI',    '10-03-2024', 'Active',   'Community Service, Wellness, Meditation'],
        ['Sunita Devi',    'Female', '35', 'Hindu',     '8877665544', 'COIMBATORE', '20-04-2024', 'Active',   'Weekly Gathering'],
        ['Mohan Raj',      'Male',   '52', 'Hindu',     '7766554433', 'MADURAI',    '05-05-2024', 'Inactive', 'Wellness'],
    ]
    buf = io.StringIO()
    for row in rows:
        buf.write('\t'.join(row) + '\n')
    output = io.BytesIO(buf.getvalue().encode('utf-8'))
    return send_file(output, mimetype='text/tab-separated-values', as_attachment=True,
                     download_name='sample_members_import.csv')


@csv_import_bp.route('/csv-import/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('csv_import.index'))

    file = request.files['file']
    if not file.filename:
        flash('No file selected.', 'danger')
        return redirect(url_for('csv_import.index'))

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ('csv', 'tsv', 'txt'):
        flash('Only .csv / .tsv files are allowed.', 'danger')
        return redirect(url_for('csv_import.index'))

    try:
        df = read_csv_flexible(file)

        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            flash(
                f'Missing required columns: {", ".join(missing)}. '
                f'Found columns: {", ".join(df.columns.tolist())}',
                'danger'
            )
            return redirect(url_for('csv_import.index'))

        existing_mobiles = {
            m.mobile_number
            for m in Member.query.with_entities(Member.mobile_number).all()
        }
        valid_categories = {
            c.name.strip(): c
            for c in Category.query.filter_by(status='active').all()
        }

        preview_data = []
        for _, row in df.iterrows():
            mobile    = str(row.get('mobile_number', '')).strip()
            is_dup    = bool(mobile) and mobile in existing_mobiles

            cat_str   = str(row.get('category', '')).strip()
            categories = (
                [c.strip() for c in cat_str.split(',') if c.strip()]
                if cat_str and cat_str not in ('nan', 'None')
                else []
            )
            invalid_cats = [c for c in categories if c not in valid_categories]

            raw_status = str(row.get('status', 'active')).strip().lower()
            status = 'active' if raw_status in ('active', '1', 'yes', 'true') else 'inactive'

            preview_data.append({
                'full_name':        str(row.get('full_name', '')).strip(),
                'gender':           str(row.get('gender',    '')).strip(),
                'age':              str(row.get('age',       '')).strip(),
                'religion':         str(row.get('religion',  '')).strip(),
                'mobile_number':    mobile,
                'area':             str(row.get('area',      '')).strip().upper(),
                'join_date':        str(row.get('join_date', '')).strip(),
                'status':           status,
                'category':         categories,
                'is_duplicate':     is_dup,
                'invalid_categories': invalid_cats,
            })

        # ── Store preview on disk, keep only a small token in the cookie ──
        token = save_preview(preview_data, file.filename)
        flask_session['csv_token']    = token
        flask_session['csv_filename'] = file.filename

        duplicates = sum(1 for r in preview_data if r['is_duplicate'])
        invalid    = sum(1 for r in preview_data if r['invalid_categories'])

        return render_template(
            'csv_import/preview.html',
            preview=preview_data,
            filename=file.filename,
            total=len(preview_data),
            duplicates=duplicates,
            invalid=invalid,
        )

    except Exception as e:
        flash(f'Error reading file: {str(e)}', 'danger')
        return redirect(url_for('csv_import.index'))


@csv_import_bp.route('/csv-import/confirm', methods=['POST'])
@login_required
def confirm():
    token    = flask_session.get('csv_token')
    filename = flask_session.get('csv_filename', 'unknown.csv')

    preview_data, _ = load_preview(token)
    if not preview_data:
        flash('Session expired or preview not found. Please re-upload.', 'warning')
        return redirect(url_for('csv_import.index'))

    valid_categories = {
        c.name.strip(): c
        for c in Category.query.filter_by(status='active').all()
    }
    existing_mobiles = {
        m.mobile_number
        for m in Member.query.with_entities(Member.mobile_number).all()
    }

    imported  = 0
    duplicates = 0
    failed    = 0

    for row in preview_data:
        if row['is_duplicate']:
            duplicates += 1
            continue
        if row['invalid_categories']:
            failed += 1
            continue
        try:
            age = None
            try:
                age = int(row.get('age', ''))
            except (ValueError, TypeError):
                pass

            member = Member(
                member_id     = Member.generate_member_id(),
                full_name     = row['full_name'],
                gender        = row['gender']   or None,
                age           = age,
                religion      = row['religion'] or None,
                mobile_number = row['mobile_number'] or None,
                area          = row['area'] or None,   # already uppercase
                join_date     = parse_date(row.get('join_date')),
                status        = row.get('status', 'active'),
                created_by    = current_user.id,
            )
            for cat_name in row.get('category', []):
                cat = valid_categories.get(cat_name.strip())
                if cat:
                    member.categories.append(cat)

            db.session.add(member)
            existing_mobiles.add(row['mobile_number'])
            imported += 1

        except Exception:
            failed += 1

    hist = ImportHistory(
        filename        = filename,
        imported_count  = imported,
        duplicate_count = duplicates,
        failed_count    = failed,
        imported_by     = current_user.id,
    )
    db.session.add(hist)
    db.session.commit()

    # Clean up
    delete_preview(token)
    flask_session.pop('csv_token',    None)
    flask_session.pop('csv_filename', None)

    log_action(
        'Import CSV',
        f'Imported {imported} members from {filename}. '
        f'Duplicates: {duplicates}, Failed: {failed}'
    )
    flash(
        f'Import complete: {imported} imported, '
        f'{duplicates} duplicates skipped, {failed} failed.',
        'success'
    )
    return redirect(url_for('csv_import.index'))


@csv_import_bp.route('/csv-import/cancel', methods=['GET', 'POST'])
@login_required
def cancel():
    """Cancel a pending import and clean up the temp file."""
    token = flask_session.pop('csv_token', None)
    flask_session.pop('csv_filename', None)
    delete_preview(token)
    flash('Import cancelled.', 'info')
    return redirect(url_for('csv_import.index'))
