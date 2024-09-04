from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
app = FastAPI()



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Location(BaseModel):
    name: str
    longitude: float
    latitude: float
    sales: int

class Product(BaseModel):
    name: str
    value: float
    amount: str

class SalesData(BaseModel):
    labels: List[str]
    datasets: List[dict]

class Customer(BaseModel):
    id: str
    country: str
    date: str
    purchases: int
    sales: str


locations = [
    {
      "name": "United Kingdom",
      "longitude": -0.1276,
      "latitude": 51.5074,
      "sales": 467100,
    },
    { "name": "Netherlands", "longitude": 4.9041, "latitude": 52.3676, "sales": 22400 },
    { "name": "EIRE", "longitude": -6.2603, "latitude": 53.3498, "sales": 18300 },
    { "name": "France", "longitude": 2.3522, "latitude": 48.8566, "sales": 14600 },
    { "name": "Germany", "longitude": 13.405, "latitude": 52.52, "sales": 14400 },
]

products = [
    { "name": "Jumbo bag strawberry", "value": 0.9, "amount": "$4.7K" },
    { "name": "Party bunting", "value": 0.4, "amount": "$3.3K" },
    { "name": "Regency cakestand 3 tier", "value": 0.2, "amount": "$2.7K" },
    { "name": "Postage", "value": 0.16, "amount": "$1.7K" },
    { "name": "White hanging heart t-light holder", "value": 0.1, "amount": "$1K" },
]

sales_data = {
    "labels": ['26 Feb', '3 Mar', '8 Mar', '13 Mar', '18 Mar', '23 Mar', '28 Mar', '2 Apr'],
    "datasets": [
        {
            "type": 'bar',
            "label": 'Sales',
            "data": [20, 30, 25, 35, 40, 50, 45, 60],
            "backgroundColor": 'rgba(54, 162, 235, 0.5)',
            "borderColor": 'rgba(54, 162, 235, 1)',
            "borderWidth": 1,
        },
        {
            "type": 'line',
            "label": 'Number of Purchases',
            "data": [10, 15, 13, 20, 18, 23, 21, 27],
            "fill": False,
            "borderColor": 'rgba(255, 99, 132, 1)',
            "tension": 0.4,
        },
    ],
}

customers = [
    { "id": '14646', "country": 'Netherlands', "date": '30 Mar 2022', "purchases": 4, "sales": '$21.5K' },
    { "id": '15646', "country": 'United Kingdom', "date": '22 Mar 2022', "purchases": 2, "sales": '$17.8K' },
    { "id": '14766', "country": 'EIRE', "date": '3 Mar 2022', "purchases": 1, "sales": '$15.6K' },
    { "id": '19646', "country": 'France', "date": '12 Mar 2022', "purchases": 2, "sales": '$12.2K' },
    { "id": '15746', "country": 'Germany', "date": '3 Mar 2022', "purchases": 4, "sales": '$10.5K' },
    { "id": '19246', "country": 'France', "date": '26 Mar 2022', "purchases": 3, "sales": '$10K' },
]

@app.get("/locations", response_model=List[Location])
async def get_locations():
    return locations

@app.get("/products", response_model=List[Product])
async def get_products():
    return products

@app.get("/sales_data", response_model=SalesData)
async def get_sales_data():
    return sales_data

@app.get("/customers", response_model=List[Customer])
async def get_customers():
    return customers

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)