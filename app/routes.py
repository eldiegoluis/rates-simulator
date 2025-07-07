import json
from flask import Flask, render_template, request, jsonify, session, url_for, redirect, Blueprint, current_app
from app.main import process_product_dimensions, process_initial_inventory, process_order_simulation

from typing import Any

from app.models import ProductCatalog, InitialInventory, Size


bp = Blueprint('calculator',__name__)

# 1) Home view → serves index.html
@bp.route('/')
def index():
    current_app.logger.info('Route accessed: / (index)')
    return render_template('index.html')

@bp.route('/summary')
def summary():
    current_app.logger.info('Route accessed: /summary')
    return render_template('summary.html')

@bp.route('/checkout', methods=['GET'])
def checkout_page():
    """
    Renders the checkout page where users input quantities for initial inventory.
    This page needs the ProductCatalog from the session to display product names.
    """
    current_app.logger.info('Route accessed: /checkout [GET]')
    product_catalog: ProductCatalog = session.get('product_catalog_data')

    if not product_catalog:
        current_app.logger.warning('Redirecting from /checkout: No product catalog found in session.')
        # Redirect back to product details input if no catalog is found
        return redirect(url_for('calculator.index')) # Or render an error page
    current_app.logger.debug('Product catalog found in session for /checkout.')
    return render_template('checkout.html') # Serve the checkout page HTML


@bp.route('/details', methods=['GET', 'POST'])
def details():
    """
    Flask endpoint to receive product dimensions, calculate volumetrics,
    and store the ProductCatalog in memory for the current session/user.
    """
    current_app.logger.info(f'Route accessed: /details [{request.method}]')



    if not request.is_json:
        current_app.logger.error('Bad Request to /details: Request must be JSON.')
        return jsonify({"error": "Request must be JSON"}), 400

    data: dict[str, list[dict[str, Any]]] = request.get_json()
    raw_products_data = data.get('products')

    if not raw_products_data:
        current_app.logger.error('Bad Request to /details: No product data provided in JSON.')
        return jsonify({"error": "No product data provided"}), 400

    try:
        current_app.logger.debug(f'Processing product dimensions for {len(raw_products_data)} products.')
        # Process the raw product data, which generates product_id for each Product object
        product_catalog: ProductCatalog = process_product_dimensions(raw_products_data)

        # Prepare the response: a list of product dictionaries including product_id
        # This is the data `index.html` will store and `checkout.html` will use.
        response_products = [
            {
                "product_id": p.product_id,
                "product_name": p.product_name,
                "weight": p.weight,
                "height": p.height,
                "width": p.width,
                "depth": p.depth,
                "vol": p.vol,
                "vol_weight": p.vol_weight
            }
            for p in product_catalog.products
        ]
        
        session["product_catalog_data"] = response_products
        current_app.logger.info(f'Successfully processed {len(response_products)} products and stored in session.')

        return jsonify({
            "message": "Product details processed successfully",
            "products": response_products # <-- THIS IS THE KEY: return products with their IDs
        }), 200

    except ValueError as ve:
        current_app.logger.error(f'Validation Error processing product data for /details: {ve}')
        return jsonify({"error": f"Invalid input data: {ve}"}), 400
    except KeyError as ke:
        current_app.logger.error(f'Key Error processing product data for /details: Missing field - {ke}')
        return jsonify({"error": f"Missing product data field: {ke}"}), 400
    except Exception as e:
        current_app.logger.exception('Unhandled exception during product processing on /details.')
        return jsonify({"error": "An unexpected server error occurred."}), 500



