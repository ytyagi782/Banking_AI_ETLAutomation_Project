"""Layer 3 : Staging -> DWH  |  Merchants -> DimMerchant_Type1."""

import pytest
from validations import validations as v

LAYER = "StagingToDWH"
TABLE = "Merchants"


@pytest.mark.order(3)
@pytest.mark.staging_to_dwh
@pytest.mark.merchants
@pytest.mark.basic
class TestMerchantsBasic:

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


@pytest.mark.order(3)
@pytest.mark.staging_to_dwh
@pytest.mark.merchants
@pytest.mark.transformation
class TestMerchantsDwhLoad:

    def test_data_integrity(self):
        assert v.data_integrity_Validation(LAYER, TABLE)
