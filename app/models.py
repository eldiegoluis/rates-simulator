from enum import Enum, auto
from dataclasses import dataclass, field, asdict
import uuid
from typing import List, Any


# Core identifying attributes (user input - Part 1)
@dataclass
class Product:
    product_name: str
    weight: float
    height: float
    width: float
    depth: float
    product_id: str = field(default_factory=lambda: str(uuid.uuid4()), init=False)

    # independent computed fields
    vol_weight: float = field(default=0.0, init=False)
    vol: float  = field(default=0.0, init=False)

    def to_dict(self):
        # asdict() from dataclasses is great for converting dataclasses to dicts
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Product':

        product = cls(
            product_name=data['product_name'],
            weight=data['weight'],
            height=data['height'],
            width=data['width'],
            depth=data['depth']
        )
        # Restore init=False fields if they exist in the data
        if 'product_id' in data:
            product.product_id = data['product_id']
        if 'vol_weight' in data:
            product.vol_weight = data['vol_weight']
        if 'vol' in data:
            product.vol = data['vol']
        return product
   
class Size(Enum):
    S = auto()
    M = auto()
    L = auto()
    XL = auto()


# For Part 2: Reception and Storage (Initial Inventory)
@dataclass
class ReceivedProduct:
    product: Product        # Reference to the Product master data
    quantity_received: int  # Quantity initially received/stored
    # Computed fields for this specific batch (quantity-dependent totals)
    total_inbound_fee: float = field(default=0.0, init=False)
    total_storage_fee: float = field(default=0.0, init=False) # Prorated total for this batch
    vol_to_store: float   = field(default=0.0, init=False)
    large_strg_flag: bool = field(default=False, init=False)


    def to_dict(self) -> dict[str, Any]:
        data = {
            "quantity_received": self.quantity_received,
            "total_inbound_fee": self.total_inbound_fee,
            "total_storage_fee": self.total_storage_fee,
            "large_strg_flag": self.large_strg_flag,
            "vol_to_store": self.vol_to_store,
        }
        # Nested dataclass: call its to_dict method
        data["product"] = self.product.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ReceivedProduct':
        # Reconstruct nested Product first
        product_data = data.get("product")
        if product_data is None:
            raise ValueError("Missing 'product' data in ReceivedProduct dictionary.")
        product_instance = Product.from_dict(product_data)

        received_product = cls(
            product=product_instance,
            quantity_received=data.get("quantity_received")
        )
        # Restore init=False fields from dictionary, providing defaults if not present
        received_product.total_inbound_fee = data.get("total_inbound_fee", 0.0)
        received_product.total_storage_fee = data.get("total_storage_fee", 0.0)
        received_product.large_strg_flag = data.get("large_strg_flag", False)
        received_product.vol_to_store = data.get("vol_to_store", 0.0)

        return received_product



# For Part 3 (Option 1): Single Order Simulation
@dataclass
class OrderProduct:
    product: Product        # Reference to the Product master data
    quantity_ordered: int   # Quantity for a specific order
    # Computed fields for this order item


    def to_dict(self) -> dict[str, Any]:
        data = {
            "quantity_ordered": self.quantity_ordered,
        }
        data["product"] = self.product.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'OrderProduct':
        product_data = data.get("product")
        if product_data is None:
            raise ValueError("Missing 'product' data in OrderProduct dictionary.")
        product_instance = Product.from_dict(product_data)

        order_product = cls(
            product=product_instance,
            quantity_ordered=data.get("quantity_ordered")
        )
        return order_product


