"""Layer 1 : Source -> PreStaging  |  Branches table."""

import pytest
from validations import validations as v

LAYER = "SourceToPreStaging"
TABLE = "Branches"


@pytest.mark.order(1)
@pytest.mark.source_to_prestaging
@pytest.mark.branches
@pytest.mark.basic
class TestBranchesBasic:

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
@pytest.mark.branches
@pytest.mark.datamove
class TestBranchesDirectMove:

    @pytest.mark.direct_move_check
    def test_direct_move(self):
        assert v.direct_move_Validation(LAYER, TABLE)
