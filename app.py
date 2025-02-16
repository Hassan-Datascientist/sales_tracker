from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64

# Initialize Flask app
app = Flask(__name__)

# MongoDB connection setup (this only needs to happen once)
client = MongoClient("mongodb://localhost:27017/")
db = client['sales_db']
products_collection = db['products']

# Helper Functions
def calculate_tax(price):
    return price * 0.18  # 18% tax

def calculate_profit(purchase_price, sales_price):
    tax = calculate_tax(sales_price)
    return sales_price - purchase_price - tax

# Routes

@app.route('/')
def index():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    # Dummy login, in practice you would validate user credentials
    # Let's check the MongoDB connection here as well
    try:
        # Attempt to fetch one product to verify the connection
        product = products_collection.find_one()
        if product:
            print("MongoDB connection successful!")
        else:
            print("No products found in the database.")
        return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"Error with MongoDB connection: {e}")
        return f"Error connecting to the database: {e}"

@app.route('/dashboard')
def dashboard():
    # Get all products for the dashboard
    products = list(products_collection.find())
    return render_template('dashboard.html', products=products)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    try:
        if request.method == 'POST':
            # Add product to MongoDB
            name = request.form['name']
            category = request.form['category']
            purchase_price = float(request.form['purchase_price'])
            sales_price = float(request.form['sales_price'])
            quantity_sold = int(request.form['quantity_sold'])
            stock_status = request.form['stock_status']

            # Create product data
            product_data = {
                'name': name,
                'category': category,
                'purchase_price': purchase_price,
                'sales_price': sales_price,
                'quantity_sold': quantity_sold,
                'stock_status': stock_status
            }

            # Insert product data
            products_collection.insert_one(product_data)
            return redirect(url_for('dashboard'))

    except Exception as e:
        print(f"Error occurred: {e}")
        return f"An error occurred: {e}"

    return render_template('add_product.html')

@app.route('/view_reports')
def view_reports():
    # Aggregation query to get reports based on stock status
    pipeline = [
        {
            '$group': {
                '_id': '$stock_status',
                'total_quantity_sold': {'$sum': '$quantity_sold'},
                'total_revenue': {'$sum': {'$multiply': ['$sales_price', '$quantity_sold']}}},
        }
    ]

    report = list(products_collection.aggregate(pipeline))

    # Calculate the profit after aggregation
    for record in report:
        total_revenue = record['total_revenue']
        # Iterate through the products in the stock_status category to calculate profit
        category_products = list(products_collection.find({'stock_status': record['_id']}))
        total_profit = 0
        for product in category_products:
            total_profit += calculate_profit(product['purchase_price'], product['sales_price'])
        record['total_profit'] = total_profit

    return render_template('reports.html', report=report)

@app.route('/generate_charts')
def generate_charts():
    # Data retrieval
    products = list(products_collection.find())

    # Bar chart data
    names = [product['name'] for product in products]
    sold_quantities = [product['quantity_sold'] for product in products]

    # Generate bar chart
    plt.figure(figsize=(10, 6))
    sns.barplot(x=names, y=sold_quantities, palette='Blues_d')
    plt.xlabel('Product')
    plt.ylabel('Quantity Sold')
    plt.title('Product Quantity Sold')

    # Save bar chart to image
    bar_img = io.BytesIO()
    plt.savefig(bar_img, format='png')
    bar_img.seek(0)
    bar_plot_url = base64.b64encode(bar_img.getvalue()).decode('utf8')
    plt.close()  # Close the plot to avoid overlap

    # Pie chart data
    categories = [product['category'] for product in products]
    category_sales = {cat: categories.count(cat) for cat in set(categories)}

    # Generate pie chart
    plt.figure(figsize=(8, 8))
    plt.pie(category_sales.values(), labels=category_sales.keys(), autopct='%1.1f%%', startangle=140)
    plt.title('Product Type Sales Distribution')

    # Save pie chart to image
    pie_img = io.BytesIO()
    plt.savefig(pie_img, format='png')
    pie_img.seek(0)
    pie_plot_url = base64.b64encode(pie_img.getvalue()).decode('utf8')
    plt.close()  # Close the plot to avoid overlap

    # Render the template with both charts
    return render_template('charts.html', bar_plot_url=bar_plot_url, pie_plot_url=pie_plot_url)

if __name__ == '__main__':
    app.run(debug=True)
