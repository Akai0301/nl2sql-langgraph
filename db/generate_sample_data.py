#!/usr/bin/env python3
"""
PostgreSQL Sample Data Generator for nl2sql-langgraph

This script extends the existing sample data to support complex query scenarios:
- YoY analysis: Add 2024 Q4 data
- RFM analysis: Expand customers to 50 with diverse patterns
- Distribution queries: Add low-end products

Usage:
    python db/generate_sample_data.py

Environment:
    POSTGRES_DSN: PostgreSQL connection string (required)
"""

import os
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Tuple

import psycopg

# ============================================
# Configuration
# ============================================

# New customer count by member level
NEW_CUSTOMERS = {
    "钻石": 5,   # High frequency + High value
    "金卡": 10,  # Medium frequency + Medium value
    "银卡": 10,  # Low frequency + Medium value
    "普通": 10,  # Low frequency + Low value
}

# New low-end products
NEW_PRODUCTS = [
    ("P401", "Apple AirPods 2", "电子产品", "配件", "Apple", 999.00),
    ("P402", "小米手环 8", "电子产品", "配件", "小米", 259.00),
    ("P403", "华为充电宝 10000mAh", "电子产品", "配件", "华为", 199.00),
    ("P404", "罗技鼠标 M330", "电子产品", "配件", "罗技", 149.00),
    ("P405", "小米电饭煲 3L", "家电", "小家电", "小米", 299.00),
    ("P406", "九阳豆浆机", "家电", "小家电", "九阳", 399.00),
    ("P407", "苏泊尔保温杯", "家电", "小家电", "苏泊尔", 99.00),
    ("P408", "三只松鼠坚果礼盒", "食品饮料", "零食", "三只松鼠", 168.00),
]

# Order periods to generate
ORDER_PERIODS = [
    # 2024 Q4 - YoY baseline
    {"start": "2024-10-01", "end": "2024-10-31", "count": 70, "promo": False},
    {"start": "2024-11-01", "end": "2024-11-30", "count": 75, "promo": False},
    {"start": "2024-12-01", "end": "2024-12-31", "count": 80, "promo": True},  # Double 11/12
    # 2025 H1 gap filler
    {"start": "2025-04-01", "end": "2025-04-30", "count": 20, "promo": False},
    {"start": "2025-05-01", "end": "2025-05-31", "count": 20, "promo": False},
    {"start": "2025-06-01", "end": "2025-06-30", "count": 20, "promo": False},
    {"start": "2025-07-01", "end": "2025-07-31", "count": 20, "promo": False},
    {"start": "2025-08-01", "end": "2025-08-31", "count": 20, "promo": False},
    {"start": "2025-09-01", "end": "2025-09-30", "count": 20, "promo": False},
]

# Member level behavior patterns
MEMBER_BEHAVIOR = {
    "钻石": {"orders_per_month": (5, 8), "avg_amount": (5000, 15000), "discount_rate": (0.08, 0.15)},
    "金卡": {"orders_per_month": (2, 4), "avg_amount": (2000, 5000), "discount_rate": (0.05, 0.10)},
    "银卡": {"orders_per_month": (0.5, 1.5), "avg_amount": (1000, 3000), "discount_rate": (0.03, 0.08)},
    "普通": {"orders_per_month": (0.2, 0.5), "avg_amount": (500, 1500), "discount_rate": (0.01, 0.05)},
}

# Chinese name components
SURNAMES = ["王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴", "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗"]
GIVEN_NAMES = ["伟", "芳", "娜", "敏", "静", "丽", "强", "磊", "军", "洋", "勇", "艳", "杰", "涛", "明", "超", "秀", "霞", "平", "刚", "桂", "文", "华", "建", "国"]

# Age groups
AGE_GROUPS = ["20-25", "25-30", "30-35", "35-40", "40-45"]

# Gender
GENDERS = ["男", "女"]


# ============================================
# Helper Functions
# ============================================

def generate_chinese_name() -> str:
    """Generate a random Chinese name."""
    surname = random.choice(SURNAMES)
    given = random.choice(GIVEN_NAMES)
    if random.random() > 0.5:
        given += random.choice(GIVEN_NAMES)
    return surname + given


def random_date_in_range(start: str, end: str) -> datetime:
    """Generate a random date within the range."""
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    delta = (end_dt - start_dt).days
    random_days = random.randint(0, delta)
    return start_dt + timedelta(days=random_days)


def random_time(is_promo: bool = False) -> str:
    """Generate a random time string."""
    if is_promo:
        # Double 11/12: 00:00 - 24:00
        hour = random.randint(0, 23)
    else:
        # Normal: 10:00 - 22:00
        hour = random.randint(10, 21)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}:{second:02d}"


