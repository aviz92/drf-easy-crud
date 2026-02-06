class TestDummy:
    def test_dummy1(self) -> None:
        assert 1 == 1  # pylint: disable=R0133,R0124


def test_dummy2() -> None:
    assert 1 == 1  # pylint: disable=R0133,R0124
