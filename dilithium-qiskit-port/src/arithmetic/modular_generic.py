from abc import ABC, abstractmethod

class ModularBackend(ABC):
    """
    Abstract Base Class for Modular Arithmetic implementations.
    This allows swapping between different modulus implementations (q=7, q=17, q=8380417, etc.)
    without changing the high-level NTT logic.
    """
    
    def __init__(self, q):
        self.q = q

    @abstractmethod
    def add_mod(self, qc, reg_a, reg_b, aux):
        """
        Computes |a>|b> -> |a>|(a+b)%q>
        """
        pass

    @abstractmethod
    def sub_mod(self, qc, reg_a, reg_b, aux):
        """
        Computes |a>|b> -> |a>|(a-b)%q>
        """
        pass

    @abstractmethod
    def mul_const_mod(self, qc, reg_a, const, aux, reg_out=None):
        """
        Computes |a> -> |(a*const)%q>
        This operation might happen in place or using an output register depending on implementation strategy.
        Usually for reversible computing:
        |a>|0> -> |a>|a*c>
        """
        pass
