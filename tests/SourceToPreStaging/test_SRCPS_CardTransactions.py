"""Layer 1 : Source -> PreStaging  |  CardTransactions table."""

import pytest
from validations import validations as v

LAYER = "SourceToPreStaging"
TABLE = "CardTransactions"


@pytest.mark.order(1)
@pytest.mark.source_to_prestaging
@pytest.mark.cardtransactions
@pytest.mark.basic
class TestCardTransactionsBasic:

    @pytest.mark.metadata_check
    def test_metadata(self):
        assert v.Metadata_Validation(LAYER, TABLE)

    @pytest.mark.count_check
    def test_count(self):
        assert v.Count_Validation(LAYER, TABLE)

    @pytest.mark.duplicate_check
    def test_duplicates(self):
        assert v.Duplicate_Validation(LAYER, TABLE)

    @pytest.mark.null_check
    def test_nulls(self):
        assert v.Null_Validation(LAYER, TABLE)

    @pytest.mark.constraint_check
    def test_constraints(self):
        assert v.Constraint_Validation(LAYER, TABLE)


@pytest.mark.order(1)
@pytest.mark.source_to_prestaging
@pytest.mark.cardtransactions
@pytest.mark.datamove
class TestCardTransactionsDirectMove:

    @pytest.mark.direct_move_check
    def test_direct_move(self):
        assert v.direct_move_Validation(LAYER, TABLE)
