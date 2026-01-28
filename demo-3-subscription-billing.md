# Demo 3: Subscription & Billing

## What This Demo Shows

- **Temporal constraints** - billing cycles, trial periods, grace periods
- **Plan transitions** - upgrades, downgrades, proration
- **Complex invariants** - financial consistency, no double-charging
- **Event-driven state changes** - payment success/failure, renewal triggers

---

## The Model

```yaml
# subscription_model.yaml

entities:
  Account:
    attributes:
      - name: email
        type: string
        unique: true
      - name: created_at
        type: datetime
      - name: timezone
        type: string
        default: "UTC"
    relationships:
      - has_many: Subscription
      - has_many: PaymentMethod
      - has_many: Invoice
    
    invariants:
      - description: "Account must have at least one payment method to have active subscription"

  Plan:
    attributes:
      - name: name
        type: string
        unique: true
      - name: price_monthly
        type: decimal
      - name: price_yearly
        type: decimal
      - name: features
        type: list[string]
      - name: tier
        type: integer
        description: "For upgrade/downgrade logic: higher = more features"
      - name: trial_days
        type: integer
        default: 0
      - name: active
        type: boolean
        default: true
    
    invariants:
      - description: "Yearly price should be less than 12x monthly (discount)"
        formal: "price_yearly < price_monthly * 12"
      - description: "Tier must be unique across plans"

  Subscription:
    belongs_to: Account
    belongs_to: Plan
    has_many: Invoice
    
    attributes:
      - name: billing_cycle
        type: enum[monthly, yearly]
      - name: current_period_start
        type: datetime
      - name: current_period_end
        type: datetime
      - name: trial_end
        type: datetime
        optional: true
      - name: cancel_at_period_end
        type: boolean
        default: false
      - name: canceled_at
        type: datetime
        optional: true
    
    states:
      - name: trialing
        initial: true
        condition: "trial_end.present && now < trial_end"
      - name: active
      - name: past_due
        description: "Payment failed, in grace period"
      - name: unpaid
        description: "Grace period expired, service limited"
      - name: canceled
        terminal: true
      - name: expired
        terminal: true
        description: "Trial ended without conversion"
    
    transitions:
      - from: trialing
        to: active
        trigger: trial.convert
        requires:
          - account.has_valid_payment_method
        effects:
          - create_invoice(amount: prorated_amount)
          - charge_payment_method
      
      - from: trialing
        to: expired
        trigger: trial.end
        requires:
          - not account.has_valid_payment_method
      
      - from: trialing
        to: canceled
        trigger: customer.cancel
      
      - from: active
        to: active
        trigger: billing.renew
        requires:
          - not cancel_at_period_end
        effects:
          - create_invoice(amount: plan_price)
          - advance_period(by: billing_cycle)
          - charge_payment_method
      
      - from: active
        to: past_due
        trigger: payment.failed
        effects:
          - schedule_retry(in: 3.days)
          - notify_customer(type: payment_failed)
      
      - from: active
        to: canceled
        trigger: billing.renew
        requires:
          - cancel_at_period_end
      
      - from: past_due
        to: active
        trigger: payment.success
      
      - from: past_due
        to: unpaid
        trigger: grace_period.expired
        effects:
          - restrict_service
          - notify_customer(type: service_restricted)
      
      - from: unpaid
        to: active
        trigger: payment.success
        effects:
          - restore_service
      
      - from: unpaid
        to: canceled
        trigger: unpaid_period.expired
        effects:
          - write_off_debt
      
      - from: [active, past_due, unpaid]
        to: canceled
        trigger: admin.cancel
        effects:
          - calculate_final_invoice
          - refund_if_applicable
    
    plan_changes:
      upgrade:
        description: "Moving to higher tier plan"
        condition: "new_plan.tier > current_plan.tier"
        timing: immediate
        proration: credit_remaining_then_charge_new
      
      downgrade:
        description: "Moving to lower tier plan"
        condition: "new_plan.tier < current_plan.tier"
        timing: end_of_period
        proration: none
      
      cycle_change:
        description: "Monthly ↔ Yearly"
        timing: end_of_period
        proration: none
    
    invariants:
      - description: "current_period_end > current_period_start"
      - description: "Only one active/trialing subscription per account"
      - description: "Cannot downgrade during trial"
      - description: "Past due period max 14 days before unpaid"
      - description: "Unpaid period max 30 days before canceled"
    
    unclear:
      - "Proration calculation when upgrade mid-cycle - daily or exact?"
      - "What if payment method expires during active subscription?"
      - "Can paused state exist? (voluntary hold without canceling)"
      - "Team plans: how to handle seat count changes?"

  Invoice:
    belongs_to: Account
    belongs_to: Subscription
    has_many: LineItem
    
    attributes:
      - name: amount
        type: decimal
      - name: status
        type: enum[draft, open, paid, void, uncollectible]
      - name: due_date
        type: datetime
      - name: paid_at
        type: datetime
        optional: true
      - name: period_start
        type: datetime
      - name: period_end
        type: datetime
    
    states:
      - name: draft
        initial: true
      - name: open
      - name: paid
        terminal: true
      - name: void
        terminal: true
      - name: uncollectible
        terminal: true
    
    transitions:
      - from: draft
        to: open
        trigger: invoice.finalize
      
      - from: open
        to: paid
        trigger: payment.success
        effects:
          - record_payment
          - send_receipt
      
      - from: open
        to: void
        trigger: admin.void
        requires:
          - not partially_paid
      
      - from: open
        to: uncollectible
        trigger: collection.failed
        effects:
          - write_off
    
    invariants:
      - description: "Amount must equal sum of line items"
        formal: "amount == line_items.sum(li => li.amount)"
      - description: "paid_at only set when status is paid"
      - description: "Cannot void a paid invoice"

  PaymentMethod:
    belongs_to: Account
    
    attributes:
      - name: type
        type: enum[card, bank, paypal]
      - name: last_four
        type: string
      - name: expires_at
        type: datetime
        optional: true
      - name: is_default
        type: boolean
    
    invariants:
      - description: "Exactly one default payment method per account"
      - description: "Cannot delete payment method with open invoices"

temporal_rules:
  trial_conversion:
    description: "Auto-convert or expire at trial end"
    trigger: "subscription.trial_end reached"
    action: |
      if account.has_valid_payment_method:
        subscription.convert()
      else:
        subscription.expire()
  
  renewal:
    description: "Charge and renew at period end"
    trigger: "subscription.current_period_end reached"
    condition: "subscription.state == active"
    action: "subscription.renew()"
  
  grace_period:
    description: "Move to unpaid after 14 days past_due"
    trigger: "14 days after entering past_due"
    action: "subscription.expire_grace_period()"
  
  payment_retry:
    description: "Retry failed payments"
    schedule: "days 3, 5, 7 after failure"
    action: "attempt_payment(subscription)"

system_invariants:
  - description: "Revenue recognized = sum of paid invoices"
  - description: "No double-charging: one invoice per subscription per period"
  - description: "Refunds cannot exceed total paid"
  - description: "Active subscription count = count where state in [trialing, active, past_due, unpaid]"
```

