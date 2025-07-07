from ..models import Product
from ..config import get_settings


def compute_volume_weight(product: Product) -> float:
    
    """Returns either actual weight or dimensional weight, whichever is greater."""
    
    s = get_settings()

    dimensional_weight = (product.vol) / s.DIVISOR
    return max(product.weight, dimensional_weight)

def compute_volume(product: Product) -> float:

    return product.height * product.width * product.depth

def apply_volumetrics(products: list[Product]) -> None:
    for p in products:
        p.vol = compute_volume(p)
        p.vol_weight = compute_volume_weight(p)



