import pytest
from main.domain.track_history import History

class DumbObject:
    def __init__(self):
        self.collection_1 = list()
        self.collection_2 = set()

    def add_to_collection_1(self, new):
        self.collection_1.append(new)
    
    def add_to_collection_2(self, new):
        self.collection_2.add(new)

@History("collection_1", save=False)
class TrackSingleAttribute(DumbObject):
    pass

@History("all", save=False)
class TrackAll(DumbObject):
    pass


def test_history_specific_attribute():
    obj = TrackSingleAttribute()
    obj.add_to_collection_1("hey, I am new here.")
    new = obj.collect_new
    print(new)
    assert new == [(("collection_1", ["hey, I am new here."]))]
    assert obj.collect_new == []
