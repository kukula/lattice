"""Tests for test_generator.models."""

from lattice.test_generator.models import (
    GenerationResult,
    TestCase,
    TestFile,
    TestType,
)


class TestTestCase:
    """Tests for TestCase dataclass."""

    def test_basic_transition_test_case(self):
        """Test creating a basic transition test case."""
        tc = TestCase(
            name="test_order_draft_to_submitted",
            test_type=TestType.POSITIVE_TRANSITION,
            entity="Order",
            description="Order transitions from draft to submitted",
            from_state="draft",
            to_state="submitted",
            trigger="customer.submit",
            guards=["line_items.count > 0"],
            effects=["reserve_inventory(line_items)"],
        )

        assert tc.name == "test_order_draft_to_submitted"
        assert tc.test_type == TestType.POSITIVE_TRANSITION
        assert tc.entity == "Order"
        assert tc.from_state == "draft"
        assert tc.to_state == "submitted"
        assert tc.trigger == "customer.submit"
        assert len(tc.guards) == 1
        assert len(tc.effects) == 1

    def test_happy_path_test_case(self):
        """Test creating a happy path test case."""
        tc = TestCase(
            name="test_order_lifecycle_to_delivered",
            test_type=TestType.HAPPY_PATH,
            entity="Order",
            description="Test path: draft → submitted → delivered",
            path=["draft", "submitted", "delivered"],
        )

        assert tc.test_type == TestType.HAPPY_PATH
        assert tc.path == ["draft", "submitted", "delivered"]
        assert tc.from_state is None  # Not required for happy path

    def test_invariant_test_case(self):
        """Test creating an invariant test case."""
        tc = TestCase(
            name="test_order_invariant_total_equals_sum",
            test_type=TestType.ENTITY_INVARIANT,
            entity="Order",
            description="Order total equals sum of line items",
            formal="total == line_items.sum(li => li.quantity * li.unit_price)",
        )

        assert tc.test_type == TestType.ENTITY_INVARIANT
        assert tc.formal is not None


class TestTestFile:
    """Tests for TestFile dataclass."""

    def test_empty_test_file(self):
        """Test creating an empty test file."""
        tf = TestFile(entity="Order", filename="test_order.py")

        assert tf.entity == "Order"
        assert tf.filename == "test_order.py"
        assert tf.test_cases == []

    def test_test_file_with_cases(self):
        """Test creating a test file with test cases."""
        tc1 = TestCase(
            name="test_1",
            test_type=TestType.POSITIVE_TRANSITION,
            entity="Order",
            description="Test 1",
        )
        tc2 = TestCase(
            name="test_2",
            test_type=TestType.NEGATIVE_TRANSITION,
            entity="Order",
            description="Test 2",
        )

        tf = TestFile(
            entity="Order",
            filename="test_order.py",
            test_cases=[tc1, tc2],
        )

        assert len(tf.test_cases) == 2


class TestGenerationResult:
    """Tests for GenerationResult dataclass."""

    def test_empty_result(self):
        """Test empty generation result."""
        result = GenerationResult()

        assert result.files == []
        assert result.total_tests == 0

    def test_total_tests_calculation(self):
        """Test that total_tests correctly sums across files."""
        tc1 = TestCase(
            name="test_1",
            test_type=TestType.POSITIVE_TRANSITION,
            entity="Order",
            description="Test 1",
        )
        tc2 = TestCase(
            name="test_2",
            test_type=TestType.POSITIVE_TRANSITION,
            entity="Order",
            description="Test 2",
        )
        tc3 = TestCase(
            name="test_3",
            test_type=TestType.SYSTEM_INVARIANT,
            entity="system",
            description="Test 3",
        )

        file1 = TestFile(
            entity="Order",
            filename="test_order.py",
            test_cases=[tc1, tc2],
        )
        file2 = TestFile(
            entity="system",
            filename="test_system.py",
            test_cases=[tc3],
        )

        result = GenerationResult(files=[file1, file2])

        assert result.total_tests == 3
        assert len(result.files) == 2


class TestTestType:
    """Tests for TestType enum."""

    def test_all_types_exist(self):
        """Verify all expected test types exist."""
        assert TestType.POSITIVE_TRANSITION
        assert TestType.NEGATIVE_TRANSITION
        assert TestType.HAPPY_PATH
        assert TestType.ENTITY_INVARIANT
        assert TestType.SYSTEM_INVARIANT

    def test_type_values(self):
        """Test test type string values."""
        assert TestType.POSITIVE_TRANSITION.value == "positive_transition"
        assert TestType.NEGATIVE_TRANSITION.value == "negative_transition"
        assert TestType.HAPPY_PATH.value == "happy_path"
        assert TestType.ENTITY_INVARIANT.value == "entity_invariant"
        assert TestType.SYSTEM_INVARIANT.value == "system_invariant"
