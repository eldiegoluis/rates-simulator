from .models import Product, ProductCatalog, ReceivedProduct, OrderProduct, SalesSimulationProduct, InitialInventory, CustomerOrder
from .services.volumetrics import apply_volumetrics

from .config import get_settings

from .services.inbound import process_inbound
from .services.storage import get_storage_fees
from .services.outbound import get_outbound_fees_for_sales_simulation, get_outbound_fees_for_single_order

from typing import Any
import math

def process_product_dimensions(raw_products: list[dict]) -> ProductCatalog:

    # 1) Instantiate Product objects
   
    products = []
    for idx, p_data in enumerate(raw_products):
        try:
            # Ensure keys match dataclass attributes
            product = Product(
                product_name=p_data['product_name'],
                weight=float(p_data['weight']),
                height=float(p_data['height']),
                width=float(p_data['width']),
                depth=float(p_data['depth'])
            )
            products.append(product)
        except (KeyError, ValueError) as e:
            print(f"Error processing product data at index {idx}: {e}. Data: {p_data}")
            # In a real application, you'd handle this more gracefully,
            # perhaps returning an error message to the user.
            continue # Skip to the next product

    # 2) Apply volumetric calculations (modifies products in-place)
    apply_volumetrics(products)

    # 3) Return the processed products as a ProductCatalog
    return ProductCatalog(products=products)

def process_initial_inventory(
    product_catalog: ProductCatalog,
    raw_quantity_data: list[dict[str, Any]]
) -> InitialInventory:
    """
    Orchestrates the calculation of inbound and storage fees for an initial inventory batch.

    Args:
        product_catalog: The ProductCatalog object containing master Product definitions
                         (from Part 1, retrieved from session).
        raw_quantity_data: A list of dictionaries from the frontend,
                           each with 'product_id' and 'quantity_received'.

    Returns:
        An InitialInventory object containing the processed ReceivedProduct list
        and the aggregate total inbound and storage costs.
    """
    s = get_settings() # Get settings once for this orchestration

    # Create a dictonary for quick lookup of Product objects by product_id

    product_map = {p.product_id: p for p in product_catalog.products}

    received_products: list[ReceivedProduct] = []
    for item_data in raw_quantity_data:
        product_id = item_data.get('product_id')
        quantity = int(item_data.get('quantity_received', 0))

        product = product_map.get(product_id)
        if product and quantity > 0:
            received_product = ReceivedProduct(product=product, quantity_received=quantity)
            received_products.append(received_product)
        elif not product:
            print(f"Warning: Product with ID '{product_id}' not found in catalog. Skipping.")   

    # Populate the InitialInventory container object
    initial_inventory = InitialInventory(
        received_products = received_products
    )


    # Calculate Inbound Fees (modifies received_products in-place)
    # The first element of the tuple is the modified list, which we re-assign.
    process_inbound(initial_inventory)       


    # Calculate Storage Fees (modifies received_products in-place)
    # Again, re-assign the list as it's modified and returned.  
    received_products, total_storage_cost = get_storage_fees(received_products, s)

    initial_inventory.received_products = received_products
    initial_inventory.total_storage_cost_for_batch = total_storage_cost


    return initial_inventory




