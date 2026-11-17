import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from tag_parser import parse_list_parameter  # noqa: E402
from tag_parser import parse_tags  # noqa: E402
from tag_parser import sanitize_key_segment  # noqa: E402
from tag_parser import split_item  # noqa: E402
from tag_parser import split_items  # noqa: E402


def test_single_tag():
    assert parse_tags("[<Environment-Production>]") == {"Environment": ["Production"]}


def test_multiple_categories_and_whitespace():
    raw = "[<Environment-Production>, <Backup-Gold>,<Owner-Team Ops>]"
    assert parse_tags(raw) == {
        "Environment": ["Production"],
        "Backup": ["Gold"],
        "Owner": ["Team Ops"],
    }


def test_multiple_tags_same_category_sorted_unique():
    raw = "[<App-Web>, <App-DB>, <App-Web>]"
    assert parse_tags(raw) == {"App": ["DB", "Web"]}


def test_empty_values():
    for raw in [None, "", "[]", "none", "None", "[ ]"]:
        assert parse_tags(raw) == {}


def test_split_first_and_last():
    assert split_item("Backup-Policy-Gold") == ("Backup", "Policy-Gold")
    assert split_item("Backup-Policy-Gold", split_mode="last") == (
        "Backup-Policy",
        "Gold",
    )


def test_known_categories_win_longest_match():
    known = ["Backup", "Backup-Policy"]
    assert split_item("Backup-Policy-Gold", known) == ("Backup-Policy", "Gold")
    assert split_item("Backup-Silver", known) == ("Backup", "Silver")


def test_item_without_separator():
    assert split_item("Orphan") == ("", "Orphan")


def test_tag_names_with_commas_are_kept():
    assert split_items("[<Owner-Smith, John>, <Env-Dev>]") == [
        "Owner-Smith, John",
        "Env-Dev",
    ]


def test_sanitize_key_segment():
    assert sanitize_key_segment("A|B:C") == "A/B_C"
    assert sanitize_key_segment("") == "Uncategorized"


def test_parse_list_parameter():
    assert parse_list_parameter(" a, b ,,c ") == ["a", "b", "c"]
    assert parse_list_parameter(None) == []
