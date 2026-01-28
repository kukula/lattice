# Demo 2: Order Lifecycle (E-commerce)

## What This Demo Shows

- **State machine validation** - reachability, terminal states, transition completeness
- **Cross-entity constraints** - inventory, payment, shipping dependencies
- **Invariant verification** - totals, consistency rules
- **Complex transition guards** - multi-condition requirements

---

## The Model

```yaml
# order_model.yaml

entities:
  Customer:
    attributes:
      - name: email
        type: string
        unique: true
      - name: default_payment_method
        type: reference[PaymentMethod]
        optional: true
    relationships:
      - has_many: Order
      - has_many: PaymentMethod

  PaymentMethod:
    belongs_to: Customer
    attributes:
      - name: type
        type: enum[card, bank, wallet]
      - name: last_four
        type: string
      - name: expired
        type: boolean
    
    invariants:
      - description: "Cannot use expired payment method"

  Order:
    belongs_to: Customer
    has_many: LineItem
    has_one: Shipment
    
    attributes:
      - name: total
        type: decimal
      - name: created_at
        type: datetime
      - name: notes
        type: string
        optional: true
    
    states:
      - name: draft
        initial: true
      - name: submitted
      - name: payment_pending
      - name: paid
      - name: processing
      - name: shipped
      - name: delivered
        terminal: true
      - name: cancelled
        terminal: true
      - name: refunded
        terminal: true
    
    transitions:
      - from: draft
        to: submitted
        trigger: customer.submit
        requires:
          - line_items.count > 0
          - line_items.all(li => li.product.in_stock)
        effects:
          - reserve_inventory(line_items)
      
      - from: submitted
        to: payment_pending
        trigger: system.process_payment
        requires:
          - customer.has_valid_payment_method
      
      - from: payment_pending
        to: paid
        trigger: payment.success
        effects:
          - record_payment(amount: total)
      
      - from: payment_pending
        to: submitted
        trigger: payment.failed
        effects:
          - notify_customer(reason: payment_failed)
      
      - from: paid
        to: processing
        trigger: warehouse.acknowledge
      
      - from: processing
        to: shipped
        trigger: warehouse.ship
        requires:
          - shipment.tracking_number.present
        effects:
          - deduct_inventory(line_items)
          - notify_customer(tracking: shipment.tracking_number)
      
      - from: shipped
        to: delivered
        trigger: carrier.confirm_delivery
      
      # Cancellation paths
      - from: [draft, submitted]
        to: cancelled
        trigger: customer.cancel
        effects:
          - release_inventory(line_items)
      
      - from: [payment_pending]
        to: cancelled
        trigger: customer.cancel
        effects:
          - cancel_payment_if_pending
          - release_inventory(line_items)
      
      - from: paid
        to: cancelled
        trigger: admin.cancel
        requires:
          - not shipped
        effects:
          - initiate_refund(amount: total)
          - release_inventory(line_items)
      
      # Refund path
      - from: [paid, processing]
        to: refunded
        trigger: admin.refund
        effects:
          - process_refund(amount: total)
          - release_inventory(line_items)
      
      - from: delivered
        to: refunded
        trigger: admin.refund
        requires:
          - days_since_delivery <= 30
        effects:
          - process_refund(amount: total)
          - create_return_shipment
    
    invariants:
      - description: "Order total equals sum of line item subtotals"
        formal: "total == line_items.sum(li => li.quantity * li.unit_price)"
      
      - description: "Cannot ship without payment"
        formal: "state == shipped => payment.recorded"
      
      - description: "Delivered orders cannot be cancelled, only refunded"
      
      - description: "Inventory is reserved from submit until ship or cancel"
    
    unclear:
      - "Partial shipment: what if only some items in stock?"
      - "Partial refund: can we refund individual line items?"
      - "What if carrier loses package? delivered vs lost state?"
      - "Backorder: hold submitted until inventory available?"

  LineItem:
    belongs_to: Order
    belongs_to: Product
    
    attributes:
      - name: quantity
        type: integer
        min: 1
      - name: unit_price
        type: decimal
        description: "Price at time of adding to order"
    
    computed:
      - name: subtotal
        formula: "quantity * unit_price"
    
    invariants:
      - description: "Quantity must be positive"
      - description: "Unit price captured at add time, not affected by product price changes"

  Product:
    has_many: LineItem
    
    attributes:
      - name: sku
        type: string
        unique: true
      - name: name
        type: string
      - name: price
        type: decimal
      - name: inventory_count
        type: integer
      - name: reserved_count
        type: integer
        default: 0
    
    computed:
      - name: available
        formula: "inventory_count - reserved_count"
      - name: in_stock
        formula: "available > 0"
    
    invariants:
      - description: "Inventory cannot go negative"
        formal: "inventory_count >= 0"
      - description: "Reserved cannot exceed inventory"
        formal: "reserved_count <= inventory_count"
      - description: "Available is always non-negative"
        formal: "available >= 0"

  Shipment:
    belongs_to: Order
    
    attributes:
      - name: carrier
        type: string
      - name: tracking_number
        type: string
      - name: shipped_at
        type: datetime
      - name: delivered_at
        type: datetime
        optional: true
    
    states:
      - name: pending
        initial: true
      - name: in_transit
      - name: delivered
        terminal: true
      - name: returned
        terminal: true

system_invariants:
  - description: "Total reserved inventory equals sum of reserved across submitted/paid/processing orders"
  - description: "No overselling: cannot submit order if available inventory insufficient"
  - description: "Financial consistency: sum of payments = sum of paid order totals"
```

