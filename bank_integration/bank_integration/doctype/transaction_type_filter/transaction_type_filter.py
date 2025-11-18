# Copyright (c) 2025, Akhilam Inc and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TransactionTypeFilter(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        filter_action: DF.Literal["Include", "Exclude"]
        transaction_type: DF.Literal["", "DISPUTE_REVERSAL", "DISPUTE_LOST", "REFUND", "REFUND_REVERSAL", "REFUND_FAILURE", "PAYMENT_RESERVE_HOLD", "PAYMENT_RESERVE_RELEASE", "PAYOUT", "PAYOUT_FAILURE", "PAYOUT_REVERSAL", "CONVERSION_SELL", "CONVERSION_BUY", "CONVERSION_REVERSAL", "DEPOSIT", "ADJUSTMENT", "FEE", "DD_CREDIT", "DD_DEBIT", "DC_CREDIT", "DC_DEBIT", "TRANSFER", "PAYMENT", "ISSUING_AUTHORISATION_HOLD", "ISSUING_AUTHORISATION_RELEASE", "ISSUING_CAPTURE", "ISSUING_REFUND", "PURCHASE", "PREPAYMENT", "PREPAYMENT_RELEASE"]
    # end: auto-generated types

    pass
