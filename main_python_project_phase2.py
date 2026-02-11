#!/usr/bin/env python3
"""
Multi-Store Inventory & Billing System with SQLite

Features:
- Login
- Inventory CRUD (store, item, qty, price, category)
- Sales (records each sale with timestamp)
- Returns (records each return with timestamp)
- Transfers between stores (records history + timestamp)
- Day totals (per store per date; updated on sale/return)
- Reports: low-stock, consolidated stock value, day totals, transfer history, sales/returns by date
- All relevant tables include datetime/date fields for reporting
"""

import sqlite3
from datetime import datetime, date
import sys

DB_NAME = "multi_store_inventory.db"
PASSWORD = "Jivika_project"


# -------------------- Utilities --------------------
def now_iso():
    """Return current datetime in ISO format (local time)."""
    return datetime.now().isoformat(sep=" ", timespec="seconds")


def today_str():
    """Return current date as YYYY-MM-DD"""
    return date.today().isoformat()


# -------------------- Database Initialization --------------------
def init_db(conn: sqlite3.Connection):
    """Create or upgrade the database schema to match project requirements."""
    cur = conn.cursor()

    # -------------------- CREATE TABLES IF NOT EXISTS --------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store TEXT NOT NULL,
    item TEXT NOT NULL,
    qty INTEGER NOT NULL,
    price INTEGER NOT NULL,
    category TEXT,
    created_at TEXT,
    updated_at TEXT,
    UNIQUE(store, item)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        item TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS day_totals (
        store TEXT NOT NULL,
        date TEXT NOT NULL,
        total INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (store, date)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transfers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_store TEXT NOT NULL,
        to_store TEXT NOT NULL,
        item TEXT NOT NULL,
        qty INTEGER NOT NULL,
        transferred_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        store TEXT NOT NULL,
        item TEXT NOT NULL,
        qty INTEGER NOT NULL,
        price INTEGER NOT NULL,
        total_amount INTEGER NOT NULL,
        sold_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        store TEXT NOT NULL,
        item TEXT NOT NULL,
        qty INTEGER NOT NULL,
        refund_amount INTEGER NOT NULL,
        returned_at TEXT NOT NULL
    )
    """)

    conn.commit()

# -------------------- Database Helper Functions --------------------
def upsert_day_total(conn: sqlite3.Connection, store: str, amount_delta: int, date_str: str = None):
    """
    Increase or decrease day_totals[store,date] by amount_delta.
    Creates the row if not exists.
    """
    if date_str is None:
        date_str = today_str()
    cur = conn.cursor()
    cur.execute("SELECT total FROM day_totals WHERE store=? AND date=?", (store, date_str))
    row = cur.fetchone()
    if row:
        new_total = row[0] + amount_delta
        cur.execute("UPDATE day_totals SET total=?, updated_at=? WHERE store=? AND date=?",
                    (new_total, now_iso(), store, date_str))
    else:
        cur.execute("INSERT INTO day_totals (store, date, total, updated_at) VALUES (?,?,?,?)",
                    (store, date_str, amount_delta, now_iso()))
    conn.commit()


# -------------------- CRUD: Inventory & Categories --------------------
def add_item(conn: sqlite3.Connection, store, item, qty, price, category=None):
    """Add item to inventory (or overwrite if same store+item exists)."""
    now = now_iso()
    cur = conn.cursor()

    # Basic validation
    if qty < 0 or price < 0:
        print("Quantity and price must be non-negative.")
        return

    # Upsert inventory row
    try:
        cur.execute("""
            INSERT INTO inventory (store, item, qty, price, category, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(store, item) DO UPDATE SET
            qty=excluded.qty, price=excluded.price, category=excluded.category, updated_at=excluded.updated_at
        """, (store, item, qty, price, category, now, now))
        conn.commit()
    except sqlite3.Error as e:
        print("DB error while adding item:", e)
        return

    # Update categories table (if category provided)
    if category:
        cur.execute("INSERT OR REPLACE INTO categories (item, category, created_at) VALUES (?, ?, ?)",
                    (item, category, now))
        conn.commit()

    print(f"Item '{item}' added/updated in Store {store} (qty={qty}, price={price}, category={category})")


def update_item(conn: sqlite3.Connection, store, item, new_qty=None, new_price=None, new_category=None):
    cur = conn.cursor()
    cur.execute("SELECT qty, price, category FROM inventory WHERE store=? AND item=?", (store, item))
    row = cur.fetchone()
    if not row:
        print(f"Item '{item}' not found in Store {store}.")
        return

    qty = new_qty if new_qty is not None else row[0]
    price = new_price if new_price is not None else row[1]
    category = new_category if new_category is not None else row[2]
    now = now_iso()

    if qty < 0 or price < 0:
        print("Quantity and price must be non-negative.")
        return

    cur.execute("UPDATE inventory SET qty=?, price=?, category=?, updated_at=? WHERE store=? AND item=?",
                (qty, price, category, now, store, item))
    conn.commit()

    if new_category:
        cur.execute("INSERT OR REPLACE INTO categories (item, category, created_at) VALUES (?, ?, ?)",
                    (item, new_category, now))
        conn.commit()

    print(f"Updated {store}.{item} -> qty={qty}, price={price}, category={category}")


def delete_item(conn: sqlite3.Connection, store, item):
    cur = conn.cursor()
    cur.execute("DELETE FROM inventory WHERE store=? AND item=?", (store, item))
    conn.commit()
    print(f"Deleted {store}.{item} (if existed).")


def search_product(conn: sqlite3.Connection, item):
    cur = conn.cursor()
    cur.execute("SELECT store, qty, price, category FROM inventory WHERE item=?", (item,))
    rows = cur.fetchall()
    print(f"\n🔎 Searching for '{item}' ...")
    if not rows:
        print("❌ Product not found in any store.")
        return
    for r in rows:
        print(f"Store {r[0]} → Qty={r[1]}, Price=₹{r[2]}, Category={r[3]}")


# -------------------- Transactions: Sell / Return / Transfer --------------------
def sell(conn: sqlite3.Connection, store, item, qty):
    """Sell qty units from store.item; record sale and update day_totals."""
    cur = conn.cursor()
    cur.execute("SELECT qty, price FROM inventory WHERE store=? AND item=?", (store, item))
    row = cur.fetchone()
    if not row:
        print("Error: item not found.")
        return
    current_qty, price = row
    if qty <= 0:
        print("Sell quantity must be positive.")
        return
    if current_qty < qty:
        print("Error: Not enough stock.")
        return

    new_qty = current_qty - qty
    cur.execute("UPDATE inventory SET qty=?, updated_at=? WHERE store=? AND item=?",
                (new_qty, now_iso(), store, item))

    total_amount = price * qty
    sold_at = now_iso()
    cur.execute("INSERT INTO sales (store, item, qty, price, total_amount, sold_at) VALUES (?, ?, ?, ?, ?, ?)",
                (store, item, qty, price, total_amount, sold_at))

    # Update day_totals for today
    upsert_day_total(conn, store, total_amount, today_str())

    conn.commit()
    print(f"SELL: {store}.{item} x{qty} -> ₹{total_amount} | Remaining qty={new_qty}")


def return_item(conn: sqlite3.Connection, store, item, qty):
    """Process a return: add qty back to inventory, record return, and subtract from day_totals."""
    cur = conn.cursor()
    cur.execute("SELECT qty, price FROM inventory WHERE store=? AND item=?", (store, item))
    row = cur.fetchone()
    if not row:
        print("Error: item not found.")
        return

    current_qty, price = row
    if qty <= 0:
        print("Return quantity must be positive.")
        return

    new_qty = current_qty + qty
    cur.execute("UPDATE inventory SET qty=?, updated_at=? WHERE store=? AND item=?",
                (new_qty, now_iso(), store, item))

    refund_amount = price * qty
    returned_at = now_iso()
    cur.execute("INSERT INTO returns (store, item, qty, refund_amount, returned_at) VALUES (?, ?, ?, ?, ?)",
                (store, item, qty, refund_amount, returned_at))

    # Subtract refund from day_totals for today
    upsert_day_total(conn, store, -refund_amount, today_str())

    conn.commit()
    print(f"RETURN: {store}.{item} x{qty} -> Refund ₹{refund_amount} | New qty={new_qty}")


def transfer(conn: sqlite3.Connection, from_store, to_store, item, qty):
    """Transfer qty units from one store to another, recording the event."""
    cur = conn.cursor()
    cur.execute("SELECT qty, price, category FROM inventory WHERE store=? AND item=?", (from_store, item))
    row = cur.fetchone()
    if not row:
        print(f"Error: {from_store}.{item} not found.")
        return
    from_qty, price, category = row
    if qty <= 0:
        print("Transfer quantity must be positive.")
        return
    if from_qty < qty:
        print("Error: Not enough stock to transfer.")
        return

    # Reduce from source
    cur.execute("UPDATE inventory SET qty=?, updated_at=? WHERE store=? AND item=?",
                (from_qty - qty, now_iso(), from_store, item))

    # Increase in destination (insert row if not exist)
    cur.execute("SELECT qty FROM inventory WHERE store=? AND item=?", (to_store, item))
    to_row = cur.fetchone()
    if to_row:
        cur.execute("UPDATE inventory SET qty = qty + ?, updated_at=? WHERE store=? AND item=?",
                    (qty, now_iso(), to_store, item))
    else:
        cur.execute("INSERT INTO inventory (store, item, qty, price, category, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (to_store, item, qty, price, category, now_iso(), now_iso()))

    # Record transfer
    cur.execute("INSERT INTO transfers (from_store, to_store, item, qty, transferred_at) VALUES (?, ?, ?, ?, ?)",
                (from_store, to_store, item, qty, now_iso()))

    conn.commit()
    print(f"TRANSFER: {from_store} -> {to_store} | {item} x{qty}")


# -------------------- Reports & Views --------------------
def show_inventory(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("SELECT store, item, qty, price, category, updated_at FROM inventory ORDER BY store, item")
    rows = cur.fetchall()
    print("\n--- Current Inventory ---")
    if not rows:
        print("Inventory is empty.")
        return
    for r in rows:
        print(f"{r[0]} | {r[1]} → qty={r[2]}, price=₹{r[3]}, category={r[4]} (updated {r[5]})")


def low_stock_report(conn: sqlite3.Connection, threshold: int = 10):
    cur = conn.cursor()
    cur.execute("SELECT store, item, qty FROM inventory WHERE qty < ? ORDER BY store", (threshold,))
    rows = cur.fetchall()
    print(f"\n--- Low Stock Items (threshold < {threshold}) ---")
    if not rows:
        print("No low-stock items found.")
        return
    for r in rows:
        print(f"{r[0]}.{r[1]} → {r[2]}")


def consolidated_stock_value(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("SELECT SUM(qty * price) FROM inventory")
    total = cur.fetchone()[0] or 0
    print(f"\nConsolidated Stock Value across stores: ₹{total}")


def show_day_totals(conn: sqlite3.Connection, date_str: str = None):
    if date_str is None:
        date_str = today_str()
    cur = conn.cursor()
    cur.execute("SELECT store, total FROM day_totals WHERE date=? ORDER BY store", (date_str,))
    rows = cur.fetchall()
    print(f"\n--- Day Totals for {date_str} ---")
    if not rows:
        print("No totals recorded for this date.")
        return
    for r in rows:
        print(f"Store {r[0]} → ₹{r[1]}")


def show_transfer_history(conn: sqlite3.Connection, limit: int = 50):
    cur = conn.cursor()
    cur.execute("SELECT from_store, to_store, item, qty, transferred_at FROM transfers ORDER BY transferred_at DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    print("\n--- Transfer History (most recent first) ---")
    if not rows:
        print("No transfers recorded.")
        return
    for r in rows:
        print(f"{r[0]} → {r[1]} | {r[2]} x{r[3]} at {r[4]}")


def show_sales(conn: sqlite3.Connection, date_from: str = None, date_to: str = None):
    cur = conn.cursor()
    q = "SELECT store, item, qty, price, total_amount, sold_at FROM sales"
    params = []
    if date_from and date_to:
        q += " WHERE date(sold_at) BETWEEN date(?) AND date(?)"
        params = [date_from, date_to]
    elif date_from:
        q += " WHERE date(sold_at) >= date(?)"
        params = [date_from]
    elif date_to:
        q += " WHERE date(sold_at) <= date(?)"
        params = [date_to]
    q += " ORDER BY sold_at DESC LIMIT 200"
    cur.execute(q, params)
    rows = cur.fetchall()
    print("\n--- Sales Records ---")
    if not rows:
        print("No sales found for the given range.")
        return
    for r in rows:
        print(f"{r[5]} | Store {r[0]} | {r[1]} x{r[2]} @₹{r[3]} -> ₹{r[4]}")


def show_returns(conn: sqlite3.Connection, date_from: str = None, date_to: str = None):
    cur = conn.cursor()
    q = "SELECT store, item, qty, refund_amount, returned_at FROM returns"
    params = []
    if date_from and date_to:
        q += " WHERE date(returned_at) BETWEEN date(?) AND date(?)"
        params = [date_from, date_to]
    elif date_from:
        q += " WHERE date(returned_at) >= date(?)"
        params = [date_from]
    elif date_to:
        q += " WHERE date(returned_at) <= date(?)"
        params = [date_to]
    q += " ORDER BY returned_at DESC LIMIT 200"
    cur.execute(q, params)
    rows = cur.fetchall()
    print("\n--- Return Records ---")
    if not rows:
        print("No returns found for the given range.")
        return
    for r in rows:
        print(f"{r[4]} | Store {r[0]} | {r[1]} x{r[2]} -> Refund ₹{r[3]}")


def show_categories(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("SELECT item, category, created_at FROM categories ORDER BY item")
    rows = cur.fetchall()
    print("\n--- Categories ---")
    if not rows:
        print("No categories recorded.")
        return
    for r in rows:
        print(f"{r[0]} → {r[1]} (added {r[2]})")


# -------------------- CLI Menu --------------------
def main_menu(conn: sqlite3.Connection):
    menu = """
===== MULTI-STORE INVENTORY SYSTEM =====
1. Add Item
2. Update Item
3. Delete Item
4. Search Product
5. Sell Item
6. Return Item
7. Transfer Stock
8. Show Inventory
9. Reports (day totals / low stock / consolidated value)
10. Transfer History
11. Sales Records (by date range)
12. Return Records (by date range)
13. Categories
14. Exit
"""
    while True:
        print(menu)
        choice = input("Enter choice: ").strip()

        if choice == '1':
            store = input("Store (A/B): ").upper().strip()
            item = input("Item name: ").lower().strip()
            try:
                qty = int(input("Quantity: "))
                price = int(input("Price (integer): "))
            except ValueError:
                print("Quantity and price must be integers.")
                continue
            category = input("Category (optional): ").strip() or None
            add_item(conn, store, item, qty, price, category)

        elif choice == '2':
            store = input("Store (A/B): ").upper().strip()
            item = input("Item name: ").lower().strip()
            qty_input = input("New quantity (leave blank to skip): ").strip()
            price_input = input("New price (leave blank to skip): ").strip()
            cat_input = input("New category (leave blank to skip): ").strip()
            qty = int(qty_input) if qty_input else None
            price = int(price_input) if price_input else None
            cat = cat_input if cat_input else None
            update_item(conn, store, item, qty, price, cat)

        elif choice == '3':
            store = input("Store (A/B): ").upper().strip()
            item = input("Item name: ").lower().strip()
            delete_item(conn, store, item)

        elif choice == '4':
            item = input("Enter product name to search: ").lower().strip()
            search_product(conn, item)

        elif choice == '5':
            store = input("Store (A/B): ").upper().strip()
            item = input("Item name: ").lower().strip()
            try:
                qty = int(input("Quantity to sell: "))
            except ValueError:
                print("Quantity must be integer.")
                continue
            sell(conn, store, item, qty)

        elif choice == '6':
            store = input("Store (A/B): ").upper().strip()
            item = input("Item name: ").lower().strip()
            try:
                qty = int(input("Quantity to return: "))
            except ValueError:
                print("Quantity must be integer.")
                continue
            return_item(conn, store, item, qty)

        elif choice == '7':
            from_store = input("From store: ").upper().strip()
            to_store = input("To store: ").upper().strip()
            item = input("Item name: ").lower().strip()
            try:
                qty = int(input("Quantity to transfer: "))
            except ValueError:
                print("Quantity must be integer.")
                continue
            transfer(conn, from_store, to_store, item, qty)

        elif choice == '8':
            show_inventory(conn)

        elif choice == '9':
            print("Reports menu:")
            print(" a) Show today's day totals")
            print(" b) Low stock report")
            print(" c) Consolidated stock value")
            sel = input("Choose (a/b/c): ").strip().lower()
            if sel == 'a':
                show_day_totals(conn)
            elif sel == 'b':
                try:
                    t = int(input("Enter low-stock threshold (default 10): ") or 10)
                except ValueError:
                    t = 10
                low_stock_report(conn, t)
            elif sel == 'c':
                consolidated_stock_value(conn)
            else:
                print("Invalid reports option.")

        elif choice == '10':
            show_transfer_history(conn)

        elif choice == '11':
            print("Enter date range for sales (YYYY-MM-DD). Leave blank for no bound.")
            d1 = input("From date: ").strip() or None
            d2 = input("To date: ").strip() or None
            show_sales(conn, d1, d2)

        elif choice == '12':
            print("Enter date range for returns (YYYY-MM-DD). Leave blank for no bound.")
            d1 = input("From date: ").strip() or None
            d2 = input("To date: ").strip() or None
            show_returns(conn, d1, d2)

        elif choice == '13':
            show_categories(conn)

        elif choice == '14':
            print("Exiting program. Goodbye!")
            break

        else:
            print("Invalid choice. Try again.")


# -------------------- Main: Login + DB setup --------------------
def main():
    print("Name - Jivika")
    print("Enrollment No. - 2502140028")
    print("\n----------- LOGIN -----------")
    chances = 3
    for attempt in range(3):
        print(f"You have {chances} chance(s) left.")
        p = input("Enter password: ").strip()
        if p != PASSWORD:
            print("Access Denied ❌ Wrong Password")
            chances -= 1
            if chances <= 0:
                print("Too many attempts. Exiting.")
                sys.exit(1)
            continue
        else:
            print("Access Granted ✅ Welcome to Inventory System\n")
            break

    # open/create DB
    conn = sqlite3.connect(DB_NAME)
    # enable foreign keys if needed later
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)

    # optional: seed some sample data if inventory empty
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM inventory")
    if cur.fetchone()[0] == 0:
        print("Seeding sample data...")
        add_item(conn, "A", "pen", 50, 10, "stationery")
        add_item(conn, "A", "notebook", 10, 40, "stationery")
        add_item(conn, "B", "pen", 20, 10, "stationery")
        print("Sample data inserted.")

    # launch menu
    try:
        main_menu(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
