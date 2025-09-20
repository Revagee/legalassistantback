from pydantic import BaseModel
from typing import Literal
from src.database.plans import SubscriptionPlan


class SubscriptionRequest(BaseModel):
    subscription_plan: SubscriptionPlan
    phone: str
    card: str
    cvv: str
    card_exp_month: str
    card_exp_year: str


class CallbackRequest(BaseModel):
    data: str  # base64-encoded JSON string from LiqPay
    signature: str


class Plan(BaseModel):
    id: int
    name: str
    amount: float
    currency: str
    billing_period: str

class PlansResponse(BaseModel):
    plans: list[Plan]


class LiqPayCreateSubscriptionResponse(BaseModel):
    acq_id: int | None = None
    action: str | None = None
    agent_commission: float | None = None
    amount: float | None = None
    authcode_debit: str | None = None
    amount_bonus: float | None = None
    amount_credit: float | None = None
    amount_debit: float | None = None
    card_token: str | None = None
    commission_credit: float | None = None
    commission_debit: float | None = None
    create_date: str | None = None
    currency: str | None = None
    currency_credit: str | None = None
    currency_debit: str | None = None
    description: str | None = None
    end_date: str | None = None
    is_3ds: bool | None = None
    liqpay_order_id: str | None = None
    mpi_eci: int | None = None
    order_id: str | None = None
    payment_id: int | None = None
    paytype: str | None = None
    public_key: str | None = None
    receiver_commission: float | None = None
    result: str | None = None
    rrn_debit: str | None = None
    sender_bonus: float | None = None
    sender_card_bank: str | None = None
    sender_card_country: str | None = None
    sender_card_mask2: str | None = None
    sender_card_type: str | None = None
    sender_commission: float | None = None
    sender_first_name: str | None = None
    sender_last_name: str | None = None
    sender_phone: str | None = None
    status: Literal["error", "success", "reversed", "failure", "subscribed"]
    transaction_id: int | None = None
    type: str | None = None
    version: int | None = None


class LiqPayCallbackData(BaseModel):
    acq_id: int | None = None
    action: str | None = None
    agent_commission: float | None = None
    amount: float | None = None
    amount_bonus: float | None = None
    amount_credit: float | None = None
    amount_debit: float | None = None
    authcode_credit: str | None = None
    authcode_debit: str | None = None
    card_token: str | None = None
    commission_credit: float | None = None
    commission_debit: float | None = None
    completion_date: str | None = None
    create_date: str | None = None
    currency: str | None = None
    currency_credit: str | None = None
    currency_debit: str | None = None
    customer: str | None = None
    description: str | None = None
    end_date: str | None = None
    err_code: str | None = None
    err_description: str | None = None
    info: str | None = None
    ip: str | None = None
    is_3ds: bool | None = None
    liqpay_order_id: str | None = None
    mpi_eci: int | None = None
    order_id: str | None = None
    payment_id: int | None = None
    paytype: str | None = None
    public_key: str | None = None
    receiver_commission: float | None = None
    redirect_to: str | None = None
    refund_date_last: str | None = None
    rrn_credit: str | None = None
    rrn_debit: str | None = None
    sender_bonus: float | None = None
    sender_card_bank: str | None = None
    sender_card_country: str | None = None
    sender_card_mask2: str | None = None
    sender_card_type: str | None = None
    sender_commission: float | None = None
    sender_first_name: str | None = None
    sender_last_name: str | None = None
    sender_phone: str | None = None
    status: Literal[
        "error", "failure", "reversed", "subscribed", "success", "unsubscribed",
        "3ds_verify", "captcha_verify", "cvv_verify", "ivr_verify", "otp_verify",
        "password_verify", "phone_verify", "pin_verify", "receiver_verify",
        "sender_verify", "senderapp_verify", "wait_qr", "wait_sender",
        "cash_wait", "hold_wait", "invoice_wait", "prepared", "processing",
        "wait_accept", "wait_card", "wait_compensation", "wait_lc",
        "wait_reserve", "wait_secure"
    ]
    wait_reserve_status: str | None = None
    token: str | None = None
    type: str | None = None
    version: int | None = None
    err_erc: str | None = None
    product_category: str | None = None
    product_description: str | None = None
    product_name: str | None = None
    product_url: str | None = None
    refund_amount: float | None = None
    verifycode: str | None = None


class LiqPayCallbackResponse(BaseModel):
    data: str # base64 encoded json
    signature: str