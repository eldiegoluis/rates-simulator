from ..models import Product, ReceivedProduct, InitialInventory, Size
from ..config import get_settings
from typing import List, Tuple

def compute_inbound_rates(initial_inventory: InitialInventory) -> None:
    s = get_settings()

    total_inbound_cost_for_batch = 0.0

    rate = s.get_in_rate_by_size(initial_inventory.size)

    for rp in initial_inventory.received_products:
        rp.total_inbound_fee = rate * rp.quantity_received * rp.product.vol_weight
        total_inbound_cost_for_batch += rp.total_inbound_fee 

    initial_inventory.total_inbound_cost_for_batch = total_inbound_cost_for_batch



def assign_size(initial_inventory: InitialInventory) -> None:
    s = get_settings()

    total_vol_weight_in = 0.0

    for rp in initial_inventory.received_products:
        total_vol_weight_in += rp.product.vol_weight * rp.quantity_received

    if total_vol_weight_in > s.XL_VOL_WEIGHT_LIMIT_IN:
        initial_inventory.size = Size.XL
    elif total_vol_weight_in > s.L_VOL_WEIGHT_LIMIT_IN:
        initial_inventory.size = Size.L
    elif total_vol_weight_in > s.M_VOL_WEIGHT_LIMIT_IN:
        initial_inventory.size = Size.M
    else:
        initial_inventory.size = Size.S



def process_inbound(initial_inventory: InitialInventory) -> None:

    assign_size(initial_inventory)

    # Compute individual inbound rates and flags (modifies received_products in-place)
    compute_inbound_rates(initial_inventory)