---

## Expected Structural Validation Output

```
$ intent validate subscription_model.yaml

ERRORS:
  (none)

WARNINGS:
  ⚠ Subscription state 'unpaid' allows transition to 'active' on payment.success
    but also to 'canceled' on unpaid_period.expired. 
    What if payment succeeds on the same day as expiry?
  
  ⚠ Plan.trial_days can be 0, but Subscription initial state is 'trialing'.
    How does a no-trial subscription start?
  
  ⚠ Invoice state 'draft' only transitions to 'open', but invoices are 
    created in effects. Are they auto-finalized?

UNCLEAR (4 items):
  ? "Proration calculation when upgrade mid-cycle"
  ? "What if payment method expires during active subscription"
  ? "Can paused state exist?"
  ? "Team plans: seat count changes"

TEMPORAL ANALYSIS:
  ✓ trial_conversion: triggers at trial_end
  ✓ renewal: triggers at current_period_end
  ✓ grace_period: triggers 14 days after past_due entry
  ⚠ payment_retry: schedule defined but retry count limit not specified
```

---

## Expected Semantic Validation Output

```
$ intent analyze subscription_model.yaml

POTENTIAL ISSUES:

CONTRADICTION:
  Invariant: "Only one active/trialing subscription per account"
  But plan_changes.upgrade has timing=immediate, which would create 
  overlap if implemented as new subscription.
  → Recommendation: Clarify if upgrade mutates existing or creates new subscription.

MISSING:
  No handling for payment method expiration during active subscription.
  If card expires mid-cycle, what triggers the update request?
  → Recommendation: Add payment_method.expiring_soon event and notification.

MISSING:
  Plan can be set to active=false (deprecated), but no handling for 
  existing subscriptions on deprecated plans.
  → Recommendation: Add migration path or grandfathering rules.

EDGE_CASE:
  Downgrade scheduled for end_of_period, but customer goes past_due 
  before period ends. Does downgrade still apply?
  → Recommendation: Define interaction between scheduled changes and payment states.

EDGE_CASE:
  Account has multiple payment methods, default fails, retry uses default again.
  Should retry cycle through available methods?

AMBIGUOUS:
  "refund_if_applicable" in admin.cancel effects. What makes a refund applicable?
  Prorated unused time? Full refund? Depends on reason?

TEMPORAL_CONFLICT:
  grace_period rule says 14 days, invariant says "Past due period max 14 days".
  These should match but are defined in two places.
  → Recommendation: Single source of truth for grace period duration.
```