# For Part 3 (Option 2): Monthly Sales Percentage Simulation
@dataclass
class SalesSimulationProduct:
    product: Product            # Reference to the Product master data
    # No quantity here, as it's derived from the percentage and initial inventory
    sales_percentage: float # e.g., 0.10 for 10%
    quantity_sold: int = field(default=0)
    
    total_orders_cost_per_product: float = field(default=0.0, init=False) # The aggregate of computing the number of orders based off of sales percentage of the received products and supposing every order had only 1 item of the product inside 


    def to_dict(self) -> dict[str, Any]:
        data = {
            "sales_percentage": self.sales_percentage,
            "quantity_sold": self.quantity_sold,
            "total_orders_cost_per_product": self.total_orders_cost_per_product,
        }
        data["product"] = self.product.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'SalesSimulationProduct':
        product_data = data.get("product")
        if product_data is None:
            raise ValueError("Missing 'product' data in SalesSimulationProduct dictionary.")
        product_instance = Product.from_dict(product_data)

        sales_product = cls(
            product=product_instance,
            sales_percentage=data.get("sales_percentage")
        )
        sales_product.quantity_sold = data.get("quantity_sold", 0)
        sales_product.total_orders_cost_per_product = data.get("total_orders_cost_per_product", 0.0)
        return sales_product



# NEW CONTAINER DATACLASSES FOR EACH STAGE

# For Part 1 (User enters dimensions, before quantities)
@dataclass
class ProductCatalog:
    products: List[Product] # List of master product definitions

    def to_dict(self) -> dict[str, Any]:
        # Convert the ProductCatalog to a dictionary.
        # Iterate through products and call their to_dict() method.
        return {
            "products": [p.to_dict() for p in self.products]
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ProductCatalog':
        # Reconstruct each Product from its dictionary data
        products_data = data.get("products", [])
        products_list = [Product.from_dict(p_data) for p_data in products_data]
        return cls(products=products_list)


# For Part 2 (User enters quantities for initial reception/storage)
@dataclass
class InitialInventory:
    received_products: List[ReceivedProduct]
    total_inbound_cost_for_batch: float = field(default=0.0, init=False) 
    total_storage_cost_for_batch: float = field(default=0.0, init=False) 
    size:                         Size  = field(default=None, init=False)
    
    def to_dict(self) -> dict[str, Any]:
        data = {
            "received_products": [rp.to_dict() for rp in self.received_products],
            "total_inbound_cost_for_batch": self.total_inbound_cost_for_batch,
            "total_storage_cost_for_batch": self.total_storage_cost_for_batch,
        }
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'InitialInventory':
        received_products_data = data.get("received_products", [])
        received_products_list = [ReceivedProduct.from_dict(rp_data) for rp_data in received_products_data]

        inventory = cls(received_products=received_products_list)
        inventory.total_inbound_cost_for_batch = data.get("total_inbound_cost_for_batch", 0.0)
        inventory.total_storage_cost_for_batch = data.get("total_storage_cost_for_batch", 0.0)
        return inventory



# For Part 3 (Option 1: Single Order)
@dataclass
class CustomerOrder:
    order_id: str
    order_products: List[OrderProduct]
    total_order_cost: float = field(default=0.0, init=False) # Aggregate total


    def to_dict(self) -> dict[str, Any]:
        data = {
            "order_id": self.order_id,
            "order_products": [op.to_dict() for op in self.order_products],
            "total_order_cost": self.total_order_cost,
        }
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'CustomerOrder':
        order_products_data = data.get("order_products", [])
        order_products_list = [OrderProduct.from_dict(op_data) for op_data in order_products_data]

        order = cls(
            order_id=data.get("order_id"),
            order_products=order_products_list
        )
        order.total_order_cost = data.get("total_order_cost", 0.0)
        return order


# For Part 3 (Option 2: Monthly Sales Simulation)
@dataclass
class MonthlySalesSimulation:
    simulation_id: str
    sales_products: List[SalesSimulationProduct]
    total_monthly_cost: float = field(default=0.0, init=False)


    def to_dict(self) -> dict[str, Any]:
        data = {
            "simulation_id": self.simulation_id,
            "sales_products": [ssp.to_dict() for ssp in self.sales_products],
            "total_monthly_cost": self.total_monthly_cost,
        }
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'MonthlySalesSimulation':
        sales_products_data = data.get("sales_products", [])
        sales_products_list = [SalesSimulationProduct.from_dict(ssp_data) for ssp_data in sales_products_data]

        simulation = cls(
            simulation_id=data.get("simulation_id"),
            sales_products=sales_products_list
        )
        simulation.total_monthly_cost = data.get("total_monthly_cost", 0.0)
        return simulation