---

## Expected Structural Validation Output

```
$ intent validate order_model.yaml

ERRORS:
  (none)

WARNINGS:
  ⚠ State 'processing' has only one outbound transition (to 'shipped')
    Consider: what if processing fails?
  
  ⚠ No transition from 'shipped' to 'cancelled'
    If carrier returns undeliverable, how is this handled?
  
  ⚠ Shipment entity has states but no transitions defined
    State machine incomplete.

UNCLEAR (4 items):
  ? "Partial shipment: what if only some items in stock?"
  ? "Partial refund: can we refund individual line items?"
  ? "What if carrier loses package?"
  ? "Backorder: hold submitted until inventory available?"

STATE MACHINE ANALYSIS (Order):
  Initial: draft
  Terminal: delivered, cancelled, refunded
  All states reachable: ✓
  Coverage: 9/9 states have at least one inbound transition
```

---

## Expected Semantic Validation Output

```
$ intent analyze order_model.yaml

POTENTIAL ISSUES:

MISSING:
  No transition handles 'payment timeout'. What if payment_pending 
  never receives success or failure?
  → Recommendation: Add timeout transition back to submitted or to cancelled.

MISSING:
  Shipment has states [pending, in_transit, delivered, returned] but 
  no transitions. How does shipment move between states?
  → Recommendation: Define shipment state machine or link to Order transitions.

EDGE_CASE:
  Order in 'paid' state, admin cancels, refund initiated.
  But what if refund fails? Order stuck in cancelled with no money returned.
  → Recommendation: Add refund_failed handling or refund_pending state.

EDGE_CASE:
  Customer submits order, inventory reserved. Customer never completes payment.
  Inventory reserved indefinitely?
  → Recommendation: Add reservation timeout or expiry.

AMBIGUOUS:
  'release_inventory' appears in multiple transitions. 
  Is it idempotent? What if called twice?

CONTRADICTION:
  Invariant says "Delivered orders cannot be cancelled, only refunded"
  but there's a transition delivered → refunded with 30-day limit.
  After 30 days, delivered order has no valid transitions but isn't terminal.
  → Recommendation: Mark delivered as terminal or add post-30-day handling.
```

---

## Generated Test Cases