---

## Generated Test Cases

```python
# test_subscription_lifecycle.py (generated)

class TestTrialFlow:
    """Trial period handling"""
    
    def test_trial_converts_with_payment_method(self):
        account = create_account(payment_methods=[valid_card])
        sub = create_subscription(account=account, state="trialing", trial_end=now)
        
        trigger_trial_end(sub)
        
        assert sub.state == "active"
        assert sub.invoices.count() == 1
    
    def test_trial_expires_without_payment_method(self):
        account = create_account(payment_methods=[])
        sub = create_subscription(account=account, state="trialing", trial_end=now)
        
        trigger_trial_end(sub)
        
        assert sub.state == "expired"
        assert sub.invoices.count() == 0
    
    def test_customer_can_cancel_during_trial(self):
        sub = create_subscription(state="trialing")
        
        sub.cancel(by="customer")
        
        assert sub.state == "canceled"
        assert sub.canceled_at is not None


class TestRenewal:
    """Billing cycle renewal"""
    
    def test_active_subscription_renews(self):
        sub = create_subscription(
            state="active",
            billing_cycle="monthly",
            current_period_end=now
        )
        
        trigger_renewal(sub)
        
        assert sub.state == "active"
        assert sub.current_period_start == now
        assert sub.current_period_end == now + timedelta(days=30)
        assert sub.invoices.last().amount == sub.plan.price_monthly
    
    def test_cancel_at_period_end_cancels_on_renewal(self):
        sub = create_subscription(
            state="active",
            cancel_at_period_end=True,
            current_period_end=now
        )
        
        trigger_renewal(sub)
        
        assert sub.state == "canceled"
        assert sub.invoices.last() is None  # no new invoice


class TestPaymentFailure:
    """Past due and recovery flow"""
    
    def test_payment_failure_moves_to_past_due(self):
        sub = create_subscription(state="active")
        
        simulate_payment_failure(sub)
        
        assert sub.state == "past_due"
    
    def test_payment_success_recovers_from_past_due(self):
        sub = create_subscription(state="past_due")
        
        simulate_payment_success(sub)
        
        assert sub.state == "active"
    
    def test_grace_period_expiry_moves_to_unpaid(self):
        sub = create_subscription(state="past_due", past_due_since=days_ago(14))
        
        trigger_grace_period_expiry(sub)
        
        assert sub.state == "unpaid"
    
    def test_unpaid_expiry_cancels(self):
        sub = create_subscription(state="unpaid", unpaid_since=days_ago(30))
        
        trigger_unpaid_expiry(sub)
        
        assert sub.state == "canceled"
    
    def test_payment_success_recovers_from_unpaid(self):
        sub = create_subscription(state="unpaid")
        
        simulate_payment_success(sub)
        
        assert sub.state == "active"


class TestPlanChanges:
    """Upgrade and downgrade flows"""
    
    def test_upgrade_immediate(self):
        basic_plan = create_plan(name="Basic", tier=1, price_monthly=10)
        pro_plan = create_plan(name="Pro", tier=2, price_monthly=20)
        
        sub = create_subscription(plan=basic_plan, state="active", days_into_period=15)
        
        sub.change_plan(pro_plan)
        
        assert sub.plan == pro_plan
        assert sub.invoices.last().amount < 20  # prorated
    
    def test_downgrade_at_period_end(self):
        pro_plan = create_plan(name="Pro", tier=2, price_monthly=20)
        basic_plan = create_plan(name="Basic", tier=1, price_monthly=10)
        
        sub = create_subscription(plan=pro_plan, state="active")
        original_period_end = sub.current_period_end
        
        sub.change_plan(basic_plan)
        
        assert sub.plan == pro_plan  # not changed yet
        assert sub.scheduled_plan_change == basic_plan
        
        trigger_renewal(sub)
        
        assert sub.plan == basic_plan
        assert sub.invoices.last().amount == 10
    
    def test_cannot_downgrade_during_trial(self):
        pro_plan = create_plan(tier=2)
        basic_plan = create_plan(tier=1)
        
        sub = create_subscription(plan=pro_plan, state="trialing")
        
        with pytest.raises(InvalidPlanChange):
            sub.change_plan(basic_plan)


class TestInvoiceInvariants:
    """Invoice consistency"""
    
    def test_invoice_amount_equals_line_items(self):
        invoice = create_invoice(line_items=[
            LineItem(description="Pro Plan - Monthly", amount=Decimal("20.00")),
            LineItem(description="Additional Seat", amount=Decimal("5.00")),
        ])
        
        assert invoice.amount == Decimal("25.00")
    
    def test_cannot_void_paid_invoice(self):
        invoice = create_invoice(status="paid")
        
        with pytest.raises(InvalidTransition):
            invoice.void()
    
    def test_one_invoice_per_period(self):
        sub = create_subscription(state="active")
        period_start = sub.current_period_start
        
        trigger_renewal(sub)
        
        invoices_for_period = sub.invoices.filter(period_start=period_start)
        assert invoices_for_period.count() == 1


class TestSystemInvariants:
    """Cross-entity consistency"""
    
    def test_no_double_charging(self):
        sub = create_subscription(state="active", current_period_end=now)
        
        trigger_renewal(sub)
        trigger_renewal(sub)  # accidentally called twice
        
        # Should only create one invoice for the period
        assert sub.invoices.filter(period_start=now).count() == 1
    
    def test_refund_cannot_exceed_paid(self):
        sub = create_subscription()
        total_paid = sum(i.amount for i in sub.invoices.filter(status="paid"))
        
        with pytest.raises(InvalidRefund):
            sub.refund(amount=total_paid + 1)
```

