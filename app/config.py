import os
from dotenv import load_dotenv
from functools import lru_cache
from typing import NamedTuple, List, Tuple
from .models import Size

load_dotenv()

class Settings(NamedTuple):

    STRG_VOL_LIMIT: int
    STRG_UNIT_VOL: int
    STRG_RATE_REG: float
    STRG_RATE_LRG: float

    M_VOL_WEIGHT_LIMIT_IN : int
    L_VOL_WEIGHT_LIMIT_IN : int
    XL_VOL_WEIGHT_LIMIT_IN : int

    S_VOL_WEIGHT_LIMIT_OUT : int
    M_VOL_WEIGHT_LIMIT_OUT : int
    L_VOL_WEIGHT_LIMIT_OUT : int

    IN_VOL_WEIGHT_LIMIT: int

    S_RATE_IN : int
    M_RATE_IN : int 
    L_RATE_IN : int
    XL_RATE_IN : int



    S_RATE_OUT: float
    M_RATE_OUT: float
    L_RATE_OUT: float
    XL_RATE_OUT: float
 

    DIVISOR: int

    IN_TIERS: dict[Size, tuple[int, float]]

    @property
    def sorted_tiers(self) -> List[Tuple[float, float]]:
        """
        Returns a list of tiers, sorted in descending order by volume/weight limit.
        Each tier is a tuple: (volume_weight_limit, rate).
        """
        return sorted([
            (self.L_VOL_WEIGHT_LIMIT_OUT, self.L_RATE_OUT),
            (self.M_VOL_WEIGHT_LIMIT_OUT, self.M_RATE_OUT),
            (self.S_VOL_WEIGHT_LIMIT_OUT, self.S_RATE_OUT)
        ], key=lambda x: x[0], reverse=True)


    def get_in_rate_by_size(self, size: Size) -> float:
        """
        Rapidly retrieves the inbound rate for a given Size.
        Raises KeyError if the size is not found.
        """
        return self.IN_TIERS[size][1] # [1] because the value is (limit, rate)

@lru_cache()
def get_settings() -> Settings:
    return Settings(
        M_VOL_WEIGHT_LIMIT_IN  = int(os.getenv("M_VOL_WEIGHT_LIMIT_IN")),
        L_VOL_WEIGHT_LIMIT_IN  = int(os.getenv("L_VOL_WEIGHT_LIMIT_IN")),
        XL_VOL_WEIGHT_LIMIT_IN  = int(os.getenv("XL_VOL_WEIGHT_LIMIT_IN")),

        S_RATE_IN          = float(os.getenv("S_RATE_IN")),
        M_RATE_IN          = float(os.getenv("M_RATE_IN")),
        L_RATE_IN          = float(os.getenv("L_RATE_IN")),
        XL_RATE_IN          = float(os.getenv("XL_RATE_IN")),


        STRG_VOL_LIMIT       = int(os.getenv("STRG_VOL_LIMIT")),
        STRG_UNIT_VOL        = int(os.getenv("STRG_UNIT_VOL")),
        STRG_RATE_REG        = float(os.getenv("STRG_RATE_REG")),
        STRG_RATE_LRG        = float(os.getenv("STRG_RATE_LRG")),
        
        IN_VOL_WEIGHT_LIMIT = int(os.getenv("IN_VOL_WEIGHT_LIMIT")),

        S_VOL_WEIGHT_LIMIT_OUT   = int(os.getenv("S_VOL_WEIGHT_LIMIT_OUT")),
        M_VOL_WEIGHT_LIMIT_OUT   = int(os.getenv("M_VOL_WEIGHT_LIMIT_OUT")),
        L_VOL_WEIGHT_LIMIT_OUT   = int(os.getenv("L_VOL_WEIGHT_LIMIT_OUT")),
        
        S_RATE_OUT               = float(os.getenv("S_RATE_OUT")),
        M_RATE_OUT               = float(os.getenv("M_RATE_OUT")),
        L_RATE_OUT               = float(os.getenv("L_RATE_OUT")),
        XL_RATE_OUT         = float(os.getenv("XL_RATE_OUT")),
        
        DIVISOR              = int(os.getenv("DIVISOR")),

        IN_TIERS={
            Size.S: (0, float(os.getenv("S_RATE_IN"))),    # (limit, rate)
            Size.M: (int(os.getenv("M_VOL_WEIGHT_LIMIT_IN")), float(os.getenv("S_RATE_IN"))),
            Size.L: (int(os.getenv("L_VOL_WEIGHT_LIMIT_IN")), float(os.getenv("L_RATE_IN"))),
            Size.XL: (int(os.getenv("XL_VOL_WEIGHT_LIMIT_IN")), float(os.getenv("XL_RATE_IN"))),
        },

    )
