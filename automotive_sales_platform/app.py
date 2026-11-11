"""Automotive Sales Management Platform - Flask app.

Run:  python app.py   then open http://127.0.0.1:5000
"""
import sqlite3
from datetime import date

from flask import Flask, flash, g, jsonify, redirect, render_template, request, url_for

from database import connect, init_db

app = Flask(__name__)
app.secret_key = "change-this-secret-key"   # needed for flash messages
LOW_STOCK = 2


def get_db():
    if "db" not in g:
        g.db = connect()
    return g.db


@app.teardown_appcontext
def close_db(_):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.template_filter("inr")
def inr(value):
    return f"₹{(value or 0):,.0f}"


def kpis(db):
    row = db.execute(
        "SELECT COALESCE(SUM(quantity*price_at_sale),0) revenue, "
        "COALESCE(SUM(quantity),0) units, COUNT(*) orders FROM sales").fetchone()
    return {
        "revenue": row["revenue"], "units": row["units"], "orders": row["orders"],
        "in_stock": db.execute("SELECT COALESCE(SUM(stock),0) FROM vehicles").fetchone()[0],
        "customers": db.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
    }


# ---------------- Dashboard ----------------
@app.route("/")
def dashboard():
    db = get_db()
    by_make = db.execute(
        "SELECT v.make, SUM(s.quantity) units, SUM(s.quantity*s.price_at_sale) revenue "
        "FROM sales s JOIN vehicles v ON v.id = s.vehicle_id "
        "GROUP BY v.make ORDER BY revenue DESC").fetchall()
    monthly = db.execute(
        "SELECT strftime('%Y-%m', sale_date) month, SUM(quantity*price_at_sale) revenue "
        "FROM sales GROUP BY month ORDER BY month").fetchall()
    low = db.execute("SELECT * FROM vehicles WHERE stock <= ? ORDER BY stock", (LOW_STOCK,)).fetchall()
    recent = db.execute(
        "SELECT s.*, v.make, v.model, c.name customer FROM sales s "
        "JOIN vehicles v ON v.id = s.vehicle_id JOIN customers c ON c.id = s.customer_id "
        "ORDER BY sale_date DESC, s.id DESC LIMIT 5").fetchall()
    reps = db.execute(
        "SELECT salesperson, SUM(quantity) units, SUM(quantity*price_at_sale) revenue "
        "FROM sales GROUP BY salesperson ORDER BY revenue DESC").fetchall()
    return render_template(
        "index.html", kpi=kpis(db), by_make=by_make, monthly=monthly, low=low, recent=recent,
        reps=reps, max_make=max((r["revenue"] for r in by_make), default=1) or 1,
        max_month=max((r["revenue"] for r in monthly), default=1) or 1)


# ---------------- Vehicles ----------------
@app.route("/vehicles", methods=["GET", "POST"])
def vehicles():
    db = get_db()
    if request.method == "POST":
        try:
            make, model = request.form["make"].strip(), request.form["model"].strip()
            year, price, stock = (int(request.form["year"]), float(request.form["price"]),
                                  int(request.form["stock"]))
            if not make or not model or price <= 0 or stock < 0:
                raise ValueError
        except (KeyError, ValueError):
            flash("Please enter valid vehicle details.", "error")
            return redirect(url_for("vehicles"))
        db.execute("INSERT INTO vehicles (make, model, year, price, stock) VALUES (?,?,?,?,?)",
                   (make, model, year, price, stock))
        db.commit()
        flash(f"Added {make} {model}.", "ok")
        return redirect(url_for("vehicles"))
    rows = db.execute("SELECT * FROM vehicles ORDER BY make, model").fetchall()
    return render_template("vehicles.html", vehicles=rows, low_stock=LOW_STOCK,
                           this_year=date.today().year)


