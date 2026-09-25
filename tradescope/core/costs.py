"""Landed-cost calculator and Incoterms 2020 reference.

Tax defaults are editable in the UI and should be checked against current rules:
  Indonesia import: PPN (VAT) effectively 11% for most goods; PPh 22 import
  2.5% with an importer ID (API), 7.5% without.
  Taiwan import: business tax (VAT) 5%.
"""
from __future__ import annotations

DEFAULTS = {
    "tw_to_id": {"vat": 11.0, "income_tax": 2.5, "duty": 5.0},
    "id_to_tw": {"vat": 5.0, "income_tax": 0.0, "duty": 5.0},
}


def landed_cost(goods: float, freight: float, insurance_pct: float, duty_pct: float,
                vat_pct: float, income_tax_pct: float, other_fees: float) -> dict:
    insurance = (goods + freight) * insurance_pct / 100
    cif = goods + freight + insurance
    duty = cif * duty_pct / 100
    tax_base = cif + duty
    vat = tax_base * vat_pct / 100
    income_tax = tax_base * income_tax_pct / 100
    total = cif + duty + vat + income_tax + other_fees
    return {"goods": goods, "freight": freight, "insurance": insurance, "cif": cif, "duty": duty,
            "vat": vat, "income_tax": income_tax, "other_fees": other_fees, "total": total}


# term, full name, mode, seller pays main carriage, seller insures, risk-transfer key (i18n)
INCOTERMS = [
    ("EXW", "Ex Works", "any", False, False, "risk_exw"),
    ("FCA", "Free Carrier", "any", False, False, "risk_fca"),
    ("CPT", "Carriage Paid To", "any", True, False, "risk_cpt"),
    ("CIP", "Carriage and Insurance Paid To", "any", True, True, "risk_cpt"),
    ("DAP", "Delivered at Place", "any", True, False, "risk_dap"),
    ("DPU", "Delivered at Place Unloaded", "any", True, False, "risk_dpu"),
    ("DDP", "Delivered Duty Paid", "any", True, False, "risk_ddp"),
    ("FAS", "Free Alongside Ship", "sea", False, False, "risk_fas"),
    ("FOB", "Free on Board", "sea", False, False, "risk_fob"),
    ("CFR", "Cost and Freight", "sea", True, False, "risk_fob"),
    ("CIF", "Cost, Insurance and Freight", "sea", True, True, "risk_fob"),
]
