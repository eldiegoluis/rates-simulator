import math
from typing import List, NamedTuple, Tuple
from ..models import Product, ReceivedProduct
from ..config import get_settings, Settings

s = get_settings()

class BillingInfo(NamedTuple):
    shelves: int
    price: float


def compute_strg_vol_and_flag_for_received_products(
    received_products: List[ReceivedProduct], s: Settings
) -> Tuple[float, float]:
    """
    Partition products into regular and large storage volumes, flagging each product.
    Modifies ReceivedProduct objects in place.

    Returns:
        (regular_vol_sum, large_vol_sum)
    """
    regular_vol_sum = 0.0
    large_vol_sum = 0.0

    for rp in received_products:
        # total volume for all units
        rp.vol_to_store = rp.product.vol * rp.quantity_received * 1.3

        if rp.vol_to_store < s.STRG_VOL_LIMIT:
            rp.large_strg_flag = False
            regular_vol_sum += rp.vol_to_store
        else:
            rp.large_strg_flag = True
            large_vol_sum += rp.vol_to_store

    return regular_vol_sum, large_vol_sum


def compute_shelves(volume: float, s: Settings) -> int:
    """
    Compute number of storage-unit "shelves" needed.
    """
    if volume == 0:
        return 0
    return math.ceil(volume / s.STRG_UNIT_VOL)


def compute_price_of_shelves(shelves: int, large: bool, s: Settings) -> float:
    """
    Compute total shelf-fee given count and item size.
    """
    rate = s.STRG_RATE_LRG if large else s.STRG_RATE_REG
    return shelves * rate


def compute_prorata_for_received_products(
    received_products: List[ReceivedProduct],
    regular_info: BillingInfo,
    large_info: BillingInfo,
    s: Settings
) -> None:
    """
    Distribute shelf-fee pro rata back onto each product, ensuring the sum of fees
    matches the total billed price. Modifies ReceivedProduct objects in place.
    """
    # Separate products into regular and large categories for easier processing
    # Create temporary lists (references to the original objects)
    regular_products = [rp for rp in received_products if not rp.large_strg_flag]
    large_products = [rp for rp in received_products if rp.large_strg_flag]

    # Calculate the total *actual* volume for each category
    total_actual_regular_vol = sum(rp.vol_to_store for rp in regular_products)
    total_actual_large_vol = sum(rp.vol_to_store for rp in large_products)

    # Prorate fees for regular products
    remaining_regular_price = regular_info.price
    if regular_products: # Only proceed if there are regular products
        for i, rp in enumerate(regular_products):
            if total_actual_regular_vol > 0:
                # Calculate the prorated share based on actual volume
                prorated_share = rp.vol_to_store / total_actual_regular_vol
                rp_fee = prorated_share * regular_info.price
                
                # For the last product, assign the remaining price to ensure the sum is exact
                if i == len(regular_products) - 1:
                    rp.total_storage_fee = remaining_regular_price
                else:
                    rp.total_storage_fee = rp_fee
                
                remaining_regular_price -= rp.total_storage_fee # Subtract the actual assigned fee
            else:
                rp.total_storage_fee = 0.0 # No volume, no fee
    
    # Prorate fees for large products
    remaining_large_price = large_info.price
    if large_products: # Only proceed if there are large products
        for i, rp in enumerate(large_products):
            if total_actual_large_vol > 0:
                prorated_share = rp.vol_to_store / total_actual_large_vol
                rp_fee = prorated_share * large_info.price
                
                if i == len(large_products) - 1:
                    rp.total_storage_fee = remaining_large_price
                else:
                    rp.total_storage_fee = rp_fee
                
                remaining_large_price -= rp.total_storage_fee # Subtract the actual assigned fee
            else:
                rp.total_storage_fee = 0.0 # No volume, no fee

    # Orchestrator
def get_storage_fees(
    received_products: List[ReceivedProduct],
    s: Settings = None
    ) -> Tuple[List[ReceivedProduct], float]:
    """
    Main entrypoint for storage service. Flags large items, calculates
    shelving needs, prorates fees per product, and returns total storage fee.

    Returns:
        (annotated_products, total_storage_fee)
    """
    if s is None:
        s = get_settings()

    # Partition volumes and flag
    reg_vol, large_vol = compute_strg_vol_and_flag_for_received_products(received_products, s)

    # Compute billing info for each category
    if reg_vol > 0:
        reg_shelves = compute_shelves(reg_vol, s)
        reg_info = BillingInfo(
            shelves=reg_shelves,
            price=compute_price_of_shelves(reg_shelves, large=False, s=s)
        )
    else:
        reg_info = BillingInfo(0, 0.0)

    if large_vol > 0:
        large_shelves = compute_shelves(large_vol, s)
        large_info = BillingInfo(
            shelves=large_shelves,
            price=compute_price_of_shelves(large_shelves, large=True, s=s)
        )
    else:
        large_info = BillingInfo(0, 0.0)

    # Apply pro rata back to products
    compute_prorata_for_received_products(received_products, reg_info, large_info, s)

    total_storage_fee = reg_info.price + large_info.price
    
    return received_products, total_storage_fee