from decimal import Decimal


def calculate_discount(amount, member_level: str, is_promo: bool) -> float:
    """Calculate discount amount based on member level and promo status."""
    amount = float(amount)  # Convert Decimal to float if needed
    base_rate = random.uniform(*MEMBER_BEHAVIOR[member_level]["discount_rate"])
    if is_promo:
        base_rate += random.uniform(0.05, 0.15)  # Extra promo discount
    discount = amount * base_rate
    return round(discount, 2)


def calculate_profit(amount) -> float:
    """Calculate profit amount with random margin."""
    amount = float(amount)  # Convert Decimal to float if needed
    margin = random.uniform(0.15, 0.25)
    return round(amount * margin, 2)


# ============================================
# Main Script
# ============================================

def main():
    """Main entry point."""
    # Get connection string from environment
    dsn = os.environ.get("POSTGRES_DSN")
    if not dsn:
        print("ERROR: POSTGRES_DSN environment variable is required")
        return 1

    print("Connecting to PostgreSQL database...")

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            # ============================================
            # Step 0: Clean up any previously inserted new data
            # ============================================
            print("\n[Step 0] Cleaning up any previously inserted new data...")

            cur.execute("DELETE FROM fact_orders WHERE order_id > 100155")
            deleted_orders = cur.rowcount
            cur.execute("DELETE FROM dim_customer WHERE customer_code >= 'C016'")
            deleted_customers = cur.rowcount
            cur.execute("DELETE FROM dim_product WHERE product_code >= 'P401'")
            deleted_products = cur.rowcount
            conn.commit()
            print(f"  Deleted: {deleted_orders} orders, {deleted_customers} customers, {deleted_products} products")

            # ============================================
            # Step 1: Query existing data
            # ============================================
            print("\n[Step 1] Querying existing data...")

            # Existing customers (need customer_id for orders)
            cur.execute("SELECT customer_id, customer_code, member_level FROM dim_customer")
            existing_customers = cur.fetchall()
            existing_customer_codes = [c[1] for c in existing_customers]
            print(f"  Existing customers: {len(existing_customers)}")

            # Existing products
            cur.execute("SELECT product_code, unit_price FROM dim_product")
            existing_products = cur.fetchall()
            existing_product_codes = [p[0] for p in existing_products]
            print(f"  Existing products: {len(existing_products)}")

            # All products with prices (for order generation)
            cur.execute("SELECT product_code, unit_price FROM dim_product")
            all_products_prices = cur.fetchall()

            # Regions
            cur.execute("SELECT region_code FROM dim_region WHERE region_level = '市'")
            regions = [r[0] for r in cur.fetchall()]
            print(f"  Regions: {len(regions)}")

            # Channels (need channel_id for orders)
            cur.execute("SELECT channel_id, channel_code FROM dim_channel")
            channels_data = cur.fetchall()
            channel_code_to_id = {c[1]: c[0] for c in channels_data}
            channel_ids = [c[0] for c in channels_data]
            print(f"  Channels: {len(channels_data)}")

            # Max order_id
            cur.execute("SELECT COALESCE(MAX(order_id), 0) FROM fact_orders")
            max_order_id = cur.fetchone()[0]
            print(f"  Max order_id: {max_order_id}")

            # ============================================
            # Step 2: Insert new customers
            # ============================================
            print("\n[Step 2] Inserting new customers...")

            new_customer_code = 16
            new_customers_data = []

            cities = ["上海", "北京", "广州", "深圳", "杭州", "南京", "苏州", "武汉", "青岛", "宁波", "天津", "济南", "郑州", "南宁", "成都", "重庆", "西安", "长沙", "福州", "昆明"]

            for member_level, count in NEW_CUSTOMERS.items():
                for _ in range(count):
                    customer_code = f"C{new_customer_code:03d}"
                    customer_name = generate_chinese_name()
                    gender = random.choice(GENDERS)
                    age_group = random.choice(AGE_GROUPS)

                    # Earlier registration for higher member levels
                    if member_level == "钻石":
                        register_year = random.randint(2022, 2023)
                        register_month = random.randint(1, 12)
                    elif member_level == "金卡":
                        register_year = random.randint(2022, 2024)
                        register_month = random.randint(1, 9)
                    elif member_level == "银卡":
                        register_year = random.randint(2023, 2024)
                        register_month = random.randint(1, 9)
                    else:
                        register_year = random.randint(2023, 2024)
                        register_month = random.randint(1, 9)

                    register_date = f"{register_year}-{register_month:02d}-{random.randint(1, 28):02d}"
                    city = random.choice(cities)

                    new_customers_data.append(
                        (customer_code, customer_name, gender, age_group, member_level, register_date, city)
                    )
                    new_customer_code += 1

            # Insert new customers
            cur.executemany(
                """
                INSERT INTO dim_customer(customer_code, customer_name, gender, age_group, member_level, register_date, city)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                new_customers_data
            )
            print(f"  Inserted {len(new_customers_data)} new customers")

            # Query all customers with their IDs to build mapping
            cur.execute("SELECT customer_id, customer_code, member_level FROM dim_customer")
            all_customers = cur.fetchall()

            # Build mappings: customer_id -> member_level, customer_code -> customer_id
            customer_id_level_map = {c[0]: c[2] for c in all_customers}
            customer_code_to_id = {c[1]: c[0] for c in all_customers}

            all_customer_ids = list(customer_id_level_map.keys())

            # ============================================
            # Step 3: Insert new products
            # ============================================
            print("\n[Step 3] Inserting new products...")

            for product in NEW_PRODUCTS:
                cur.execute(
                    """
                    INSERT INTO dim_product(product_code, product_name, category_l1, category_l2, brand, unit_price, status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'active')
                    """,
                    product
                )
            print(f"  Inserted {len(NEW_PRODUCTS)} new products")

            # Update all products prices
            all_products_prices.extend([(p[0], p[5]) for p in NEW_PRODUCTS])

            # Group products by price range for order generation
            low_price_products = [p for p in all_products_prices if p[1] < 1000]
            mid_price_products = [p for p in all_products_prices if 1000 <= p[1] < 5000]
            high_price_products = [p for p in all_products_prices if 5000 <= p[1] < 10000]
            luxury_products = [p for p in all_products_prices if p[1] >= 10000]

            # ============================================
            # Step 4: Generate and insert new orders
            # ============================================
            print("\n[Step 4] Generating and inserting new orders...")

            order_id = max_order_id + 1
            total_orders = 0

            # Assign customers to periods based on member level behavior
            # We need to distribute orders across customers to match their behavior patterns

            for period in ORDER_PERIODS:
                period_orders = []
                period_start_dt = datetime.strptime(period["start"], "%Y-%m-%d")
                period_end_dt = datetime.strptime(period["end"], "%Y-%m-%d")
                days_in_period = (period_end_dt - period_start_dt).days + 1

                # Calculate target orders per customer level
                customers_by_level = {
                    level: [c_id for c_id, l in customer_id_level_map.items() if l == level]
                    for level in NEW_CUSTOMERS.keys()
                }

                # Distribute orders across member levels
                for level, customers in customers_by_level.items():
                    if not customers:
                        continue

                    behavior = MEMBER_BEHAVIOR[level]
                    orders_per_month_range = behavior["orders_per_month"]

                    # Calculate expected orders for this level in this period
                    avg_orders_per_month = (orders_per_month_range[0] + orders_per_month_range[1]) / 2
                    months_in_period = days_in_period / 30.0
                    orders_per_customer = int(avg_orders_per_month * months_in_period)

                    # Assign orders to customers of this level
                    for customer_id in customers:
                        # Random variation in order count
                        actual_orders = max(1, int(orders_per_customer * random.uniform(0.8, 1.2)))

                        for _ in range(actual_orders):
                            # Select product based on member level's typical amount range
                            avg_amount_range = behavior["avg_amount"]
                            target_amount = random.uniform(*avg_amount_range)

                            # Choose product that matches target amount
                            if target_amount < 1000:
                                product_pool = low_price_products
                            elif target_amount < 5000:
                                product_pool = mid_price_products + low_price_products
                            elif target_amount < 10000:
                                product_pool = high_price_products + mid_price_products
                            else:
                                product_pool = luxury_products + high_price_products

                            if not product_pool:
                                product_pool = all_products_prices

                            product_code, unit_price = random.choice(product_pool)
                            unit_price = float(unit_price)  # Convert Decimal to float

                            # Quantity (lower for expensive products)
                            if unit_price > 5000:
                                quantity = random.choices([1, 2], weights=[0.8, 0.2])[0]
                            elif unit_price > 2000:
                                quantity = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
                            else:
                                quantity = random.choices([1, 2, 3, 4, 5], weights=[0.4, 0.3, 0.2, 0.05, 0.05])[0]

                            order_amount = unit_price * quantity
                            discount_amount = calculate_discount(order_amount, level, period["promo"])
                            actual_amount = order_amount - discount_amount
                            profit_amount = calculate_profit(actual_amount)

                            # Random date and time
                            order_date = random_date_in_range(period["start"], period["end"])
                            order_time_str = random_time(period["promo"])
                            order_timestamp = f"{order_date.strftime('%Y-%m-%d')} {order_time_str}"

                            # Random region and channel
                            region_code = random.choice(regions)
                            channel_id = random.choice(channel_ids)

                            # Order status
                            order_status = random.choices(
                                ["completed", "cancelled"],
                                weights=[0.95, 0.05]
                            )[0]

                            period_orders.append((
                                order_id,
                                order_date.strftime('%Y-%m-%d'),
                                order_timestamp,
                                customer_id,
                                product_code,
                                region_code,
                                channel_id,
                                quantity,
                                unit_price,
                                order_amount,
                                discount_amount,
                                actual_amount,
                                profit_amount,
                                order_status
                            ))
                            order_id += 1

                # Insert orders for this period
                if period_orders:
                    cur.executemany(
                        """
                        INSERT INTO fact_orders(order_id, order_date, order_time, customer_id, product_code,
                                               region_code, channel_id, quantity, unit_price, order_amount,
                                               discount_amount, actual_amount, profit_amount, order_status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        period_orders
                    )
                    total_orders += len(period_orders)
                    print(f"  Period {period['start']} to {period['end']}: {len(period_orders)} orders")

            print(f"\n  Total new orders inserted: {total_orders}")

            # ============================================
            # Step 5: Verify and summarize
            # ============================================
            print("\n[Step 5] Verification and summary...")

            # Count records
            cur.execute("SELECT COUNT(*) FROM dim_customer")
            customer_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM dim_product")
            product_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM fact_orders")
            order_count = cur.fetchone()[0]

            cur.execute("SELECT MIN(order_date), MAX(order_date) FROM fact_orders")
            date_range = cur.fetchone()

            cur.execute("SELECT member_level, COUNT(*) FROM dim_customer GROUP BY member_level ORDER BY member_level")
            level_dist = cur.fetchall()

            print("\n" + "=" * 50)
            print("SUMMARY")
            print("=" * 50)
            print(f"  Customers: {customer_count} (target: 50)")
            print(f"  Products:  {product_count} (target: 28)")
            print(f"  Orders:    {order_count} (target: 500)")
            print(f"  Date range: {date_range[0]} to {date_range[1]}")
            print("\n  Customer distribution by member level:")
            for level, count in level_dist:
                print(f"    {level}: {count}")

            # ============================================
            # Step 6: Run verification queries
            # ============================================
            print("\n[Step 6] Running verification queries...")

            # YoY comparison
            cur.execute("""
                SELECT
                    EXTRACT(YEAR FROM order_date) as year,
                    EXTRACT(MONTH FROM order_date) as month,
                    SUM(actual_amount) as sales
                FROM fact_orders
                WHERE EXTRACT(MONTH FROM order_date) = 12
                GROUP BY EXTRACT(YEAR FROM order_date), EXTRACT(MONTH FROM order_date)
                ORDER BY year
            """)
            yoy_data = cur.fetchall()
            print("\n  December sales YoY:")
            for row in yoy_data:
                print(f"    {int(row[0])}年12月: {row[2]:,.2f}元")

            # Customer spending distribution
            cur.execute("""
                SELECT
                    spending_level,
                    COUNT(*) as customer_count
                FROM (
                    SELECT
                        dim_customer.customer_id,
                        CASE
                            WHEN SUM(actual_amount) > 50000 THEN '高消费(>5万)'
                            WHEN SUM(actual_amount) > 20000 THEN '中高消费(2-5万)'
                            WHEN SUM(actual_amount) > 5000 THEN '中等消费(5千-2万)'
                            ELSE '低消费(<5千)'
                        END as spending_level
                    FROM fact_orders
                    JOIN dim_customer ON fact_orders.customer_id = dim_customer.customer_id
                    GROUP BY dim_customer.customer_id
                ) sub
                GROUP BY spending_level
                ORDER BY spending_level
            """)
            spending_dist = cur.fetchall()
            print("\n  Customer spending distribution:")
            for row in spending_dist:
                print(f"    {row[0]}: {row[1]} customers")

            # Order amount distribution
            cur.execute("""
                SELECT
                    CASE
                        WHEN actual_amount > 10000 THEN '超大额(>1万)'
                        WHEN actual_amount > 5000 THEN '大额(5千-1万)'
                        WHEN actual_amount > 2000 THEN '中额(2千-5千)'
                        ELSE '小额(<2千)'
                    END as amount_level,
                    COUNT(*) as order_count
                FROM fact_orders
                GROUP BY amount_level
                ORDER BY amount_level
            """)
            amount_dist = cur.fetchall()
            print("\n  Order amount distribution:")
            for row in amount_dist:
                print(f"    {row[0]}: {row[1]} orders")

            conn.commit()

            print("\n" + "=" * 50)
            print("Data generation completed successfully!")
            print("=" * 50)

    return 0


if __name__ == "__main__":
    exit(main())