@app.route("/vehicles/<int:vid>/restock", methods=["POST"])
def restock(vid):
    try:
        qty = int(request.form["qty"])
        if qty < 1:
            raise ValueError
    except (KeyError, ValueError):
        flash("Restock quantity must be 1 or more.", "error")
        return redirect(url_for("vehicles"))
    db = get_db()
    db.execute("UPDATE vehicles SET stock = stock + ? WHERE id = ?", (qty, vid))
    db.commit()
    flash(f"Added {qty} unit(s) to stock.", "ok")
    return redirect(url_for("vehicles"))


@app.route("/vehicles/<int:vid>/delete", methods=["POST"])
def delete_vehicle(vid):
    db = get_db()
    try:
        db.execute("DELETE FROM vehicles WHERE id = ?", (vid,))
        db.commit()
        flash("Vehicle deleted.", "ok")
    except sqlite3.IntegrityError:
        flash("Cannot delete a vehicle that has sales records.", "error")
    return redirect(url_for("vehicles"))


# ---------------- Customers ----------------
@app.route("/customers", methods=["GET", "POST"])
def customers():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Customer name is required.", "error")
            return redirect(url_for("customers"))
        db.execute("INSERT INTO customers (name, phone, email) VALUES (?,?,?)",
                   (name, request.form.get("phone", "").strip(), request.form.get("email", "").strip()))
        db.commit()
        flash(f"Added customer {name}.", "ok")
        return redirect(url_for("customers"))
    rows = db.execute(
        "SELECT c.*, COALESCE(SUM(s.quantity*s.price_at_sale),0) spent, COUNT(s.id) orders "
        "FROM customers c LEFT JOIN sales s ON s.customer_id = c.id "
        "GROUP BY c.id ORDER BY spent DESC").fetchall()
    return render_template("customers.html", customers=rows)


# ---------------- Sales ----------------
@app.route("/sales", methods=["GET", "POST"])
def sales():
    db = get_db()
    if request.method == "POST":
        try:
            vid, cid = int(request.form["vehicle_id"]), int(request.form["customer_id"])
            qty = int(request.form["quantity"])
            disc = float(request.form.get("discount") or 0)
        except (KeyError, ValueError):
            flash("Invalid sale details.", "error")
            return redirect(url_for("sales"))
        vehicle = db.execute("SELECT * FROM vehicles WHERE id = ?", (vid,)).fetchone()
        if not vehicle or qty < 1 or not 0 <= disc <= 20:
            flash("Check quantity (1+) and discount (0-20%).", "error")
            return redirect(url_for("sales"))
        # Reduce stock only if enough units are available
        cur = db.execute("UPDATE vehicles SET stock = stock - ? WHERE id = ? AND stock >= ?",
                         (qty, vid, qty))
        if cur.rowcount == 0:
            flash(f"Not enough stock. Only {vehicle['stock']} unit(s) available.", "error")
            return redirect(url_for("sales"))
        final = round(vehicle["price"] * (1 - disc / 100), 2)
        db.execute("INSERT INTO sales (vehicle_id, customer_id, quantity, price_at_sale, "
                   "sale_date, salesperson) VALUES (?,?,?,?,?,?)",
                   (vid, cid, qty, final, date.today().isoformat(),
                    request.form.get("salesperson", "").strip() or "Unassigned"))
        db.commit()
        flash(f"Sale recorded: {qty} x {vehicle['make']} {vehicle['model']} for "
              f"{inr(final * qty)}.", "ok")
        return redirect(url_for("sales"))
    history = db.execute(
        "SELECT s.*, v.make, v.model, c.name customer FROM sales s "
        "JOIN vehicles v ON v.id = s.vehicle_id JOIN customers c ON c.id = s.customer_id "
        "ORDER BY sale_date DESC, s.id DESC").fetchall()
    return render_template(
        "sales.html", history=history,
        vehicles=db.execute("SELECT * FROM vehicles WHERE stock > 0 ORDER BY make, model").fetchall(),
        customers=db.execute("SELECT * FROM customers ORDER BY name").fetchall())


# ---------------- JSON API ----------------
@app.route("/api/summary")
def api_summary():
    return jsonify(kpis(get_db()))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