@bp.route('/calculate-inventory-costs', methods=['POST'])
def calculate_inventory_costs():
    """
    Flask endpoint to receive quantity updates from the frontend (dynamic calculations).
    Retrieves ProductCatalog, calculates inbound and storage costs, stores InitialInventory,
    and returns costs for dynamic UI update.
    """

    current_app.logger.info('Route accessed: /calculate-inventory-costs [POST]')
    if not request.is_json:
        current_app.logger.error('Bad Request to /calculate-inventory-costs: Request must be JSON.')
        return jsonify({"error": "Request must be JSON"}), 400

    raw_quantity_data: list[dict[str, Any]] = request.get_json().get('quantities', [])
    current_app.logger.debug(f'Received {len(raw_quantity_data)} quantity entries for cost calculation.')      
    
    product_catalog: ProductCatalog | None = None # Initialize as None

    # 1. Retrieve the ProductCatalog from the session
    product_catalog_data = {"products": session.get('product_catalog_data')}
    if not product_catalog_data:
        current_app.logger.warning('Missing ProductCatalog in session for /calculate-inventory-costs.')
        return jsonify({"error": "Product catalog not found in session. Please submit product dimensions first."}), 400

    try:
        product_catalog = ProductCatalog.from_dict(product_catalog_data)
        current_app.logger.debug('ProductCatalog successfully reconstructed from session.')
    except Exception as e:
        current_app.logger.exception(f"Error reconstructing ProductCatalog from session in /calculate-inventory-costs: {e}")
        # If reconstruction fails, clear the session data and redirect
        session.pop('product_catalog_data', None)
        return redirect(url_for('calculator.index'))

    try:
        # 2. Use the new orchestrator to process initial inventory (calculates fees)
        current_app.logger.debug('Calling process_initial_inventory.')
        initial_inventory: InitialInventory = process_initial_inventory(
            product_catalog,
            raw_quantity_data
        )

        # 3. Store the full InitialInventory object in the session (for Part 3 later)
        session['initial_inventory_data'] = initial_inventory.to_dict()
        current_app.logger.info('InitialInventory successfully calculated and stored in session.')
        # 4. Prepare per-product details for the frontend
        total_quantity_received = 0
        detailed_received_products = []
        for rp in initial_inventory.received_products:
            total_quantity_received += rp.quantity_received
            detailed_received_products.append(rp.to_dict())

        size = initial_inventory.size
        if size is Size.S:
            in_size_text = 'Pequeño'
        elif size is Size.M:
            in_size_text = 'Mediano'
        elif size is Size.L:
            in_size_text = 'Grande'
        elif size is Size.XL:
            in_size_text = 'Extragrande'
        # 5. Return the calculated total costs AND per-product details to the frontend
        current_app.logger.info('Successfully calculated inventory costs and returning response.')
        return jsonify({
            "status": "success",
            "total_inbound_cost": initial_inventory.total_inbound_cost_for_batch,
            "total_storage_cost": initial_inventory.total_storage_cost_for_batch,
            "received_products_details": detailed_received_products, # NEW: Per-product details
            "in_size_text" : in_size_text,
            "total_quantity_received" : total_quantity_received
        }), 200

    except Exception as e:
        current_app.logger.exception(f"Internal server error during cost calculation on /calculate-inventory-costs: {e}")
        return jsonify({"error": f"Internal server error during cost calculation: {str(e)}"}), 500




# --- Helper to get product catalog for frontend if needed via AJAX (e.g. on checkout.html load) ---
@bp.route('/api/get-product-catalog-shortened', methods=['GET'])
def api_get_product_catalog_shortened():
    """
    API endpoint to return the product catalog as JSON, typically called by JS on checkout.html.
    """
    current_app.logger.info('Route accessed: /api/get-product-catalog-shortened [GET]')
    # Retrieve the stored ProductCatalog from the session
    # Using .get() is safer as it returns None if the key doesn't exist
    product_catalog_data: ProductCatalog = session.get('product_catalog_data')

    if not product_catalog_data:
        current_app.logger.warning('No product catalog found in session for /api/get-product-catalog-shortened.')
        return jsonify({"error": "No product catalog found in session. Please submit products first."}), 404
    
    product_catalog: ProductCatalog | None = None # Initialize as None

    try:
        product_catalog = ProductCatalog.from_dict(product_catalog_data)
        current_app.logger.debug('ProductCatalog successfully reconstructed from session for API call.')
    except Exception as e:
        current_app.logger.exception(f"Error reconstructing ProductCatalog from session in /api/get-product-catalog-shortened: {e}")
        # If reconstruction fails, clear the session data and redirect
        session.pop('product_catalog_data', None)
        return redirect(url_for('calculator.index'))

    # Convert Product objects to a serializable format for JSON response
    serializable_products = [
        {
            "product_id": p.product_id,
            "product_name": p.product_name
        }
        for p in product_catalog.products
    ]
    current_app.logger.info(f'Returning shortened product catalog for {len(serializable_products)} products.')
    return jsonify({"products": serializable_products}), 200



