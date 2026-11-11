# Automotive Sales Management Platform

A simple base web application for a car dealership: manage vehicle inventory, customers
and sales, with a live dashboard. Built with Python, Flask and SQLite.

## Features
- **Dashboard** - total revenue, units sold, orders, stock, customers; revenue by make,
  monthly revenue, salesperson performance, low-stock alerts and recent sales.
- **Vehicles** - add vehicles, restock, delete (blocked if the vehicle has sales).
- **Customers** - add customers and see orders and total spent per customer.
- **Sales** - record a sale with quantity, discount (max 20%) and salesperson. Stock is
  reduced automatically and a sale is rejected if there is not enough stock.
- **JSON API** - `GET /api/summary` returns the key figures.

## Run
```bash
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 in your browser. On first run the database
(`autosales.db`) is created with sample vehicles, customers and sales.
Delete `autosales.db` to reset to the sample data.

## Project structure
| Path | Purpose |
|---|---|
| `app.py` | Flask routes and business logic |
| `database.py` | SQLite schema and sample data |
| `templates/` | HTML pages (Jinja2) |
| `static/style.css` | Styling |

## Before real use
Change `app.secret_key` in `app.py`, add user login and roles, and turn off `debug=True`.

## Ideas to extend
User login (Flask-Login), test drive bookings, invoices as PDF, EMI calculator, lead
tracking, service/after-sales module, charts with Chart.js, switch to PostgreSQL/MySQL.
