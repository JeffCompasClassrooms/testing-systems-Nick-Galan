import os
import pytest
from mydb import MyDB

TEST_FILE = "test_db_file.pkl"


def describe_mydb():

    @pytest.fixture
    def db():
        db = MyDB(TEST_FILE)
        yield db
        if os.path.isfile(TEST_FILE):
            os.remove(TEST_FILE)

    def describe_init():
        def it_creates_the_database_file_on_disk(db):
            assert os.path.isfile(TEST_FILE)

        def it_initializes_with_an_empty_list(db):
            assert db.loadStrings() == []

    def describe_loadStrings():
        def it_reads_back_strings_saved_to_disk(db):
            data = ["alpha", "beta"]
            db.saveStrings(data)
            loaded = db.loadStrings()
            assert loaded == data

    def describe_saveStrings():
        def it_overwrites_existing_contents(db):
            db.saveStrings(["first"])
            db.saveStrings(["second", "third"])
            loaded = db.loadStrings()
            assert loaded == ["second", "third"]

    def describe_saveString():
        def it_appends_a_single_string_to_empty_db(db):
            db.saveString("one")
            assert db.loadStrings() == ["one"]

        def it_appends_multiple_strings_in_order(db):
            db.saveString("one")
            db.saveString("two")
            db.saveString("three")
            assert db.loadStrings() == ["one", "two", "three"]
