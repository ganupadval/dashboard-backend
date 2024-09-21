from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy import create_engine, MetaData, func
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
import numpy as np
from fastapi.middleware.cors import CORSMiddleware

# Database configuration (replace with your connection string)
DATABASE_URL = "mssql+pyodbc://Prospect:DevEvaluation#2024@164.52.200.249:8524/DevEvaluation?driver=ODBC+Driver+17+for+SQL+Server"

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Reflect the tables
metadata = MetaData()
metadata.reflect(bind=engine)

# Automap base to automatically generate ORM models from the reflected tables
Base = automap_base(metadata=metadata)
Base.prepare()

# Access your existing tables as Python ORM models
CustomerMaster = Base.classes.customer_master
GoodsSale = Base.classes.goods_sale
GoodsSaleItems = Base.classes.goods_sale_items
ItemMaster = Base.classes.item_master
PurchaseOrder = Base.classes.purchase_order
PurchasedItems = Base.classes.purchased_items
SupplierMaster = Base.classes.supplier_master

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this as per your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper function to calculate seasonal index
def calculate_seasonal_index(sales_data):
    monthly_sales = {}
    for sale_date, quantity in sales_data:
        month = sale_date.month
        if month not in monthly_sales:
            monthly_sales[month] = []
        monthly_sales[month].append(quantity)
    
    monthly_averages = {month: np.mean(quantities) for month, quantities in monthly_sales.items()}
    overall_average = np.mean(list(monthly_averages.values()))
    seasonal_index = {month: avg / overall_average for month, avg in monthly_averages.items()}
    return seasonal_index

# Forecast future demand using the seasonal index, rounding to two decimal places
def forecast_demand(base_demand, seasonal_index, month):
    return round(base_demand * seasonal_index.get(month, 1), 2)