---

## State Machine Visualization

```
                                    ┌────────────────┐
                                    │                │
                         convert    │                ▼
┌──────────┐ ─────────────────────▶ │ ┌────────────────┐
│ trialing │                        │ │     active     │◀─────────┐
└──────────┘                        │ └────────────────┘          │
     │                              │        │    ▲               │
     │ trial.end (no payment)       │        │    │               │
     │                              │        │    │ payment       │
     ▼                              │        │    │ success       │
┌──────────┐                        │        │    │               │
│ expired  │                        │        ▼    │               │
└──────────┘                        │ ┌────────────────┐          │
                                    │ │   past_due    │──────────┘
     ┌──────────────────────────────┘ └────────────────┘
     │                                       │
     │ customer.cancel                       │ grace_period
     │ (from any non-terminal)               │ expired
     │                                       ▼
     │                                ┌────────────────┐
     │                                │     unpaid     │
     │                                └────────────────┘
     │                                       │
     │                                       │ unpaid_period
     │                                       │ expired
     ▼                                       ▼
┌─────────────────────────────────────────────────────┐
│                     canceled                         │
└─────────────────────────────────────────────────────┘
```

---

## Temporal Rules Visualization

```
Timeline for a subscription lifecycle:

Day 0          Day 14         Day 28         Day 42         Day 56
  │              │              │              │              │
  │   TRIAL      │    ACTIVE    │   PAST_DUE   │    UNPAID    │  CANCELED
  │   (14 days)  │   (varies)   │  (14 days)   │  (30 days)   │
  │              │              │              │              │
  └──────────────┴──────────────┴──────────────┴──────────────┘
        │              │              │              │
    trial_end      renew        payment      grace_period    unpaid
    (convert or    (charge)     failed       expired         expired
     expire)                    │
                                │
                         Retry schedule:
                         Day 31: retry 1
                         Day 33: retry 2  
                         Day 35: retry 3
```

---

## What This Demo Validates

| Capability | Demonstrated |
|------------|--------------|
| Temporal constraints | ✓ Trial periods, grace periods, retry schedules |
| Event-driven transitions | ✓ payment.success, payment.failed, period.end |
| Complex state conditions | ✓ State depends on time (trialing while now < trial_end) |
| Plan change rules | ✓ Upgrade immediate, downgrade at period end |
| Proration logic | ✓ credit_remaining_then_charge_new |
| Financial invariants | ✓ No double-charging, refunds ≤ paid |
| Multi-entity consistency | ✓ Subscription ↔ Invoice ↔ PaymentMethod |
| Scheduled future changes | ✓ cancel_at_period_end, scheduled_plan_change |
| Grace period handling | ✓ past_due → unpaid → canceled flow |
| Test generation | ✓ Trial, renewal, failure recovery, plan changes |