@bp.route('/simulate-order', methods=['POST'])
def simulate_order():
    """
    Handles single order simulation requests.
    Calculates total outbound fees for the order and returns the aggregate cost.
    """

    current_app.logger.info('Route accessed: /simulate-order [POST]')
    if not request.is_json:
        current_app.logger.error('Bad Request to /simulate-order: Request must be JSON.')
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    order_items_data = data.get('order_items', [])
    current_app.logger.debug(f'Received {len(order_items_data)} order items for single order simulation.')

    product_catalog_data: dict[str, ProductCatalog] = {'products': session.get('product_catalog_data')}

    if product_catalog_data.get('products') is None:
        current_app.logger.warning('No product catalog found in session for /simulate-order.')
        return jsonify({"error": "No product catalog found in session. Please submit products first."}), 404
    
    product_catalog: ProductCatalog | None = None # Initialize as None

    try:
        product_catalog = ProductCatalog.from_dict(product_catalog_data)
        current_app.logger.debug('ProductCatalog successfully reconstructed from session for order simulation.')
    except Exception as e:
        current_app.logger.exception(f"Error reconstructing ProductCatalog from session in /simulate-order: {e}")
        # If reconstruction fails, clear the session data and redirect
        session.pop('product_catalog_data', None)
        return redirect(url_for('calculator.index'))
    try:
        # Call the main order simulation orchestrator with 'single_order' type
        # It will return an empty list for per-product details, and the total cost.
        current_app.logger.debug('Calling process_order_simulation for single order.')
        per_product_details, total_order_cost = process_order_simulation(
            simulation_type='single_order',
            data={'order_items': order_items_data}, # Pass the specific data for this type
            product_catalog=product_catalog
        )
        current_app.logger.info(f'Single order simulation successful. Total cost: {total_order_cost:.2f}')
        return jsonify({
            "status": "success",
            "simulation_type": "single_order",
            "total_order_cost": total_order_cost,
            "order_products_details": per_product_details
        }), 200

    except Exception as e:
        current_app.logger.exception(f"Internal server error during single order simulation on /simulate-order: {e}")
        return jsonify({"error": f"Internal server error during single order simulation: {str(e)}"}), 500


@bp.route('/simulate-monthly-sales', methods=['POST'])
def simulate_monthly_sales():
    """
    Handles monthly sales percentage simulation requests.
    Calculates and returns prorated per-product costs and the total monthly cost.
    """

    current_app.logger.info('Route accessed: /simulate-monthly-sales [POST]')
    if not request.is_json:
        current_app.logger.error('Bad Request to /simulate-monthly-sales: Request must be JSON.')
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    sales_percentages_data = data.get('sales_percentages', [])
    current_app.logger.debug(f'Received {len(sales_percentages_data)} sales percentage entries for monthly simulation.')
    product_catalog_data: dict[str, ProductCatalog] = {'products': session.get('product_catalog_data')}

    if product_catalog_data.get('products') is None:
        current_app.logger.warning('No product catalog found in session for /simulate-monthly-sales.')
        return jsonify({"error": "No product catalog found in session. Please submit products first."}), 404
    
    product_catalog: ProductCatalog | None = None # Initialize as None

    try:
        product_catalog = ProductCatalog.from_dict(product_catalog_data)
        current_app.logger.debug('ProductCatalog successfully reconstructed from session for monthly sales simulation.')
    except Exception as e:
        current_app.logger.exception(f"Error reconstructing ProductCatalog from session in /simulate-monthly-sales: {e}")
        # If reconstruction fails, clear the session data and redirect
        session.pop('product_catalog_data', None)
        return redirect(url_for('calculator.index'))
    
    initial_inventory_data: InitialInventory = session.get('initial_inventory_data')

    if not initial_inventory_data:
        current_app.logger.warning('No initial inventory found in session for /simulate-monthly-sales.')
        return jsonify({"error": "No product inventory found in session. Please submit quantities first."}), 404
    
    initial_inventory: InitialInventory | None = None # Initialize as None

    try:
        initial_inventory = InitialInventory.from_dict(initial_inventory_data)
        current_app.logger.debug('InitialInventory successfully reconstructed from session for monthly sales simulation.')
    except Exception as e:
        current_app.logger.exception(f"Error reconstructing InitialInventory from session in /simulate-monthly-sales: {e}")
        # If reconstruction fails, clear the session data and redirect
        session.pop('initial_inventory_data', None)
        return redirect(url_for('calculator.index'))

    if not product_catalog:
        current_app.logger.error('Logical error: Product catalog is unexpectedly None after checks for /simulate-monthly-sales.')
        return jsonify({"error": "Product catalog not found. Please submit product dimensions first."}), 400
    if not initial_inventory:
        current_app.logger.error('Logical error: Initial inventory is unexpectedly None after checks for /simulate-monthly-sales.')
        return jsonify({"error": "Initial inventory not found. Please complete reception and storage first."}), 400

    try:
        # Call the main order simulation orchestrator with 'monthly_sales' type
        current_app.logger.debug('Calling process_order_simulation for monthly sales.')
        per_product_details, total_monthly_cost = process_order_simulation(
            simulation_type='monthly_sales',
            data={'sales_percentages': sales_percentages_data}, # Pass the specific data
            product_catalog=product_catalog,
            initial_inventory=initial_inventory # Required for this simulation type
        )
        current_app.logger.info(f'Monthly sales simulation successful. Total monthly cost: {total_monthly_cost:.2f}')
        return jsonify({
            "status": "success",
            "simulation_type": "monthly_sales",
            "total_monthly_cost": total_monthly_cost,
            "sales_products_details": per_product_details 
        }), 200

    except Exception as e:
        current_app.logger.exception(f"Internal server error during monthly sales simulation on /simulate-monthly-sales: {e}")
        return jsonify({"error": f"Internal server error during monthly sales simulation: {str(e)}"}), 500

