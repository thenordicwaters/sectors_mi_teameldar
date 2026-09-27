from app.services.scoring.base import ScoringMethod
from app.services.scoring.methods.financials_quality import FinancialsQualityMethod
from app.services.scoring.methods.foreign_flow import ForeignFlowMethod
from app.services.scoring.methods.magic_formula import MagicFormulaMethod
from app.services.scoring.methods.momentum import MomentumMethod
from app.services.scoring.methods.piotroski import PiotroskiMethod

def registered_methods() -> list[ScoringMethod]:
    """Adding a method = one new file in methods/ + one line here."""
    return [
        PiotroskiMethod(),
        MagicFormulaMethod(),
        MomentumMethod(),
        ForeignFlowMethod(),
        FinancialsQualityMethod(),
    ]
