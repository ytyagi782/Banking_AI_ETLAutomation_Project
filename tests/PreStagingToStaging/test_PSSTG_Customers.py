"""Layer 2 : PreStaging -> Staging  |  Customers table."""

import pytest
from validations import validations as v

LAYER = "PreStagingToStaging"
TABLE = "Customers"


@pytest.mark.order(2)
@pytest.mark.prestaging_to_staging
@pytest.mark.customers
@pytest.mark.basic
class TestCustomersBasic:

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
@pytest.mark.customers
@pytest.mark.transformation
class TestCustomersTransformation:

    def test_transformation_rules(self):
        assert v.Transformation_Validation(LAYER, TABLE)

    def test_data_integrity(self):
        assert v.data_integrity_Validation(LAYER, TABLE)