@app.get("/procurement-plan")
def create_procurement_plan(
    date: str = Query(...),
    months: int = Query(1, gt=0, le=12),  # Default to 1 month, valid range 1-12
    db: Session = Depends(get_db)
):
    # Parse the provided date
    try:
        cutoff_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use 'YYYY-MM-DD'.")

    # Calculate the future date based on the number of months
    future_date = cutoff_date + timedelta(days=months * 30)  # Approximate to 30 days per month

    procurement_plan = []

    # Fetch all items from ItemMaster
    items = db.query(ItemMaster).all()

    # Batch fetch sales and purchase data
    sales_data = db.query(GoodsSale.sale_date, GoodsSaleItems.item_id, GoodsSaleItems.quantity)\
        .join(GoodsSaleItems, GoodsSale.sale_id == GoodsSaleItems.sale_id)\
        .filter(GoodsSale.sale_date <= cutoff_date)\
        .all()

    purchase_data = db.query(PurchasedItems.item_id, PurchasedItems.delivered_quantity, PurchaseOrder.po_id)\
        .join(PurchaseOrder, PurchaseOrder.po_id == PurchasedItems.po_id)\
        .filter(PurchasedItems.delivery_date <= cutoff_date)\
        .all()

    for item in items:
        item_id = item.item_id

        # Fetch sales and purchase data for the item
        item_sales_data = [(sale_date, quantity) for sale_date, item_id_, quantity in sales_data if item_id_ == item_id]
        item_purchase_data = [data for data in purchase_data if data.item_id == item_id]

        if not item_sales_data:
            continue  # Skip if no sales data found

        # Calculate total sales and purchases
        total_sales = sum([quantity for _, quantity in item_sales_data])
        total_purchases = sum([data.delivered_quantity for data in item_purchase_data])

        # Calculate available stock
        available_stock = total_purchases - total_sales

        # Fetch minimum stock level for the item
        minimum_stock = item.minimum_quantity

        # Calculate seasonal index and base demand
        seasonal_index = calculate_seasonal_index(item_sales_data)
        base_demand = total_sales / len(item_sales_data)

        # Forecast demand for the specified future period
        forecasted_demand = sum(
            forecast_demand(base_demand, seasonal_index, (cutoff_date.month + i - 1) % 12 + 1)
            for i in range(1, months + 1)
        )

        # Determine if an order is needed
        if forecasted_demand > available_stock:
            required_quantity = forecasted_demand - available_stock
               # Round the required quantity to the nearest larger multiple of 10
            order_quantity = (int((required_quantity + 9) / 10)) * 10

            # Find the best supplier based on delivery time and reliability
            supplier_data = db.query(SupplierMaster.supplier_name, PurchaseOrder.po_date, PurchasedItems.delivery_date,
                                     PurchasedItems.ordered_quantity, PurchasedItems.delivered_quantity)\
                .join(PurchaseOrder, PurchaseOrder.supplier_id == SupplierMaster.supplier_id)\
                .filter(PurchasedItems.item_id == item_id)\
                .all()

            if not supplier_data:
                continue  # Skip if no suppliers found

            best_supplier = None
            best_delivery_time = float('inf')
            best_reliability = -1

            for supplier_name, po_date, delivery_date, ordered_quantity, delivered_quantity in supplier_data:
                delivery_time = (delivery_date - po_date).days
                if delivery_time < 0:
                    continue  # Skip invalid delivery times

                reliability = delivered_quantity / ordered_quantity if ordered_quantity > 0 else 0

                if delivery_time < best_delivery_time or (delivery_time == best_delivery_time and reliability > best_reliability):
                    best_supplier = supplier_name
                    best_delivery_time = delivery_time
                    best_reliability = reliability

            procurement_plan.append({
                "item_name": item.item_name,
                "available_stock": available_stock,
                "forecasted_demand": forecasted_demand,
                "order_required": True,
                "minimum_quantity":minimum_stock,
                "order_quantity": order_quantity,
                "best_supplier": best_supplier,
                "delivery_time": best_delivery_time,
                "reliability": best_reliability,
            })
        else:
            # Check if available stock is below minimum stock level
            if available_stock < minimum_stock:
                # Calculate the required order quantity
                required_quantity = minimum_stock - available_stock

                # Round the required quantity to the nearest larger multiple of 10
                order_quantity = (int((required_quantity + 9) / 10)) * 10

                # Find the best supplier even if stock is below minimum
                supplier_data = db.query(SupplierMaster.supplier_name, PurchaseOrder.po_date, PurchasedItems.delivery_date,
                                         PurchasedItems.ordered_quantity, PurchasedItems.delivered_quantity)\
                    .join(PurchaseOrder, PurchaseOrder.supplier_id == SupplierMaster.supplier_id)\
                    .filter(PurchasedItems.item_id == item_id)\
                    .all()

                if not supplier_data:
                    continue  # Skip if no suppliers found

                best_supplier = None
                best_delivery_time = float('inf')
                best_reliability = -1

                for supplier_name, po_date, delivery_date, ordered_quantity, delivered_quantity in supplier_data:
                    delivery_time = (delivery_date - po_date).days
                    if delivery_time < 0:
                        continue  # Skip invalid delivery times

                    reliability = delivered_quantity / ordered_quantity if ordered_quantity > 0 else 0

                    if delivery_time < best_delivery_time or (delivery_time == best_delivery_time and reliability > best_reliability):
                        best_supplier = supplier_name
                        best_delivery_time = delivery_time
                        best_reliability = reliability

                procurement_plan.append({
                    "item_name": item.item_name,
                    "available_stock": available_stock,
                    "forecasted_demand": forecasted_demand,
                    "order_required": True,
                    "minimum_quantity":minimum_stock,
                    "order_quantity": order_quantity,
                    "best_supplier": best_supplier,
                    "delivery_time": best_delivery_time,
                    "reliability": best_reliability,
                    # "message": "Stock is below minimum required level."
                })

    return {"procurement_plan": procurement_plan}
