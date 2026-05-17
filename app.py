from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.secret_key = "steel_advanced_v9_2026"

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'factory_v9.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# الجداول
class Coil(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coil_code = db.Column(db.String(50), unique=True)
    coil_type = db.Column(db.String(50)) # النوع (صاج بارد، مجلفن، إلخ)
    thickness = db.Column(db.Float)
    width = db.Column(db.Float)
    remaining_weight = db.Column(db.Float)
    location = db.Column(db.String(100))

class CuttingOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100))
    coil_code = db.Column(db.String(50))
    requested_weight = db.Column(db.Float)
    length = db.Column(db.Float)
    sheet_count = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.now)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    orders = CuttingOrder.query.order_by(CuttingOrder.id.desc()).all()
    excel_coils = []
    excel_path = os.path.join(basedir, 'coils_list.xlsx')
    
    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path)
            df.columns = df.columns.str.strip()
            excel_coils = df.to_dict(orient='records')
        except: pass

    db_coils = {c.coil_code: c for c in Coil.query.all()}
    final_inventory = []
    for row in excel_coils:
        code = str(row.get('coil_code', ''))
        # تحديث الوزن والنوع من قاعدة البيانات إذا تم تعديلهم
        if code in db_coils:
            row['remaining_weight'] = db_coils[code].remaining_weight
            row['coil_type'] = db_coils[code].coil_type or row.get('coil_type', 'غير محدد')
        else:
            row['remaining_weight'] = row.get('total_weight', 0)
            row['coil_type'] = row.get('coil_type', 'غير محدد')
        final_inventory.append(row)

    return render_template('slitting.html', inventory=final_inventory, orders=orders)

@app.route('/add_order', methods=['POST'])
def add_order():
    code = request.form.get('coil_code')
    req_w = float(request.form.get('requested_weight') or 0)
    
    coil = Coil.query.filter_by(coil_code=code).first()
    if not coil:
        coil = Coil(
            coil_code=code,
            coil_type=request.form.get('coil_type'),
            thickness=float(request.form.get('thickness') or 0),
            width=float(request.form.get('width') or 0),
            remaining_weight=float(request.form.get('total_weight_original') or 20000),
            location="المخزن"
        )
        db.session.add(coil)

    new_order = CuttingOrder(
        customer_name=request.form.get('customer_name'),
        coil_code=code,
        requested_weight=req_w,
        length=float(request.form.get('cut_length') or 0),
        sheet_count=int(request.form.get('sheet_count') or 0)
    )
    db.session.add(new_order)
    db.session.commit()
    flash("✅ تم تسجيل أمر التقطيع")
    return redirect(url_for('index'))

@app.route('/complete_order/<int:id>')
def complete_order(id):
    order = CuttingOrder.query.get_or_404(id)
    coil = Coil.query.filter_by(coil_code=order.coil_code).first()
    if coil and coil.remaining_weight >= order.requested_weight:
        coil.remaining_weight -= order.requested_weight
        db.session.delete(order)
        db.session.commit()
        flash("✔️ تم التنفيذ بنجاح")
    else:
        flash("❌ فشل: الوزن غير متوفر", "danger")
    return redirect(url_for('index'))

@app.route('/delete_order/<int:id>')
def delete_order(id):
    order = CuttingOrder.query.get_or_404(id)
    db.session.delete(order)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)