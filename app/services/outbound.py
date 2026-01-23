import math
from ..models import Product, OrderProduct, SalesSimulationProduct
from ..config import get_settings, Settings
from typing import Tuple, List

def _calc_tiers_fee(remaining: float, s: Settings) -> float:
    
    tiers = s.sorted_tiers
    
    fee = 0.0
    prev_weight = 55
    while remaining > 0:
        for vol_weight, rate in tiers:
            if remaining >= vol_weight:
                fee += rate
                remaining -= prev_weight
                prev_weight = vol_weight
                # Once a tier is applied, restart checking from the highest tier.
                break
        else:
            # remainder below smallest block: charge one smallest‑block fee
            fee += tiers[-1][1]
            remaining = 0
    return fee


def compute_outbound(vol_weight: float,
                    s : Settings,
                    ) -> float:
    # here we deal with the whole order vol_weight 

    limit = s.XL_VOL_WEIGHT_LIMIT_OUT
    xl = s.XL_RATE_OUT

    if vol_weight < limit:
        if vol_weight < 5:
            return s.S_RATE_OUT
        if vol_weight < 15:
            return s.M_RATE_OUT
        if vol_weight < 55:
            return s.L_RATE_OUT
        return s.XL_RATE_OUT
    
    # above limit: chunk into full‑limit + remainder
    full_chunks = vol_weight // limit
    fee = full_chunks * xl
    remaining_vol_weight = vol_weight - (full_chunks * limit)

    fee += _calc_tiers_fee(remaining_vol_weight, s)
    
    return fee


def get_outbound_fees_for_single_order(
                                            order_products: List[OrderProduct], 
                                            s: object
                                        ) -> Tuple[List[OrderProduct], float]:

    if s is None:
        s = get_settings()

    vol_weight_total = 0.0  # Total vol_weight for items subject to picking charges

    for op in order_products:
        # Calculate total volumetric weight for this single line item in the order
        line_item_vol_weight = op.product.vol_weight * op.quantity_ordered
        vol_weight_total += line_item_vol_weight


    fee = compute_outbound(
        vol_weight_total,
        s,
    )


    total_outbound_fee = fee
    return order_products , total_outbound_fee


def get_outbound_fees_for_sales_simulation(
    sales_products: List[SalesSimulationProduct], s: object
) -> Tuple[List[SalesSimulationProduct], float]:
    """
    Calculates picking and outbound fees for a monthly sales simulation,
    assuming each sale is a separate 1-unit order.
    Sets 'large_picking_flag' and 'total_orders_cost_per_product' on SalesSimulationProduct instances.

    Args:
        sales_products: A list of SalesSimulationProduct objects.
        s: Settings object.

    Returns:
        A tuple containing:
        - The list of SalesSimulationProduct objects with updated calculated fields.
        - The total aggregate cost for all simulated sales.
    """
    total_monthly_simulation_cost = 0.0

    for ssp in sales_products:
        # For Sales Simulation, each 'sale' is a 1-unit order.
        # So, the 'vol_weight' for a single unit order is just the product's per-unit vol_weight.
        single_unit_vol_weight = ssp.product.vol_weight 

        cost_per_single_unit = compute_outbound(
            single_unit_vol_weight,
            s
        )

        # Calculate the total cost for this product's simulated sales
        # (simulated_quantity_sold * cost_per_single_unit_order)
        cost_per_single_unit_order = cost_per_single_unit
        ssp.total_orders_cost_per_product = ssp.quantity_sold * cost_per_single_unit_order

        total_monthly_simulation_cost += ssp.total_orders_cost_per_product

    return sales_products, total_monthly_simulation_cost