def process_order_simulation(
    simulation_type: str,
    data: dict[str, Any], # This will contain either raw_order_data or raw_sales_data
    product_catalog: ProductCatalog,
    initial_inventory: InitialInventory | None = None # Needed for Sales Percentage simulation
    ) -> tuple[list[dict[str, Any]], float]: # Returns serializable product details and total cost
    """
    Orchestrates the order simulation process based on the requested type.

    Args:
        simulation_type: 'single_order' or 'monthly_sales'.
        data: Raw data specific to the simulation type (e.g., list of order items, or sales percentages).
        product_catalog: The master ProductCatalog.
        initial_inventory: Optional, the InitialInventory object (from Part 2), needed for monthly_sales to get quantity_received.

    Returns:
        A tuple:
        - list of dictionaries with serializable per-product details (e.g., for Sales Sim).
        - The aggregate total cost for the simulation.
    """
    s = get_settings() # Get settings once for the orchestration

    # Create a dictionary for quick lookup of Product objects by product_id
    product_map = {p.product_id: p for p in product_catalog.products}

    if simulation_type == 'single_order':
        raw_order_items = data.get('order_items', [])
        order_products: list[OrderProduct] = []
        for item_data in raw_order_items:
            product_id = item_data.get('product_id')
            quantity_ordered = int(item_data.get('quantity_ordered', 0))
            product = product_map.get(product_id)
            if product and quantity_ordered > 0:
                order_product = OrderProduct(product=product, quantity_ordered=quantity_ordered)
                order_products.append(order_product)
            elif not product:
                print(f"Warning: Product with ID '{product_id}' not found in catalog for single order. Skipping.")

        # Calculate outbound fees for the customer order
        modified_order_products, total_order_cost = get_outbound_fees_for_single_order(order_products, s)

        # Prepare serializable per-product details for the frontend
        # This is the NEW part based on your request.
        serializable_order_products = []
        for op in modified_order_products:
            serializable_order_products.append({
                "product_id": op.product.product_id,
                "product_name": op.product.product_name,
                "quantity_ordered": op.quantity_ordered,
                # Note: No per-product fees like picking_cost, outbound_cost
                # are explicitly included here (ONLY TOTAL ORDER COST DISPLAYED).
            })
        return serializable_order_products, total_order_cost


    elif simulation_type == 'monthly_sales':
        if not initial_inventory:
            raise ValueError("Initial inventory data is required for monthly sales simulation.")

        raw_sales_data = data.get('sales_percentages', [])
        sales_products: list[SalesSimulationProduct] = []

        # Create a map for quick lookup of ReceivedProduct (for quantity_received)
        received_product_map = {rp.product.product_id: rp for rp in initial_inventory.received_products}

        for sales_item_data in raw_sales_data:
            product_id = sales_item_data.get('product_id')
            sales_percentage = float(sales_item_data.get('sales_percentage', 0.0))
            sales_percentage = sales_percentage / 100


            product = product_map.get(product_id)
            received_product_in_inventory = received_product_map.get(product_id)

            if product and received_product_in_inventory and sales_percentage > 0:
                # Calculate simulated_quantity_sold based on initial inventory
                quantity_sold = math.floor(
                    received_product_in_inventory.quantity_received * sales_percentage
                )
                if 0 < quantity_sold < 1:
                    quantity_sold = 1
                if quantity_sold > 0:
                    sales_product = SalesSimulationProduct(
                        product=product,
                        sales_percentage=sales_percentage,
                        quantity_sold=quantity_sold
                    )
                    sales_products.append(sales_product)
            elif not product:
                print(f"Warning: Product with ID '{product_id}' not found in catalog for sales sim. Skipping.")
            elif not received_product_in_inventory:
                print(f"Warning: Product with ID '{product_id}' not found in initial inventory for sales sim. Skipping.")
            # else: sales_percentage is 0, so we skip

        # Calculate outbound fees for sales simulation
        modified_sales_products, total_monthly_cost = get_outbound_fees_for_sales_simulation(sales_products, s)

        # Prepare serializable per-product details for the frontend
        serializable_sales_products = []
        for ssp in modified_sales_products:
            serializable_sales_products.append({
                "product_id": ssp.product.product_id,
                "product_name": ssp.product.product_name,
                "sales_percentage": ssp.sales_percentage,
                "simulated_quantity_sold": ssp.quantity_sold,
                "total_orders_cost_per_product": ssp.total_orders_cost_per_product
            })
        return serializable_sales_products, total_monthly_cost

    else:
        raise ValueError(f"Unknown simulation type: {simulation_type}")