```python
# test_order_lifecycle.py (generated)

class TestHappyPath:
    """Positive cases: valid order flow works"""
    
    def test_complete_order_flow(self):
        """draft → submitted → payment_pending → paid → processing → shipped → delivered"""
        order = create_order(state="draft", line_items=[item])
        
        order.submit()
        assert order.state == "submitted"
        
        order.process_payment()
        assert order.state == "payment_pending"
        
        simulate_payment_success(order)
        assert order.state == "paid"
        
        order.warehouse_acknowledge()
        assert order.state == "processing"
        
        order.ship(tracking="TRACK123")
        assert order.state == "shipped"
        
        simulate_delivery_confirmation(order)
        assert order.state == "delivered"


class TestTransitionGuards:
    """Negative cases: guards prevent invalid transitions"""
    
    def test_cannot_submit_empty_order(self):
        order = create_order(state="draft", line_items=[])
        with pytest.raises(InvalidTransition):
            order.submit()
    
    def test_cannot_submit_with_out_of_stock_item(self):
        product = create_product(inventory_count=0)
        order = create_order(state="draft", line_items=[LineItem(product=product)])
        with pytest.raises(InvalidTransition):
            order.submit()
    
    def test_cannot_ship_without_tracking(self):
        order = create_order(state="processing")
        with pytest.raises(InvalidTransition):
            order.ship(tracking=None)
    
    def test_cannot_refund_delivered_after_30_days(self):
        order = create_order(state="delivered", delivered_at=days_ago(31))
        with pytest.raises(InvalidTransition):
            order.refund()


class TestCancellation:
    """Cancellation paths from various states"""
    
    def test_customer_can_cancel_draft(self):
        order = create_order(state="draft")
        order.cancel(by="customer")
        assert order.state == "cancelled"
    
    def test_customer_can_cancel_submitted(self):
        order = create_order(state="submitted")
        order.cancel(by="customer")
        assert order.state == "cancelled"
    
    def test_customer_cannot_cancel_paid(self):
        order = create_order(state="paid")
        with pytest.raises(InvalidTransition):
            order.cancel(by="customer")
    
    def test_admin_can_cancel_paid(self):
        order = create_order(state="paid")
        order.cancel(by="admin")
        assert order.state == "cancelled"
    
    def test_cannot_cancel_shipped(self):
        order = create_order(state="shipped")
        with pytest.raises(InvalidTransition):
            order.cancel(by="admin")


class TestInventoryInvariants:
    """Inventory consistency across order lifecycle"""
    
    def test_submit_reserves_inventory(self):
        product = create_product(inventory_count=10, reserved_count=0)
        order = create_order(line_items=[LineItem(product=product, quantity=3)])
        
        order.submit()
        
        assert product.reserved_count == 3
        assert product.available == 7
    
    def test_cancel_releases_inventory(self):
        product = create_product(inventory_count=10, reserved_count=3)
        order = create_order(state="submitted", line_items=[LineItem(product=product, quantity=3)])
        
        order.cancel()
        
        assert product.reserved_count == 0
        assert product.available == 10
    
    def test_ship_deducts_inventory(self):
        product = create_product(inventory_count=10, reserved_count=3)
        order = create_order(state="processing", line_items=[LineItem(product=product, quantity=3)])
        
        order.ship(tracking="TRACK123")
        
        assert product.inventory_count == 7
        assert product.reserved_count == 0
    
    def test_cannot_oversell(self):
        product = create_product(inventory_count=2)
        order = create_order(line_items=[LineItem(product=product, quantity=5)])
        
        with pytest.raises(InvalidTransition):
            order.submit()


class TestPaymentFailure:
    """Payment failure handling"""
    
    def test_payment_failed_returns_to_submitted(self):
        order = create_order(state="payment_pending")
        simulate_payment_failure(order)
        assert order.state == "submitted"
    
    def test_customer_notified_on_payment_failure(self, mock_notifications):
        order = create_order(state="payment_pending")
        simulate_payment_failure(order)
        mock_notifications.assert_called_with(
            customer=order.customer,
            reason="payment_failed"
        )


class TestInvariants:
    """Order invariants hold across all operations"""
    
    def test_total_equals_line_item_sum(self):
        order = create_order(line_items=[
            LineItem(quantity=2, unit_price=Decimal("10.00")),
            LineItem(quantity=1, unit_price=Decimal("25.00")),
        ])
        assert order.total == Decimal("45.00")
    
    def test_total_unchanged_when_product_price_changes(self):
        product = create_product(price=Decimal("10.00"))
        order = create_order(line_items=[LineItem(product=product, quantity=2)])
        original_total = order.total
        
        product.price = Decimal("15.00")
        
        assert order.total == original_total  # captured at add time
```

---

## State Machine Visualization

```
                    ┌─────────────────────────────────────────┐
                    │                                         │
                    ▼                                         │
┌───────┐     ┌───────────┐     ┌─────────────────┐     ┌─────────┐
│ draft │────▶│ submitted │────▶│ payment_pending │────▶│  paid   │
└───────┘     └───────────┘     └─────────────────┘     └─────────┘
    │              │                    │                    │
    │              │                    │ payment.failed     │
    │              │                    └────────────────────┘
    │              │                                         │
    ▼              ▼                                         ▼
┌───────────────────────┐                            ┌─────────────┐
│      cancelled        │◀───────────────────────────│ processing  │
└───────────────────────┘         admin.cancel       └─────────────┘
                                                           │
                                                           ▼
                                  ┌──────────┐       ┌───────────┐
                                  │ refunded │◀──────│  shipped  │
                                  └──────────┘       └───────────┘
                                       ▲                   │
                                       │                   ▼
                                       │             ┌───────────┐
                                       └─────────────│ delivered │
                                         (≤30 days)  └───────────┘
```

---

## What This Demo Validates

| Capability | Demonstrated |
|------------|--------------|
| State machine: reachability | ✓ All states reachable from draft |
| State machine: terminals | ✓ delivered, cancelled, refunded marked terminal |
| State machine: completeness | ✓ Missing processing failure transition detected |
| Cross-entity constraints | ✓ Inventory reservation/release across states |
| Transition guards | ✓ Multi-condition requirements |
| Effects tracking | ✓ Side effects documented per transition |
| Invariant verification | ✓ Total calculation, inventory bounds |
| Temporal constraints | ✓ 30-day refund window |
| Test generation | ✓ Happy path, guards, cancellation, invariants |
