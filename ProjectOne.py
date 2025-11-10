print('Name-Jivika')
print('Enrollment No.-2502140028')
password="Jivika_project"
print('-----------LOGIN-----------')
chances=3
for i in range(3):
    print(f'You have {chances} chance only❗')
    psswd = input("Enter password:")
    if psswd!=password:
        print("Access Denied ❌ Wrong Password")
        chances-=1
        continue
    else:
        print("Access Granted ✅ Welcome to Inventory System")

        print('Multi-Store Inventory & Billing System')

        # Initial Inventory
        inv = {
            'A': {'pen': {'qty': 50, 'price': 10}, 'notebook': {'qty': 10, 'price': 40}},
            'B': {'pen': {'qty': 20, 'price': 10}}
        }
        print(inv)
        # Day totals for each store
        day_totals = {'A': 0, 'B': 0}

        # Low stock threshold
        LOW_STOCK_THRESHOLD = 10

        # Unique product categories
        categories = set()

        # store stock transfer history as list of tuples
        transfer_log = []

        # ---------- CRUD FUNCTIONS ----------
        def add_item(store, item, qty, price):
            if store not in inv:
                inv[store] = {}
            inv[store][item] = {'qty': qty, 'price': price}
            print(f"Item '{item}' added to Store {store} with qty={qty}, price={price}.")


        def update_item(store, item, qty=None, price=None):
            if store in inv and item in inv[store]:
                if qty is not None:
                    inv[store][item]['qty'] = qty
                if price is not None:
                    inv[store][item]['price'] = price
                print(f"Updated {store}.{item} -> qty={inv[store][item]['qty']}, price={inv[store][item]['price']}")
            else:
                print(f"Item '{item}' not found in Store {store}.")


        def delete_item(store, item):
            if store in inv and item in inv[store]:
                del inv[store][item]
                print(f"Deleted '{item}' from Store {store}.")
            else:
                print(f"Item '{item}' not found in Store {store}.")


        def search_product(name):
            found = False
            print(f"\n🔎 Searching for '{name}' ...")
            for store, items in inv.items():
                if name in items:
                    found = True
                    print(f"✅ Found in Store {store} → Price: ₹{items[name]['price']}, Qty: {items[name]['qty']}")
            if not found:
                print("❌ Product not found in any store.")


        # ---------- TRANSACTION FUNCTIONS ----------
        def sell(store, item, qty):
            if store not in inv or item not in inv[store]:
                print(f"Error: {store}.{item} not found!")
                return
            if inv[store][item]['qty'] < qty:
                print(f"Error: Not enough stock in {store}.{item}!")
                return
            inv[store][item]['qty'] -= qty
            bill = inv[store][item]['price'] * qty
            day_totals[store] += bill
            print(f"SELL {store} {item} x{qty} -> ₹{bill} | {store}.{item}={inv[store][item]['qty']}")


        def return_item(store, item, qty):
            if store not in inv or item not in inv[store]:
                print(f"Error: {store}.{item} not found!")
                return
            inv[store][item]['qty'] += qty
            refund = inv[store][item]['price'] * qty
            day_totals[store] -= refund
            print(f"RETURN {store} {item} x{qty} -> ₹{refund} | {store}.{item}={inv[store][item]['qty']}")


        def transfer(from_store, to_store, item, qty):
            if from_store not in inv or item not in inv[from_store]:
                print(f"Error: {from_store}.{item} not found!")
                return
            if inv[from_store][item]['qty'] < qty:
                print(f"Error: Not enough stock in {from_store}.{item}!")
                return

            # Ensure destination store has the item
            if to_store not in inv:
                inv[to_store] = {}
            if item not in inv[to_store]:
                inv[to_store][item] = {'qty': 0, 'price': inv[from_store][item]['price']}

            inv[from_store][item]['qty'] -= qty
            inv[to_store][item]['qty'] += qty

            # ✅ Record the transfer in history
            transfer_log.append((from_store, to_store, item, qty))
            print(f"TRANSFER {from_store}->{to_store} {item} x{qty} | "
                  f"{from_store}.{item}={inv[from_store][item]['qty']} | {to_store}.{item}={inv[to_store][item]['qty']}")


        # ---------- REPORT FUNCTIONS ----------
        def low_stock():
            print("\nLow Stock Items:")
            found = False
            for store, items in inv.items():
                for item, data in items.items():
                    if data['qty'] < LOW_STOCK_THRESHOLD:
                        print(f"{store}.{item} ({data['qty']})")
                        found = True
            if not found:
                print("No low-stock items found.")


        def consolidated_stock_value():
            total_value = sum(data['qty'] * data['price']
                              for store in inv.values()
                              for data in store.values())
            print(f"\nConsolidated Stock Value across stores: ₹{total_value}")


        def show_day_totals():
            print(f"\nDay Totals: A=₹{day_totals['A']}, B=₹{day_totals['B']}")


        def show_inventory():
            print("\nCurrent Inventory:")
            for store, items in inv.items():
                print(f" Store {store}:")
                for item, data in items.items():
                    print(f"  {item} -> qty={data['qty']}, price={data['price']}")

        def show_transfer_history():
            print("\n🔁 Stock Transfer History:")
            if not transfer_log:
                print("No transfer records yet.")
            else:
                for record in transfer_log:
                    f, t, item, q = record
                    print(f"{f} → {t} | {item} x{q}")


        def show_categories():
            """Display all unique product categories"""
            print("\n🏷️ Product Categories in System:")
            for cat in categories:
                print(f"- {cat}")


        # ---------- MAIN MENU ----------
        def main_menu():
            while True:
                print("\n===== MULTI-STORE INVENTORY SYSTEM =====")
                print("1. Add Item")
                print("2. Update Item")
                print("3. Delete Item")
                print("4. Search Product")
                print("5. Sell Item")
                print("6. Return Item")
                print("7. Transfer Stock")
                print("8. Show Inventory")
                print("9. Show Reports (Day Totals / Low Stock / Consolidated Value)")
                print("10. Show Transfer History")
                print("11. Show Product Categories")
                print("12. Exit")

                choice = input("Enter choice: ")

                if choice == '1':
                    store = input("Store (A/B): ").upper()
                    item = input("Item name: ")
                    qty = int(input("Quantity: "))
                    price = int(input("Price: "))
                    add_item(store, item, qty, price)

                elif choice == '2':
                    store = input("Store (A/B): ").upper()
                    item = input("Item name: ")
                    qty = input("New quantity (leave blank to skip): ")
                    price = input("New price (leave blank to skip): ")
                    update_item(store, item,
                                int(qty) if qty else None,
                                int(price) if price else None)

                elif choice == '3':
                    store = input("Store (A/B): ").upper()
                    item = input("Item name: ")
                    delete_item(store, item)

                elif choice == '4':
                    name = input("Enter product name to search: ")
                    search_product(name)

                elif choice == '5':
                    store = input("Store (A/B): ").upper()
                    item = input("Item name: ")
                    qty = int(input("Quantity to sell: "))
                    sell(store, item, qty)

                elif choice == '6':
                    store = input("Store (A/B): ").upper()
                    item = input("Item name: ")
                    qty = int(input("Quantity to return: "))
                    return_item(store, item, qty)

                elif choice == '7':
                    from_store = input("From store (A/B): ").upper()
                    to_store = input("To store (A/B): ").upper()
                    item = input("Item name: ")
                    qty = int(input("Quantity to transfer: "))
                    transfer(from_store, to_store, item, qty)

                elif choice == '8':
                    show_inventory()

                elif choice == '9':
                    show_day_totals()
                    low_stock()
                    consolidated_stock_value()

                elif choice == '10':
                    show_transfer_history()

                elif choice == '11':
                    show_categories()

                elif choice == '12':
                    print("Exiting program... Goodbye!")
                    break

                else:
                    print("Invalid choice! Try again.")


        # ---------- RUN PROGRAM ----------
        if __name__ == "__main__":
            main_menu()
        break