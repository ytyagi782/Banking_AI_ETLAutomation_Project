"""Layer 2 : PreStaging -> Staging  |  Accounts table."""

import pytest
from validations import validations as v

LAYER = "PreStagingToStaging"
TABLE = "Accounts"


@pytest.mark.order(2)
@pytest.mark.prestaging_to_staging
@pytest.mark.accounts
@pytest.mark.basic
class TestAccountsBasic:

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


@pytest.mark.order(2)
@pytest.mark.prestaging_to_staging
@pytest.mark.accounts
@pytest.mark.transformation
class TestAccountsTransformation:
    """Transformation rules + integrity of accepted records vs source."""

    def test_transformation_rules(self):
        assert v.Transformation_Validation(LAYER, TABLE)

    def test_data_integrity(self):
        assert v.data_integrity_Validation(LAYER, TABLE)
